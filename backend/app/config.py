"""
Configuration for the Biotech Deal Network backend.
All settings can be overridden via environment variables.
"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "Biotech Deal Network"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Neo4j
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "biotech123")
    
    # ClinicalTrials.gov API
    clinicaltrials_api_base: str = "https://clinicaltrials.gov/api/v2"
    clinicaltrials_page_size: int = 100
    clinicaltrials_max_trials: int = 500
    
    # Indication seed configuration
    # Default: Mucosal Melanoma (MuM)
    default_indication: str = os.getenv("DEFAULT_INDICATION", "MuM")
    indication_terms: dict = {
        "MuM": [
            "mucosal melanoma",
            "mucosal malignant melanoma",
            "melanoma of mucosa",
            "uveal melanoma",
            "metastatic uveal melanoma",
            "ocular melanoma"
        ],
        # Add more indications as needed
    }
    
    # LLM enrichment (optional)
    llm_enrichment_enabled: bool = os.getenv("LLM_ENRICHMENT_ENABLED", "false").lower() == "true"
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Data quality
    min_confidence_threshold: float = 0.5
    
    class Config:
        env_file = ".env"
        extra = "allow"
    
    def get_indication_terms(self, indication: str) -> List[str]:
        """Get search terms for an indication."""
        return self.indication_terms.get(indication, [indication])


settings = Settings()
