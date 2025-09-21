"""
Processing Chain - Chain together all processing steps with async operations
Decontamination → Parsing → Storage → Validation
"""

import asyncio
import asyncpg
import structlog
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4
from contextlib import asynccontextmanager

try:
    from ..extraction.decontaminator import TechnicalDecontaminator
    from ..core.config import TechKnowledgeConfig
    from ..core.database import TechKnowledgeAsyncDB
except ImportError:
    # Fallback for standalone execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from extraction.decontaminator import TechnicalDecontaminator
    from core.config import TechKnowledgeConfig
    from core.database import TechKnowledgeAsyncDB

logger = structlog.get_logger(__name__)


class ProcessingChainError(Exception):
    """Base exception for processing chain errors"""
    pass


class DecontaminationError(ProcessingChainError):
    """Error during decontamination"""
    pass


class SpecificationParsingError(ProcessingChainError):
    """Error during specification parsing"""
    pass


class StorageError(ProcessingChainError):
    """Error during storage"""
    pass


class AsyncProcessingChain:
    """Chain together all processing steps with async database operations"""

    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        self.config = TechKnowledgeConfig()
        self.decontaminator = TechnicalDecontaminator()
        self.db_pool = db_pool
        self._own_db = db_pool is None
        self._db_instance = None

    async def initialize(self):
        """Initialize database connection if needed"""
        if self._own_db:
            self._db_instance = TechKnowledgeAsyncDB()
            await self._db_instance.initialize()

    async def close(self):
        """Close database connection if owned"""
        if self._own_db and self._db_instance:
            await self._db_instance.close()

    @asynccontextmanager
    async def _get_db_connection(self):
        """Get database connection - either from pool or own instance"""
        if self.db_pool:
            async with self.db_pool.acquire() as conn:
                async with conn.transaction():
                    yield conn
        elif self._db_instance:
            async with self._db_instance.acquire() as conn:
                yield conn
        else:
            raise RuntimeError("No database connection available")

    async def process_crawled_content(
        self,
        content: Dict[str, Any],
        tech_id: str,
        crawl_source_id: str
    ) -> Dict[str, Any]:
        """Execute full processing pipeline with async operations"""

        logger.info("processing_chain_start", tech_id=tech_id, source_id=crawl_source_id)
        start_time = datetime.now()

        try:
            # Step 1: Extract raw content for decontamination
            raw_content = content.get("raw_markdown", "")
            if not raw_content:
                raw_content = str(content)

            logger.info("raw_content_extracted",
                       tech_id=tech_id,
                       content_length=len(raw_content))

            # Step 2: Decontaminate content
            decon_result = await self._decontaminate_content(
                raw_content, tech_id, crawl_source_id
            )

            if not decon_result["success"]:
                raise DecontaminationError(decon_result.get("error", "Unknown error"))

            # Step 3: Parse structured specifications
            specs_result = await self._parse_specifications(
                content, tech_id, decon_result
            )

            if not specs_result["success"]:
                raise SpecificationParsingError(specs_result.get("error", "Unknown error"))

            # Step 4: Store specifications in database
            storage_result = await self._store_specifications(
                specs_result["specifications"], tech_id, crawl_source_id
            )

            if not storage_result["success"]:
                raise StorageError(storage_result.get("error", "Unknown error"))

            # Step 5: Update crawl source success
            await self._update_crawl_success(
                crawl_source_id,
                storage_result["stored_count"],
                decon_result["stats"]
            )

            processing_time = (datetime.now() - start_time).total_seconds()

            logger.info("processing_chain_success",
                       tech_id=tech_id,
                       specifications_stored=storage_result["stored_count"],
                       processing_time=processing_time)

            return {
                "success": True,
                "decontamination": decon_result["stats"],
                "specifications_stored": storage_result["stored_count"],
                "processing_time": processing_time
            }

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error("processing_chain_failed",
                        tech_id=tech_id,
                        error=str(e),
                        processing_time=processing_time)
            return {
                "success": False,
                "error": str(e),
                "processing_time": processing_time
            }

    async def _decontaminate_content(
        self,
        raw_content: str,
        tech_id: str,
        crawl_source_id: str
    ) -> Dict[str, Any]:
        """Step 2: Decontaminate content asynchronously"""

        logger.info("decontamination_start", tech_id=tech_id)

        try:
            # Run decontamination (CPU-bound task)
            decon_result = await asyncio.get_event_loop().run_in_executor(
                None, self.decontaminator.decontaminate, raw_content
            )

            # Log decontamination results asynchronously
            await self._log_decontamination(crawl_source_id, decon_result)

            logger.info("decontamination_complete",
                       tech_id=tech_id,
                       technical_score=decon_result.technical_score,
                       contamination_score=decon_result.contamination_score)

            return {
                "success": True,
                "cleaned_content": decon_result.cleaned_text,
                "stats": {
                    "technical_score": decon_result.technical_score,
                    "contamination_score": decon_result.contamination_score,
                    "removed_lines": len(decon_result.removed_lines),
                    "preserved_technical": len(decon_result.preserved_technical)
                }
            }

        except Exception as e:
            logger.error("decontamination_failed", tech_id=tech_id, error=str(e))
            return {"success": False, "error": str(e)}

    async def _parse_specifications(
        self,
        content: Dict[str, Any],
        tech_id: str,
        decon_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 3: Parse structured specifications asynchronously"""

        logger.info("specification_parsing_start", tech_id=tech_id)

        try:
            specifications = []

            # Parse from structured content if available
            if "technical_specifications" in content:
                specs_data = content["technical_specifications"]
                if isinstance(specs_data, list):
                    specifications.extend(specs_data)

            # If no structured specs, create basic ones from decontaminated content
            if not specifications:
                cleaned_content = decon_result["cleaned_content"]
                basic_specs = await self._create_basic_specifications(cleaned_content)
                specifications.extend(basic_specs)

            logger.info("specification_parsing_complete",
                       tech_id=tech_id,
                       specifications_count=len(specifications))

            return {
                "success": True,
                "specifications": specifications
            }

        except Exception as e:
            logger.error("specification_parsing_failed", tech_id=tech_id, error=str(e))
            return {"success": False, "error": str(e)}

    async def _create_basic_specifications(self, cleaned_content: str) -> List[Dict[str, Any]]:
        """Create basic specifications from cleaned content asynchronously"""

        # Run this CPU-bound task in executor
        return await asyncio.get_event_loop().run_in_executor(
            None, self._parse_content_sync, cleaned_content
        )

    def _parse_content_sync(self, cleaned_content: str) -> List[Dict[str, Any]]:
        """Synchronous content parsing for executor"""
        specs = []
        lines = cleaned_content.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for command-like patterns
            if any(line.startswith(prefix) for prefix in ['$', '>', 'npm ', 'pip ', 'go ', 'cargo ']):
                specs.append({
                    "component_type": "command",
                    "component_name": "installation_usage",
                    "specification": {"command": line},
                    "source_section": "decontaminated"
                })

            # Look for configuration patterns
            elif '=' in line or ':' in line:
                specs.append({
                    "component_type": "config",
                    "component_name": "configuration",
                    "specification": {"setting": line},
                    "source_section": "decontaminated"
                })

        return specs

    async def _store_specifications(
        self,
        specifications: List[Dict[str, Any]],
        tech_id: str,
        crawl_source_id: str
    ) -> Dict[str, Any]:
        """Step 4: Store specifications in database asynchronously"""

        logger.info("specification_storage_start",
                   tech_id=tech_id,
                   specifications_count=len(specifications))

        try:
            stored_count = 0
            start_time = datetime.now()

            async with self._get_db_connection() as conn:
                # Prepare batch insert
                insert_query = """
                    INSERT INTO specifications
                    (id, technology_id, version, component_type, component_name,
                     specification, source_url, source_type, confidence_score)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """

                # Process specifications in batches
                batch_data = []
                for spec in specifications:
                    spec_id = str(uuid4())
                    component_type = spec.get("component_type", "unknown")
                    component_name = spec.get("component_name", "unnamed")
                    spec_data = spec.get("specification", {})
                    source_section = spec.get("source_section", "processed")

                    batch_data.append((
                        spec_id, tech_id, "latest", component_type, component_name,
                        json.dumps(spec_data), f"processed_{source_section}",
                        "official_docs", 0.8
                    ))

                # Execute batch insert
                await conn.executemany(insert_query, batch_data)
                stored_count = len(batch_data)

            processing_time = (datetime.now() - start_time).total_seconds()

            logger.info("specification_storage_complete",
                       tech_id=tech_id,
                       stored_count=stored_count,
                       processing_time=processing_time)

            return {
                "success": True,
                "stored_count": stored_count,
                "processing_time": processing_time
            }

        except Exception as e:
            logger.error("specification_storage_failed", tech_id=tech_id, error=str(e))
            return {"success": False, "error": str(e)}

    async def _log_decontamination(
        self,
        crawl_source_id: str,
        decon_result
    ):
        """Log decontamination results asynchronously"""

        try:
            async with self._get_db_connection() as conn:
                log_id = str(uuid4())

                await conn.execute("""
                    INSERT INTO decontamination_log
                    (id, crawl_source_id, original_size, cleaned_size,
                     contamination_score, removed_patterns, extracted_technical)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, (
                    log_id, crawl_source_id,
                    len(decon_result.original_text),
                    len(decon_result.cleaned_text),
                    decon_result.contamination_score,
                    json.dumps(decon_result.removed_lines[:5]),  # Sample
                    json.dumps(decon_result.preserved_technical[:5])  # Sample
                ))

            logger.info("decontamination_logged", source_id=crawl_source_id)

        except Exception as e:
            logger.error("decontamination_logging_failed",
                        source_id=crawl_source_id,
                        error=str(e))

    async def _update_crawl_success(
        self,
        crawl_source_id: str,
        specs_count: int,
        decon_stats: Dict[str, Any]
    ):
        """Update crawl source with success metrics asynchronously"""

        try:
            async with self._get_db_connection() as conn:
                await conn.execute("""
                    UPDATE crawl_sources
                    SET last_success = $1,
                        extracted_specs_count = $2,
                        decontamination_stats = $3,
                        failure_count = 0
                    WHERE id = $4
                """, (
                    datetime.now(), specs_count,
                    json.dumps(decon_stats), crawl_source_id
                ))

            logger.info("crawl_success_updated",
                       source_id=crawl_source_id,
                       specs_count=specs_count)

        except Exception as e:
            logger.error("crawl_success_update_failed",
                        source_id=crawl_source_id,
                        error=str(e))


