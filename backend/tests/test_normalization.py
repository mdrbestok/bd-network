"""
Tests for the normalization service.
"""
import pytest
from app.services.normalization_service import NormalizationService


@pytest.fixture
def normalization_service():
    return NormalizationService()


class TestNormalizeIntervention:
    """Tests for intervention name normalization."""
    
    def test_basic_normalization(self, normalization_service):
        """Test basic drug name cleanup."""
        result = normalization_service.normalize_intervention("  Pembrolizumab  ")
        assert result is not None
        assert result["name"] == "pembrolizumab"
    
    def test_known_alias_resolution(self, normalization_service):
        """Test that known aliases resolve to canonical names."""
        # Keytruda should resolve to pembrolizumab
        result = normalization_service.normalize_intervention("Keytruda")
        assert result is not None
        assert result["name"] == "pembrolizumab"
        assert "keytruda" in [s.lower() for s in result.get("synonyms", [])] or result["name"] == "pembrolizumab"
    
    def test_another_alias(self, normalization_service):
        """Test another alias resolution."""
        result = normalization_service.normalize_intervention("Opdivo")
        assert result is not None
        assert result["name"] == "nivolumab"
    
    def test_placebo_filtered(self, normalization_service):
        """Test that placebo is filtered out."""
        result = normalization_service.normalize_intervention("Placebo")
        assert result is None
    
    def test_sham_filtered(self, normalization_service):
        """Test that sham procedures are filtered out."""
        result = normalization_service.normalize_intervention("Sham procedure")
        assert result is None
    
    def test_dosage_removal(self, normalization_service):
        """Test that dosage information is removed."""
        result = normalization_service.normalize_intervention("Pembrolizumab 200mg")
        assert result is not None
        assert "mg" not in result["name"].lower()
        assert "200" not in result["name"]
    
    def test_dosage_per_kg_removal(self, normalization_service):
        """Test that per-kg dosage is removed."""
        result = normalization_service.normalize_intervention("Nivolumab 3mg/kg")
        assert result is not None
        assert "mg" not in result["name"].lower()
        assert "kg" not in result["name"].lower()
    
    def test_combination_split(self, normalization_service):
        """Test that combination therapies are identified."""
        result = normalization_service.normalize_intervention("Ipilimumab + Nivolumab")
        assert result is not None
        # Should return first drug as primary
        assert result["name"] == "ipilimumab"
        # Should identify combination
        assert "combination_with" in result
    
    def test_combination_with_plus(self, normalization_service):
        """Test combination with 'plus' separator."""
        result = normalization_service.normalize_intervention("Pembrolizumab plus Chemotherapy")
        assert result is not None
        assert result["name"] == "pembrolizumab"
    
    def test_unknown_drug_capitalized(self, normalization_service):
        """Test that unknown drugs are capitalized properly."""
        result = normalization_service.normalize_intervention("experimental drug xyz")
        assert result is not None
        assert result["name"] == "Experimental Drug Xyz"
    
    def test_empty_string_handled(self, normalization_service):
        """Test that empty strings are handled."""
        result = normalization_service.normalize_intervention("")
        assert result is None
    
    def test_whitespace_only_handled(self, normalization_service):
        """Test that whitespace-only strings are handled."""
        result = normalization_service.normalize_intervention("   ")
        assert result is None


class TestModalityDetection:
    """Tests for modality detection."""
    
    def test_antibody_detection_mab_suffix(self, normalization_service):
        """Test detection of antibody modality from -mab suffix."""
        modality = normalization_service._detect_modality("pembrolizumab")
        assert modality == "antibody"
    
    def test_antibody_detection_umab_suffix(self, normalization_service):
        """Test detection from -umab suffix."""
        modality = normalization_service._detect_modality("nivolumab")
        assert modality == "antibody"
    
    def test_small_molecule_detection_nib_suffix(self, normalization_service):
        """Test detection of small molecule from -nib suffix."""
        modality = normalization_service._detect_modality("dabrafenib")
        assert modality == "small_molecule"
    
    def test_cell_therapy_detection(self, normalization_service):
        """Test detection of cell therapy."""
        modality = normalization_service._detect_modality("CAR-T cell therapy")
        assert modality == "cell_therapy"
    
    def test_vaccine_detection(self, normalization_service):
        """Test detection of vaccine modality."""
        modality = normalization_service._detect_modality("Cancer vaccine")
        assert modality == "vaccine"
    
    def test_bispecific_detection(self, normalization_service):
        """Test detection of bispecific antibody."""
        modality = normalization_service._detect_modality("Bispecific antibody XYZ")
        assert modality == "bispecific"


class TestTargetDetection:
    """Tests for molecular target detection."""
    
    def test_pd1_detection(self, normalization_service):
        """Test detection of PD-1 target."""
        targets = normalization_service._detect_targets(
            "Anti-PD-1 antibody",
            ["melanoma"]
        )
        assert "PD-1" in targets
    
    def test_pdl1_detection(self, normalization_service):
        """Test detection of PD-L1 target."""
        targets = normalization_service._detect_targets(
            "Atezolizumab",
            ["PD-L1 positive melanoma"]
        )
        assert "PD-L1" in targets
    
    def test_ctla4_detection(self, normalization_service):
        """Test detection of CTLA-4 target."""
        targets = normalization_service._detect_targets(
            "Ipilimumab",
            ["CTLA-4 blockade in melanoma"]
        )
        assert "CTLA-4" in targets
    
    def test_braf_detection(self, normalization_service):
        """Test detection of BRAF target."""
        targets = normalization_service._detect_targets(
            "BRAF inhibitor",
            ["BRAF-mutant melanoma"]
        )
        assert "BRAF" in targets
    
    def test_multiple_targets(self, normalization_service):
        """Test detection of multiple targets."""
        targets = normalization_service._detect_targets(
            "PD-1/LAG-3 combination",
            ["melanoma"]
        )
        assert "PD-1" in targets
        assert "LAG-3" in targets


class TestAssetEnrichment:
    """Tests for full asset enrichment."""
    
    def test_enrichment_returns_structure(self, normalization_service):
        """Test that enrichment returns expected structure."""
        result = normalization_service.enrich_asset(
            "pembrolizumab",
            ["melanoma", "uveal melanoma"],
            "https://clinicaltrials.gov/study/NCT12345"
        )
        
        assert "modality" in result
        assert "targets" in result
        assert "modality_confidence" in result
        assert "targets_confidence" in result
    
    def test_enrichment_detects_modality(self, normalization_service):
        """Test that enrichment detects modality for known drug."""
        result = normalization_service.enrich_asset(
            "nivolumab",
            ["melanoma"],
            "https://clinicaltrials.gov/study/NCT12345"
        )
        
        assert result["modality"] == "antibody"
        assert result["modality_confidence"] is not None
    
    def test_enrichment_with_pd1_in_condition(self, normalization_service):
        """Test target detection from condition text."""
        result = normalization_service.enrich_asset(
            "experimental drug",
            ["PD-1 refractory melanoma"],
            "https://clinicaltrials.gov/study/NCT12345"
        )
        
        assert "PD-1" in result["targets"]


class TestGetCanonicalName:
    """Tests for canonical name lookup."""
    
    def test_known_drug_canonical(self, normalization_service):
        """Test canonical name for known drug."""
        canonical = normalization_service.get_canonical_name("Keytruda")
        assert canonical == "pembrolizumab"
    
    def test_unknown_drug_returns_cleaned(self, normalization_service):
        """Test that unknown drug returns cleaned input."""
        canonical = normalization_service.get_canonical_name("some new drug")
        assert canonical == "Some New Drug"
