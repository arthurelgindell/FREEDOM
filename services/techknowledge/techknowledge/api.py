"""
TechKnowledge Service API
Exposes unified knowledge management endpoints
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import structlog
import os

from core.database import TechKnowledgeDB

# Configure logging
logger = structlog.get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="TechKnowledge Service",
    description="Unified technical knowledge management system",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
db = None

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    global db

    # Set environment for Docker PostgreSQL
    os.environ['POSTGRES_HOST'] = os.getenv('POSTGRES_HOST', 'postgres')
    os.environ['POSTGRES_DB'] = 'techknowledge'
    os.environ['POSTGRES_USER'] = os.getenv('POSTGRES_USER', 'freedom')
    os.environ['POSTGRES_PASSWORD'] = os.getenv('POSTGRES_PASSWORD', 'freedom_dev')

    db = TechKnowledgeDB()

    logger.info("techknowledge_service_started",
                host=os.environ['POSTGRES_HOST'],
                database='techknowledge')

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    global db
    if db:
        db.close()

# Request/Response models
class TechnologyResponse(BaseModel):
    id: str
    name: str
    category: str
    official_url: str
    github_repo: Optional[str]
    specifications_count: int

class SpecificationResponse(BaseModel):
    id: str
    technology_id: str
    technology_name: str
    version: str
    component_type: str
    component_name: str
    specification: Dict[str, Any]
    confidence_score: float
    source_url: Optional[str]

class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    include_specs: bool = True

# Endpoints
@app.get("/health")
async def health():
    """Health check endpoint"""
    global db
    if not db:
        raise HTTPException(status_code=503, detail="Service not initialized")

    health_status = db.health_check() if hasattr(db, 'health_check') else {}
    return {
        "status": "healthy" if health_status.get("database_connected") else "unhealthy",
        "database_connected": health_status.get("database_connected", False),
        "technologies_count": health_status.get("technologies_count", 0),
        "specifications_count": health_status.get("specifications_count", 0)
    }

@app.get("/technologies", response_model=List[TechnologyResponse])
async def get_technologies(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, description="Maximum number of results")
):
    """Get all technologies"""
    global db

    query = """
        SELECT
            t.id, t.name, t.category, t.official_url, t.github_repo,
            COUNT(s.id) as specifications_count
        FROM technologies t
        LEFT JOIN specifications s ON t.id = s.technology_id
    """

    if category:
        query += f" WHERE t.category = '{category}'"

    query += """
        GROUP BY t.id, t.name, t.category, t.official_url, t.github_repo
        ORDER BY t.created_at DESC
        LIMIT %s
    """

    results = db.execute_query(query, (limit,))

    return [TechnologyResponse(**row) for row in results]

@app.get("/technologies/{tech_id}/specifications", response_model=List[SpecificationResponse])
async def get_technology_specifications(
    tech_id: str,
    version: Optional[str] = Query(None, description="Filter by version")
):
    """Get specifications for a technology"""
    global db

    query = """
        SELECT
            s.id, s.technology_id, t.name as technology_name,
            s.version, s.component_type, s.component_name,
            s.specification, s.confidence_score, s.source_url
        FROM specifications s
        JOIN technologies t ON s.technology_id = t.id
        WHERE s.technology_id = %s
    """

    params = [tech_id]

    if version:
        query += " AND s.version = %s"
        params.append(version)

    query += " ORDER BY s.extracted_at DESC"

    results = db.execute_query(query, tuple(params))

    return [SpecificationResponse(**row) for row in results]

@app.post("/search")
async def search_knowledge(request: SearchRequest):
    """Search across technologies and specifications"""
    global db

    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")

    # Simple search across technologies and specifications
    query = """
        SELECT
            t.id, t.name, t.category, t.official_url,
            s.version, s.component_type, s.component_name
        FROM technologies t
        LEFT JOIN specifications s ON t.id = s.technology_id
        WHERE
            t.name ILIKE %s OR
            t.category ILIKE %s OR
            s.component_name ILIKE %s OR
            s.component_type ILIKE %s
        ORDER BY t.created_at DESC
        LIMIT %s
    """

    search_pattern = f"%{request.query}%"
    params = [search_pattern] * 4 + [request.limit]

    results = db.execute_query(query, tuple(params))

    return {
        "query": request.query,
        "results": results,
        "count": len(results)
    }

@app.get("/stats")
async def get_statistics():
    """Get system statistics"""
    global db

    stats = db.execute_query("""
        SELECT
            (SELECT COUNT(*) FROM technologies) as total_technologies,
            (SELECT COUNT(*) FROM specifications) as total_specifications,
            (SELECT COUNT(DISTINCT category) FROM technologies) as categories_count,
            (SELECT COUNT(DISTINCT version) FROM specifications) as versions_count,
            (SELECT COUNT(*) FROM github_validations) as github_validations,
            (SELECT COUNT(*) FROM decontamination_log) as decontaminated_items
    """)

    return stats[0] if stats else {}

@app.post("/crawl/{technology_name}")
async def trigger_crawl(technology_name: str):
    """Trigger a crawl for a specific technology"""
    # This would trigger the actual crawl process
    # For now, return a placeholder response
    return {
        "status": "crawl_initiated",
        "technology": technology_name,
        "message": f"Crawl for {technology_name} has been queued"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)