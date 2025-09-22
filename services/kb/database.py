"""
FREEDOM Knowledge Base Database Layer
Salvaged and enhanced from techknowledge/core/database.py
"""

import os
import asyncio
import asyncpg
import structlog
import json
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from uuid import uuid4
import numpy as np

# Configure logging
logger = structlog.get_logger(__name__)


class KnowledgeBaseDB:
    """Production-ready async PostgreSQL connection manager for Knowledge Base service"""

    def __init__(self):
        """Initialize async connection pool with environment configuration"""
        self.host = os.getenv('POSTGRES_HOST', 'localhost')
        self.port = int(os.getenv('POSTGRES_PORT', '5432'))
        self.database = os.getenv('POSTGRES_DB', 'freedom_kb')
        self.user = os.getenv('POSTGRES_USER', 'freedom')
        self.password = os.getenv('POSTGRES_PASSWORD', 'freedom_dev')
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False

    async def initialize(self):
        """Initialize the connection pool with enhanced settings for production"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=5,
                max_size=25,
                command_timeout=30,
                server_settings={
                    'application_name': 'freedom-kb-service'
                }
            )
            self._initialized = True
            logger.info("kb_database_initialized",
                       host=self.host,
                       port=self.port,
                       database=self.database)

            # Verify pgvector extension
            await self._verify_extensions()

        except Exception as e:
            logger.error("failed_to_create_kb_pool", error=str(e))
            raise

    async def _verify_extensions(self):
        """Verify required PostgreSQL extensions are available"""
        async with self.pool.acquire() as conn:
            # Check pgvector extension
            result = await conn.fetchrow(
                "SELECT * FROM pg_extension WHERE extname = 'vector'"
            )
            if not result:
                raise RuntimeError("pgvector extension not found. Install with CREATE EXTENSION vector;")

            logger.info("pgvector_extension_verified")

    @asynccontextmanager
    async def acquire(self):
        """Get a connection from the pool with automatic transaction management"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn

    async def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dictionaries"""
        async with self.acquire() as conn:
            try:
                if params:
                    rows = await conn.fetch(query, *params)
                else:
                    rows = await conn.fetch(query)
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error("query_execution_failed", query=query[:100], error=str(e))
                raise

    async def execute_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """Execute query and return single result"""
        async with self.acquire() as conn:
            try:
                if params:
                    row = await conn.fetchrow(query, *params)
                else:
                    row = await conn.fetchrow(query)
                return dict(row) if row else None
            except Exception as e:
                logger.error("single_query_execution_failed", query=query[:100], error=str(e))
                raise

    async def insert_returning(self, query: str, params: tuple) -> Optional[Dict[str, Any]]:
        """Execute INSERT query with RETURNING clause"""
        async with self.acquire() as conn:
            try:
                row = await conn.fetchrow(query, *params)
                return dict(row) if row else None
            except Exception as e:
                logger.error("insert_returning_failed", query=query[:100], error=str(e))
                raise

    async def vector_similarity_search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search with pgvector

        Args:
            query_embedding: Query vector (1536 dimensions for OpenAI)
            limit: Maximum number of results
            similarity_threshold: Minimum cosine similarity score

        Returns:
            List of specifications with similarity scores
        """
        async with self.acquire() as conn:
            try:
                # Convert to pgvector format
                query_vector = f"[{','.join(map(str, query_embedding))}]"

                query = """
                    SELECT
                        s.id,
                        s.technology_id,
                        s.version,
                        s.component_type,
                        s.component_name,
                        s.specification,
                        s.source_url,
                        s.confidence_score,
                        t.name as technology_name,
                        1 - (s.embedding <=> $1::vector) as similarity_score
                    FROM specifications s
                    JOIN technologies t ON s.technology_id = t.id
                    WHERE s.embedding IS NOT NULL
                        AND 1 - (s.embedding <=> $1::vector) > $2
                    ORDER BY s.embedding <=> $1::vector
                    LIMIT $3
                """

                rows = await conn.fetch(query, query_vector, similarity_threshold, limit)
                return [dict(row) for row in rows]

            except Exception as e:
                logger.error("vector_search_failed", error=str(e))
                raise

    async def store_specification_with_embedding(
        self,
        technology_name: str,
        version: str,
        component_type: str,
        component_name: str,
        specification: Dict[str, Any],
        source_url: str,
        embedding: List[float],
        confidence_score: float = 1.0
    ) -> Optional[str]:
        """
        Store specification with vector embedding

        Returns:
            Specification ID if successful, None otherwise
        """
        async with self.acquire() as conn:
            try:
                # Get or create technology
                tech_result = await conn.fetchrow(
                    "SELECT id FROM technologies WHERE name = $1",
                    technology_name
                )

                if not tech_result:
                    # Create technology entry
                    tech_id = str(uuid4())
                    await conn.execute(
                        """
                        INSERT INTO technologies (id, name, category, active)
                        VALUES ($1, $2, $3, $4)
                        """,
                        tech_id, technology_name, "ingested", True
                    )
                else:
                    tech_id = tech_result['id']

                # Convert embedding to pgvector format
                embedding_vector = f"[{','.join(map(str, embedding))}]"

                # Insert specification
                spec_id = str(uuid4())
                query = """
                    INSERT INTO specifications (
                        id, technology_id, version, component_type, component_name,
                        specification, source_url, source_type, confidence_score, embedding
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::vector)
                    RETURNING id
                """

                result = await conn.fetchrow(
                    query,
                    spec_id, tech_id, version, component_type, component_name,
                    json.dumps(specification), source_url, "api_ingest", confidence_score, embedding_vector
                )

                return str(result['id']) if result else None

            except Exception as e:
                logger.error("specification_storage_failed",
                            tech_name=technology_name,
                            component_type=component_type,
                            error=str(e))
                return None

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        try:
            async with self.acquire() as conn:
                # Test basic connectivity
                result = await conn.fetchrow("SELECT 1 as alive")

                # Check pgvector extension
                vector_check = await conn.fetchrow(
                    "SELECT * FROM pg_extension WHERE extname = 'vector'"
                )

                # Count specifications
                spec_count = await conn.fetchrow(
                    "SELECT COUNT(*) as count FROM specifications"
                )

                # Check recent activity
                recent_activity = await conn.fetchrow(
                    """
                    SELECT COUNT(*) as recent_specs
                    FROM specifications
                    WHERE extracted_at > NOW() - INTERVAL '24 hours'
                    """
                )

                return {
                    "status": "healthy",
                    "database_status": "connected" if bool(result) else "disconnected",
                    "database_connected": bool(result),
                    "pgvector_available": bool(vector_check),
                    "total_specifications": spec_count['count'],
                    "recent_specifications": recent_activity['recent_specs'],
                    "timestamp": datetime.utcnow().isoformat()
                }

        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def close(self):
        """Close all connections in the pool"""
        if self.pool:
            await self.pool.close()
            self._initialized = False
            logger.info("kb_database_pool_closed")


# Singleton instance for service
_kb_db_instance = None

async def get_kb_db() -> KnowledgeBaseDB:
    """Get singleton knowledge base database instance"""
    global _kb_db_instance
    if _kb_db_instance is None:
        _kb_db_instance = KnowledgeBaseDB()
        await _kb_db_instance.initialize()
    return _kb_db_instance

async def close_kb_db():
    """Close the singleton database instance"""
    global _kb_db_instance
    if _kb_db_instance:
        await _kb_db_instance.close()
        _kb_db_instance = None