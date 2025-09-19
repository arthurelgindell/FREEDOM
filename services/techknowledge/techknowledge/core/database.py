"""
TechKnowledge Database Connection Manager
Refactored with async connection pooling and proper transaction management
"""

import os
import asyncio
import asyncpg
import structlog
from contextlib import asynccontextmanager, contextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import uuid4

# Configure logging
logger = structlog.get_logger(__name__)


class TechKnowledgeAsyncDB:
    """Async PostgreSQL connection manager with pooling for technical knowledge system"""

    def __init__(self):
        """Initialize async connection pool with environment configuration"""
        self.host = os.getenv('POSTGRES_HOST', 'localhost')
        self.port = int(os.getenv('POSTGRES_PORT', '5432'))
        self.database = 'techknowledge'
        self.user = os.getenv('POSTGRES_USER', 'arthurdell')
        self.password = os.getenv('POSTGRES_PASSWORD', '')
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False

    async def initialize(self):
        """Initialize the connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=3,
                max_size=15,
                command_timeout=60
            )
            self._initialized = True
            logger.info("async_database_initialized",
                       host=self.host,
                       port=self.port,
                       database=self.database)
        except Exception as e:
            logger.error("failed_to_create_async_pool", error=str(e))
            raise

    @asynccontextmanager
    async def acquire(self):
        """Get a connection from the pool with automatic transaction management"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn

    async def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a query and return results as list of dictionaries

        Args:
            query: SQL query to execute
            params: Query parameters (prevents SQL injection)

        Returns:
            List of result dictionaries for SELECT queries, empty list for others
        """
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

    async def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute query multiple times with different parameters"""
        async with self.acquire() as conn:
            try:
                result = await conn.executemany(query, params_list)
                return len(params_list)  # asyncpg executemany doesn't return rowcount
            except Exception as e:
                logger.error("batch_execution_failed", query=query[:100], error=str(e))
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

    async def check_database_exists(self) -> bool:
        """Check if techknowledge database exists"""
        try:
            # Connect to default postgres database
            temp_pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database='postgres',
                user=self.user,
                password=self.password,
                min_size=1,
                max_size=1
            )

            async with temp_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT 1 FROM pg_database WHERE datname = $1",
                    self.database
                )
                exists = row is not None

            await temp_pool.close()
            return exists

        except Exception as e:
            logger.error("database_existence_check_failed", error=str(e))
            return False

    async def close(self):
        """Close all connections in the pool"""
        if self.pool:
            await self.pool.close()
            self._initialized = False
            logger.info("async_database_pool_closed")


# Singleton instance
_async_db_instance = None

async def get_async_db() -> TechKnowledgeAsyncDB:
    """Get singleton async database instance"""
    global _async_db_instance
    if _async_db_instance is None:
        _async_db_instance = TechKnowledgeAsyncDB()
        await _async_db_instance.initialize()
    return _async_db_instance


# Async convenience functions for common operations
async def store_specification_async(
    technology_id: str,
    version: str,
    component_type: str,
    component_name: str,
    specification: Dict[str, Any],
    source_url: str,
    source_type: str,
    confidence_score: float = 1.0
) -> Optional[str]:
    """
    Store a pure technical specification asynchronously

    Returns:
        Specification ID if successful, None otherwise
    """
    db = await get_async_db()

    query = """
        INSERT INTO specifications (
            id, technology_id, version, component_type, component_name,
            specification, source_url, source_type, confidence_score
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id
    """

    spec_id = str(uuid4())

    try:
        result = await db.insert_returning(
            query,
            (spec_id, technology_id, version, component_type, component_name,
             specification, source_url, source_type, confidence_score)
        )
        return result['id'] if result else None
    except Exception as e:
        logger.error("specification_storage_failed",
                    tech_id=technology_id,
                    component_type=component_type,
                    error=str(e))
        return None


async def get_technology_by_name_async(name: str) -> Optional[Dict[str, Any]]:
    """Get technology record by name asynchronously"""
    db = await get_async_db()
    return await db.execute_one(
        "SELECT * FROM technologies WHERE name = $1",
        (name,)
    )


async def get_current_version_async(technology_name: str) -> Optional[str]:
    """Get current version for a technology asynchronously"""
    db = await get_async_db()

    query = """
        SELECT v.version_current
        FROM versions v
        JOIN technologies t ON v.technology_id = t.id
        WHERE t.name = $1
        ORDER BY v.last_checked DESC
        LIMIT 1
    """

    result = await db.execute_one(query, (technology_name,))
    return result['version_current'] if result else None


