"""
Pipeline Orchestrator - Core automation engine for TechKnowledge
Refactored with async database operations, connection pooling, and transaction management
"""

import asyncio
import asyncpg
import structlog
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID
from contextlib import asynccontextmanager
from pydantic_settings import BaseSettings
from pydantic import SecretStr

try:
    from ..core.config import TechKnowledgeConfig
    from ..core.models import Technology
except ImportError:
    # Fallback for standalone execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.config import TechKnowledgeConfig
    from core.models import Technology

# Setup structured logging
def setup_logging():
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
        cache_logger_on_first_use=True,
    )

setup_logging()
logger = structlog.get_logger()


class PipelineConfig(BaseSettings):
    """Configuration for TechKnowledge pipeline"""
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "arthurdell"
    postgres_password: SecretStr = SecretStr("")
    postgres_database: str = "techknowledge"

    max_parallel_crawls: int = 5
    crawl_timeout_seconds: int = 30
    retry_attempts: int = 3

    model_config = {
        "env_file": ".env",
        "env_prefix": "TECHKNOWLEDGE_",
        "extra": "ignore"
    }


class PipelineError(Exception):
    """Base exception for pipeline errors"""
    pass


class CrawlError(PipelineError):
    """Error during crawling"""
    pass


class DatabasePool:
    """Async database connection pool manager"""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Initialize the connection pool"""
        self.pool = await asyncpg.create_pool(
            host=self.config.postgres_host,
            port=self.config.postgres_port,
            database=self.config.postgres_database,
            user=self.config.postgres_user,
            password=self.config.postgres_password.get_secret_value(),
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        logger.info("database_pool_initialized",
                   host=self.config.postgres_host,
                   database=self.config.postgres_database)

    @asynccontextmanager
    async def acquire(self):
        """Acquire connection with transaction context"""
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                yield connection

    async def close(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("database_pool_closed")


class TechKnowledgePipeline:
    """Main orchestrator for automated processing with async database operations"""

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.db_pool = DatabasePool(self.config)
        self.semaphore = asyncio.Semaphore(self.config.max_parallel_crawls)
        self._initialized = False

    async def __aenter__(self):
        """Async context manager entry"""
        await self.db_pool.initialize()
        self._initialized = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.db_pool.close()
        self._initialized = False

    async def process_pending_technologies(self) -> Dict[str, Any]:
        """Find and process unprocessed registrations with async operations"""
        if not self._initialized:
            raise RuntimeError("Pipeline not initialized. Use async context manager.")

        logger.info("scanning_pending_technologies")

        async with self.db_pool.acquire() as conn:
            # Find crawl sources that have never been crawled
            rows = await conn.fetch("""
                SELECT cs.id, cs.technology_id, cs.url, t.name, t.category
                FROM crawl_sources cs
                JOIN technologies t ON cs.technology_id = t.id
                WHERE cs.last_crawled IS NULL AND cs.active = true
                ORDER BY t.created_at ASC
            """)

            if not rows:
                logger.info("no_pending_technologies")
                return {"processed": 0, "message": "No pending technologies"}

            logger.info("found_pending_technologies", count=len(rows))

            # Process in parallel with semaphore
            tasks = []
            for row in rows:
                task = self._process_with_semaphore(row)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            return self._format_results(results, rows)

    async def _process_with_semaphore(self, row) -> Dict[str, Any]:
        """Process technology with semaphore limiting"""
        async with self.semaphore:
            return await self.process_technology(
                row['technology_id'],
                row['id'],
                row['name']
            )

    def _format_results(self, results: List, rows: List) -> Dict[str, Any]:
        """Format processing results"""
        formatted_results = []
        successful = 0

        for i, result in enumerate(results):
            row = rows[i]
            if isinstance(result, Exception):
                formatted_results.append({
                    "technology": row['name'],
                    "success": False,
                    "message": f"Processing failed: {str(result)}"
                })
                logger.error("technology_processing_failed",
                           tech_id=row['technology_id'],
                           name=row['name'],
                           error=str(result))
            else:
                formatted_results.append({
                    "technology": row['name'],
                    "success": result["success"],
                    "message": result.get("message", "")
                })
                if result["success"]:
                    successful += 1
                    logger.info("technology_processing_success",
                              tech_id=row['technology_id'],
                              name=row['name'])

        return {
            "processed": len(results),
            "successful": successful,
            "results": formatted_results,
            "message": f"Processed {len(results)} technologies ({successful} successful)"
        }

    async def process_technology(self, tech_id: str, source_id: str, name: str) -> Dict[str, Any]:
        """Process a single technology through full pipeline with proper error handling"""
        logger.info("processing_technology", tech_id=tech_id, name=name)

        try:
            async with self.db_pool.acquire() as conn:
                # Start transaction - mark crawl as started
                await conn.execute(
                    "UPDATE crawl_sources SET last_crawled = $1 WHERE id = $2",
                    datetime.now(), source_id
                )

                try:
                    # Simulate crawling with timeout
                    result = await self._crawl_with_timeout(source_id)

                    # Update success
                    await conn.execute("""
                        UPDATE crawl_sources
                        SET last_success = $1, failure_count = 0
                        WHERE id = $2
                    """, datetime.now(), source_id)

                    return {
                        "success": True,
                        "message": f"Successfully processed {name}",
                        "data": result
                    }

                except CrawlError as e:
                    # Update failure
                    await conn.execute("""
                        UPDATE crawl_sources
                        SET last_failure = $1, failure_count = failure_count + 1
                        WHERE id = $2
                    """, datetime.now(), source_id)

                    logger.error("crawl_failed", tech_id=tech_id, error=str(e))
                    raise

        except Exception as e:
            logger.exception("processing_failed", tech_id=tech_id)
            return {
                "success": False,
                "message": f"Failed to process {name}: {str(e)}"
            }

    async def _crawl_with_timeout(self, source_id: str) -> dict:
        """Perform crawl with automatic timeout extension and retry"""
        max_retries = 3
        base_timeout = self.config.crawl_timeout_seconds

        for attempt in range(max_retries):
            timeout = base_timeout * (2 ** attempt)  # Progressive: 30s, 60s, 120s

            try:
                logger.info("crawl_attempt",
                           source_id=source_id,
                           attempt=attempt + 1,
                           timeout=timeout)

                result = await asyncio.wait_for(
                    self._perform_crawl(source_id),
                    timeout=timeout
                )

                logger.info("crawl_success",
                           source_id=source_id,
                           attempt=attempt + 1)
                return result

            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    logger.warning("crawl_timeout_retry",
                                 source_id=source_id,
                                 attempt=attempt + 1,
                                 next_timeout=base_timeout * (2 ** (attempt + 1)))
                    # Brief pause before retry
                    await asyncio.sleep(5)
                    continue
                else:
                    logger.error("crawl_timeout_final", source_id=source_id)
                    raise CrawlError(f"Crawl failed after {max_retries} attempts with progressive timeouts")

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning("crawl_error_retry",
                                 source_id=source_id,
                                 attempt=attempt + 1,
                                 error=str(e))
                    await asyncio.sleep(10)  # Longer pause for errors
                    continue
                else:
                    raise CrawlError(f"Crawl failed after {max_retries} attempts: {str(e)}")

        raise CrawlError(f"Unexpected: All retry attempts exhausted for {source_id}")

    async def _perform_crawl(self, source_id: str) -> dict:
        """Perform actual crawling and processing operation with automatic fallback"""
        logger.info("performing_real_crawl", source_id=source_id)

        try:
            # Get source URL and technology info from database
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT cs.url, cs.technology_id, t.name, t.official_url, t.github_repo FROM crawl_sources cs JOIN technologies t ON cs.technology_id = t.id WHERE cs.id = $1",
                    source_id
                )

                if not row:
                    raise CrawlError(f"Source {source_id} not found")

                primary_url = row['url']
                tech_id = row['technology_id']
                tech_name = row['name']

                # Generate fallback URLs automatically
                fallback_urls = self._generate_fallback_urls(tech_name, row['official_url'], row['github_repo'])
                all_urls = [primary_url] + fallback_urls

            # Import crawling and processing components
            from .crawl_executor import CrawlExecutor
            from .fallback_crawler import FallbackCrawler
            from .processing_chain import AsyncProcessingChain

            # Initialize components
            crawler = CrawlExecutor()
            fallback_crawler = FallbackCrawler()
            processor = AsyncProcessingChain(self.db_pool)

            logger.info("crawling_urls", primary_url=primary_url, fallback_count=len(fallback_urls), source_id=source_id)

            # Try multiple URLs and crawling strategies automatically
            crawl_result = None
            successful_url = None

            for url_index, url in enumerate(all_urls):
                logger.info("trying_url", url=url, url_index=url_index + 1, total_urls=len(all_urls))

                # Strategy 1: Multi-page crawl
                try:
                    crawl_result = await crawler.crawl_multiple_pages(url, source_id, max_pages=5)
                    if crawl_result["success"] and self._validate_crawl_result(crawl_result):
                        logger.info("multipage_crawl_success", url=url, source_id=source_id)
                        successful_url = url
                        break
                except Exception as e:
                    logger.warning("multipage_crawl_failed", url=url, error=str(e))

                # Strategy 2: Single page crawl
                try:
                    crawl_result = await crawler.crawl_source(url, source_id)
                    if crawl_result["success"] and self._validate_crawl_result(crawl_result):
                        logger.info("single_crawl_success", url=url, source_id=source_id)
                        successful_url = url
                        break
                except Exception as e:
                    logger.warning("single_crawl_failed", url=url, error=str(e))

                # Strategy 3: Fallback crawler
                try:
                    crawl_result = await fallback_crawler.crawl_generic_url(url)
                    if crawl_result["success"] and self._validate_crawl_result(crawl_result):
                        logger.info("fallback_crawl_success", url=url, source_id=source_id)
                        successful_url = url
                        break
                except Exception as e:
                    logger.warning("fallback_crawl_failed", url=url, error=str(e))

                logger.warning("all_strategies_failed_for_url", url=url)

            if not crawl_result or not crawl_result["success"] or not successful_url:
                raise CrawlError(f"All crawling strategies failed for all URLs: {all_urls}")

            # Update database with successful URL if different from primary
            if successful_url != primary_url:
                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE crawl_sources SET url = $1 WHERE id = $2",
                        successful_url, source_id
                    )
                logger.info("updated_successful_url", old_url=primary_url, new_url=successful_url)

            # Process crawled content
            logger.info("processing_content", source_id=source_id)

            # Handle different content formats
            if isinstance(crawl_result["content"], list):
                # Multi-page content
                total_specs = 0
                for page_data in crawl_result["content"]:
                    process_result = await processor.process_crawled_content(
                        page_data, tech_id, source_id
                    )
                    if process_result["success"]:
                        total_specs += process_result.get("specifications_stored", 0)

                # Update crawl source with aggregate results
                async with self.db_pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE crawl_sources
                        SET extracted_specs_count = $1,
                            decontamination_stats = $2
                        WHERE id = $3
                    """, total_specs, '{"multi_page": true, "total_specs": ' + str(total_specs) + '}', source_id)

            else:
                # Single page content
                process_result = await processor.process_crawled_content(
                    crawl_result, tech_id, source_id
                )

                if process_result["success"]:
                    # Update crawl source with results
                    async with self.db_pool.acquire() as conn:
                        import json
                        decon_stats = process_result.get("decontamination", {})
                        await conn.execute("""
                            UPDATE crawl_sources
                            SET extracted_specs_count = $1,
                                decontamination_stats = $2
                            WHERE id = $3
                        """,
                        process_result.get("specifications_stored", 0),
                        json.dumps(decon_stats),
                        source_id)

            # Final validation: Confirm specifications were actually created
            specs_created = 0
            if 'process_result' in locals():
                specs_created = process_result.get("specifications_stored", 0)
            elif 'total_specs' in locals():
                specs_created = total_specs

            # Verify in database
            async with self.db_pool.acquire() as conn:
                db_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM specifications WHERE technology_id = $1",
                    tech_id
                )

            if db_count == 0:
                raise CrawlError(f"Processing completed but no specifications found in database for {tech_name}")

            logger.info("crawl_processing_complete",
                       source_id=source_id,
                       tech_name=tech_name,
                       url=successful_url,
                       specifications_created=specs_created,
                       db_verified_count=db_count)

            return {
                "source_id": source_id,
                "crawled_at": datetime.now().isoformat(),
                "status": "success",
                "url": successful_url,
                "specifications_created": specs_created,
                "db_verified_count": db_count,
                "automation_complete": True
            }

        except Exception as e:
            logger.error("crawl_processing_failed", source_id=source_id, error=str(e))

            # Update with failure stats
            async with self.db_pool.acquire() as conn:
                import json
                error_stats = {"error": str(e), "failed_at": datetime.now().isoformat()}
                await conn.execute("""
                    UPDATE crawl_sources
                    SET decontamination_stats = $1
                    WHERE id = $2
                """, json.dumps(error_stats), source_id)

            raise CrawlError(f"Crawl processing failed: {str(e)}")

    def _generate_fallback_urls(self, tech_name: str, official_url: str, github_repo: str) -> List[str]:
        """Generate fallback URLs automatically based on technology name and known patterns"""
        fallback_urls = []

        # Clean tech name
        clean_name = tech_name.lower().replace('-', '').replace('_', '')

        # Common documentation patterns
        doc_patterns = [
            f"https://{clean_name}.readthedocs.io/",
            f"https://docs.{clean_name}.org/",
            f"https://{clean_name}.github.io/",
            f"https://{tech_name}.dev/docs/",
            f"https://github.com/{tech_name}/{tech_name}?tab=readme-ov-file"
        ]

        # Add official URL variations if provided
        if official_url:
            base_domain = official_url.rstrip('/')
            fallback_urls.extend([
                f"{base_domain}/docs/",
                f"{base_domain}/documentation/",
                f"{base_domain}/reference/",
                f"{base_domain}/api/",
                f"{base_domain}/guide/"
            ])

        # Add GitHub patterns if provided
        if github_repo:
            fallback_urls.extend([
                f"https://github.com/{github_repo}?tab=readme-ov-file",
                f"https://github.com/{github_repo}/blob/main/README.md",
                f"https://github.com/{github_repo}/wiki",
                f"https://{github_repo.split('/')[0]}.github.io/{github_repo.split('/')[1]}/"
            ])

        # Add common doc patterns
        fallback_urls.extend(doc_patterns)

        # Remove duplicates and None values
        return list(dict.fromkeys([url for url in fallback_urls if url]))

    def _validate_crawl_result(self, crawl_result: Dict[str, Any]) -> bool:
        """Validate that crawl result contains sufficient content"""
        if not crawl_result.get("success", False):
            return False

        content = crawl_result.get("content", "")
        if isinstance(content, list):
            # Multi-page content
            total_content = sum(len(str(page)) for page in content)
            return total_content > 1000  # At least 1KB total content
        else:
            # Single page content
            return len(str(content)) > 500  # At least 500 chars

    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get overall pipeline status with async operations"""
        if not self._initialized:
            raise RuntimeError("Pipeline not initialized. Use async context manager.")

        async with self.db_pool.acquire() as conn:
            # Count technologies by processing status
            row = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_technologies,
                    COUNT(CASE WHEN cs.last_crawled IS NULL THEN 1 END) as pending,
                    COUNT(CASE WHEN cs.last_success IS NOT NULL THEN 1 END) as completed,
                    COUNT(CASE WHEN cs.last_failure IS NOT NULL AND cs.last_success IS NULL THEN 1 END) as failed
                FROM technologies t
                LEFT JOIN crawl_sources cs ON t.id = cs.technology_id
                WHERE t.active = true
            """)

            total = row['total_technologies']
            pending = row['pending']
            completed = row['completed']
            failed = row['failed']

            return {
                "total_technologies": total,
                "pending": pending,
                "completed": completed,
                "failed": failed,
                "completion_rate": (completed / total * 100) if total > 0 else 0
            }


