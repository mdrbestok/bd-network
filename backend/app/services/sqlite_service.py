"""
SQLite-based graph storage service.
Alternative to Neo4j for running without Docker.
"""
import json
import logging
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from datetime import datetime, date

from ..models.nodes import Company, Asset, Deal, Document, Trial
from ..models.edges import PartyTo, Covers, SupportedBy, Owns, HasTrial, SponsorsTrial

logger = logging.getLogger(__name__)


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

# Database file location
DB_PATH = Path(__file__).parent.parent.parent / "data" / "bdnetwork.db"


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
                    PRIMARY KEY (company_id, asset_id)
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
        """Insert or update an Asset."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO assets
                (asset_id, name, synonyms, modality, targets, indications, stage_current, 
                 modality_confidence, targets_confidence, evidence, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                asset.asset_id,
                asset.name,
                json.dumps(asset.synonyms),
                asset.modality,
                json.dumps(asset.targets),
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
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO trials
                (trial_id, title, phase, status, start_date, completion_date, interventions,
                 conditions, sponsors, collaborators, enrollment, study_type, brief_summary,
                 source_url, evidence, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trial.trial_id,
                trial.title,
                trial.phase,
                trial.status,
                str(trial.start_date) if trial.start_date else None,
                str(trial.completion_date) if trial.completion_date else None,
                json.dumps(trial.interventions),
                json.dumps(trial.conditions),
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
    
    def create_owns(self, rel: Owns):
        """Create OWNS relationship."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO owns 
                (company_id, asset_id, from_date, to_date, confidence, source, is_current, evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
    
    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get an asset by ID with related data."""
        with self.connection() as conn:
            cursor = conn.cursor()
            
            # Get asset
            cursor.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,))
            asset_row = cursor.fetchone()
            if not asset_row:
                return None
            
            asset = self._row_to_dict(asset_row)
            
            # Get trials
            cursor.execute("""
                SELECT t.*
                FROM trials t
                JOIN has_trial ht ON t.trial_id = ht.trial_id
                WHERE ht.asset_id = ?
            """, (asset_id,))
            asset['trials'] = [self._row_to_dict(row) for row in cursor.fetchall()]
            
            # Get owners
            cursor.execute("""
                SELECT c.*, o.confidence, o.source as ownership_source
                FROM companies c
                JOIN owns o ON c.company_id = o.company_id
                WHERE o.asset_id = ?
            """, (asset_id,))
            asset['owners'] = []
            for row in cursor.fetchall():
                owner = self._row_to_dict(row)
                owner['ownership'] = {
                    'confidence': row['confidence'],
                    'source': row['ownership_source']
                }
                asset['owners'].append(owner)
            
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
    
    def get_indication_graph(
        self,
        indication_terms: List[str],
        depth: int = 2,
        phase_filter: Optional[List[str]] = None,
        modality_filter: Optional[List[str]] = None,
        include_trials: bool = False,
        limit: int = 500
    ) -> Dict[str, Any]:
        """Get the network graph for an indication."""
        nodes = []
        edges = []
        seen_nodes = set()
        seen_edges = set()
        
        with self.connection() as conn:
            cursor = conn.cursor()
            
            # Build query to match ANY of the indication terms
            term_conditions = " OR ".join(["LOWER(conditions) LIKE ?" for _ in indication_terms])
            term_params = [f"%{term.lower()}%" for term in indication_terms]
            
            # Find trials matching any indication term
            cursor.execute(f"""
                SELECT * FROM trials 
                WHERE {term_conditions}
                LIMIT ?
            """, (*term_params, limit))
            
            trial_rows = cursor.fetchall()
            
            for trial_row in trial_rows:
                trial = self._row_to_dict(trial_row)
                trial_id = trial['trial_id']
                
                # Apply phase filter
                if phase_filter and trial.get('phase') not in phase_filter:
                    continue
                
                # Add trial node if including trials
                if include_trials and trial_id not in seen_nodes:
                    seen_nodes.add(trial_id)
                    nodes.append({
                        "id": trial_id,
                        "type": "trial",
                        "label": trial.get('title', trial_id)[:50],
                        "data": trial
                    })
                
                # Get companies sponsoring this trial
                cursor.execute("""
                    SELECT c.*, st.role
                    FROM companies c
                    JOIN sponsors_trial st ON c.company_id = st.company_id
                    WHERE st.trial_id = ?
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
                    
                    if include_trials:
                        edge_id = f"{company_id}-sponsors-{trial_id}"
                        if edge_id not in seen_edges:
                            seen_edges.add(edge_id)
                            edges.append({
                                "id": edge_id,
                                "source": company_id,
                                "target": trial_id,
                                "type": "SPONSORS_TRIAL",
                                "label": company_row['role'] or "sponsor",
                                "data": {"role": company_row['role']}
                            })
                
                # Get all companies sponsoring this trial (for creating edges to assets)
                trial_sponsor_ids = []
                cursor.execute("""
                    SELECT company_id FROM sponsors_trial WHERE trial_id = ?
                """, (trial_id,))
                for row in cursor.fetchall():
                    trial_sponsor_ids.append(row['company_id'])
                
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
                    
                    if include_trials:
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
                    
                    # Create edges from all sponsors of this trial to this asset
                    # This ensures all assets used in trials appear connected to their sponsors
                    for sponsor_id in trial_sponsor_ids:
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
        
        # Build condition for matching any term
        term_conditions = " OR ".join(["LOWER(conditions) LIKE ?" for _ in indication_terms])
        term_params = [f"%{term.lower()}%" for term in indication_terms]
        
        with self.connection() as conn:
            cursor = conn.cursor()
            
            # Trials by phase
            cursor.execute(f"""
                SELECT phase, COUNT(*) as count 
                FROM trials 
                WHERE {term_conditions}
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
                WHERE {term_conditions.replace('conditions', 't.conditions')}
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
                WHERE ({term_conditions.replace('conditions', 't.conditions')}) AND a.modality IS NOT NULL
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
                WHERE {term_conditions.replace('conditions', 't.conditions')}
            """, term_params)
            stats["total_trials"] = cursor.fetchone()['trials']
            
            cursor.execute(f"""
                SELECT COUNT(DISTINCT a.asset_id) as assets
                FROM assets a
                JOIN has_trial ht ON a.asset_id = ht.asset_id
                JOIN trials t ON ht.trial_id = t.trial_id
                WHERE {term_conditions.replace('conditions', 't.conditions')}
            """, term_params)
            stats["total_assets"] = cursor.fetchone()['assets']
            
            cursor.execute(f"""
                SELECT COUNT(DISTINCT c.company_id) as companies
                FROM companies c
                JOIN sponsors_trial st ON c.company_id = st.company_id
                JOIN trials t ON st.trial_id = t.trial_id
                WHERE {term_conditions.replace('conditions', 't.conditions')}
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