# Legacy sync wrapper class for backwards compatibility
class TechKnowledgeDB:
    """Synchronous wrapper - DEPRECATED. Use TechKnowledgeAsyncDB instead."""

    def __init__(self):
        logger.warning("sync_db_deprecated",
                      message="TechKnowledgeDB is deprecated. Use TechKnowledgeAsyncDB.")
        import psycopg2
        from psycopg2.pool import SimpleConnectionPool
        from psycopg2.extras import RealDictCursor
        from contextlib import contextmanager

        self.host = os.getenv('POSTGRES_HOST', 'localhost')
        self.port = int(os.getenv('POSTGRES_PORT', '5432'))
        self.database = 'techknowledge'
        self.user = os.getenv('POSTGRES_USER', 'arthurdell')
        self.password = os.getenv('POSTGRES_PASSWORD', '')

        try:
            self.pool = SimpleConnectionPool(
                1, 10,  # Reduced pool size for legacy compatibility
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            logger.info("legacy_sync_pool_initialized")
        except Exception as e:
            logger.error("legacy_sync_pool_failed", error=str(e))
            raise

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool with automatic cleanup"""
        conn = None
        try:
            conn = self.pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error("legacy_connection_error", error=str(e))
            raise
        finally:
            if conn:
                self.pool.putconn(conn)

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute query - DEPRECATED"""
        with self.get_connection() as conn:
            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if cur.description:
                    return cur.fetchall()
                return []

    def health_check(self) -> Dict[str, Any]:
        """Check health of database connection"""
        try:
            with self.get_connection() as conn:
                from psycopg2.extras import RealDictCursor
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT COUNT(*) as technologies_count FROM technologies")
                    tech_count = cur.fetchone()['technologies_count']
                    cur.execute("SELECT COUNT(*) as specifications_count FROM specifications")
                    spec_count = cur.fetchone()['specifications_count']
                    return {
                        "database_connected": True,
                        "technologies_count": tech_count,
                        "specifications_count": spec_count
                    }
        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            return {
                "database_connected": False,
                "technologies_count": 0,
                "specifications_count": 0,
                "error": str(e)
            }

    def close(self):
        """Close all connections in the pool"""
        if hasattr(self, 'pool'):
            self.pool.closeall()
            logger.info("legacy_sync_pool_closed")


# Backwards compatibility
def get_db() -> TechKnowledgeDB:
    """Get legacy sync database instance - DEPRECATED"""
    logger.warning("get_db_deprecated",
                   message="get_db() is deprecated. Use get_async_db() instead.")
    return TechKnowledgeDB()


# Legacy sync functions - DEPRECATED
def store_specification(
    technology_id: str,
    version: str,
    component_type: str,
    component_name: str,
    specification: Dict[str, Any],
    source_url: str,
    source_type: str,
    confidence_score: float = 1.0
) -> Optional[str]:
    """Store specification synchronously - DEPRECATED"""
    logger.warning("sync_store_specification_deprecated")
    db = get_db()

    from psycopg2.extras import Json
    query = """
        INSERT INTO specifications (
            id, technology_id, version, component_type, component_name,
            specification, source_url, source_type, confidence_score
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """

    spec_id = str(uuid4())
    result = db.insert_returning(
        query,
        (spec_id, technology_id, version, component_type, component_name,
         Json(specification), source_url, source_type, confidence_score)
    )

    return str(result['id']) if result else None


def get_technology_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get technology by name synchronously - DEPRECATED"""
    logger.warning("sync_get_technology_deprecated")
    db = get_db()
    return db.execute_one(
        "SELECT * FROM technologies WHERE name = %s",
        (name,)
    )


def get_current_version(technology_name: str) -> Optional[str]:
    """Get current version synchronously - DEPRECATED"""
    logger.warning("sync_get_version_deprecated")
    db = get_db()

    query = """
        SELECT v.version_current
        FROM versions v
        JOIN technologies t ON v.technology_id = t.id
        WHERE t.name = %s
        ORDER BY v.last_checked DESC
        LIMIT 1
    """

    result = db.execute_one(query, (technology_name,))
    return result['version_current'] if result else None


# Create convenient aliases
Database = TechKnowledgeAsyncDB
AsyncDatabase = TechKnowledgeAsyncDB
SyncDatabase = TechKnowledgeDB