"""
FREEDOM Knowledge Base Service
Production-ready FastAPI service with vector search capabilities
"""

import os
import time
import asyncio
import structlog
from datetime import datetime
from contextlib import asynccontextmanager
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import get_kb_db, close_kb_db, KnowledgeBaseDB
from embeddings import get_embedding_service, EmbeddingService
from models import (
    IngestRequest, QueryRequest, IngestResponse, QueryResponse,
    HealthCheckResponse, ErrorResponse, SpecificationResult
)

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Service startup time for uptime calculation
service_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("kb_service_starting")

    # Initialize database connection
    try:
        db = await get_kb_db()
        logger.info("kb_service_started", database_initialized=True)
    except Exception as e:
        logger.error("kb_service_startup_failed", error=str(e))
        raise

    yield

    # Cleanup
    logger.info("kb_service_shutting_down")
    await close_kb_db()
    logger.info("kb_service_shutdown_complete")


# Create FastAPI app
app = FastAPI(
    title="FREEDOM Knowledge Base Service",
    description="Production-ready knowledge base with vector search for technical specifications",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_database() -> KnowledgeBaseDB:
    """Dependency to get database instance"""
    return await get_kb_db()


def get_embeddings() -> EmbeddingService:
    """Dependency to get embedding service"""
    return get_embedding_service()


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
            timestamp=datetime.utcnow().isoformat()
        ).dict()
    )


@app.get("/health", response_model=HealthCheckResponse)
async def health_check(db: KnowledgeBaseDB = Depends(get_database)):
    """Comprehensive health check endpoint"""
    try:
        start_time = time.time()

        # Get database health
        health_data = await db.health_check()

        # Add uptime
        health_data["uptime_seconds"] = time.time() - service_start_time

        processing_time = (time.time() - start_time) * 1000
        logger.info("health_check_completed", processing_time_ms=processing_time)

        return HealthCheckResponse(**health_data)

    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )


@app.post("/ingest", response_model=IngestResponse)
async def ingest_specification(
    request: IngestRequest,
    db: KnowledgeBaseDB = Depends(get_database),
    embeddings: EmbeddingService = Depends(get_embeddings)
):
    """
    Ingest a technical specification with automatic embedding generation

    This endpoint:
    1. Validates the input specification
    2. Generates vector embeddings for semantic search
    3. Stores the specification in the database
    4. Returns the specification ID
    """
    start_time = time.time()

    try:
        logger.info("ingest_request_received",
                   technology=request.technology_name,
                   component=f"{request.component_type}/{request.component_name}")

        # Extract text for embedding
        text_for_embedding = embeddings.extract_text_for_embedding(request.specification)

        # Generate embedding
        embedding = await embeddings.generate_embedding(text_for_embedding)

        # Store in database
        spec_id = await db.store_specification_with_embedding(
            technology_name=request.technology_name,
            version=request.version,
            component_type=request.component_type,
            component_name=request.component_name,
            specification=request.specification,
            source_url=request.source_url,
            embedding=embedding,
            confidence_score=request.confidence_score
        )

        processing_time = (time.time() - start_time) * 1000

        if spec_id:
            logger.info("specification_ingested_successfully",
                       spec_id=spec_id,
                       processing_time_ms=processing_time)

            return IngestResponse(
                success=True,
                specification_id=spec_id,
                message="Specification ingested successfully",
                processing_time_ms=processing_time
            )
        else:
            logger.error("specification_storage_failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store specification"
            )

    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        logger.error("ingest_failed",
                    error=str(e),
                    processing_time_ms=processing_time)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )


@app.post("/query", response_model=QueryResponse)
async def query_knowledge_base(
    request: QueryRequest,
    db: KnowledgeBaseDB = Depends(get_database),
    embeddings: EmbeddingService = Depends(get_embeddings)
):
    """
    Query the knowledge base using semantic vector search

    This endpoint:
    1. Converts the query to a vector embedding
    2. Performs similarity search against stored specifications
    3. Returns ranked results with similarity scores
    4. Filters by technology if specified
    """
    start_time = time.time()

    try:
        logger.info("query_request_received",
                   query_preview=request.query[:100],
                   limit=request.limit,
                   similarity_threshold=request.similarity_threshold)

        # Generate query embedding
        query_embedding = await embeddings.generate_embedding(request.query)

        # Perform vector search
        results = await db.vector_similarity_search(
            query_embedding=query_embedding,
            limit=request.limit,
            similarity_threshold=request.similarity_threshold
        )

        # Apply technology filter if specified
        if request.technology_filter:
            results = [
                r for r in results
                if r['technology_name'].lower() == request.technology_filter.lower()
            ]

        # Convert to response format
        spec_results = []
        for result in results:
            spec_result = SpecificationResult(
                id=str(result['id']),
                technology_name=result['technology_name'],
                version=result['version'],
                component_type=result['component_type'],
                component_name=result['component_name'],
                specification=result['specification'],
                source_url=result['source_url'],
                confidence_score=result['confidence_score'],
                similarity_score=round(result['similarity_score'], 4),
                extracted_at=datetime.fromisoformat(str(result.get('extracted_at', datetime.utcnow())))
            )
            spec_results.append(spec_result)

        processing_time = (time.time() - start_time) * 1000

        logger.info("query_completed_successfully",
                   results_count=len(spec_results),
                   processing_time_ms=processing_time)

        return QueryResponse(
            query=request.query,
            results=spec_results,
            total_results=len(spec_results),
            processing_time_ms=processing_time,
            similarity_threshold_used=request.similarity_threshold
        )

    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        logger.error("query_failed",
                    error=str(e),
                    processing_time_ms=processing_time)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}"
        )


@app.get("/stats")
async def get_service_stats(db: KnowledgeBaseDB = Depends(get_database)):
    """Get service statistics"""
    try:
        # Get basic stats from database
        stats = await db.execute_query("""
            SELECT
                COUNT(*) as total_specifications,
                COUNT(DISTINCT technology_id) as unique_technologies,
                COUNT(DISTINCT component_type) as unique_component_types,
                COUNT(*) FILTER (WHERE extracted_at > NOW() - INTERVAL '24 hours') as recent_specifications,
                COUNT(*) FILTER (WHERE embedding IS NOT NULL) as specifications_with_embeddings
            FROM specifications
        """)

        # Get technology breakdown
        tech_breakdown = await db.execute_query("""
            SELECT
                t.name as technology_name,
                COUNT(s.id) as specification_count
            FROM technologies t
            LEFT JOIN specifications s ON t.id = s.technology_id
            GROUP BY t.id, t.name
            ORDER BY specification_count DESC
            LIMIT 10
        """)

        return {
            "service_uptime_seconds": time.time() - service_start_time,
            "database_stats": stats[0] if stats else {},
            "top_technologies": tech_breakdown,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error("stats_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
        log_config=None  # Use structlog instead
    )