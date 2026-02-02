"""
Tests for the ClinicalTrials.gov ingestion service.
"""
import pytest
import json
from datetime import datetime
from app.services.clinicaltrials_service import ClinicalTrialsService
from app.models.nodes import Trial, Document, Evidence


@pytest.fixture
def ct_service():
    return ClinicalTrialsService()


@pytest.fixture
def sample_trial_response():
    """Sample trial data from CT.gov API."""
    return {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT12345678",
                "briefTitle": "Study of Drug X in Uveal Melanoma",
                "officialTitle": "A Phase 2 Study of Drug X in Patients with Metastatic Uveal Melanoma"
            },
            "statusModule": {
                "overallStatus": "RECRUITING",
                "startDateStruct": {
                    "date": "2023-01-15"
                },
                "primaryCompletionDateStruct": {
                    "date": "2025-12-31"
                },
                "enrollmentInfo": {
                    "count": 100
                }
            },
            "designModule": {
                "phases": ["PHASE2"],
                "studyType": "INTERVENTIONAL"
            },
            "conditionsModule": {
                "conditions": ["Uveal Melanoma", "Metastatic Uveal Melanoma"]
            },
            "armsInterventionsModule": {
                "interventions": [
                    {
                        "name": "Pembrolizumab",
                        "type": "DRUG"
                    },
                    {
                        "name": "Placebo",
                        "type": "DRUG"
                    }
                ]
            },
            "sponsorCollaboratorsModule": {
                "leadSponsor": {
                    "name": "Merck Sharp & Dohme LLC",
                    "class": "INDUSTRY"
                },
                "collaborators": [
                    {
                        "name": "National Cancer Institute",
                        "class": "NIH"
                    }
                ]
            },
            "descriptionModule": {
                "briefSummary": "This study evaluates the safety and efficacy of pembrolizumab in uveal melanoma."
            }
        }
    }


class TestParseTrialBasics:
    """Tests for basic trial parsing."""
    
    def test_parse_nct_id(self, ct_service, sample_trial_response):
        """Test NCT ID is extracted correctly."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert trial.trial_id == "NCT12345678"
    
    def test_parse_title(self, ct_service, sample_trial_response):
        """Test title is extracted correctly."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert trial.title == "Study of Drug X in Uveal Melanoma"
    
    def test_parse_phase(self, ct_service, sample_trial_response):
        """Test phase is extracted correctly."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert trial.phase == "PHASE2"
    
    def test_parse_status(self, ct_service, sample_trial_response):
        """Test status is extracted correctly."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert trial.status == "RECRUITING"
    
    def test_parse_enrollment(self, ct_service, sample_trial_response):
        """Test enrollment is extracted correctly."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert trial.enrollment == 100


class TestParseTrialDates:
    """Tests for date parsing."""
    
    def test_parse_start_date(self, ct_service, sample_trial_response):
        """Test start date is parsed correctly."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert trial.start_date is not None
        assert trial.start_date.year == 2023
        assert trial.start_date.month == 1
        assert trial.start_date.day == 15
    
    def test_parse_completion_date(self, ct_service, sample_trial_response):
        """Test completion date is parsed correctly."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert trial.completion_date is not None
        assert trial.completion_date.year == 2025


class TestParseTrialInterventions:
    """Tests for intervention parsing."""
    
    def test_interventions_extracted(self, ct_service, sample_trial_response):
        """Test interventions are extracted."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert len(interventions) > 0
    
    def test_placebo_filtered(self, ct_service, sample_trial_response):
        """Test placebo is filtered from interventions."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert "Placebo" not in interventions
        assert "Pembrolizumab" in interventions


class TestParseTrialSponsors:
    """Tests for sponsor parsing."""
    
    def test_lead_sponsor_extracted(self, ct_service, sample_trial_response):
        """Test lead sponsor is extracted."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert len(sponsors) > 0
        assert "Merck Sharp & Dohme LLC" in sponsors
    
    def test_collaborators_extracted(self, ct_service, sample_trial_response):
        """Test collaborators are extracted."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert len(collaborators) > 0
        assert "National Cancer Institute" in collaborators
    
    def test_sponsors_in_trial_object(self, ct_service, sample_trial_response):
        """Test sponsors are stored in trial object."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert trial.sponsors == sponsors


