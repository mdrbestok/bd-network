"""
Graph service for high-level graph operations and queries.
"""
import logging
import os
from typing import Dict, Any, Optional, List

from .clinicaltrials_service import get_clinicaltrials_service
from .normalization_service import get_normalization_service
from ..config import settings

logger = logging.getLogger(__name__)


def get_db_service():
    """Get the appropriate database service based on configuration."""
    use_sqlite = os.getenv("USE_SQLITE", "true").lower() == "true"
    
    if use_sqlite:
        from .sqlite_service import get_sqlite_service
        return get_sqlite_service()
    else:
        from .neo4j_service import get_neo4j_service
        return get_neo4j_service()


class GraphService:
    """High-level service for graph operations."""
    
    def __init__(self):
        self.db = get_db_service()
        self.ct_service = get_clinicaltrials_service()
        self.normalization = get_normalization_service()
    
    def init_database(self):
        """Initialize the database schema."""
        self.db.init_schema()
    
    def ingest_indication(
        self,
        indication: str,
        max_trials: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Run full ingestion for an indication.
        
        Args:
            indication: The indication code (e.g., "MuM")
            max_trials: Maximum trials to fetch
        
        Returns:
            Ingestion statistics
        """
        return self.ct_service.ingest_for_indication(
            indication,
            self.db,
            self.normalization,
            max_trials
        )
    
    def get_indication_network(
        self,
        indication: str,
        depth: int = 2,
        phase_filter: Optional[List[str]] = None,
        modality_filter: Optional[List[str]] = None,
        include_trials: bool = False,
        trial_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get the network graph for an indication. trial_filter: none, recruiting, active_not_recruiting, all."""
        # Map indication code to search terms for matching in conditions
        terms = settings.get_indication_terms(indication)
        
        # Search using ALL terms for better recall
        return self.db.get_indication_graph(
            indication_terms=terms if terms else [indication],
            depth=depth,
            phase_filter=phase_filter,
            modality_filter=modality_filter,
            include_trials=include_trials,
            trial_filter=trial_filter
        )
    
    def get_company_details(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed company information."""
        return self.db.get_company(company_id)
    
    def get_asset_details(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed asset information (includes user overrides)."""
        return self.db.get_asset(asset_id)

    def update_asset(
        self,
        asset_id: str,
        modality: Optional[str] = None,
        targets: Optional[List[str]] = None,
        owner_company_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Set user overrides for an asset (modality, targets) and/or set company relationship. Ingestion will not overwrite these."""
        if not hasattr(self.db, 'set_asset_override'):
            return None
        if modality is not None or targets is not None:
            self.db.set_asset_override(asset_id, modality=modality, targets=targets)
        if owner_company_id is not None:
            rel_type = relationship_type or 'owns'
            if rel_type == 'owns':
                self.db.upsert_owns_user_confirmed(owner_company_id, asset_id, confidence=1.0)
            elif rel_type == 'licenses':
                self.db.upsert_licenses_user_confirmed(owner_company_id, asset_id, confidence=1.0)
            elif rel_type == 'uses_as_comparator':
                # For comparator, we need a trial_id - for user-set, use a placeholder
                self.db.upsert_uses_as_comparator_user_confirmed(owner_company_id, asset_id)
        return self.get_asset_details(asset_id)

    def create_company(self, name: str) -> str:
        """Create or get a company by name (e.g. for adding a new sponsor). Returns company_id."""
        from ..models.nodes import Company, Evidence
        company_id = Company.generate_id(name)
        company = Company(
            company_id=company_id,
            name=name.strip(),
            company_type="industry",
            evidence=[Evidence(source_type="user_added", confidence=1.0)]
        )
        self.db.upsert_company(company)
        return company_id

    def get_trial_details(self, trial_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed trial information."""
        return self.db.get_trial(trial_id)
    
    def search(self, query: str, limit: int = 20) -> Dict[str, List[Dict]]:
        """Search across all node types."""
        return self.db.search_all(query, limit)
    
    def get_landscape(self, indication: str) -> Dict[str, Any]:
        """Get landscape statistics and summary for an indication."""
        terms = settings.get_indication_terms(indication)
        
        stats = self.db.get_landscape_stats(terms if terms else [indication])
        
        # Add standard of care info (placeholder for POC)
        stats["standard_of_care"] = {
            "available": False,
            "note": "Standard of care information requires validated medical sources and is not yet implemented.",
            "placeholder_info": self._get_soc_placeholder(indication)
        }
        
        return stats
    
    def _get_soc_placeholder(self, indication: str) -> Optional[Dict[str, Any]]:
        """
        Get placeholder SoC info for known indications.
        These are marked as needing verified sources.
        """
        soc_data = {
            "MuM": {
                "indication_full_name": "Metastatic Uveal Melanoma / Mucosal Melanoma",
                "needs_citation": True,
                "summary": (
                    "For metastatic uveal melanoma, treatment options are limited. "
                    "Tebentafusp (Kimmtrak) is approved for HLA-A*02:01-positive patients. "
                    "Other approaches include checkpoint inhibitors (pembrolizumab, ipilimumab + nivolumab), "
                    "though response rates are generally lower than in cutaneous melanoma. "
                    "Liver-directed therapies may be considered for hepatic metastases."
                ),
                "key_agents": [
                    {"name": "Tebentafusp", "approved": True, "notes": "FDA approved 2022 for HLA-A*02:01+ mUM"},
                    {"name": "Pembrolizumab", "approved": False, "notes": "Used off-label; limited efficacy"},
                    {"name": "Ipilimumab + Nivolumab", "approved": False, "notes": "Combination checkpoint therapy"}
                ],
                "disclaimer": (
                    "NEEDS CITED SOURCES - This information is for demonstration only. "
                    "Treatment decisions should be based on current NCCN guidelines and consultation "
                    "with qualified oncologists."
                )
            }
        }
        
        return soc_data.get(indication)
    
    def get_stats(self) -> Dict[str, int]:
        """Get overall database statistics."""
        # Use the db service's get_stats if available
        if hasattr(self.db, 'get_stats'):
            return self.db.get_stats()
        
        # Fallback for Neo4j
        try:
            query = """
            MATCH (c:Company) WITH count(c) as companies
            MATCH (a:Asset) WITH companies, count(a) as assets
            MATCH (t:Trial) WITH companies, assets, count(t) as trials
            MATCH (d:Deal) WITH companies, assets, trials, count(d) as deals
            MATCH (doc:Document) WITH companies, assets, trials, deals, count(doc) as documents
            RETURN companies, assets, trials, deals, documents
            """
            
            with self.db.session() as session:
                result = session.run(query)
                record = result.single()
                
                if record:
                    return {
                        "companies": record["companies"],
                        "assets": record["assets"],
                        "trials": record["trials"],
                        "deals": record["deals"],
                        "documents": record["documents"]
                    }
        except Exception as e:
            logger.warning(f"Failed to get stats: {e}")
        
        return {"companies": 0, "assets": 0, "trials": 0, "deals": 0, "documents": 0}


# Singleton instance
_graph_service: Optional[GraphService] = None


def get_graph_service() -> GraphService:
    """Get or create graph service singleton."""
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service
