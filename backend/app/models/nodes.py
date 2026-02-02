"""
Node models for the property graph.
These represent the core entities in the biotech deal network.
"""
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field
import hashlib


class Evidence(BaseModel):
    """Evidence/provenance for a field value."""
    source_type: str  # "clinicaltrials", "sec", "press_release", "inferred"
    source_url: Optional[str] = None
    source_id: Optional[str] = None  # e.g., NCT number
    confidence: float = 1.0
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    input_fields: Optional[List[str]] = None  # for LLM-inferred fields


class Company(BaseModel):
    """Company node representing a pharma/biotech company or organization."""
    company_id: str
    name: str
    aliases: List[str] = Field(default_factory=list)
    country: Optional[str] = None
    public_flag: Optional[bool] = None
    tickers: List[str] = Field(default_factory=list)
    cik: Optional[str] = None  # SEC CIK number
    status: Optional[str] = None  # active, acquired, etc.
    # Organization type: "industry", "academic", "government", "investigator", "other"
    company_type: Optional[str] = None
    evidence: List[Evidence] = Field(default_factory=list)
    
    @classmethod
    def generate_id(cls, name: str) -> str:
        """Generate a deterministic ID from company name."""
        normalized = name.lower().strip()
        return f"company_{hashlib.md5(normalized.encode()).hexdigest()[:12]}"
    
    @classmethod
    def infer_type_from_name(cls, name: str, sponsor_class: Optional[str] = None) -> str:
        """Infer company type from name and sponsor class."""
        name_lower = name.lower()
        
        # First, check sponsor class from ClinicalTrials.gov (most reliable)
        if sponsor_class:
            sponsor_class_upper = sponsor_class.upper()
            if sponsor_class_upper == "INDUSTRY":
                return "industry"
            elif sponsor_class_upper in ("NIH", "FED"):
                return "government"
            elif sponsor_class_upper == "OTHER_GOV":
                return "government"
        
        # Check for individual investigators (MD, PhD, Dr., Prof.)
        investigator_patterns = [
            ", md", " md,", " m.d.", ", phd", " ph.d.", ", do,", ", do ",
            "prof. dr.", "prof dr", ", facs"
        ]
        if any(pattern in name_lower for pattern in investigator_patterns):
            return "investigator"
        
        # Check for government agencies
        gov_patterns = [
            "national institutes of health", "national cancer institute",
            "fda", "cdc", "department of defense", "department of health",
            "ministry of", "veterans affairs", "russian academy"
        ]
        if any(pattern in name_lower for pattern in gov_patterns):
            return "government"
        
        # Check for consortia and non-profits
        nonprofit_patterns = [
            "eortc", "unicancer", "organisation for research", "organization for research",
            "alliance for clinical", "cooperative group", "study group",
            "research network", "research alliance", "partnership",
            "association nationale", "melanoma research", "cancer research network",
            "solti", "hoosier", "swog"
        ]
        if any(pattern in name_lower for pattern in nonprofit_patterns):
            return "nonprofit"
        
        # Check name patterns for academic/medical institutions
        academic_patterns = [
            "university", "college", "école", "universität", "universidad", "universitaire",
            "hospital", "medical center", "cancer center", "clinic", "clinique",
            "institute", "institut", "research center", "academy",
            "school of medicine", "faculty of", "health network",
            "comprehensive cancer", "curie", "hospitalier", "hopital",
            "charite", "chu de", "chu ", "karolinska", "moffitt", "sloan kettering",
            "dana-farber", "mayo clinic", "fred hutchinson", "northwell",
            "m.d. anderson", "md anderson", "memorial sloan", "city of hope",
            "centre jean perrin", "retina research", "foundation"
        ]
        if any(pattern in name_lower for pattern in academic_patterns):
            return "academic"
        
        # Check for obvious industry patterns
        industry_patterns = [
            "inc.", "inc,", " inc", "ltd.", "ltd,", " ltd", "llc", "l.l.c.",
            "corp.", "corp,", "corporation", "gmbh", " ab", " a/s", " sa", " ag",
            "pharmaceuticals", "therapeutics", "biosciences", "biopharma", 
            "biotech", "pharma", "oncology", "medicines", "biopharmaceuticals"
        ]
        if any(pattern in name_lower for pattern in industry_patterns):
            return "industry"
        
        # Known pharma companies without obvious suffixes
        known_pharma = [
            "astrazeneca", "bristol-myers", "bristol myers", "novartis", 
            "servier", "viriom", "roche", "sanofi", "pfizer", "merck",
            "regeneron", "genentech", "amgen", "gilead", "abbvie"
        ]
        if any(pattern in name_lower for pattern in known_pharma):
            return "industry"
        
        # If sponsor_class was INDUSTRY, trust it
        if sponsor_class and sponsor_class.upper() == "INDUSTRY":
            return "industry"
        
        # Default to "other" for unclassified
        return "other"