class TestParseTrialConditions:
    """Tests for condition parsing."""
    
    def test_conditions_extracted(self, ct_service, sample_trial_response):
        """Test conditions are extracted."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert len(trial.conditions) == 2
        assert "Uveal Melanoma" in trial.conditions


class TestDocumentCreation:
    """Tests for document node creation."""
    
    def test_document_created(self, ct_service, sample_trial_response):
        """Test document is created."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert doc is not None
        assert doc.doc_type == "clinical_trial"
    
    def test_document_has_url(self, ct_service, sample_trial_response):
        """Test document has correct URL."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert doc.url == "https://clinicaltrials.gov/study/NCT12345678"
    
    def test_document_has_hash(self, ct_service, sample_trial_response):
        """Test document has content hash."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert doc.text_hash is not None
        assert len(doc.text_hash) == 64  # SHA256 hex length


class TestEvidence:
    """Tests for evidence tracking."""
    
    def test_trial_has_evidence(self, ct_service, sample_trial_response):
        """Test trial has evidence attached."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert len(trial.evidence) > 0
    
    def test_evidence_has_source_type(self, ct_service, sample_trial_response):
        """Test evidence has correct source type."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert trial.evidence[0].source_type == "clinicaltrials"
    
    def test_evidence_has_source_url(self, ct_service, sample_trial_response):
        """Test evidence has source URL."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert trial.evidence[0].source_url is not None
        assert "NCT12345678" in trial.evidence[0].source_url
    
    def test_evidence_has_source_id(self, ct_service, sample_trial_response):
        """Test evidence has source ID."""
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(sample_trial_response)
        assert trial.evidence[0].source_id == "NCT12345678"


class TestPhaseToStage:
    """Tests for phase to stage conversion."""
    
    def test_phase1_conversion(self, ct_service):
        """Test Phase 1 converts to phase1."""
        assert ct_service._phase_to_stage("PHASE1") == "phase1"
    
    def test_phase2_conversion(self, ct_service):
        """Test Phase 2 converts to phase2."""
        assert ct_service._phase_to_stage("PHASE2") == "phase2"
    
    def test_phase3_conversion(self, ct_service):
        """Test Phase 3 converts to phase3."""
        assert ct_service._phase_to_stage("PHASE3") == "phase3"
    
    def test_phase4_conversion(self, ct_service):
        """Test Phase 4 converts to approved."""
        assert ct_service._phase_to_stage("PHASE4") == "approved"
    
    def test_early_phase_conversion(self, ct_service):
        """Test Early Phase 1 converts to phase1."""
        assert ct_service._phase_to_stage("EARLY_PHASE1") == "phase1"
    
    def test_none_phase(self, ct_service):
        """Test None phase returns None."""
        assert ct_service._phase_to_stage(None) is None


class TestEdgeCases:
    """Tests for edge cases in parsing."""
    
    def test_missing_phase(self, ct_service):
        """Test handling of missing phase."""
        trial_data = {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT00000001",
                    "briefTitle": "Test Trial"
                },
                "statusModule": {
                    "overallStatus": "COMPLETED"
                },
                "designModule": {},
                "conditionsModule": {
                    "conditions": ["Test Condition"]
                },
                "armsInterventionsModule": {
                    "interventions": []
                },
                "sponsorCollaboratorsModule": {
                    "leadSponsor": {
                        "name": "Test Sponsor"
                    }
                },
                "descriptionModule": {}
            }
        }
        
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(trial_data)
        assert trial.phase is None
    
    def test_missing_interventions(self, ct_service):
        """Test handling of missing interventions."""
        trial_data = {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT00000002",
                    "briefTitle": "Observational Study"
                },
                "statusModule": {
                    "overallStatus": "COMPLETED"
                },
                "designModule": {
                    "studyType": "OBSERVATIONAL"
                },
                "conditionsModule": {
                    "conditions": ["Test Condition"]
                },
                "armsInterventionsModule": {},
                "sponsorCollaboratorsModule": {
                    "leadSponsor": {
                        "name": "Test Sponsor"
                    }
                },
                "descriptionModule": {}
            }
        }
        
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(trial_data)
        assert len(interventions) == 0
    
    def test_empty_sponsor(self, ct_service):
        """Test handling when sponsor module is incomplete."""
        trial_data = {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT00000003",
                    "briefTitle": "Test Trial"
                },
                "statusModule": {
                    "overallStatus": "COMPLETED"
                },
                "designModule": {},
                "conditionsModule": {
                    "conditions": ["Test Condition"]
                },
                "armsInterventionsModule": {},
                "sponsorCollaboratorsModule": {}
            }
        }
        
        trial, doc, interventions, sponsors, collaborators = ct_service.parse_trial(trial_data)
        assert len(sponsors) == 0
        assert len(collaborators) == 0