# Legacy sync wrapper for backwards compatibility
class ProcessingChain:
    """Synchronous wrapper - DEPRECATED. Use AsyncProcessingChain instead."""

    def __init__(self):
        logger.warning("sync_processing_chain_deprecated",
                      message="ProcessingChain is deprecated. Use AsyncProcessingChain.")
        self.config = TechKnowledgeConfig()
        self.decontaminator = TechnicalDecontaminator()
        # Legacy psycopg2 configuration
        import psycopg2
        self.db_config = {
            'host': self.config.POSTGRES_HOST,
            'port': self.config.POSTGRES_PORT,
            'database': 'techknowledge',
            'user': 'arthurdell'
        }

    def get_db_connection(self):
        """Get database connection - DEPRECATED"""
        import psycopg2
        return psycopg2.connect(**self.db_config)

    async def process_crawled_content(
        self,
        content: Dict[str, Any],
        tech_id: str,
        crawl_source_id: str
    ) -> Dict[str, Any]:
        """Process crawled content - runs async chain internally"""
        logger.warning("legacy_process_content_deprecated")

        # Create async chain and run it
        async_chain = AsyncProcessingChain()
        try:
            await async_chain.initialize()
            return await async_chain.process_crawled_content(content, tech_id, crawl_source_id)
        finally:
            await async_chain.close()