# Test function for refactored pipeline
async def test_pipeline_orchestrator():
    """Test the refactored pipeline orchestrator"""
    print("🧪 REFACTORED PIPELINE ORCHESTRATOR TEST")
    print("=" * 50)

    config = PipelineConfig()
    async with TechKnowledgePipeline(config) as pipeline:
        try:
            # Test 1: Get current status
            print("\n1. PIPELINE STATUS:")
            status = await pipeline.get_pipeline_status()
            print(f"   📊 Total technologies: {status['total_technologies']}")
            print(f"   ⏳ Pending: {status['pending']}")
            print(f"   ✅ Completed: {status['completed']}")
            print(f"   ❌ Failed: {status['failed']}")
            print(f"   📈 Completion rate: {status['completion_rate']:.1f}%")

            # Test 2: Process pending technologies
            print("\n2. PROCESSING PENDING:")
            result = await pipeline.process_pending_technologies()
            print(f"   🔧 Processed: {result['processed']} technologies")
            print(f"   ✅ Successful: {result.get('successful', 0)} technologies")
            print(f"   💬 Message: {result['message']}")

            if 'results' in result:
                for tech_result in result['results']:
                    status_icon = "✅" if tech_result['success'] else "❌"
                    print(f"   {status_icon} {tech_result['technology']}: {tech_result['message']}")

            # Test 3: Check status after processing
            print("\n3. POST-PROCESSING STATUS:")
            final_status = await pipeline.get_pipeline_status()
            print(f"   📊 Pending: {final_status['pending']} (was {status['pending']})")
            print(f"   ✅ Completed: {final_status['completed']} (was {status['completed']})")
            print(f"   📈 Completion rate: {final_status['completion_rate']:.1f}%")

            print(f"\n✅ REFACTORED PIPELINE TEST: PASSED")
            print("🚀 Async Pipeline with Connection Pooling is functional")
            return True

        except Exception as e:
            print(f"\n❌ REFACTORED PIPELINE TEST: FAILED")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    asyncio.run(test_pipeline_orchestrator())