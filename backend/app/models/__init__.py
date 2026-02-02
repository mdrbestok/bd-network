"""Data models for the Biotech Deal Network."""
from .nodes import Company, Asset, Deal, Document, Trial
from .edges import PartyTo, Covers, SupportedBy, Owns, HasTrial, SponsorsTrial

__all__ = [
    "Company", "Asset", "Deal", "Document", "Trial",
    "PartyTo", "Covers", "SupportedBy", "Owns", "HasTrial", "SponsorsTrial"
]