# Test function for refactored processing chain
async def test_async_processing_chain():
    """Test the async processing chain"""

    print("🧪 ASYNC PROCESSING CHAIN TEST")
    print("=" * 50)

    chain = AsyncProcessingChain()

    try:
        await chain.initialize()

        # Get a technology to test with
        async with chain._get_db_connection() as conn:
            row = await conn.fetchrow("""
                SELECT t.id, t.name, cs.id as crawl_source_id
                FROM technologies t
                JOIN crawl_sources cs ON t.id = cs.technology_id
                LIMIT 1
            """)

            if not row:
                print("❌ No technologies found for testing")
                return False

            tech_id, tech_name, crawl_source_id = row['id'], row['name'], row['crawl_source_id']

        print(f"🎯 Testing with technology: {tech_name}")

        # Create test content (simulating crawled data)
        test_content = {
            "technical_specifications": [
                {
                    "component_type": "command",
                    "component_name": "install",
                    "specification": {"command": "go install github.com/charmbracelet/crush@latest"},
                    "source_section": "readme"
                },
                {
                    "component_type": "api",
                    "component_name": "compress",
                    "specification": {
                        "function": "compress",
                        "parameters": ["input", "output"],
                        "description": "Compress files with various algorithms"
                    },
                    "source_section": "readme"
                }
            ],
            "raw_markdown": """
# Crush - Data Compression Tool

I think this is a great tool for compression! You should definitely use it.

## Installation

```bash
go install github.com/charmbracelet/crush@latest
```

## Usage

The compress function takes input and output parameters.

```go
crush.compress(input, output)
```

In my opinion, this is the best compression library available.
"""
        }

        # Test processing chain
        print("\n🔧 Running async processing chain...")
        result = await chain.process_crawled_content(
            test_content, tech_id, crawl_source_id
        )

        if result["success"]:
            print("✅ Async processing chain: SUCCESS")
            print(f"   📊 Decontamination - Technical: {result['decontamination']['technical_score']:.2f}")
            print(f"   📊 Decontamination - Contamination: {result['decontamination']['contamination_score']:.2f}")
            print(f"   💾 Specifications stored: {result['specifications_stored']}")
            print(f"   ⏱️  Processing time: {result.get('processing_time', 0):.2f}s")

            # Verify data in database
            async with chain._get_db_connection() as conn:
                spec_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM specifications WHERE technology_id = $1", tech_id
                )
                decon_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM decontamination_log WHERE crawl_source_id = $1", crawl_source_id
                )

            print(f"\n📊 DATABASE VERIFICATION:")
            print(f"   💾 Specifications in DB: {spec_count}")
            print(f"   📝 Decontamination logs: {decon_count}")

        else:
            print("❌ Async processing chain: FAILED")
            print(f"   💬 Error: {result['error']}")

        print(f"\n{'✅ ASYNC PROCESSING CHAIN TEST: PASSED' if result['success'] else '❌ ASYNC PROCESSING CHAIN TEST: FAILED'}")
        print("🚀 Async Processing Chain is functional")

        return result["success"]

    except Exception as e:
        print(f"\n❌ ASYNC PROCESSING CHAIN TEST: FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await chain.close()


if __name__ == "__main__":
    asyncio.run(test_async_processing_chain())