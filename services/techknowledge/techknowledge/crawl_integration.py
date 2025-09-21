"""
TechKnowledge Crawl Integration Module
Integrates with the Playwright × Firecrawl stack for automated documentation updates
"""

import httpx
import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

ROUTER_URL = "http://router:8003"

class CrawlIntegration:
    """Integrates TechKnowledge with the crawl stack for automated doc updates"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def crawl_documentation(
        self,
        urls: List[str],
        intent: str = "extract technical documentation",
        auth_required: bool = False,
        credentials: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Crawl documentation sites using the router service

        Args:
            urls: List of documentation URLs to crawl
            intent: Purpose of crawling
            auth_required: Whether authentication is needed
            credentials: Optional auth credentials

        Returns:
            List of crawl results
        """
        results = []

        for url in urls:
            task = {
                "url": url,
                "intent": intent
            }

            if auth_required and credentials:
                task["credentials"] = credentials

            try:
                # Submit to router
                response = await self.client.post(
                    f"{ROUTER_URL}/crawl",
                    json=task
                )
                response.raise_for_status()

                result = response.json()
                task_id = result.get("task_id")

                # If queued, wait for completion
                if result.get("queued"):
                    logger.info(f"Task {task_id} queued for Playwright processing")

                    # Poll for completion (max 60 seconds)
                    for _ in range(60):
                        await asyncio.sleep(1)

                        status_resp = await self.client.get(
                            f"{ROUTER_URL}/status/{task_id}"
                        )
                        status_data = status_resp.json()

                        if status_data.get("status") == "completed":
                            result = status_data.get("data", {})
                            break

                results.append({
                    "url": url,
                    "task_id": task_id,
                    "data": result.get("data", {}),
                    "status": result.get("status", "unknown"),
                    "timestamp": datetime.now().isoformat()
                })

                logger.info(f"Successfully crawled {url}")

            except Exception as e:
                logger.error(f"Failed to crawl {url}: {str(e)}")
                results.append({
                    "url": url,
                    "error": str(e),
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })

        return results

    async def update_knowledge_base(self, crawl_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process crawl results and update TechKnowledge database

        Args:
            crawl_results: Results from crawl_documentation

        Returns:
            Update summary
        """
        updated = 0
        failed = 0

        for result in crawl_results:
            if result.get("status") == "completed" and result.get("data"):
                try:
                    # Extract content from crawl result
                    data = result["data"]
                    content = data.get("content", {})

                    # Process and store in knowledge base
                    # This would integrate with existing TechKnowledge storage

                    updated += 1
                    logger.info(f"Updated knowledge base with content from {result['url']}")

                except Exception as e:
                    logger.error(f"Failed to update KB with {result['url']}: {str(e)}")
                    failed += 1
            else:
                failed += 1

        return {
            "updated": updated,
            "failed": failed,
            "total": len(crawl_results),
            "timestamp": datetime.now().isoformat()
        }

    async def schedule_periodic_updates(
        self,
        doc_sources: List[Dict[str, Any]],
        interval_hours: int = 24
    ):
        """
        Schedule periodic documentation updates

        Args:
            doc_sources: List of documentation sources with URLs and credentials
            interval_hours: Update interval in hours
        """
        while True:
            try:
                logger.info("Starting scheduled documentation update")

                for source in doc_sources:
                    urls = source.get("urls", [])
                    credentials = source.get("credentials")
                    auth_required = source.get("auth_required", False)

                    # Crawl documentation
                    results = await self.crawl_documentation(
                        urls=urls,
                        auth_required=auth_required,
                        credentials=credentials
                    )

                    # Update knowledge base
                    summary = await self.update_knowledge_base(results)

                    logger.info(f"Update complete for {source.get('name')}: {summary}")

                # Wait for next update cycle
                await asyncio.sleep(interval_hours * 3600)

            except Exception as e:
                logger.error(f"Error in periodic update: {str(e)}")
                await asyncio.sleep(3600)  # Retry after 1 hour on error

    async def close(self):
        """Clean up resources"""
        await self.client.aclose()


# Example usage
async def main():
    """Example of using the crawl integration"""
    integration = CrawlIntegration()

    try:
        # Example: Crawl public documentation
        public_docs = await integration.crawl_documentation(
            urls=[
                "https://docs.python.org/3/",
                "https://fastapi.tiangolo.com/",
                "https://redis.io/docs/"
            ],
            intent="extract API documentation"
        )

        # Example: Crawl authenticated documentation
        private_docs = await integration.crawl_documentation(
            urls=["https://internal-docs.company.com/api"],
            intent="login and extract internal API docs",
            auth_required=True,
            credentials={
                "username": "doc_reader",
                "password": "secure_password"
            }
        )

        # Update knowledge base
        all_results = public_docs + private_docs
        summary = await integration.update_knowledge_base(all_results)

        print(f"Documentation update summary: {summary}")

    finally:
        await integration.close()


if __name__ == "__main__":
    asyncio.run(main())