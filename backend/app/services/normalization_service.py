"""
Asset normalization and enrichment service.
Handles cleanup of intervention names and optional LLM enrichment.
"""
import re
import logging
from typing import Dict, Any, Optional, List

from ..config import settings

logger = logging.getLogger(__name__)


# Known drug name aliases (expandable)
# Maps canonical name -> list of known aliases/code names
DRUG_ALIASES = {
    # Immunocore - tebentafusp (KIMMTRAK)
    "tebentafusp": ["kimmtrak", "ime-403", "imcgp100", "imc-gp100", "imcgp-100", "tebentafusp-tebn"],
    # IDEAYA - darovasertib
    "darovasertib": ["ide196", "ide-196", "lxs196", "lxs-196"],
    # Merck - pembrolizumab (Keytruda)
    "pembrolizumab": ["keytruda", "mk-3475", "mk3475", "lambrolizumab"],
    # BMS - nivolumab (Opdivo)
    "nivolumab": ["opdivo", "bms-936558", "mdx-1106", "ono-4538"],
    # BMS - ipilimumab (Yervoy)
    "ipilimumab": ["yervoy", "mdx-010", "bms-734016"],
    # Pfizer - crizotinib (Xalkori)
    "crizotinib": ["xalkori", "pf-02341066"],
    # Generic chemotherapy
    "dacarbazine": ["dtic", "dtic-dome"],
    "temozolomide": ["temodar", "temodal"],
    # AstraZeneca - atezolizumab (Tecentriq) - actually Roche/Genentech
    "atezolizumab": ["tecentriq", "mpdl3280a"],
    # AstraZeneca - durvalumab (Imfinzi)
    "durvalumab": ["imfinzi", "medi4736"],
    # AstraZeneca - tremelimumab (Imjudo)
    "tremelimumab": ["imjudo", "cp-675,206"],
    # BMS - relatlimab (Opdualag)
    "relatlimab": ["opdualag", "bms-986016"],
    "sorafenib": ["nexavar"],
    "sunitinib": ["sutent"],
    "vemurafenib": ["zelboraf"],
    "dabrafenib": ["tafinlar"],
    "trametinib": ["mekinist"],
    "cobimetinib": ["cotellic"],
    "binimetinib": ["mektovi"],
    "encorafenib": ["braftovi"],
    "selumetinib": ["koselugo"],
}