class Asset(BaseModel):
    """Asset node representing a drug/therapeutic asset."""
    asset_id: str
    name: str
    synonyms: List[str] = Field(default_factory=list)
    modality: Optional[str] = None  # small molecule, antibody, cell therapy, etc.
    targets: List[str] = Field(default_factory=list)
    indications: List[str] = Field(default_factory=list)
    stage_current: Optional[str] = None  # preclinical, phase1, phase2, phase3, approved
    evidence: List[Evidence] = Field(default_factory=list)
    
    # Inferred fields with confidence
    modality_confidence: Optional[float] = None
    targets_confidence: Optional[float] = None
    
    @classmethod
    def generate_id(cls, name: str) -> str:
        """Generate a deterministic ID from asset name."""
        normalized = name.lower().strip()
        return f"asset_{hashlib.md5(normalized.encode()).hexdigest()[:12]}"


class Deal(BaseModel):
    """Deal node representing a business transaction."""
    deal_id: str
    deal_type: str  # license, acquisition, collaboration, etc.
    announce_date: Optional[date] = None
    summary: Optional[str] = None
    status: Optional[str] = None  # announced, completed, terminated
    value_usd: Optional[float] = None
    evidence: List[Evidence] = Field(default_factory=list)
    
    @classmethod
    def generate_id(cls, deal_type: str, parties: List[str], date_str: str = "") -> str:
        """Generate a deterministic ID from deal info."""
        combined = f"{deal_type}_{'-'.join(sorted(parties))}_{date_str}".lower()
        return f"deal_{hashlib.md5(combined.encode()).hexdigest()[:12]}"


class Document(BaseModel):
    """Document node representing a source document."""
    doc_id: str
    doc_type: str  # clinical_trial, sec_filing, press_release, guideline
    publisher: Optional[str] = None
    url: str
    published_at: Optional[datetime] = None
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    text_hash: Optional[str] = None
    raw_content: Optional[str] = None  # Store raw JSON/text for provenance
    
    @classmethod
    def generate_id(cls, url: str) -> str:
        """Generate a deterministic ID from URL."""
        return f"doc_{hashlib.md5(url.encode()).hexdigest()[:12]}"
    
    @classmethod
    def compute_hash(cls, content: str) -> str:
        """Compute hash of document content."""
        return hashlib.sha256(content.encode()).hexdigest()


class Trial(BaseModel):
    """Trial node representing a clinical trial."""
    trial_id: str  # NCT number
    title: str
    phase: Optional[str] = None
    status: Optional[str] = None  # recruiting, completed, terminated, etc.
    start_date: Optional[date] = None
    completion_date: Optional[date] = None
    interventions: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    sponsors: List[str] = Field(default_factory=list)
    collaborators: List[str] = Field(default_factory=list)
    enrollment: Optional[int] = None
    study_type: Optional[str] = None
    brief_summary: Optional[str] = None
    evidence: List[Evidence] = Field(default_factory=list)
    
    # Direct link to source
    source_url: str = ""
    
    @property
    def phase_numeric(self) -> Optional[int]:
        """Convert phase to numeric for sorting."""
        phase_map = {
            "early phase 1": 0,
            "phase 1": 1,
            "phase 1/phase 2": 1,
            "phase 2": 2,
            "phase 2/phase 3": 2,
            "phase 3": 3,
            "phase 4": 4,
            "not applicable": -1
        }
        if self.phase:
            return phase_map.get(self.phase.lower(), None)
        return None
