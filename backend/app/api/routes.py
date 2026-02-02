"""
API routes for the Biotech Deal Network.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..services.graph_service import get_graph_service
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Request/Response Models ====================

class HealthResponse(BaseModel):
    status: str
    database: str
    stats: dict


class IngestRequest(BaseModel):
    indication_terms: Optional[List[str]] = None
    indication: str = "MuM"
    max_trials: Optional[int] = None


class IngestResponse(BaseModel):
    status: str
    indication: str
    stats: dict


class SearchResult(BaseModel):
    companies: List[dict]
    assets: List[dict]
    trials: List[dict]


class GraphResponse(BaseModel):
    nodes: List[dict]
    edges: List[dict]


class LandscapeResponse(BaseModel):
    indication: str
    assets_by_phase: List[dict]
    sponsors_by_trial_count: List[dict]
    modalities: List[dict]
    targets: List[dict]
    total_trials: int
    total_assets: int
    total_companies: int
    standard_of_care: dict


# ==================== Endpoints ====================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    Returns database status and basic stats.
    """
    try:
        graph_service = get_graph_service()
        stats = graph_service.get_stats()
        
        return HealthResponse(
            status="healthy",
            database="connected",
            stats=stats
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            database=f"error: {str(e)}",
            stats={}
        )


@router.post("/ingest/clinicaltrials", response_model=IngestResponse)
async def ingest_clinical_trials(request: IngestRequest):
    """
    Ingest clinical trials for an indication.
    
    This endpoint:
    1. Fetches trials from ClinicalTrials.gov for the given indication
    2. Extracts companies (sponsors) and assets (interventions)
    3. Creates nodes and relationships in the graph
    """
    try:
        graph_service = get_graph_service()
        
        # Ensure schema is initialized
        graph_service.init_database()
        
        # Run ingestion
        stats = graph_service.ingest_indication(
            indication=request.indication,
            max_trials=request.max_trials
        )
        
        return IngestResponse(
            status="completed",
            indication=request.indication,
            stats=stats
        )
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=SearchResult)
async def search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, le=100, description="Maximum results per type")
):
    """
    Search across companies, assets, and trials.
    """
    try:
        graph_service = get_graph_service()
        results = graph_service.search(q, limit)
        
        return SearchResult(
            companies=results.get("companies", []),
            assets=results.get("assets", []),
            trials=results.get("trials", [])
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/indication", response_model=GraphResponse)
async def get_indication_graph(
    name: str = Query(..., description="Indication code (e.g., MuM)"),
    depth: int = Query(2, ge=1, le=10, description="Graph traversal depth"),
    phases: Optional[str] = Query(None, description="Comma-separated phase filters"),
    modalities: Optional[str] = Query(None, description="Comma-separated modality filters"),
    include_trials: bool = Query(False, description="Include trial nodes in graph")
):
    """
    Get the network graph for an indication.
    
    Returns nodes and edges for visualization.
    """
    try:
        graph_service = get_graph_service()
        
        # Parse filters
        phase_filter = phases.split(",") if phases else None
        modality_filter = modalities.split(",") if modalities else None
        
        result = graph_service.get_indication_network(
            indication=name,
            depth=depth,
            phase_filter=phase_filter,
            modality_filter=modality_filter,
            include_trials=include_trials
        )
        
        return GraphResponse(
            nodes=result.get("nodes", []),
            edges=result.get("edges", [])
        )
    except Exception as e:
        logger.error(f"Graph query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{company_id}")
async def get_company(company_id: str):
    """
    Get detailed information about a company.
    
    Returns company data with related assets, trials, and deals.
    """
    try:
        graph_service = get_graph_service()
        result = graph_service.get_company_details(company_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Company not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Company query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/asset/{asset_id}")
async def get_asset(asset_id: str):
    """
    Get detailed information about an asset.
    
    Returns asset data with related trials, owners, and deals.
    """
    try:
        graph_service = get_graph_service()
        result = graph_service.get_asset_details(asset_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Asset query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trial/{trial_id}")
async def get_trial(trial_id: str):
    """
    Get detailed information about a clinical trial.
    """
    try:
        graph_service = get_graph_service()
        result = graph_service.get_trial_details(trial_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Trial not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trial query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/landscape", response_model=LandscapeResponse)
async def get_landscape(
    indication: str = Query("MuM", description="Indication code")
):
    """
    Get landscape summary for an indication.
    
    Returns statistics about assets, sponsors, modalities, and targets,
    plus a standard of care summary (if available).
    """
    try:
        graph_service = get_graph_service()
        result = graph_service.get_landscape(indication)
        
        return LandscapeResponse(
            indication=indication,
            assets_by_phase=result.get("assets_by_phase", []),
            sponsors_by_trial_count=result.get("sponsors_by_trial_count", []),
            modalities=result.get("modalities", []),
            targets=result.get("targets", []),
            total_trials=result.get("total_trials", 0),
            total_assets=result.get("total_assets", 0),
            total_companies=result.get("total_companies", 0),
            standard_of_care=result.get("standard_of_care", {})
        )
    except Exception as e:
        logger.error(f"Landscape query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/indications")
async def get_configured_indications():
    """
    Get list of configured indications and their search terms.
    """
    return {
        "default": settings.default_indication,
        "indications": settings.indication_terms
    }


@router.post("/admin/clear")
async def clear_database():
    """
    Clear all data from the database (admin/dev use only).
    """
    try:
        from ..services.neo4j_service import get_neo4j_service
        neo4j = get_neo4j_service()
        neo4j.clear_database()
        
        return {"status": "cleared"}
    except Exception as e:
        logger.error(f"Clear database failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