# Known drug owners - maps canonical drug name to owner company name
# This prevents misattribution when drugs are used as comparators in other companies' trials
KNOWN_DRUG_OWNERS = {
    # IDEAYA assets
    "darovasertib": {"owner": "IDEAYA Biosciences", "modality": "small_molecule", "targets": ["PKC"], "fda_approved": False},
    # Immunocore assets
    "tebentafusp": {"owner": "Immunocore", "modality": "bispecific", "targets": ["gp100", "CD3"], "fda_approved": True, "brand_name": "KIMMTRAK", "approval_date": "2022-01-25"},
    # Merck assets
    "pembrolizumab": {"owner": "Merck", "modality": "antibody", "targets": ["PD-1"], "fda_approved": True, "brand_name": "Keytruda"},
    # BMS assets
    "nivolumab": {"owner": "Bristol-Myers Squibb", "modality": "antibody", "targets": ["PD-1"], "fda_approved": True, "brand_name": "Opdivo"},
    "ipilimumab": {"owner": "Bristol-Myers Squibb", "modality": "antibody", "targets": ["CTLA-4"], "fda_approved": True, "brand_name": "Yervoy"},
    "relatlimab": {"owner": "Bristol-Myers Squibb", "modality": "antibody", "targets": ["LAG-3"], "fda_approved": True, "brand_name": "Opdualag"},
    # Pfizer assets
    "crizotinib": {"owner": "Pfizer", "modality": "small_molecule", "targets": ["ALK", "MET", "ROS1"], "fda_approved": True, "brand_name": "Xalkori"},
    # Roche/Genentech assets
    "atezolizumab": {"owner": "Roche", "modality": "antibody", "targets": ["PD-L1"], "fda_approved": True, "brand_name": "Tecentriq"},
    # AstraZeneca assets
    "durvalumab": {"owner": "AstraZeneca", "modality": "antibody", "targets": ["PD-L1"], "fda_approved": True, "brand_name": "Imfinzi"},
    "tremelimumab": {"owner": "AstraZeneca", "modality": "antibody", "targets": ["CTLA-4"], "fda_approved": True, "brand_name": "Imjudo"},
    # Bayer assets
    "sorafenib": {"owner": "Bayer", "modality": "small_molecule", "targets": ["RAF", "VEGFR"], "fda_approved": True, "brand_name": "Nexavar"},
    # Pfizer assets
    "sunitinib": {"owner": "Pfizer", "modality": "small_molecule", "targets": ["VEGFR", "PDGFR"], "fda_approved": True, "brand_name": "Sutent"},
    # Roche assets
    "vemurafenib": {"owner": "Roche", "modality": "small_molecule", "targets": ["BRAF"], "fda_approved": True, "brand_name": "Zelboraf"},
    # Novartis assets
    "dabrafenib": {"owner": "Novartis", "modality": "small_molecule", "targets": ["BRAF"], "fda_approved": True, "brand_name": "Tafinlar"},
    "trametinib": {"owner": "Novartis", "modality": "small_molecule", "targets": ["MEK"], "fda_approved": True, "brand_name": "Mekinist"},
    # Array/Pfizer assets
    "binimetinib": {"owner": "Pfizer", "modality": "small_molecule", "targets": ["MEK"], "fda_approved": True, "brand_name": "Mektovi"},
    "encorafenib": {"owner": "Pfizer", "modality": "small_molecule", "targets": ["BRAF"], "fda_approved": True, "brand_name": "Braftovi"},
    # AstraZeneca/Merck assets
    "selumetinib": {"owner": "AstraZeneca", "modality": "small_molecule", "targets": ["MEK"], "fda_approved": True, "brand_name": "Koselugo"},
    # Generic/off-patent drugs - no specific owner
    "dacarbazine": {"owner": None, "modality": "chemotherapy", "targets": [], "fda_approved": True, "is_generic": True},
    "temozolomide": {"owner": None, "modality": "chemotherapy", "targets": [], "fda_approved": True, "is_generic": True},
}

# Company name normalization - maps variations to canonical names
COMPANY_NAME_ALIASES = {
    "ideaya biosciences": "IDEAYA Biosciences",
    "ideaya": "IDEAYA Biosciences",
    "immunocore ltd": "Immunocore",
    "immunocore limited": "Immunocore",
    "immunocore holdings": "Immunocore",
    "merck sharp & dohme": "Merck",
    "merck & co": "Merck",
    "msd": "Merck",
    "bristol-myers squibb": "Bristol-Myers Squibb",
    "bristol myers squibb": "Bristol-Myers Squibb",
    "bms": "Bristol-Myers Squibb",
    "pfizer inc": "Pfizer",
    "f. hoffmann-la roche": "Roche",
    "hoffmann-la roche": "Roche",
    "genentech": "Roche",
    "astrazeneca": "AstraZeneca",
    "novartis pharmaceuticals": "Novartis",
    "novartis ag": "Novartis",
}

# Reverse lookup: alias -> canonical name
ALIAS_TO_CANONICAL = {}
for canonical, aliases in DRUG_ALIASES.items():
    ALIAS_TO_CANONICAL[canonical.lower()] = canonical
    for alias in aliases:
        ALIAS_TO_CANONICAL[alias.lower()] = canonical

# Known modality patterns
MODALITY_PATTERNS = {
    "antibody": [
        r"mab$", r"umab$", r"zumab$", r"ximab$", r"mumab$",
        r"anti-\w+\s+antibod", r"monoclonal antibod"
    ],
    "small_molecule": [
        r"tinib$", r"nib$", r"afenib$", r"fenic$",
        r"small molecule", r"inhibitor$"
    ],
    "cell_therapy": [
        r"car-t", r"car t", r"til\s+therap", r"adoptive cell",
        r"autologous", r"lymphocyte"
    ],
    "vaccine": [
        r"vaccine", r"vaccination", r"mrna-\d+", r"bnt\d+",
        r"immunization"
    ],
    "bispecific": [
        r"bispecific", r"bi-specific", r"duobody", r"bite"
    ],
    "adc": [
        r"antibody.drug.conjugate", r"adc\b", r"vedotin", r"emtansine",
        r"maytansine", r"mertansine"
    ],
    "gene_therapy": [
        r"gene therap", r"aav", r"adeno.associated", r"lentivir"
    ],
    "oncolytic_virus": [
        r"oncolytic", r"talimogene", r"t-vec", r"imlygic"
    ],
    "checkpoint_inhibitor": [
        r"pd-1", r"pd-l1", r"ctla-4", r"lag-3", r"tim-3",
        r"checkpoint inhibitor"
    ]
}

