"""
Neo4j database service for graph storage and queries.
"""
import logging
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable

from ..config import settings
from ..models.nodes import Company, Asset, Deal, Document, Trial
from ..models.edges import PartyTo, Covers, SupportedBy, Owns, HasTrial, SponsorsTrial

logger = logging.getLogger(__name__)


class Neo4jService:
    """Service for Neo4j database operations."""
    
    _driver: Optional[Driver] = None
    
    def __init__(self):
        """Initialize Neo4j connection."""
        self._connect()
    
    def _connect(self):
        """Establish connection to Neo4j."""
        try:
            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            # Verify connectivity
            self._driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {settings.neo4j_uri}")
        except ServiceUnavailable as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        """Close the Neo4j connection."""
        if self._driver:
            self._driver.close()
    
    @contextmanager
    def session(self):
        """Get a Neo4j session context manager."""
        session = self._driver.session()
        try:
            yield session
        finally:
            session.close()
    
    def init_schema(self):
        """Initialize database schema with indexes and constraints."""
        with self.session() as session:
            # Create indexes for each node type
            indexes = [
                "CREATE INDEX company_id IF NOT EXISTS FOR (c:Company) ON (c.company_id)",
                "CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name)",
                "CREATE INDEX asset_id IF NOT EXISTS FOR (a:Asset) ON (a.asset_id)",
                "CREATE INDEX asset_name IF NOT EXISTS FOR (a:Asset) ON (a.name)",
                "CREATE INDEX deal_id IF NOT EXISTS FOR (d:Deal) ON (d.deal_id)",
                "CREATE INDEX trial_id IF NOT EXISTS FOR (t:Trial) ON (t.trial_id)",
                "CREATE INDEX doc_id IF NOT EXISTS FOR (d:Document) ON (d.doc_id)",
                # Full-text search indexes
                "CREATE FULLTEXT INDEX company_search IF NOT EXISTS FOR (c:Company) ON EACH [c.name, c.aliases]",
                "CREATE FULLTEXT INDEX asset_search IF NOT EXISTS FOR (a:Asset) ON EACH [a.name, a.synonyms]",
            ]
            for idx in indexes:
                try:
                    session.run(idx)
                except Exception as e:
                    logger.warning(f"Index creation warning: {e}")
            
            logger.info("Neo4j schema initialized")
    
    # ==================== Node Operations ====================
    
    def upsert_company(self, company: Company) -> str:
        """Insert or update a Company node."""
        query = """
        MERGE (c:Company {company_id: $company_id})
        SET c.name = $name,
            c.aliases = $aliases,
            c.country = $country,
            c.public_flag = $public_flag,
            c.tickers = $tickers,
            c.cik = $cik,
            c.status = $status,
            c.evidence = $evidence,
            c.updated_at = datetime()
        RETURN c.company_id as id
        """
        with self.session() as session:
            result = session.run(query, 
                company_id=company.company_id,
                name=company.name,
                aliases=company.aliases,
                country=company.country,
                public_flag=company.public_flag,
                tickers=company.tickers,
                cik=company.cik,
                status=company.status,
                evidence=[e.model_dump_json() for e in company.evidence]
            )
            record = result.single()
            return record["id"] if record else company.company_id
    
    def upsert_asset(self, asset: Asset) -> str:
        """Insert or update an Asset node."""
        query = """
        MERGE (a:Asset {asset_id: $asset_id})
        SET a.name = $name,
            a.synonyms = $synonyms,
            a.modality = $modality,
            a.targets = $targets,
            a.indications = $indications,
            a.stage_current = $stage_current,
            a.modality_confidence = $modality_confidence,
            a.targets_confidence = $targets_confidence,
            a.evidence = $evidence,
            a.updated_at = datetime()
        RETURN a.asset_id as id
        """
        with self.session() as session:
            result = session.run(query,
                asset_id=asset.asset_id,
                name=asset.name,
                synonyms=asset.synonyms,
                modality=asset.modality,
                targets=asset.targets,
                indications=asset.indications,
                stage_current=asset.stage_current,
                modality_confidence=asset.modality_confidence,
                targets_confidence=asset.targets_confidence,
                evidence=[e.model_dump_json() for e in asset.evidence]
            )
            record = result.single()
            return record["id"] if record else asset.asset_id
    
    def upsert_trial(self, trial: Trial) -> str:
        """Insert or update a Trial node."""
        query = """
        MERGE (t:Trial {trial_id: $trial_id})
        SET t.title = $title,
            t.phase = $phase,
            t.status = $status,
            t.start_date = $start_date,
            t.completion_date = $completion_date,
            t.interventions = $interventions,
            t.conditions = $conditions,
            t.sponsors = $sponsors,
            t.collaborators = $collaborators,
            t.enrollment = $enrollment,
            t.study_type = $study_type,
            t.brief_summary = $brief_summary,
            t.source_url = $source_url,
            t.evidence = $evidence,
            t.updated_at = datetime()
        RETURN t.trial_id as id
        """
        with self.session() as session:
            result = session.run(query,
                trial_id=trial.trial_id,
                title=trial.title,
                phase=trial.phase,
                status=trial.status,
                start_date=str(trial.start_date) if trial.start_date else None,
                completion_date=str(trial.completion_date) if trial.completion_date else None,
                interventions=trial.interventions,
                conditions=trial.conditions,
                sponsors=trial.sponsors,
                collaborators=trial.collaborators,
                enrollment=trial.enrollment,
                study_type=trial.study_type,
                brief_summary=trial.brief_summary,
                source_url=trial.source_url,
                evidence=[e.model_dump_json() for e in trial.evidence]
            )
            record = result.single()
            return record["id"] if record else trial.trial_id
    
    def upsert_document(self, doc: Document) -> str:
        """Insert or update a Document node."""
        query = """
        MERGE (d:Document {doc_id: $doc_id})
        SET d.doc_type = $doc_type,
            d.publisher = $publisher,
            d.url = $url,
            d.published_at = $published_at,
            d.retrieved_at = $retrieved_at,
            d.text_hash = $text_hash,
            d.updated_at = datetime()
        RETURN d.doc_id as id
        """
        with self.session() as session:
            result = session.run(query,
                doc_id=doc.doc_id,
                doc_type=doc.doc_type,
                publisher=doc.publisher,
                url=doc.url,
                published_at=str(doc.published_at) if doc.published_at else None,
                retrieved_at=str(doc.retrieved_at),
                text_hash=doc.text_hash
            )
            record = result.single()
            return record["id"] if record else doc.doc_id
    
    def upsert_deal(self, deal: Deal) -> str:
        """Insert or update a Deal node."""
        query = """
        MERGE (d:Deal {deal_id: $deal_id})
        SET d.deal_type = $deal_type,
            d.announce_date = $announce_date,
            d.summary = $summary,
            d.status = $status,
            d.value_usd = $value_usd,
            d.evidence = $evidence,
            d.updated_at = datetime()
        RETURN d.deal_id as id
        """
        with self.session() as session:
            result = session.run(query,
                deal_id=deal.deal_id,
                deal_type=deal.deal_type,
                announce_date=str(deal.announce_date) if deal.announce_date else None,
                summary=deal.summary,
                status=deal.status,
                value_usd=deal.value_usd,
                evidence=[e.model_dump_json() for e in deal.evidence]
            )
            record = result.single()
            return record["id"] if record else deal.deal_id
    
    # ==================== Edge Operations ====================
    
    def create_sponsors_trial(self, rel: SponsorsTrial):
        """Create SPONSORS_TRIAL relationship."""
        query = """
        MATCH (c:Company {company_id: $company_id})
        MATCH (t:Trial {trial_id: $trial_id})
        MERGE (c)-[r:SPONSORS_TRIAL]->(t)
        SET r.role = $role,
            r.evidence = $evidence
        """
        with self.session() as session:
            session.run(query,
                company_id=rel.company_id,
                trial_id=rel.trial_id,
                role=rel.role,
                evidence=[e.model_dump_json() for e in rel.evidence]
            )
    
    def create_has_trial(self, rel: HasTrial):
        """Create HAS_TRIAL relationship."""
        query = """
        MATCH (a:Asset {asset_id: $asset_id})
        MATCH (t:Trial {trial_id: $trial_id})
        MERGE (a)-[r:HAS_TRIAL]->(t)
        SET r.evidence = $evidence
        """
        with self.session() as session:
            session.run(query,
                asset_id=rel.asset_id,
                trial_id=rel.trial_id,
                evidence=[e.model_dump_json() for e in rel.evidence]
            )
    
    def create_owns(self, rel: Owns):
        """Create OWNS relationship."""
        query = """
        MATCH (c:Company {company_id: $company_id})
        MATCH (a:Asset {asset_id: $asset_id})
        MERGE (c)-[r:OWNS]->(a)
        SET r.from_date = $from_date,
            r.to_date = $to_date,
            r.confidence = $confidence,
            r.source = $source,
            r.is_current = $is_current,
            r.evidence = $evidence
        """
        with self.session() as session:
            session.run(query,
                company_id=rel.company_id,
                asset_id=rel.asset_id,
                from_date=str(rel.from_date) if rel.from_date else None,
                to_date=str(rel.to_date) if rel.to_date else None,
                confidence=rel.confidence,
                source=rel.source,
                is_current=rel.is_current,
                evidence=[e.model_dump_json() for e in rel.evidence]
            )
    
    def create_party_to(self, rel: PartyTo):
        """Create PARTY_TO relationship."""
        query = """
        MATCH (c:Company {company_id: $company_id})
        MATCH (d:Deal {deal_id: $deal_id})
        MERGE (c)-[r:PARTY_TO]->(d)
        SET r.role = $role,
            r.evidence = $evidence
        """
        with self.session() as session:
            session.run(query,
                company_id=rel.company_id,
                deal_id=rel.deal_id,
                role=rel.role,
                evidence=[e.model_dump_json() for e in rel.evidence]
            )
    
    def create_covers(self, rel: Covers):
        """Create COVERS relationship."""
        query = """
        MATCH (d:Deal {deal_id: $deal_id})
        MATCH (a:Asset {asset_id: $asset_id})
        MERGE (d)-[r:COVERS]->(a)
        SET r.evidence = $evidence
        """
        with self.session() as session:
            session.run(query,
                deal_id=rel.deal_id,
                asset_id=rel.asset_id,
                evidence=[e.model_dump_json() for e in rel.evidence]
            )
    
    # ==================== Query Operations ====================
    
    def get_company(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Get a company by ID with related data."""
        query = """
        MATCH (c:Company {company_id: $company_id})
        OPTIONAL MATCH (c)-[st:SPONSORS_TRIAL]->(t:Trial)
        OPTIONAL MATCH (c)-[o:OWNS]->(a:Asset)
        OPTIONAL MATCH (c)-[pt:PARTY_TO]->(d:Deal)
        RETURN c,
               collect(DISTINCT {trial: t, role: st.role}) as trials,
               collect(DISTINCT {asset: a, ownership: o}) as assets,
               collect(DISTINCT {deal: d, role: pt.role}) as deals
        """
        with self.session() as session:
            result = session.run(query, company_id=company_id)
            record = result.single()
            if not record:
                return None
            
            company_data = dict(record["c"])
            company_data["trials"] = [
                {**dict(t["trial"]), "role": t["role"]} 
                for t in record["trials"] if t["trial"]
            ]
            company_data["assets"] = [
                {**dict(a["asset"]), "ownership": dict(a["ownership"]) if a["ownership"] else None}
                for a in record["assets"] if a["asset"]
            ]
            company_data["deals"] = [
                {**dict(d["deal"]), "role": d["role"]}
                for d in record["deals"] if d["deal"]
            ]
            return company_data
    
    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get an asset by ID with related data."""
        query = """
        MATCH (a:Asset {asset_id: $asset_id})
        OPTIONAL MATCH (a)-[:HAS_TRIAL]->(t:Trial)
        OPTIONAL MATCH (c:Company)-[o:OWNS]->(a)
        OPTIONAL MATCH (d:Deal)-[:COVERS]->(a)
        RETURN a,
               collect(DISTINCT t) as trials,
               collect(DISTINCT {company: c, ownership: o}) as owners,
               collect(DISTINCT d) as deals
        """
        with self.session() as session:
            result = session.run(query, asset_id=asset_id)
            record = result.single()
            if not record:
                return None
            
            asset_data = dict(record["a"])
            asset_data["trials"] = [dict(t) for t in record["trials"] if t]
            asset_data["owners"] = [
                {**dict(o["company"]), "ownership": dict(o["ownership"]) if o["ownership"] else None}
                for o in record["owners"] if o["company"]
            ]
            asset_data["deals"] = [dict(d) for d in record["deals"] if d]
            return asset_data
    
    def get_trial(self, trial_id: str) -> Optional[Dict[str, Any]]:
        """Get a trial by ID with related data."""
        query = """
        MATCH (t:Trial {trial_id: $trial_id})
        OPTIONAL MATCH (c:Company)-[st:SPONSORS_TRIAL]->(t)
        OPTIONAL MATCH (a:Asset)-[:HAS_TRIAL]->(t)
        RETURN t,
               collect(DISTINCT {company: c, role: st.role}) as sponsors,
               collect(DISTINCT a) as assets
        """
        with self.session() as session:
            result = session.run(query, trial_id=trial_id)
            record = result.single()
            if not record:
                return None
            
            trial_data = dict(record["t"])
            trial_data["sponsors_detail"] = [
                {**dict(s["company"]), "role": s["role"]}
                for s in record["sponsors"] if s["company"]
            ]
            trial_data["assets"] = [dict(a) for a in record["assets"] if a]
            return trial_data
    
    def search_all(self, query_text: str, limit: int = 20) -> Dict[str, List[Dict]]:
        """Search across all node types."""
        results = {
            "companies": [],
            "assets": [],
            "trials": []
        }
        
        # Search companies
        company_query = """
        CALL db.index.fulltext.queryNodes("company_search", $query) YIELD node, score
        RETURN node, score ORDER BY score DESC LIMIT $limit
        """
        
        # Search assets
        asset_query = """
        CALL db.index.fulltext.queryNodes("asset_search", $query) YIELD node, score
        RETURN node, score ORDER BY score DESC LIMIT $limit
        """
        
        # Search trials by title (no fulltext index, use CONTAINS)
        trial_query = """
        MATCH (t:Trial)
        WHERE toLower(t.title) CONTAINS toLower($query)
        RETURN t as node, 1.0 as score LIMIT $limit
        """
        
        with self.session() as session:
            try:
                for record in session.run(company_query, query=query_text, limit=limit):
                    results["companies"].append({
                        **dict(record["node"]),
                        "score": record["score"]
                    })
            except Exception as e:
                logger.warning(f"Company search failed: {e}")
            
            try:
                for record in session.run(asset_query, query=query_text, limit=limit):
                    results["assets"].append({
                        **dict(record["node"]),
                        "score": record["score"]
                    })
            except Exception as e:
                logger.warning(f"Asset search failed: {e}")
            
            try:
                for record in session.run(trial_query, query=query_text, limit=limit):
                    results["trials"].append({
                        **dict(record["node"]),
                        "score": record["score"]
                    })
            except Exception as e:
                logger.warning(f"Trial search failed: {e}")
        
        return results
    
    def get_indication_graph(
        self,
        indication: str,
        depth: int = 2,
        phase_filter: Optional[List[str]] = None,
        modality_filter: Optional[List[str]] = None,
        include_trials: bool = False,
        limit: int = 200
    ) -> Dict[str, Any]:
        """
        Get the network graph for an indication.
        Returns nodes and edges for visualization.
        """
        # Build filter clauses
        phase_clause = ""
        if phase_filter:
            phases = "', '".join(phase_filter)
            phase_clause = f"AND t.phase IN ['{phases}']"
        
        modality_clause = ""
        if modality_filter:
            modalities = "', '".join(modality_filter)
            modality_clause = f"AND a.modality IN ['{modalities}']"
        
        # Query for trials matching the indication
        query = f"""
        MATCH (t:Trial)
        WHERE any(cond IN t.conditions WHERE toLower(cond) CONTAINS toLower($indication))
        {phase_clause}
        WITH t LIMIT $limit
        
        // Get assets linked to these trials
        OPTIONAL MATCH (a:Asset)-[:HAS_TRIAL]->(t)
        {modality_clause}
        
        // Get companies sponsoring these trials
        OPTIONAL MATCH (c:Company)-[st:SPONSORS_TRIAL]->(t)
        
        // Get ownership relationships
        OPTIONAL MATCH (c2:Company)-[o:OWNS]->(a)
        
        // Get deals if depth > 1
        {"OPTIONAL MATCH (c)-[pt:PARTY_TO]->(d:Deal)-[cov:COVERS]->(a)" if depth > 1 else ""}
        
        RETURN 
            collect(DISTINCT t) as trials,
            collect(DISTINCT a) as assets,
            collect(DISTINCT c) as companies,
            collect(DISTINCT c2) as owners,
            collect(DISTINCT {{company: c, trial: t, role: st.role}}) as sponsor_rels,
            collect(DISTINCT {{asset: a, trial: t}}) as asset_trial_rels,
            collect(DISTINCT {{company: c2, asset: a, ownership: o}}) as ownership_rels
            {"," if depth > 1 else ""}
            {"collect(DISTINCT d) as deals," if depth > 1 else ""}
            {"collect(DISTINCT {company: c, deal: d, role: pt.role}) as deal_party_rels," if depth > 1 else ""}
            {"collect(DISTINCT {deal: d, asset: a}) as deal_covers_rels" if depth > 1 else ""}
        """
        
        nodes = []
        edges = []
        seen_nodes = set()
        seen_edges = set()
        
        with self.session() as session:
            result = session.run(query, indication=indication, limit=limit)
            record = result.single()
            
            if not record:
                return {"nodes": [], "edges": []}
            
            # Process trials
            if include_trials:
                for t in record.get("trials", []):
                    if t and t["trial_id"] not in seen_nodes:
                        seen_nodes.add(t["trial_id"])
                        nodes.append({
                            "id": t["trial_id"],
                            "type": "trial",
                            "label": t.get("title", t["trial_id"])[:50],
                            "data": dict(t)
                        })
            
            # Process assets
            for a in record.get("assets", []):
                if a and a["asset_id"] not in seen_nodes:
                    seen_nodes.add(a["asset_id"])
                    nodes.append({
                        "id": a["asset_id"],
                        "type": "asset",
                        "label": a.get("name", a["asset_id"]),
                        "data": dict(a)
                    })
            
            # Process companies (sponsors and owners)
            for c in record.get("companies", []) + record.get("owners", []):
                if c and c["company_id"] not in seen_nodes:
                    seen_nodes.add(c["company_id"])
                    nodes.append({
                        "id": c["company_id"],
                        "type": "company",
                        "label": c.get("name", c["company_id"]),
                        "data": dict(c)
                    })
            
            # Process deals
            for d in record.get("deals", []):
                if d and d["deal_id"] not in seen_nodes:
                    seen_nodes.add(d["deal_id"])
                    nodes.append({
                        "id": d["deal_id"],
                        "type": "deal",
                        "label": d.get("deal_type", "Deal"),
                        "data": dict(d)
                    })
            
            # Process sponsor relationships
            for rel in record.get("sponsor_rels", []):
                if rel["company"] and rel["trial"]:
                    edge_id = f"{rel['company']['company_id']}-sponsors-{rel['trial']['trial_id']}"
                    if edge_id not in seen_edges:
                        seen_edges.add(edge_id)
                        if include_trials:
                            edges.append({
                                "id": edge_id,
                                "source": rel["company"]["company_id"],
                                "target": rel["trial"]["trial_id"],
                                "type": "SPONSORS_TRIAL",
                                "label": rel.get("role", "sponsor"),
                                "data": {"role": rel.get("role")}
                            })
            
            # Process asset-trial relationships
            for rel in record.get("asset_trial_rels", []):
                if rel["asset"] and rel["trial"]:
                    edge_id = f"{rel['asset']['asset_id']}-has_trial-{rel['trial']['trial_id']}"
                    if edge_id not in seen_edges:
                        seen_edges.add(edge_id)
                        if include_trials:
                            edges.append({
                                "id": edge_id,
                                "source": rel["asset"]["asset_id"],
                                "target": rel["trial"]["trial_id"],
                                "type": "HAS_TRIAL",
                                "label": "trial",
                                "data": {}
                            })
            
            # Process ownership relationships
            for rel in record.get("ownership_rels", []):
                if rel["company"] and rel["asset"]:
                    edge_id = f"{rel['company']['company_id']}-owns-{rel['asset']['asset_id']}"
                    if edge_id not in seen_edges:
                        seen_edges.add(edge_id)
                        ownership = rel.get("ownership", {})
                        edges.append({
                            "id": edge_id,
                            "source": rel["company"]["company_id"],
                            "target": rel["asset"]["asset_id"],
                            "type": "OWNS",
                            "label": "owns",
                            "data": {
                                "confidence": ownership.get("confidence", 1.0) if ownership else 1.0,
                                "source": ownership.get("source", "inferred") if ownership else "inferred"
                            }
                        })
            
            # Process deal relationships
            for rel in record.get("deal_party_rels", []):
                if rel.get("company") and rel.get("deal"):
                    edge_id = f"{rel['company']['company_id']}-party_to-{rel['deal']['deal_id']}"
                    if edge_id not in seen_edges:
                        seen_edges.add(edge_id)
                        edges.append({
                            "id": edge_id,
                            "source": rel["company"]["company_id"],
                            "target": rel["deal"]["deal_id"],
                            "type": "PARTY_TO",
                            "label": rel.get("role", "party"),
                            "data": {"role": rel.get("role")}
                        })
            
            for rel in record.get("deal_covers_rels", []):
                if rel.get("deal") and rel.get("asset"):
                    edge_id = f"{rel['deal']['deal_id']}-covers-{rel['asset']['asset_id']}"
                    if edge_id not in seen_edges:
                        seen_edges.add(edge_id)
                        edges.append({
                            "id": edge_id,
                            "source": rel["deal"]["deal_id"],
                            "target": rel["asset"]["asset_id"],
                            "type": "COVERS",
                            "label": "covers",
                            "data": {}
                        })
        
        return {"nodes": nodes, "edges": edges}
    
    def get_landscape_stats(self, indication: str) -> Dict[str, Any]:
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
        
        # Assets by phase
        phase_query = """
        MATCH (t:Trial)
        WHERE any(cond IN t.conditions WHERE toLower(cond) CONTAINS toLower($indication))
        WITH t.phase as phase, count(t) as count
        RETURN phase, count ORDER BY count DESC
        """
        
        # Sponsors by trial count
        sponsor_query = """
        MATCH (t:Trial)
        WHERE any(cond IN t.conditions WHERE toLower(cond) CONTAINS toLower($indication))
        MATCH (c:Company)-[:SPONSORS_TRIAL]->(t)
        WITH c.name as sponsor, c.company_id as id, count(t) as trial_count
        RETURN sponsor, id, trial_count ORDER BY trial_count DESC LIMIT 20
        """
        
        # Modalities
        modality_query = """
        MATCH (t:Trial)
        WHERE any(cond IN t.conditions WHERE toLower(cond) CONTAINS toLower($indication))
        MATCH (a:Asset)-[:HAS_TRIAL]->(t)
        WHERE a.modality IS NOT NULL
        WITH a.modality as modality, count(DISTINCT a) as count
        RETURN modality, count ORDER BY count DESC
        """
        
        # Targets
        target_query = """
        MATCH (t:Trial)
        WHERE any(cond IN t.conditions WHERE toLower(cond) CONTAINS toLower($indication))
        MATCH (a:Asset)-[:HAS_TRIAL]->(t)
        WHERE a.targets IS NOT NULL AND size(a.targets) > 0
        UNWIND a.targets as target
        WITH target, count(DISTINCT a) as count
        RETURN target, count ORDER BY count DESC LIMIT 15
        """
        
        # Totals
        totals_query = """
        MATCH (t:Trial)
        WHERE any(cond IN t.conditions WHERE toLower(cond) CONTAINS toLower($indication))
        OPTIONAL MATCH (a:Asset)-[:HAS_TRIAL]->(t)
        OPTIONAL MATCH (c:Company)-[:SPONSORS_TRIAL]->(t)
        RETURN count(DISTINCT t) as trials, count(DISTINCT a) as assets, count(DISTINCT c) as companies
        """
        
        with self.session() as session:
            # Execute queries
            for record in session.run(phase_query, indication=indication):
                if record["phase"]:
                    stats["assets_by_phase"].append({
                        "phase": record["phase"],
                        "count": record["count"]
                    })
            
            for record in session.run(sponsor_query, indication=indication):
                stats["sponsors_by_trial_count"].append({
                    "sponsor": record["sponsor"],
                    "id": record["id"],
                    "trial_count": record["trial_count"]
                })
            
            for record in session.run(modality_query, indication=indication):
                stats["modalities"].append({
                    "modality": record["modality"],
                    "count": record["count"]
                })
            
            for record in session.run(target_query, indication=indication):
                stats["targets"].append({
                    "target": record["target"],
                    "count": record["count"]
                })
            
            totals = session.run(totals_query, indication=indication).single()
            if totals:
                stats["total_trials"] = totals["trials"]
                stats["total_assets"] = totals["assets"]
                stats["total_companies"] = totals["companies"]
        
        return stats
    
    def clear_database(self):
        """Clear all data (for testing/reset)."""
        with self.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("Database cleared")


# Singleton instance
_neo4j_service: Optional[Neo4jService] = None


def get_neo4j_service() -> Neo4jService:
    """Get or create Neo4j service singleton."""
    global _neo4j_service
    if _neo4j_service is None:
        _neo4j_service = Neo4jService()
    return _neo4j_service
