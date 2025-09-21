#!/usr/bin/env python3
"""
RAG API Service for FREEDOM Platform
FastAPI endpoint for retrieval-augmented generation
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from retrieval_service import RetrievalService, RetrievalConfig
from chunking_service import ChunkingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="FREEDOM RAG API",
    description="Retrieval-Augmented Generation for 702 Technical Specifications",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'techknowledge'),
    'user': os.getenv('DB_USER', 'arthurdell')
}

# Services
retrieval_service = None
chunking_service = None

class QueryRequest(BaseModel):
    """Request model for RAG queries"""
    query: str = Field(..., description="Search query")
    top_k: int = Field(10, description="Number of chunks to retrieve")
    rerank: bool = Field(True, description="Use MLX reranking")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters for search")
    hybrid_alpha: float = Field(0.7, description="Balance between dense and sparse search")

class QueryResponse(BaseModel):
    """Response model for RAG queries"""
    query: str
    context: str
    chunks: List[Dict[str, Any]]
    retrieval_time_ms: int
    cached: bool

class ChunkingRequest(BaseModel):
    """Request model for chunking specifications"""
    batch_size: int = Field(10, description="Number of specifications to process in batch")
    use_embeddings: bool = Field(False, description="Generate OpenAI embeddings")

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    database: str
    chunks_count: int
    timestamp: str

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global retrieval_service, chunking_service

    try:
        # Initialize retrieval service
        openai_key = os.getenv('OPENAI_API_KEY')
        retrieval_service = RetrievalService(
            DB_CONFIG,
            openai_api_key=openai_key,
            mlx_endpoint=os.getenv('MLX_ENDPOINT', 'http://localhost:8000')
        )

        # Initialize chunking service
        chunking_service = ChunkingService(DB_CONFIG, openai_api_key=openai_key)

        logger.info("Services initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    if retrieval_service:
        retrieval_service.close()
    if chunking_service:
        chunking_service.close()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        with retrieval_service.conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM document_chunks")
            chunks_count = cursor.fetchone()[0]

        return HealthResponse(
            status="healthy",
            database="connected",
            chunks_count=chunks_count,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """
    Perform RAG query on technical specifications
    """
    try:
        # Configure retrieval
        config = RetrievalConfig(
            top_k=request.top_k,
            use_reranking=request.rerank,
            hybrid_alpha=request.hybrid_alpha
        )

        # Perform retrieval
        result = await retrieval_service.retrieve(
            request.query,
            config=config,
            filters=request.filters
        )

        return QueryResponse(
            query=request.query,
            context=result['context'],
            chunks=[{
                'id': str(chunk['id']),
                'text': chunk['chunk_text'][:500] + "..." if len(chunk['chunk_text']) > 500 else chunk['chunk_text'],
                'component': chunk['component_name'],
                'technology': chunk.get('technology_name'),
                'score': chunk.get('score', 0)
            } for chunk in result['chunks']],
            retrieval_time_ms=result['retrieval_time_ms'],
            cached=result['cached']
        )

    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chunk_specifications")
async def chunk_specifications(request: ChunkingRequest):
    """
    Process and chunk specifications into the vector database
    """
    try:
        # Set OpenAI key if embeddings requested
        if request.use_embeddings and not chunking_service.openai_client:
            raise HTTPException(
                status_code=400,
                detail="OpenAI API key not configured for embeddings"
            )

        # Process specifications
        chunks_created = await chunking_service.process_all_specifications(
            batch_size=request.batch_size
        )

        return {
            "status": "success",
            "chunks_created": chunks_created,
            "message": f"Successfully processed specifications into {chunks_created} chunks"
        }

    except Exception as e:
        logger.error(f"Chunking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get statistics about the RAG system"""
    try:
        with retrieval_service.conn.cursor() as cursor:
            # Total chunks
            cursor.execute("SELECT COUNT(*) FROM document_chunks")
            total_chunks = cursor.fetchone()[0]

            # Chunks by technology
            cursor.execute("""
                SELECT technology_name, COUNT(*) as count
                FROM document_chunks
                WHERE technology_name IS NOT NULL
                GROUP BY technology_name
                ORDER BY count DESC
                LIMIT 10
            """)
            tech_distribution = cursor.fetchall()

            # Chunks by component type
            cursor.execute("""
                SELECT component_type, COUNT(*) as count
                FROM document_chunks
                GROUP BY component_type
                ORDER BY count DESC
            """)
            type_distribution = cursor.fetchall()

            # Cache stats
            cursor.execute("""
                SELECT COUNT(*) as total, SUM(hit_count) as total_hits
                FROM rag_context_cache
                WHERE expires_at > NOW()
            """)
            cache_stats = cursor.fetchone()

        return {
            "total_chunks": total_chunks,
            "technology_distribution": [
                {"technology": tech[0], "count": tech[1]}
                for tech in tech_distribution
            ],
            "type_distribution": [
                {"type": t[0], "count": t[1]}
                for t in type_distribution
            ],
            "cache": {
                "entries": cache_stats[0] if cache_stats else 0,
                "total_hits": cache_stats[1] if cache_stats else 0
            }
        }

    except Exception as e:
        logger.error(f"Stats query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
async def search_specs(
    q: str = Query(..., description="Search query"),
    technology: Optional[str] = Query(None, description="Filter by technology"),
    component_type: Optional[str] = Query(None, description="Filter by component type"),
    limit: int = Query(10, description="Number of results")
):
    """
    Search specifications using hybrid search
    """
    try:
        filters = {}
        if technology:
            filters['technology'] = technology
        if component_type:
            filters['component_type'] = component_type

        config = RetrievalConfig(top_k=limit, use_reranking=False)

        result = await retrieval_service.retrieve(
            q,
            config=config,
            filters=filters
        )

        return {
            "query": q,
            "results": [{
                'id': str(chunk['id']),
                'text': chunk['chunk_text'],
                'component': chunk['component_name'],
                'technology': chunk.get('technology_name'),
                'type': chunk['component_type'],
                'score': chunk.get('score', 0)
            } for chunk in result['chunks']],
            "total": len(result['chunks']),
            "retrieval_time_ms": result['retrieval_time_ms']
        }

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "rag_api:app",
        host="0.0.0.0",
        port=5003,
        reload=True,
        log_level="info"
    )