# Known target patterns
TARGET_PATTERNS = {
    "PD-1": [r"pd-?1\b", r"programmed death.?1", r"pdcd1"],
    "PD-L1": [r"pd-?l1\b", r"programmed death.ligand.?1", r"cd274"],
    "CTLA-4": [r"ctla-?4\b", r"cd152"],
    "LAG-3": [r"lag-?3\b", r"cd223"],
    "BRAF": [r"\bbraf\b", r"b-raf"],
    "MEK": [r"\bmek\b", r"\bmek1\b", r"\bmek2\b", r"map2k"],
    "c-MET": [r"c-?met\b", r"\bmet\b", r"hgfr"],
    "VEGF": [r"\bvegf\b", r"vascular endothelial growth factor"],
    "EGFR": [r"\begfr\b", r"erbb1", r"her1"],
    "HER2": [r"\bher2\b", r"erbb2", r"neu"],
    "CD40": [r"\bcd40\b"],
    "OX40": [r"\box40\b", r"cd134"],
    "TIGIT": [r"\btigit\b"],
    "TIM-3": [r"tim-?3\b", r"havcr2"],
    "gp100": [r"\bgp100\b", r"pmel", r"melanoma antigen"],
}


class NormalizationService:
    """Service for normalizing and enriching asset/intervention data."""
    
    def __init__(self):
        self.llm_enabled = settings.llm_enrichment_enabled
    
    def normalize_intervention(self, intervention: str) -> Optional[Dict[str, Any]]:
        """
        Normalize an intervention name.
        
        Returns:
            Dict with normalized name and synonyms, or None if should be filtered
        """
        if not intervention:
            return None
        
        # Trim and clean
        name = intervention.strip()
        
        # Skip placebo and common non-drug interventions
        skip_patterns = [
            r"^placebo$",
            r"^sham",
            r"^standard\s+of\s+care$",
            r"^best\s+supportive\s+care$",
            r"^observation$",
            r"^no\s+intervention$",
            r"^waitlist",
            r"^\s*$"
        ]
        
        name_lower = name.lower()
        for pattern in skip_patterns:
            if re.match(pattern, name_lower, re.IGNORECASE):
                return None
        
        # Remove dosage information
        name = self._remove_dosage(name)
        
        # Remove parenthetical content (often dose or formulation details)
        name = re.sub(r"\s*\([^)]*\)\s*", " ", name).strip()
        
        # Split combination therapies
        combos = self._split_combinations(name)
        
        # For combinations, normalize each component
        if len(combos) > 1:
            # Return the first component as primary, others as related
            primary = self._normalize_single(combos[0])
            if primary:
                return {
                    "name": primary["name"],
                    "synonyms": primary.get("synonyms", []),
                    "combination_with": [self._normalize_single(c)["name"] for c in combos[1:] if self._normalize_single(c)]
                }
        
        return self._normalize_single(name)
    
    def _normalize_single(self, name: str) -> Optional[Dict[str, Any]]:
        """Normalize a single drug name."""
        if not name:
            return None
        
        name = name.strip()
        name_lower = name.lower()
        
        # Check if this is a known alias
        canonical = ALIAS_TO_CANONICAL.get(name_lower)
        if canonical:
            # Find all synonyms for this drug
            all_synonyms = [name] if name.lower() != canonical.lower() else []
            if canonical in DRUG_ALIASES:
                all_synonyms.extend([a for a in DRUG_ALIASES[canonical] if a.lower() != name_lower])
            
            return {
                "name": canonical,
                "synonyms": list(set(all_synonyms))
            }
        
        # Not a known drug - return cleaned name
        # Capitalize first letter of each word
        clean_name = " ".join(word.capitalize() for word in name.split())
        
        return {
            "name": clean_name,
            "synonyms": []
        }
    
    def _remove_dosage(self, name: str) -> str:
        """Remove dosage/concentration information from name."""
        # Patterns for dosage info
        patterns = [
            r"\s*\d+\.?\d*\s*(mg|g|ml|mcg|ug|µg|iu|units?)\s*(/\s*(kg|m2|day|week))?\s*",
            r"\s*\d+\.?\d*\s*%\s*",
            r"\s*q\d+[dwmh]\s*",  # q2w, q3d, etc.
            r"\s*every\s+\d+\s+(days?|weeks?|months?)\s*",
        ]
        
        result = name
        for pattern in patterns:
            result = re.sub(pattern, " ", result, flags=re.IGNORECASE)
        
        return result.strip()
    
    def _split_combinations(self, name: str) -> List[str]:
        """Split combination therapy names."""
        # Common combination separators
        separators = [
            r"\s+\+\s+",
            r"\s+plus\s+",
            r"\s+and\s+",
            r"\s+with\s+",
            r"\s+in\s+combination\s+with\s+",
            r"\s*/\s+",
            r"\s+combined\s+with\s+"
        ]
        
        pattern = "|".join(separators)
        parts = re.split(pattern, name, flags=re.IGNORECASE)
        
        return [p.strip() for p in parts if p.strip()]
    
    def enrich_asset(
        self,
        name: str,
        conditions: List[str],
        source_url: str
    ) -> Dict[str, Any]:
        """
        Enrich an asset with modality and target information.
        Uses pattern matching first, then optionally LLM.
        
        Returns:
            Dict with modality, targets, and confidence scores
        """
        result = {
            "modality": None,
            "targets": [],
            "modality_confidence": None,
            "targets_confidence": None
        }
        
        # Try pattern-based detection first
        modality = self._detect_modality(name)
        if modality:
            result["modality"] = modality
            result["modality_confidence"] = 0.8  # Pattern match confidence
        
        targets = self._detect_targets(name, conditions)
        if targets:
            result["targets"] = targets
            result["targets_confidence"] = 0.8
        
        # Optional LLM enrichment
        if self.llm_enabled and (not modality or not targets):
            llm_result = self._llm_enrich(name, conditions, source_url)
            if llm_result:
                if not result["modality"] and llm_result.get("modality"):
                    result["modality"] = llm_result["modality"]
                    result["modality_confidence"] = llm_result.get("modality_confidence", 0.6)
                
                if not result["targets"] and llm_result.get("targets"):
                    result["targets"] = llm_result["targets"]
                    result["targets_confidence"] = llm_result.get("targets_confidence", 0.6)
        
        return result
    
    def _detect_modality(self, name: str) -> Optional[str]:
        """Detect modality from drug name patterns."""
        name_lower = name.lower()
        
        for modality, patterns in MODALITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, name_lower, re.IGNORECASE):
                    return modality
        
        return None
    
    def _detect_targets(self, name: str, conditions: List[str]) -> List[str]:
        """Detect molecular targets from name and conditions."""
        targets = []
        combined_text = f"{name} {' '.join(conditions)}".lower()
        
        for target, patterns in TARGET_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    if target not in targets:
                        targets.append(target)
                    break
        
        return targets
    
    def _llm_enrich(
        self,
        name: str,
        conditions: List[str],
        source_url: str
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to enrich asset information.
        Only called if LLM enrichment is enabled.
        """
        if not settings.openai_api_key:
            return None
        
        try:
            import openai
            
            client = openai.OpenAI(api_key=settings.openai_api_key)
            
            prompt = f"""Given this drug/intervention name and associated conditions, extract structured information.

Drug name: {name}
Conditions: {', '.join(conditions[:5])}

Return a JSON object with:
- modality: one of [antibody, small_molecule, cell_therapy, vaccine, bispecific, adc, gene_therapy, oncolytic_virus, checkpoint_inhibitor, peptide, protein, radiation, other]
- targets: list of molecular targets (e.g., ["PD-1", "CTLA-4"])
- modality_confidence: 0.0-1.0
- targets_confidence: 0.0-1.0

If uncertain, use lower confidence scores. If unknown, set to null.
Return only valid JSON, no explanation."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=200
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            # Add evidence tracking
            result["evidence"] = {
                "source_type": "llm_enrichment",
                "source_url": source_url,
                "input_fields": ["name", "conditions"]
            }
            
            return result
            
        except Exception as e:
            logger.warning(f"LLM enrichment failed: {e}")
            return None
    
    def get_canonical_name(self, name: str) -> str:
        """Get the canonical name for a drug."""
        normalized = self.normalize_intervention(name)
        if normalized:
            return normalized["name"]
        return name
    
    def get_drug_owner_info(self, drug_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the known owner and metadata for a drug.
        
        Returns:
            Dict with owner, modality, targets, fda_approved, brand_name etc.
            or None if drug is not in known database.
        """
        canonical = self.get_canonical_name(drug_name).lower()
        return KNOWN_DRUG_OWNERS.get(canonical)
    
    def is_proprietary_to_sponsor(self, drug_name: str, sponsor_name: str) -> bool:
        """
        Check if a drug is proprietary to a given sponsor.
        
        Returns True if:
        - Drug is in KNOWN_DRUG_OWNERS and owner matches sponsor
        - Drug code name starts with sponsor's prefix (e.g., IDE for IDEAYA)
        - Drug is not a generic/off-patent drug
        
        Returns False if:
        - Drug is owned by a different company
        - Drug is a generic
        """
        canonical = self.get_canonical_name(drug_name).lower()
        drug_info = KNOWN_DRUG_OWNERS.get(canonical)
        
        if drug_info:
            # Known drug - check if owner matches
            owner = drug_info.get("owner")
            if owner is None:
                # Generic drug - not proprietary to anyone
                return False
            
            # Normalize sponsor name for comparison
            sponsor_lower = sponsor_name.lower()
            sponsor_canonical = COMPANY_NAME_ALIASES.get(sponsor_lower, sponsor_name)
            
            # Check if owner matches (case-insensitive partial match)
            owner_lower = owner.lower()
            if owner_lower in sponsor_lower or sponsor_lower in owner_lower:
                return True
            if sponsor_canonical.lower() == owner_lower:
                return True
            
            return False
        
        # Unknown drug - use heuristics
        drug_lower = drug_name.lower()
        sponsor_lower = sponsor_name.lower()
        
        # Check for company code prefixes in drug name
        company_prefixes = {
            "ideaya": ["ide"],
            "immunocore": ["imc", "ime"],
            "merck": ["mk"],
            "bristol-myers squibb": ["bms", "mdx"],
            "pfizer": ["pf"],
            "astrazeneca": ["medi", "az"],
            "novartis": ["nvs", "lxs"],
            "roche": ["ro", "rg"],
            "genentech": ["gne"],
        }
        
        for company, prefixes in company_prefixes.items():
            if company in sponsor_lower:
                for prefix in prefixes:
                    if drug_lower.startswith(prefix) or f"-{prefix}" in drug_lower:
                        return True
        
        # If drug has no known owner and doesn't match sponsor prefix, 
        # be conservative and don't assume ownership
        return False
    
    def normalize_company_name(self, name: str) -> str:
        """Normalize a company name to its canonical form."""
        name_lower = name.lower().strip()
        return COMPANY_NAME_ALIASES.get(name_lower, name)
    
    def enrich_asset_with_known_data(self, drug_name: str) -> Dict[str, Any]:
        """
        Enrich asset with known drug owner data.
        
        Returns dict with modality, targets, fda_approved, brand_name if known.
        """
        canonical = self.get_canonical_name(drug_name).lower()
        drug_info = KNOWN_DRUG_OWNERS.get(canonical, {})
        
        return {
            "known_owner": drug_info.get("owner"),
            "modality": drug_info.get("modality"),
            "targets": drug_info.get("targets", []),
            "fda_approved": drug_info.get("fda_approved"),
            "brand_name": drug_info.get("brand_name"),
            "is_generic": drug_info.get("is_generic", False),
        }


# Singleton instance
_normalization_service: Optional[NormalizationService] = None


def get_normalization_service() -> NormalizationService:
    """Get or create normalization service singleton."""
    global _normalization_service
    if _normalization_service is None:
        _normalization_service = NormalizationService()
    return _normalization_service
