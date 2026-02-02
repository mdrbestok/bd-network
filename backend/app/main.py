"""
Biotech Deal Network - FastAPI Application
"""
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Check if using SQLite
USE_SQLITE = os.getenv("USE_SQLITE", "true").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Biotech Deal Network API...")
    logger.info(f"Default indication: {settings.default_indication}")
    logger.info(f"Database mode: {'SQLite' if USE_SQLITE else 'Neo4j'}")
    
    # Initialize database schema
    try:
        if USE_SQLITE:
            from .services.sqlite_service import get_sqlite_service
            db = get_sqlite_service()
            db.init_schema()
        else:
            from .services.neo4j_service import get_neo4j_service
            db = get_neo4j_service()
            db.init_schema()
        logger.info("Database schema initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Biotech Deal Network API...")
    try:
        if not USE_SQLITE:
            from .services.neo4j_service import get_neo4j_service
            neo4j = get_neo4j_service()
            neo4j.close()
    except Exception:
        pass


# Create FastAPI app
app = FastAPI(
    title="Biotech Deal Network API",
    description="Graph-first, asset-aware biotech deal network with clinical trial data.",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://frontend:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
        "api_prefix": "/api"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
