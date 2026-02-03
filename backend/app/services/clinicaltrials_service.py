"""
ClinicalTrials.gov v2 API ingestion service.
"""
import logging
import json
import httpx
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlencode

from ..config import settings
from ..models.nodes import Company, Asset, Trial, Document, Evidence
from ..models.edges import SponsorsTrial, HasTrial, Owns, ParticipatesInTrial, UsesAsComparator, EdgeEvidence

logger = logging.getLogger(__name__)


class ClinicalTrialsService:
    """Service for fetching and parsing ClinicalTrials.gov data."""
    
    BASE_URL = settings.clinicaltrials_api_base
    
    def __init__(self):
        self.client = httpx.Client(timeout=60.0)
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
    
    def _build_search_url(self, condition_terms: List[str], page_token: Optional[str] = None) -> str:
        """Build the API search URL for given condition terms."""
        # Use OR to combine terms
        condition_query = " OR ".join([f'"{term}"' for term in condition_terms])
        
        params = {
            "query.cond": condition_query,
            "pageSize": settings.clinicaltrials_page_size,
            "format": "json",
            "fields": ",".join([
                "NCTId",
                "BriefTitle",
                "OfficialTitle",
                "Phase",
                "OverallStatus",
                "StartDate",
                "PrimaryCompletionDate",
                "CompletionDate",
                "Condition",
                "InterventionName",
                "InterventionType",
                "InterventionDescription",
                "LeadSponsorName",
                "LeadSponsorClass",
                "CollaboratorName",
                "EnrollmentCount",
                "StudyType",
                "BriefSummary",
                "ArmGroupInterventionName"
            ])
        }
        
        if page_token:
            params["pageToken"] = page_token
        
        return f"{self.BASE_URL}/studies?{urlencode(params)}"
    
    def fetch_trials(
        self, 
        condition_terms: List[str], 
        max_trials: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch trials from ClinicalTrials.gov for given condition terms.
        
        Args:
            condition_terms: List of condition search terms (OR'd together)
            max_trials: Maximum number of trials to fetch
        
        Returns:
            List of raw trial records from the API
        """
        max_trials = max_trials or settings.clinicaltrials_max_trials
        all_trials = []
        page_token = None
        
        while len(all_trials) < max_trials:
            url = self._build_search_url(condition_terms, page_token)
            logger.info(f"Fetching: {url}")
            
            try:
                response = self.client.get(url)
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPError as e:
                logger.error(f"HTTP error fetching trials: {e}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                break
            
            studies = data.get("studies", [])
            if not studies:
                break
            
            all_trials.extend(studies)
            logger.info(f"Fetched {len(studies)} trials, total: {len(all_trials)}")
            
            # Check for next page
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        
        return all_trials[:max_trials]
    
    def parse_trial(self, raw_trial: Dict[str, Any]) -> Tuple[Trial, Document, List[str], List[str], List[str]]:
        """
        Parse a raw trial record into structured data.
        
        Returns:
            Tuple of (Trial, Document, interventions, sponsors, collaborators)
        """
        protocol = raw_trial.get("protocolSection", {})
        id_module = protocol.get("identificationModule", {})
        status_module = protocol.get("statusModule", {})
        design_module = protocol.get("designModule", {})
        conditions_module = protocol.get("conditionsModule", {})
        interventions_module = protocol.get("armsInterventionsModule", {})
        sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
        desc_module = protocol.get("descriptionModule", {})
        
        nct_id = id_module.get("nctId", "")
        
        # Parse dates
        start_date = self._parse_date(status_module.get("startDateStruct", {}).get("date"))
        completion_date = self._parse_date(
            status_module.get("primaryCompletionDateStruct", {}).get("date") or
            status_module.get("completionDateStruct", {}).get("date")
        )
        
        # Parse phases
        phases = design_module.get("phases", [])
        phase = phases[0] if phases else None
        
        # Parse interventions
        interventions_raw = interventions_module.get("interventions", [])
        interventions = []
        for intervention in interventions_raw:
            name = intervention.get("name", "")
            if name and intervention.get("type", "").upper() not in ["PLACEBO", "SHAM"]:
                interventions.append(name)
        
        # Parse conditions
        conditions = conditions_module.get("conditions", [])
        
        # Parse sponsors
        lead_sponsor = sponsor_module.get("leadSponsor", {})
        lead_sponsor_name = lead_sponsor.get("name", "")
        lead_sponsor_class = lead_sponsor.get("class", "")
        sponsors = [lead_sponsor_name] if lead_sponsor_name else []
        
        collaborators = []
        for collab in sponsor_module.get("collaborators", []):
            collab_name = collab.get("name", "")
            if collab_name:
                collaborators.append(collab_name)
        
        # Build source URL
        source_url = f"https://clinicaltrials.gov/study/{nct_id}"
        
        # Create evidence
        evidence = Evidence(
            source_type="clinicaltrials",
            source_url=source_url,
            source_id=nct_id,
            confidence=1.0,
            extracted_at=datetime.utcnow()
        )
        
        # Create Trial node
        trial = Trial(
            trial_id=nct_id,
            title=id_module.get("briefTitle", id_module.get("officialTitle", "")),
            phase=phase,
            status=status_module.get("overallStatus", ""),
            start_date=start_date,
            completion_date=completion_date,
            interventions=interventions,
            conditions=conditions,
            sponsors=sponsors,
            collaborators=collaborators,
            enrollment=status_module.get("enrollmentInfo", {}).get("count"),
            study_type=design_module.get("studyType", ""),
            brief_summary=desc_module.get("briefSummary", ""),
            source_url=source_url,
            evidence=[evidence]
        )
        
        # Create Document node for provenance
        doc = Document(
            doc_id=Document.generate_id(source_url),
            doc_type="clinical_trial",
            publisher="ClinicalTrials.gov",
            url=source_url,
            retrieved_at=datetime.utcnow(),
            text_hash=Document.compute_hash(json.dumps(raw_trial)),
            raw_content=json.dumps(raw_trial)
        )
        
        return trial, doc, interventions, sponsors, collaborators
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse a date string from CT.gov API."""
        if not date_str:
            return None
        
        try:
            # Try various formats
            for fmt in ["%Y-%m-%d", "%Y-%m", "%B %Y", "%B %d, %Y"]:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
        except Exception:
            pass
        
        return None
    
    def ingest_for_indication(
        self,
        indication: str,
        neo4j_service,
        normalization_service,
        max_trials: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Full ingestion pipeline for an indication.
        
        Returns:
            Statistics about what was ingested
        """
        from ..config import settings
        
        # Get search terms for this indication
        terms = settings.get_indication_terms(indication)
        logger.info(f"Ingesting trials for {indication} with terms: {terms}")
        
        # Fetch raw trials
        raw_trials = self.fetch_trials(terms, max_trials)
        logger.info(f"Fetched {len(raw_trials)} trials")
        
        stats = {
            "trials": 0,
            "companies": 0,
            "assets": 0,
            "documents": 0,
            "sponsor_relations": 0,
            "asset_trial_relations": 0,
            "ownership_relations": 0
        }
        
        seen_companies = set()
        seen_assets = set()
        
        for raw_trial in raw_trials:
            try:
                # Parse trial
                trial, doc, interventions, sponsors, collaborators = self.parse_trial(raw_trial)
                
                # Upsert trial and document
                neo4j_service.upsert_trial(trial)
                neo4j_service.upsert_document(doc)
                stats["trials"] += 1
                stats["documents"] += 1
                
                # Process sponsors as companies
                # Get lead sponsor class from the raw data for type inference
                lead_sponsor_class = raw_trial.get("protocolSection", {}).get(
                    "sponsorCollaboratorsModule", {}
                ).get("leadSponsor", {}).get("class", "")
                
                all_sponsors = sponsors + collaborators
                for i, sponsor_name in enumerate(all_sponsors):
                    if not sponsor_name:
                        continue
                    
                    company_id = Company.generate_id(sponsor_name)
                    
                    # Determine company type
                    # Lead sponsors use the sponsor class, collaborators infer from name
                    is_lead = i < len(sponsors)
                    sponsor_class_for_inference = lead_sponsor_class if is_lead else None
                    company_type = Company.infer_type_from_name(sponsor_name, sponsor_class_for_inference)
                    
                    if company_id not in seen_companies:
                        company = Company(
                            company_id=company_id,
                            name=sponsor_name,
                            company_type=company_type,
                            evidence=[Evidence(
                                source_type="clinicaltrials",
                                source_url=trial.source_url,
                                source_id=trial.trial_id,
                                confidence=1.0
                            )]
                        )
                        neo4j_service.upsert_company(company)
                        seen_companies.add(company_id)
                        stats["companies"] += 1
                    
                    role = "lead_sponsor" if is_lead else "collaborator"
                    
                    # NEW DATA MODEL:
                    # - Industry sponsors connect to trials INDIRECTLY through assets (OWNS -> Asset -> HAS_TRIAL -> Trial)
                    # - Sites/academic/investigators connect DIRECTLY via PARTICIPATES_IN_TRIAL
                    if company_type == 'industry':
                        # Industry sponsors: keep SPONSORS_TRIAL for backwards compat but don't rely on it
                        # Their main connection is through OWNS/DEVELOPS -> Asset
                        rel = SponsorsTrial(
                            company_id=company_id,
                            trial_id=trial.trial_id,
                            role=role,
                            evidence=[EdgeEvidence(
                                source_type="clinicaltrials",
                                source_url=trial.source_url,
                                source_id=trial.trial_id
                            )]
                        )
                        neo4j_service.create_sponsors_trial(rel)
                    else:
                        # Sites, academic, investigators: use PARTICIPATES_IN_TRIAL
                        rel = ParticipatesInTrial(
                            company_id=company_id,
                            trial_id=trial.trial_id,
                            role="site" if company_type in ('academic', 'site') else role,
                            evidence=[EdgeEvidence(
                                source_type="clinicaltrials",
                                source_url=trial.source_url,
                                source_id=trial.trial_id
                            )]
                        )
                        neo4j_service.create_participates_in_trial(rel)
                    stats["sponsor_relations"] += 1
                
                # Process interventions as assets
                for intervention_name in interventions:
                    if not intervention_name:
                        continue
                    
                    # Normalize the intervention name
                    normalized = normalization_service.normalize_intervention(intervention_name)
                    if not normalized:
                        continue
                    
                    asset_id = Asset.generate_id(normalized["name"])
                    
                    # Get known drug info for enrichment
                    known_info = normalization_service.enrich_asset_with_known_data(normalized["name"])
                    
                    if asset_id not in seen_assets:
                        # Enrich with modality/targets if available
                        enriched = normalization_service.enrich_asset(
                            normalized["name"],
                            trial.conditions,
                            trial.source_url
                        )
                        
                        # Prefer known data over pattern-detected data
                        final_modality = known_info.get("modality") or enriched.get("modality")
                        final_targets = known_info.get("targets") or enriched.get("targets", [])
                        
                        # Build synonyms list including brand name if known
                        synonyms = list(normalized.get("synonyms", []))
                        if known_info.get("brand_name"):
                            brand = known_info["brand_name"]
                            if brand.lower() not in [s.lower() for s in synonyms]:
                                synonyms.append(brand)
                        
                        asset = Asset(
                            asset_id=asset_id,
                            name=normalized["name"],
                            synonyms=synonyms,
                            modality=final_modality,
                            targets=final_targets,
                            indications=trial.conditions[:5],  # Limit stored indications
                            stage_current=self._phase_to_stage(trial.phase),
                            modality_confidence=0.95 if known_info.get("modality") else enriched.get("modality_confidence"),
                            targets_confidence=0.95 if known_info.get("targets") else enriched.get("targets_confidence"),
                            evidence=[Evidence(
                                source_type="clinicaltrials",
                                source_url=trial.source_url,
                                source_id=trial.trial_id,
                                confidence=1.0
                            )]
                        )
                        neo4j_service.upsert_asset(asset)
                        seen_assets.add(asset_id)
                        stats["assets"] += 1
                    
                    # Create asset-trial relationship
                    has_trial = HasTrial(
                        asset_id=asset_id,
                        trial_id=trial.trial_id,
                        evidence=[EdgeEvidence(
                            source_type="clinicaltrials",
                            source_url=trial.source_url,
                            source_id=trial.trial_id
                        )]
                    )
                    neo4j_service.create_has_trial(has_trial)
                    stats["asset_trial_relations"] += 1
                    
                    # Improved ownership/relationship logic:
                    # - Proprietary drugs: create OWNS relationship
                    # - Comparator drugs: create USES_AS_COMPARATOR relationship
                    if sponsors:
                        lead_sponsor_name = sponsors[0]
                        lead_sponsor_id = Company.generate_id(lead_sponsor_name)
                        
                        # Check if this drug is proprietary to the sponsor
                        is_proprietary = normalization_service.is_proprietary_to_sponsor(
                            normalized["name"], 
                            lead_sponsor_name
                        )
                        
                        # Also check if there's a known owner that matches
                        known_owner = known_info.get("known_owner")
                        is_generic = known_info.get("is_generic", False)
                        
                        if known_owner:
                            # If we know the owner, only create ownership if it matches
                            owner_normalized = normalization_service.normalize_company_name(known_owner)
                            sponsor_normalized = normalization_service.normalize_company_name(lead_sponsor_name)
                            is_proprietary = owner_normalized.lower() == sponsor_normalized.lower()
                        
                        if is_proprietary:
                            # Sponsor owns this asset
                            owns = Owns(
                                company_id=lead_sponsor_id,
                                asset_id=asset_id,
                                confidence=0.9 if known_owner else 0.7,
                                source="confirmed_owner" if known_owner else "inferred_from_trial",
                                is_current=True,
                                evidence=[EdgeEvidence(
                                    source_type="known_data" if known_owner else "inferred",
                                    source_url=trial.source_url,
                                    source_id=trial.trial_id,
                                    confidence=0.9 if known_owner else 0.7
                                )]
                            )
                            neo4j_service.create_owns(owns)
                            stats["ownership_relations"] += 1
                        elif not is_generic and known_owner:
                            # Non-generic drug owned by someone else - it's a comparator
                            # BUT only create this relationship for industry sponsors
                            # Sites/academic don't "use comparators" - they participate in trials
                            lead_sponsor_type = Company.infer_type_from_name(lead_sponsor_name, lead_sponsor_class)
                            if lead_sponsor_type == 'industry':
                                uses_comparator = UsesAsComparator(
                                    company_id=lead_sponsor_id,
                                    asset_id=asset_id,
                                    trial_id=trial.trial_id,
                                    evidence=[EdgeEvidence(
                                        source_type="inferred_comparator",
                                        source_url=trial.source_url,
                                        source_id=trial.trial_id,
                                        confidence=0.8
                                    )]
                                )
                                neo4j_service.create_uses_as_comparator(uses_comparator)
                                stats["ownership_relations"] += 1
                
            except Exception as e:
                logger.error(f"Error processing trial: {e}")
                continue
        
        logger.info(f"Ingestion complete: {stats}")
        return stats
    
    def _phase_to_stage(self, phase: Optional[str]) -> Optional[str]:
        """Convert CT.gov phase to our stage format."""
        if not phase:
            return None
        
        phase_lower = phase.lower()
        if "phase 3" in phase_lower:
            return "phase3"
        elif "phase 2" in phase_lower:
            return "phase2"
        elif "phase 1" in phase_lower:
            return "phase1"
        elif "phase 4" in phase_lower:
            return "approved"  # Phase 4 = post-approval
        elif "early" in phase_lower:
            return "phase1"
        
        return None


# Singleton instance
_ct_service: Optional[ClinicalTrialsService] = None


def get_clinicaltrials_service() -> ClinicalTrialsService:
    """Get or create ClinicalTrials service singleton."""
    global _ct_service
    if _ct_service is None:
        _ct_service = ClinicalTrialsService()
    return _ct_service
