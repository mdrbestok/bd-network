"""
Edge models for the property graph.
These represent relationships between nodes in the biotech deal network.
"""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class EdgeEvidence(BaseModel):
    """Evidence/provenance for a relationship."""
    source_type: str
    source_url: Optional[str] = None
    source_id: Optional[str] = None
    confidence: float = 1.0
    extracted_at: datetime = Field(default_factory=datetime.utcnow)


class PartyTo(BaseModel):
    """(Company)-[:PARTY_TO {role}]->(Deal)"""
    company_id: str
    deal_id: str
    role: str  # acquirer, target, licensor, licensee, collaborator
    evidence: List[EdgeEvidence] = Field(default_factory=list)


class Covers(BaseModel):
    """(Deal)-[:COVERS]->(Asset)"""
    deal_id: str
    asset_id: str
    evidence: List[EdgeEvidence] = Field(default_factory=list)


class SupportedBy(BaseModel):
    """(Deal)-[:SUPPORTED_BY]->(Document)"""
    deal_id: str
    doc_id: str
    evidence: List[EdgeEvidence] = Field(default_factory=list)


class Owns(BaseModel):
    """(Company)-[:OWNS {from,to,confidence,source}]->(Asset)"""
    company_id: str
    asset_id: str
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    confidence: float = 1.0
    source: str = "inferred"  # inferred, deal, press_release
    is_current: bool = True
    evidence: List[EdgeEvidence] = Field(default_factory=list)


class HasTrial(BaseModel):
    """(Asset)-[:HAS_TRIAL]->(Trial)"""
    asset_id: str
    trial_id: str
    evidence: List[EdgeEvidence] = Field(default_factory=list)


class SponsorsTrial(BaseModel):
    """(Company)-[:SPONSORS_TRIAL {role}]->(Trial) - DEPRECATED: Use ParticipatesInTrial for sites"""
    company_id: str
    trial_id: str
    role: str  # lead_sponsor, collaborator
    evidence: List[EdgeEvidence] = Field(default_factory=list)


class ParticipatesInTrial(BaseModel):
    """(Company/Site)-[:PARTICIPATES_IN_TRIAL {role}]->(Trial) - For clinical sites, investigators, academic centers"""
    company_id: str
    trial_id: str
    role: str  # site, investigator, collaborator
    evidence: List[EdgeEvidence] = Field(default_factory=list)


class Licenses(BaseModel):
    """(Company)-[:LICENSES {from,to,territory}]->(Asset) - Licensing relationship"""
    company_id: str
    asset_id: str
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    territory: Optional[str] = None  # e.g., "worldwide", "US", "ex-US"
    confidence: float = 1.0
    source: str = "inferred"
    evidence: List[EdgeEvidence] = Field(default_factory=list)


class UsesAsComparator(BaseModel):
    """(Company)-[:USES_AS_COMPARATOR]->(Asset) - Drug used as comparator in trial, not owned"""
    company_id: str
    asset_id: str
    trial_id: str  # Which trial this comparator use is for
    evidence: List[EdgeEvidence] = Field(default_factory=list)
