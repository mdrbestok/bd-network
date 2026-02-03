"""
SQLite-based graph storage service.
Alternative to Neo4j for running without Docker.
"""
import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from datetime import datetime, date

from ..models.nodes import Company, Asset, Deal, Document, Trial
from ..models.edges import PartyTo, Covers, SupportedBy, Owns, HasTrial, SponsorsTrial, ParticipatesInTrial, Licenses, UsesAsComparator, EdgeEvidence

logger = logging.getLogger(__name__)


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

# Database file location
DB_PATH = Path(__file__).parent.parent.parent / "data" / "bdnetwork.db"


def _conditions_to_searchable(conditions: List[str]) -> str:
    """Normalize condition strings into one searchable string so variant phrasings match (e.g. 'Melanoma, Uveal' matches 'uveal melanoma')."""
    if not conditions:
        return ""
    combined = " ".join(c for c in conditions if isinstance(c, str))
    normalized = re.sub(r"[^\w\s]", " ", combined).lower()
    return " ".join(normalized.split())


class SQLiteService:
    """SQLite-based graph storage service."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize SQLite connection."""
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        logger.info(f"SQLite database initialized at {self.db_path}")
    
    @contextmanager
    def connection(self):
        """Get a database connection context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _init_schema(self):
        """Initialize database schema."""
        with self.connection() as conn:
            cursor = conn.cursor()
            
            # Nodes tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    company_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    aliases TEXT,
                    country TEXT,
                    public_flag INTEGER,
                    tickers TEXT,
                    cik TEXT,
                    status TEXT,
                    company_type TEXT,
                    evidence TEXT,
                    updated_at TEXT
                )
            """)
            
            # Add company_type column if it doesn't exist (migration)
            try:
                cursor.execute("ALTER TABLE companies ADD COLUMN company_type TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assets (
                    asset_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    synonyms TEXT,
                    modality TEXT,
                    targets TEXT,
                    indications TEXT,
                    stage_current TEXT,
                    modality_confidence REAL,
                    targets_confidence REAL,
                    evidence TEXT,
                    updated_at TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trials (
                    trial_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    phase TEXT,
                    status TEXT,
                    start_date TEXT,
                    completion_date TEXT,
                    interventions TEXT,
                    conditions TEXT,
                    sponsors TEXT,
                    collaborators TEXT,
                    enrollment INTEGER,
                    study_type TEXT,
                    brief_summary TEXT,
                    source_url TEXT,
                    evidence TEXT,
                    updated_at TEXT
                )
            """)
            # Searchable conditions: normalized text so "Melanoma, Uveal" matches term "uveal melanoma"
            try:
                cursor.execute("ALTER TABLE trials ADD COLUMN conditions_searchable TEXT")
            except sqlite3.OperationalError:
                pass
            # Backfill conditions_searchable from conditions for existing rows
            cursor.execute("SELECT trial_id, conditions FROM trials WHERE conditions_searchable IS NULL AND conditions IS NOT NULL")
            for row in cursor.fetchall():
                try:
                    cond_list = json.loads(row["conditions"]) if isinstance(row["conditions"], str) else row["conditions"]
                    searchable = _conditions_to_searchable(cond_list)
                    cursor.execute("UPDATE trials SET conditions_searchable = ? WHERE trial_id = ?", (searchable, row["trial_id"]))
                except (json.JSONDecodeError, TypeError):
                    pass

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    doc_type TEXT NOT NULL,
                    publisher TEXT,
                    url TEXT,
                    published_at TEXT,
                    retrieved_at TEXT,
                    text_hash TEXT,
                    updated_at TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS deals (
                    deal_id TEXT PRIMARY KEY,
                    deal_type TEXT NOT NULL,
                    announce_date TEXT,
                    summary TEXT,
                    status TEXT,
                    value_usd REAL,
                    evidence TEXT,
                    updated_at TEXT
                )
            """)
            
            # Edges tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sponsors_trial (
                    company_id TEXT,
                    trial_id TEXT,
                    role TEXT,
                    evidence TEXT,
                    PRIMARY KEY (company_id, trial_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS has_trial (
                    asset_id TEXT,
                    trial_id TEXT,
                    evidence TEXT,
                    PRIMARY KEY (asset_id, trial_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS owns (
                    company_id TEXT,
                    asset_id TEXT,
                    from_date TEXT,
                    to_date TEXT,
                    confidence REAL,
                    source TEXT,
                    is_current INTEGER,
                    evidence TEXT,
                    user_confirmed INTEGER DEFAULT 0,
                    PRIMARY KEY (company_id, asset_id)
                )
            """)
            try:
                cursor.execute("ALTER TABLE owns ADD COLUMN user_confirmed INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS asset_user_overrides (
                    asset_id TEXT PRIMARY KEY,
                    modality TEXT,
                    targets TEXT,
                    updated_at TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS party_to (
                    company_id TEXT,
                    deal_id TEXT,
                    role TEXT,
                    evidence TEXT,
                    PRIMARY KEY (company_id, deal_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS covers (
                    deal_id TEXT,
                    asset_id TEXT,
                    evidence TEXT,
                    PRIMARY KEY (deal_id, asset_id)
                )
            """)
            
            # New edge tables for corrected data model
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS participates_in_trial (
                    company_id TEXT,
                    trial_id TEXT,
                    role TEXT,
                    evidence TEXT,
                    PRIMARY KEY (company_id, trial_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS licenses (
                    company_id TEXT,
                    asset_id TEXT,
                    from_date TEXT,
                    to_date TEXT,
                    territory TEXT,
                    confidence REAL,
                    source TEXT,
                    evidence TEXT,
                    PRIMARY KEY (company_id, asset_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uses_as_comparator (
                    company_id TEXT,
                    asset_id TEXT,
                    trial_id TEXT,
                    evidence TEXT,
                    PRIMARY KEY (company_id, asset_id, trial_id)
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_name ON companies(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_asset_name ON assets(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trial_conditions ON trials(conditions)")
    
    def init_schema(self):
        """Public method to initialize schema (for compatibility)."""
        self._init_schema()
    
    # ==================== Node Operations ====================
    
    def upsert_company(self, company: Company) -> str:
        """Insert or update a Company."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO companies 
                (company_id, name, aliases, country, public_flag, tickers, cik, status, company_type, evidence, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company.company_id,
                company.name,
                json.dumps(company.aliases),
                company.country,
                1 if company.public_flag else 0 if company.public_flag is not None else None,
                json.dumps(company.tickers),
                company.cik,
                company.status,
                company.company_type,
                json.dumps([e.model_dump() for e in company.evidence], default=json_serial),
                datetime.utcnow().isoformat()
            ))
            return company.company_id
    
    def upsert_asset(self, asset: Asset) -> str:
        """Insert or update an Asset. User overrides (modality/targets) are preserved and not overwritten by ingestion."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT modality, targets FROM asset_user_overrides WHERE asset_id = ?", (asset.asset_id,))
            override = cursor.fetchone()
            modality = asset.modality
            targets = asset.targets
            if override:
                if override["modality"] is not None:
                    modality = override["modality"]
                if override["targets"]:
                    try:
                        targets = json.loads(override["targets"])
                    except (json.JSONDecodeError, TypeError):
                        pass
            cursor.execute("""
                INSERT OR REPLACE INTO assets
                (asset_id, name, synonyms, modality, targets, indications, stage_current, 
                 modality_confidence, targets_confidence, evidence, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                asset.asset_id,
                asset.name,
                json.dumps(asset.synonyms),
                modality,
                json.dumps(targets),
                json.dumps(asset.indications),
                asset.stage_current,
                asset.modality_confidence,
                asset.targets_confidence,
                json.dumps([e.model_dump() for e in asset.evidence], default=json_serial),
                datetime.utcnow().isoformat()
            ))
            return asset.asset_id
    
    def upsert_trial(self, trial: Trial) -> str:
        """Insert or update a Trial."""
        conditions_json = json.dumps(trial.conditions)
        conditions_searchable = _conditions_to_searchable(trial.conditions or [])
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO trials
                (trial_id, title, phase, status, start_date, completion_date, interventions,
                 conditions, conditions_searchable, sponsors, collaborators, enrollment, study_type, brief_summary,
                 source_url, evidence, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trial.trial_id,
                trial.title,
                trial.phase,
                trial.status,
                str(trial.start_date) if trial.start_date else None,
                str(trial.completion_date) if trial.completion_date else None,
                json.dumps(trial.interventions),
                conditions_json,
                conditions_searchable,
                json.dumps(trial.sponsors),
                json.dumps(trial.collaborators),
                trial.enrollment,
                trial.study_type,
                trial.brief_summary,
                trial.source_url,
                json.dumps([e.model_dump() for e in trial.evidence], default=json_serial),
                datetime.utcnow().isoformat()
            ))
            return trial.trial_id
    
    def upsert_document(self, doc: Document) -> str:
        """Insert or update a Document."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO documents
                (doc_id, doc_type, publisher, url, published_at, retrieved_at, text_hash, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc.doc_id,
                doc.doc_type,
                doc.publisher,
                doc.url,
                str(doc.published_at) if doc.published_at else None,
                str(doc.retrieved_at),
                doc.text_hash,
                datetime.utcnow().isoformat()
            ))
            return doc.doc_id
    
    def upsert_deal(self, deal: Deal) -> str:
        """Insert or update a Deal."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO deals
                (deal_id, deal_type, announce_date, summary, status, value_usd, evidence, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                deal.deal_id,
                deal.deal_type,
                str(deal.announce_date) if deal.announce_date else None,
                deal.summary,
                deal.status,
                deal.value_usd,
                json.dumps([e.model_dump() for e in deal.evidence], default=json_serial),
                datetime.utcnow().isoformat()
            ))
            return deal.deal_id
    
    # ==================== Edge Operations ====================
    
    def create_sponsors_trial(self, rel: SponsorsTrial):
        """Create SPONSORS_TRIAL relationship."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sponsors_trial (company_id, trial_id, role, evidence)
                VALUES (?, ?, ?, ?)
            """, (
                rel.company_id,
                rel.trial_id,
                rel.role,
                json.dumps([e.model_dump() for e in rel.evidence], default=json_serial)
            ))
    
    def create_has_trial(self, rel: HasTrial):
        """Create HAS_TRIAL relationship."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO has_trial (asset_id, trial_id, evidence)
                VALUES (?, ?, ?)
            """, (
                rel.asset_id,
                rel.trial_id,
                json.dumps([e.model_dump() for e in rel.evidence], default=json_serial)
            ))
    
    def create_owns(self, rel: Owns, user_confirmed: bool = False):
        """Create or update OWNS relationship. If user_confirmed=True, preserves existing user_confirmed=1."""
        with self.connection() as conn:
            cursor = conn.cursor()
            if user_confirmed:
                cursor.execute("""
                    INSERT INTO owns 
                    (company_id, asset_id, from_date, to_date, confidence, source, is_current, evidence, user_confirmed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                    ON CONFLICT(company_id, asset_id) DO UPDATE SET
                    confidence = excluded.confidence,
                    source = excluded.source,
                    user_confirmed = 1,
                    evidence = excluded.evidence
                """, (
                    rel.company_id,
                    rel.asset_id,
                    str(rel.from_date) if rel.from_date else None,
                    str(rel.to_date) if rel.to_date else None,
                    rel.confidence,
                    rel.source,
                    1 if rel.is_current else 0,
                    json.dumps([e.model_dump() for e in rel.evidence], default=json_serial)
                ))
            else:
                # Do not overwrite if existing row has user_confirmed=1
                cursor.execute("SELECT user_confirmed FROM owns WHERE company_id = ? AND asset_id = ?",
                               (rel.company_id, rel.asset_id))
                row = cursor.fetchone()
                if row and row[0]:
                    return  # Skip overwriting user-confirmed ownership
                cursor.execute("""
                    INSERT OR REPLACE INTO owns 
                    (company_id, asset_id, from_date, to_date, confidence, source, is_current, evidence, user_confirmed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    rel.company_id,
                    rel.asset_id,
                    str(rel.from_date) if rel.from_date else None,
                    str(rel.to_date) if rel.to_date else None,
                    rel.confidence,
                    rel.source,
                    1 if rel.is_current else 0,
                    json.dumps([e.model_dump() for e in rel.evidence], default=json_serial)
                ))

    def _clear_company_asset_relationships(self, company_id: str, asset_id: str, cursor) -> None:
        """Remove all existing relationships between a company and asset (used before setting a new one)."""
        cursor.execute("DELETE FROM owns WHERE company_id = ? AND asset_id = ?", (company_id, asset_id))
        cursor.execute("DELETE FROM licenses WHERE company_id = ? AND asset_id = ?", (company_id, asset_id))
        cursor.execute("DELETE FROM uses_as_comparator WHERE company_id = ? AND asset_id = ?", (company_id, asset_id))

    def upsert_owns_user_confirmed(self, company_id: str, asset_id: str, confidence: float = 1.0) -> None:
        """Set or confirm ownership of an asset by a company. Replaces any other relationship types."""
        with self.connection() as conn:
            cursor = conn.cursor()
            # Remove any other relationship types first
            self._clear_company_asset_relationships(company_id, asset_id, cursor)
            
            rel = Owns(
                company_id=company_id,
                asset_id=asset_id,
                confidence=confidence,
                source="user_confirmed",
                is_current=True,
                evidence=[EdgeEvidence(source_type="user_confirmed", confidence=confidence)]
            )
            cursor.execute("""
                INSERT INTO owns (company_id, asset_id, from_date, to_date, confidence, source, is_current, evidence, user_confirmed)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, 1)
                ON CONFLICT(company_id, asset_id) DO UPDATE SET confidence = ?, source = 'user_confirmed', user_confirmed = 1, evidence = ?
            """, (
                rel.company_id,
                rel.asset_id,
                None,
                None,
                rel.confidence,
                rel.source,
                json.dumps([e.model_dump() for e in rel.evidence], default=json_serial),
                rel.confidence,
                json.dumps([e.model_dump() for e in rel.evidence], default=json_serial)
            ))

    def upsert_licenses_user_confirmed(self, company_id: str, asset_id: str, confidence: float = 1.0) -> None:
        """Set a license relationship. Replaces any other relationship types."""
        with self.connection() as conn:
            cursor = conn.cursor()
            # Remove any other relationship types first
            self._clear_company_asset_relationships(company_id, asset_id, cursor)
            
            cursor.execute("""
                INSERT INTO licenses (company_id, asset_id, from_date, to_date, territory, confidence, source, evidence)
                VALUES (?, ?, NULL, NULL, NULL, ?, 'user_confirmed', ?)
                ON CONFLICT(company_id, asset_id) DO UPDATE SET confidence = ?, source = 'user_confirmed', evidence = ?
            """, (
                company_id,
                asset_id,
                confidence,
                json.dumps([{"source_type": "user_confirmed", "confidence": confidence}]),
                confidence,
                json.dumps([{"source_type": "user_confirmed", "confidence": confidence}])
            ))

    def upsert_uses_as_comparator_user_confirmed(self, company_id: str, asset_id: str, trial_id: str = "user_set") -> None:
        """Set a uses_as_comparator relationship. Replaces any other relationship types."""
        with self.connection() as conn:
            cursor = conn.cursor()
            # Remove any other relationship types first
            self._clear_company_asset_relationships(company_id, asset_id, cursor)
            
            cursor.execute("""
                INSERT INTO uses_as_comparator (company_id, asset_id, trial_id, evidence)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(company_id, asset_id, trial_id) DO UPDATE SET evidence = ?
            """, (
                company_id,
                asset_id,
                trial_id,
                json.dumps([{"source_type": "user_confirmed", "confidence": 1.0}]),
                json.dumps([{"source_type": "user_confirmed", "confidence": 1.0}])
            ))
    
    def create_party_to(self, rel: PartyTo):
        """Create PARTY_TO relationship."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO party_to (company_id, deal_id, role, evidence)
                VALUES (?, ?, ?, ?)
            """, (
                rel.company_id,
                rel.deal_id,
                rel.role,
                json.dumps([e.model_dump() for e in rel.evidence], default=json_serial)
            ))
    
    def create_covers(self, rel: Covers):
        """Create COVERS relationship."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO covers (deal_id, asset_id, evidence)
                VALUES (?, ?, ?)
            """, (
                rel.deal_id,
                rel.asset_id,
                json.dumps([e.model_dump() for e in rel.evidence], default=json_serial)
            ))
    
    def create_participates_in_trial(self, rel: ParticipatesInTrial):
        """Create PARTICIPATES_IN_TRIAL relationship (for sites, investigators, academic centers)."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO participates_in_trial (company_id, trial_id, role, evidence)
                VALUES (?, ?, ?, ?)
            """, (
                rel.company_id,
                rel.trial_id,
                rel.role,
                json.dumps([e.model_dump() for e in rel.evidence], default=json_serial)
            ))
    
    def create_licenses(self, rel: Licenses):
        """Create LICENSES relationship."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO licenses 
                (company_id, asset_id, from_date, to_date, territory, confidence, source, evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rel.company_id,
                rel.asset_id,
                str(rel.from_date) if rel.from_date else None,
                str(rel.to_date) if rel.to_date else None,
                rel.territory,
                rel.confidence,
                rel.source,
                json.dumps([e.model_dump() for e in rel.evidence], default=json_serial)
            ))
    
    def create_uses_as_comparator(self, rel: UsesAsComparator):
        """Create USES_AS_COMPARATOR relationship (for comparator drugs in trials)."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO uses_as_comparator (company_id, asset_id, trial_id, evidence)
                VALUES (?, ?, ?, ?)
            """, (
                rel.company_id,
                rel.asset_id,
                rel.trial_id,
                json.dumps([e.model_dump() for e in rel.evidence], default=json_serial)
            ))
    
    # ==================== Query Operations ====================
    
    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert a sqlite3.Row to a dictionary with JSON parsing."""
        if row is None:
            return None
        d = dict(row)
        # Parse JSON fields
        for key in ['aliases', 'synonyms', 'targets', 'indications', 'interventions', 
                    'conditions', 'sponsors', 'collaborators', 'tickers', 'evidence']:
            if key in d and d[key]:
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d
    
    def get_company(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Get a company by ID with related data."""
        with self.connection() as conn:
            cursor = conn.cursor()
            
            # Get company
            cursor.execute("SELECT * FROM companies WHERE company_id = ?", (company_id,))
            company_row = cursor.fetchone()
            if not company_row:
                return None
            
            company = self._row_to_dict(company_row)
            
            # Get trials
            cursor.execute("""
                SELECT t.*, st.role 
                FROM trials t
                JOIN sponsors_trial st ON t.trial_id = st.trial_id
                WHERE st.company_id = ?
            """, (company_id,))
            company['trials'] = [self._row_to_dict(row) for row in cursor.fetchall()]
            
            # Get assets
            cursor.execute("""
                SELECT a.*, o.confidence, o.source as ownership_source
                FROM assets a
                JOIN owns o ON a.asset_id = o.asset_id
                WHERE o.company_id = ?
            """, (company_id,))
            company['assets'] = []
            for row in cursor.fetchall():
                asset = self._row_to_dict(row)
                asset['ownership'] = {
                    'confidence': row['confidence'],
                    'source': row['ownership_source']
                }
                company['assets'].append(asset)
            
            return company
    
    def get_asset_overrides(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get user override for an asset (modality, targets). Returns None if no override."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT modality, targets FROM asset_user_overrides WHERE asset_id = ?",
                (asset_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "modality": row["modality"],
                "targets": json.loads(row["targets"]) if row["targets"] else []
            }

    def set_asset_override(self, asset_id: str, modality: Optional[str] = None, targets: Optional[List[str]] = None) -> None:
        """Set user override for asset modality/targets. ClinicalTrials.gov ingestion will not overwrite these."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT modality, targets FROM asset_user_overrides WHERE asset_id = ?", (asset_id,))
            r = cursor.fetchone()
            cur_mod = r["modality"] if r else None
            cur_tgt = json.loads(r["targets"]) if r and r["targets"] else []
            final_mod = modality if modality is not None else cur_mod
            final_tgt = targets if targets is not None else cur_tgt
            cursor.execute("""
                INSERT INTO asset_user_overrides (asset_id, modality, targets, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(asset_id) DO UPDATE SET modality = ?, targets = ?, updated_at = ?
            """, (asset_id, final_mod, json.dumps(final_tgt), datetime.utcnow().isoformat(), final_mod, json.dumps(final_tgt), datetime.utcnow().isoformat()))

    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get an asset by ID with related data. Merges user overrides for modality/targets."""
        with self.connection() as conn:
            cursor = conn.cursor()
            
            # Get asset
            cursor.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,))
            asset_row = cursor.fetchone()
            if not asset_row:
                return None
            
            asset = self._row_to_dict(asset_row)
            
            # Apply user overrides
            cursor.execute("SELECT modality, targets FROM asset_user_overrides WHERE asset_id = ?", (asset_id,))
            override_row = cursor.fetchone()
            if override_row:
                if override_row["modality"] is not None:
                    asset["modality"] = override_row["modality"]
                    asset["modality_user_confirmed"] = True
                if override_row["targets"]:
                    try:
                        asset["targets"] = json.loads(override_row["targets"])
                        asset["targets_user_confirmed"] = True
                    except (json.JSONDecodeError, TypeError):
                        pass
            
            # Get trials
            cursor.execute("""
                SELECT t.*
                FROM trials t
                JOIN has_trial ht ON t.trial_id = ht.trial_id
                WHERE ht.asset_id = ?
            """, (asset_id,))
            asset['trials'] = [self._row_to_dict(row) for row in cursor.fetchall()]
            
            # Get all company relationships for this asset
            # 1. Owners
            cursor.execute("""
                SELECT c.*, o.confidence, o.source as ownership_source, o.user_confirmed
                FROM companies c
                JOIN owns o ON c.company_id = o.company_id
                WHERE o.asset_id = ?
            """, (asset_id,))
            asset['owners'] = []
            for row in cursor.fetchall():
                owner = self._row_to_dict(row)
                owner['relationship'] = {
                    'type': 'owns',
                    'confidence': row['confidence'],
                    'source': row['ownership_source'],
                    'user_confirmed': bool(row['user_confirmed']) if 'user_confirmed' in row.keys() and row['user_confirmed'] else False
                }
                # Keep legacy 'ownership' key for backwards compatibility
                owner['ownership'] = owner['relationship']
                asset['owners'].append(owner)
            
            # 2. Licensees
            cursor.execute("""
                SELECT c.*, l.confidence, l.source, l.territory
                FROM companies c
                JOIN licenses l ON c.company_id = l.company_id
                WHERE l.asset_id = ?
            """, (asset_id,))
            asset['licensees'] = []
            for row in cursor.fetchall():
                licensee = self._row_to_dict(row)
                licensee['relationship'] = {
                    'type': 'licenses',
                    'confidence': row['confidence'],
                    'source': row['source'],
                    'territory': row['territory']
                }
                asset['licensees'].append(licensee)
            
            # 3. Comparator users
            cursor.execute("""
                SELECT c.*, u.trial_id
                FROM companies c
                JOIN uses_as_comparator u ON c.company_id = u.company_id
                WHERE u.asset_id = ?
            """, (asset_id,))
            asset['comparator_users'] = []
            for row in cursor.fetchall():
                user = self._row_to_dict(row)
                user['relationship'] = {
                    'type': 'uses_as_comparator',
                    'trial_id': row['trial_id']
                }
                asset['comparator_users'].append(user)
            
            # 4. Sites that participate in trials for this asset
            cursor.execute("""
                SELECT DISTINCT c.*
                FROM companies c
                JOIN participates_in_trial pit ON c.company_id = pit.company_id
                JOIN has_trial ht ON pit.trial_id = ht.trial_id
                WHERE ht.asset_id = ?
            """, (asset_id,))
            asset['trial_sites'] = []
            for row in cursor.fetchall():
                site = self._row_to_dict(row)
                site['relationship'] = {
                    'type': 'participates_in_trial'
                }
                asset['trial_sites'].append(site)
            
            # Also get sites from legacy sponsors_trial table (non-industry)
            cursor.execute("""
                SELECT DISTINCT c.*
                FROM companies c
                JOIN sponsors_trial st ON c.company_id = st.company_id
                JOIN has_trial ht ON st.trial_id = ht.trial_id
                WHERE ht.asset_id = ? AND c.company_type != 'industry'
            """, (asset_id,))
            seen_site_ids = {s['company_id'] for s in asset['trial_sites']}
            for row in cursor.fetchall():
                site = self._row_to_dict(row)
                if site['company_id'] not in seen_site_ids:
                    site['relationship'] = {
                        'type': 'participates_in_trial'
                    }
                    asset['trial_sites'].append(site)
            
            # Combined list of all connected companies with their relationship types
            asset['connected_companies'] = []
            for owner in asset['owners']:
                asset['connected_companies'].append({**owner, 'relationship_type': 'owns'})
            for licensee in asset['licensees']:
                asset['connected_companies'].append({**licensee, 'relationship_type': 'licenses'})
            for user in asset['comparator_users']:
                asset['connected_companies'].append({**user, 'relationship_type': 'uses_as_comparator'})
            for site in asset['trial_sites']:
                asset['connected_companies'].append({**site, 'relationship_type': 'participates_in_trial'})
            
            return asset
    
    def get_trial(self, trial_id: str) -> Optional[Dict[str, Any]]:
        """Get a trial by ID with related data."""
        with self.connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM trials WHERE trial_id = ?", (trial_id,))
            trial_row = cursor.fetchone()
            if not trial_row:
                return None
            
            trial = self._row_to_dict(trial_row)
            
            # Get sponsors
            cursor.execute("""
                SELECT c.*, st.role
                FROM companies c
                JOIN sponsors_trial st ON c.company_id = st.company_id
                WHERE st.trial_id = ?
            """, (trial_id,))
            trial['sponsors_detail'] = [self._row_to_dict(row) for row in cursor.fetchall()]
            
            # Get assets
            cursor.execute("""
                SELECT a.*
                FROM assets a
                JOIN has_trial ht ON a.asset_id = ht.asset_id
                WHERE ht.trial_id = ?
            """, (trial_id,))
            trial['assets'] = [self._row_to_dict(row) for row in cursor.fetchall()]
            
            return trial
    
    def search_all(self, query_text: str, limit: int = 20) -> Dict[str, List[Dict]]:
        """Search across all node types."""
        results = {"companies": [], "assets": [], "trials": []}
        query_pattern = f"%{query_text}%"
        
        with self.connection() as conn:
            cursor = conn.cursor()
            
            # Search companies
            cursor.execute("""
                SELECT *, 1.0 as score FROM companies 
                WHERE name LIKE ? OR aliases LIKE ?
                LIMIT ?
            """, (query_pattern, query_pattern, limit))
            results["companies"] = [self._row_to_dict(row) for row in cursor.fetchall()]
            
            # Search assets
            cursor.execute("""
                SELECT *, 1.0 as score FROM assets 
                WHERE name LIKE ? OR synonyms LIKE ?
                LIMIT ?
            """, (query_pattern, query_pattern, limit))
            results["assets"] = [self._row_to_dict(row) for row in cursor.fetchall()]
            
            # Search trials
            cursor.execute("""
                SELECT *, 1.0 as score FROM trials 
                WHERE title LIKE ? OR trial_id LIKE ?
                LIMIT ?
            """, (query_pattern, query_pattern, limit))
            results["trials"] = [self._row_to_dict(row) for row in cursor.fetchall()]
        
        return results
    
    def _trial_matches_status_filter(self, trial: Dict[str, Any], trial_filter: str) -> bool:
        """Return True if trial should be included for the given trial_filter."""
        if trial_filter == "none":
            return False
        if trial_filter == "all":
            return True
        # Normalize status: "Active, not recruiting" or "ACTIVE_NOT_RECRUITING" -> ACTIVE_NOT_RECRUITING
        raw = (trial.get("status") or "").strip()
        status = raw.upper().replace(",", "").replace(" ", "_").replace("-", "_")
        if trial_filter == "recruiting":
            return status in ("RECRUITING", "NOT_YET_RECRUITING")
        if trial_filter == "active_not_recruiting":
            return status == "ACTIVE_NOT_RECRUITING"
        return True

    def get_indication_graph(
        self,
        indication_terms: List[str],
        depth: int = 2,
        phase_filter: Optional[List[str]] = None,
        modality_filter: Optional[List[str]] = None,
        include_trials: bool = False,
        trial_filter: Optional[str] = None,
        limit: int = 500
    ) -> Dict[str, Any]:
        """Get the network graph for an indication. trial_filter: none, recruiting, active_not_recruiting, all."""
        nodes = []
        edges = []
        seen_nodes = set()
        seen_edges = set()
        # Support legacy include_trials; trial_filter overrides
        if trial_filter is not None:
            show_trials = trial_filter != "none"
        else:
            show_trials = include_trials

        with self.connection() as conn:
            cursor = conn.cursor()
            # Match if any indication term matches: for each term, all words in the term must appear in conditions_searchable
            # (so "Melanoma, Uveal" matches term "uveal melanoma" without adding config for every variant)
            searchable_col = "LOWER(COALESCE(conditions_searchable, ''))"
            term_clauses = []
            term_params: List[str] = []
            for term in indication_terms:
                words = [w for w in term.lower().split() if w]
                if not words:
                    continue
                term_clauses.append(" AND ".join([f"{searchable_col} LIKE ?" for _ in words]))
                term_params.extend([f"%{w}%" for w in words])
            where_sql = " OR ".join([f"({c})" for c in term_clauses]) if term_clauses else "1=0"
            term_params.append(limit)
            # Find trials matching any indication term
            cursor.execute(f"""
                SELECT * FROM trials
                WHERE {where_sql}
                LIMIT ?
            """, term_params)
            
            trial_rows = cursor.fetchall()
            
            for trial_row in trial_rows:
                trial = self._row_to_dict(trial_row)
                trial_id = trial['trial_id']
                
                # Apply phase filter
                if phase_filter and trial.get('phase') not in phase_filter:
                    continue
                
                # Include this trial node/edges only if it matches the status filter
                trial_in_scope = show_trials and (not trial_filter or trial_filter == "all" or self._trial_matches_status_filter(trial, trial_filter))
                
                # Add trial node if including trials and trial matches filter
                if trial_in_scope and trial_id not in seen_nodes:
                    seen_nodes.add(trial_id)
                    nodes.append({
                        "id": trial_id,
                        "type": "trial",
                        "label": trial.get('title', trial_id)[:50],
                        "data": trial
                    })
                
                # Get sites/investigators participating in this trial (non-industry)
                cursor.execute("""
                    SELECT c.*, pit.role
                    FROM companies c
                    JOIN participates_in_trial pit ON c.company_id = pit.company_id
                    WHERE pit.trial_id = ?
                """, (trial_id,))
                
                for company_row in cursor.fetchall():
                    company = self._row_to_dict(company_row)
                    company_id = company['company_id']
                    
                    if company_id not in seen_nodes:
                        seen_nodes.add(company_id)
                        nodes.append({
                            "id": company_id,
                            "type": "company",
                            "label": company.get('name', company_id),
                            "data": company
                        })
                    
                    if trial_in_scope:
                        edge_id = f"{company_id}-participates-{trial_id}"
                        if edge_id not in seen_edges:
                            seen_edges.add(edge_id)
                            edges.append({
                                "id": edge_id,
                                "source": company_id,
                                "target": trial_id,
                                "type": "PARTICIPATES_IN_TRIAL",
                                "label": company_row['role'] or "site",
                                "data": {"role": company_row['role']}
                            })
                
                # Also check old sponsors_trial for backwards compatibility during migration
                cursor.execute("""
                    SELECT c.*, st.role
                    FROM companies c
                    JOIN sponsors_trial st ON c.company_id = st.company_id
                    WHERE st.trial_id = ?
                """, (trial_id,))
                
                for company_row in cursor.fetchall():
                    company = self._row_to_dict(company_row)
                    company_id = company['company_id']
                    company_type = company.get('company_type', 'industry')
                    
                    if company_id not in seen_nodes:
                        seen_nodes.add(company_id)
                        nodes.append({
                            "id": company_id,
                            "type": "company",
                            "label": company.get('name', company_id),
                            "data": company
                        })
                    
                    # Only create SPONSORS_TRIAL edge for non-industry (sites) - industry connects through assets
                    if trial_in_scope and company_type != 'industry':
                        edge_id = f"{company_id}-sponsors-{trial_id}"
                        if edge_id not in seen_edges:
                            seen_edges.add(edge_id)
                            edges.append({
                                "id": edge_id,
                                "source": company_id,
                                "target": trial_id,
                                "type": "SPONSORS_TRIAL",
                                "label": company_row['role'] or "site",
                                "data": {"role": company_row['role']}
                            })
                
                # Industry sponsors are found through asset ownership, not direct trial links
                lead_sponsor_ids = []
                cursor.execute("""
                    SELECT st.company_id
                    FROM sponsors_trial st
                    JOIN companies c ON c.company_id = st.company_id
                    WHERE st.trial_id = ? AND st.role = 'lead_sponsor'
                    AND COALESCE(c.company_type, 'industry') = 'industry'
                """, (trial_id,))
                for row in cursor.fetchall():
                    lead_sponsor_ids.append(row['company_id'])
                
                # Get assets linked to this trial
                cursor.execute("""
                    SELECT a.*
                    FROM assets a
                    JOIN has_trial ht ON a.asset_id = ht.asset_id
                    WHERE ht.trial_id = ?
                """, (trial_id,))
                
                for asset_row in cursor.fetchall():
                    asset = self._row_to_dict(asset_row)
                    asset_id = asset['asset_id']
                    
                    # Apply modality filter
                    if modality_filter and asset.get('modality') not in modality_filter:
                        continue
                    
                    if asset_id not in seen_nodes:
                        seen_nodes.add(asset_id)
                        nodes.append({
                            "id": asset_id,
                            "type": "asset",
                            "label": asset.get('name', asset_id),
                            "data": asset
                        })
                    
                    if trial_in_scope:
                        edge_id = f"{asset_id}-has_trial-{trial_id}"
                        if edge_id not in seen_edges:
                            seen_edges.add(edge_id)
                            edges.append({
                                "id": edge_id,
                                "source": asset_id,
                                "target": trial_id,
                                "type": "HAS_TRIAL",
                                "label": "trial",
                                "data": {}
                            })
                    
                    # Get explicit owners for this asset so we don't add DEVELOPS for them (OWNS takes precedence)
                    owner_ids_for_asset = set()
                    cursor.execute("""
                        SELECT company_id FROM owns WHERE asset_id = ?
                    """, (asset_id,))
                    for row in cursor.fetchall():
                        owner_ids_for_asset.add(row['company_id'])
                    
                    # Create DEVELOPS only from industry lead sponsor to asset; skip if company already OWNS (use OWNS in graph)
                    for sponsor_id in lead_sponsor_ids:
                        if sponsor_id in owner_ids_for_asset:
                            continue
                        edge_id = f"{sponsor_id}-develops-{asset_id}"
                        if edge_id not in seen_edges:
                            seen_edges.add(edge_id)
                            edges.append({
                                "id": edge_id,
                                "source": sponsor_id,
                                "target": asset_id,
                                "type": "DEVELOPS",
                                "label": "develops",
                                "data": {
                                    "via_trial": trial_id,
                                    "inferred": True
                                }
                            })
                    
                    # Also get explicit ownership for this asset (may be different company)
                    cursor.execute("""
                        SELECT c.*, o.confidence, o.source
                        FROM companies c
                        JOIN owns o ON c.company_id = o.company_id
                        WHERE o.asset_id = ?
                    """, (asset_id,))
                    
                    for owner_row in cursor.fetchall():
                        owner = self._row_to_dict(owner_row)
                        owner_id = owner['company_id']
                        
                        if owner_id not in seen_nodes:
                            seen_nodes.add(owner_id)
                            nodes.append({
                                "id": owner_id,
                                "type": "company",
                                "label": owner.get('name', owner_id),
                                "data": owner
                            })
                        
                        edge_id = f"{owner_id}-owns-{asset_id}"
                        if edge_id not in seen_edges:
                            seen_edges.add(edge_id)
                            edges.append({
                                "id": edge_id,
                                "source": owner_id,
                                "target": asset_id,
                                "type": "OWNS",
                                "label": "owns",
                                "data": {
                                    "confidence": owner_row['confidence'],
                                    "source": owner_row['source']
                                }
                            })
        
        return {"nodes": nodes, "edges": edges}
    
    def get_landscape_stats(self, indication_terms: List[str]) -> Dict[str, Any]:
        """Get landscape statistics for an indication."""
        stats = {
            "assets_by_phase": [],
            "sponsors_by_trial_count": [],
            "modalities": [],
            "targets": [],
            "total_trials": 0,
            "total_assets": 0,
            "total_companies": 0
        }
        
        # Same "all words in term" matching as get_indication_graph (conditions_searchable)
        searchable_col = "LOWER(COALESCE(conditions_searchable, ''))"
        searchable_col_t = "LOWER(COALESCE(t.conditions_searchable, ''))"
        term_clauses = []
        term_clauses_t = []
        term_params: List[str] = []
        for term in indication_terms:
            words = [w for w in term.lower().split() if w]
            if not words:
                continue
            term_clauses.append(" AND ".join([f"{searchable_col} LIKE ?" for _ in words]))
            term_clauses_t.append(" AND ".join([f"{searchable_col_t} LIKE ?" for _ in words]))
            term_params.extend([f"%{w}%" for w in words])
        where_sql = " OR ".join([f"({c})" for c in term_clauses]) if term_clauses else "1=0"
        where_sql_t = " OR ".join([f"({c})" for c in term_clauses_t]) if term_clauses_t else "1=0"

        with self.connection() as conn:
            cursor = conn.cursor()
            # Trials by phase
            cursor.execute(f"""
                SELECT phase, COUNT(*) as count
                FROM trials
                WHERE {where_sql}
                GROUP BY phase
                ORDER BY count DESC
            """, term_params)
            stats["assets_by_phase"] = [
                {"phase": row['phase'], "count": row['count']}
                for row in cursor.fetchall() if row['phase']
            ]
            # Sponsors by trial count
            cursor.execute(f"""
                SELECT c.name as sponsor, c.company_id as id, COUNT(st.trial_id) as trial_count
                FROM companies c
                JOIN sponsors_trial st ON c.company_id = st.company_id
                JOIN trials t ON st.trial_id = t.trial_id
                WHERE {where_sql_t}
                GROUP BY c.company_id
                ORDER BY trial_count DESC
                LIMIT 20
            """, term_params)
            stats["sponsors_by_trial_count"] = [
                {"sponsor": row['sponsor'], "id": row['id'], "trial_count": row['trial_count']}
                for row in cursor.fetchall()
            ]
            # Modalities
            cursor.execute(f"""
                SELECT a.modality, COUNT(DISTINCT a.asset_id) as count
                FROM assets a
                JOIN has_trial ht ON a.asset_id = ht.asset_id
                JOIN trials t ON ht.trial_id = t.trial_id
                WHERE ({where_sql_t}) AND a.modality IS NOT NULL
                GROUP BY a.modality
                ORDER BY count DESC
            """, term_params)
            stats["modalities"] = [
                {"modality": row['modality'], "count": row['count']}
                for row in cursor.fetchall()
            ]
            # Totals
            cursor.execute(f"""
                SELECT COUNT(DISTINCT t.trial_id) as trials
                FROM trials t
                WHERE {where_sql_t}
            """, term_params)
            stats["total_trials"] = cursor.fetchone()['trials']
            cursor.execute(f"""
                SELECT COUNT(DISTINCT a.asset_id) as assets
                FROM assets a
                JOIN has_trial ht ON a.asset_id = ht.asset_id
                JOIN trials t ON ht.trial_id = t.trial_id
                WHERE {where_sql_t}
            """, term_params)
            stats["total_assets"] = cursor.fetchone()['assets']
            cursor.execute(f"""
                SELECT COUNT(DISTINCT c.company_id) as companies
                FROM companies c
                JOIN sponsors_trial st ON c.company_id = st.company_id
                JOIN trials t ON st.trial_id = t.trial_id
                WHERE {where_sql_t}
            """, term_params)
            stats["total_companies"] = cursor.fetchone()['companies']
        
        return stats
    
    def get_stats(self) -> Dict[str, int]:
        """Get overall database statistics."""
        with self.connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM companies")
            companies = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM assets")
            assets = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM trials")
            trials = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM deals")
            deals = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM documents")
            documents = cursor.fetchone()[0]
            
            return {
                "companies": companies,
                "assets": assets,
                "trials": trials,
                "deals": deals,
                "documents": documents
            }
    
    def clear_database(self):
        """Clear all data."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sponsors_trial")
            cursor.execute("DELETE FROM has_trial")
            cursor.execute("DELETE FROM owns")
            cursor.execute("DELETE FROM party_to")
            cursor.execute("DELETE FROM covers")
            cursor.execute("DELETE FROM participates_in_trial")
            cursor.execute("DELETE FROM licenses")
            cursor.execute("DELETE FROM uses_as_comparator")
            cursor.execute("DELETE FROM companies")
            cursor.execute("DELETE FROM assets")
            cursor.execute("DELETE FROM trials")
            cursor.execute("DELETE FROM documents")
            cursor.execute("DELETE FROM deals")
        logger.info("Database cleared")
    
    def close(self):
        """No-op for SQLite (connections are per-operation)."""
        pass


# Singleton instance
_sqlite_service: Optional[SQLiteService] = None


def get_sqlite_service() -> SQLiteService:
    """Get or create SQLite service singleton."""
    global _sqlite_service
    if _sqlite_service is None:
        _sqlite_service = SQLiteService()
    return _sqlite_service
