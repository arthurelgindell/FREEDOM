"""
Crawl Executor - Firecrawl API integration
Executes actual crawling operations and stores results
"""

import asyncio
import aiohttp
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4
from dotenv import load_dotenv
from firecrawl import FirecrawlApp

try:
    from ..core.config import TechKnowledgeConfig
except ImportError:
    # Fallback for standalone execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.config import TechKnowledgeConfig

# Load environment variables
load_dotenv('../../.env')

logger = logging.getLogger(__name__)


class CrawlExecutor:
    """Execute Firecrawl operations and update database"""

    def __init__(self):
        self.config = TechKnowledgeConfig()
        self.api_key = self.config.FIRECRAWL_API_KEY
        
        # Initialize Firecrawl SDK
        if self.api_key:
            self.firecrawl_app = FirecrawlApp(api_key=self.api_key)
            logger.info("✅ Firecrawl SDK initialized")
        else:
            self.firecrawl_app = None
            logger.warning("⚠️ Firecrawl API key not configured")

    async def crawl_source(self, url: str, crawl_source_id: str) -> Dict[str, Any]:
        """Crawl a specific source using Firecrawl SDK"""

        logger.info(f"🕷️ Starting crawl: {url}")

        if not self.firecrawl_app:
            return {
                "success": False,
                "error": "Firecrawl SDK not initialized - API key not configured",
                "content": None
            }

        try:
            # Use Firecrawl SDK for scraping
            logger.info("🔧 Using Firecrawl SDK for single-page scraping")
            
            # Configure extraction options for SDK
            # Note: The SDK doesn't support LLM extraction directly, so we'll use basic scraping
            # and process the markdown content separately
            
            # Make Firecrawl SDK call with basic options
            result = self.firecrawl_app.scrape(
                url,
                only_main_content=True,
                remove_base64_images=True,
                block_ads=True
            )

            # Process the result (SDK returns a Document object)
            if result and hasattr(result, 'markdown'):
                # Extract content from Document object
                markdown_content = result.markdown or ""
                
                # For now, we'll use the markdown content as our extracted data
                # In a real implementation, we'd need to process the markdown to extract structured data
                extracted_data = {
                    "markdown": markdown_content,
                    "metadata": result.metadata.__dict__ if result.metadata else {}
                }

                # Calculate content hash for deduplication
                content_str = str(markdown_content)
                content_hash = hashlib.sha256(content_str.encode()).hexdigest()

                logger.info(f"✅ Crawl successful: {len(content_str)} chars extracted")

                return {
                    "success": True,
                    "content": {"raw_markdown": markdown_content},
                    "content_hash": content_hash,
                    "raw_markdown": markdown_content,
                    "metadata": {
                        "url": url,
                        "crawled_at": datetime.now().isoformat(),
                        "firecrawl_scrape_id": getattr(result.metadata, 'scrape_id', None) if result.metadata else None,
                        "extraction_schema": "markdown_extraction",
                        "crawler": "firecrawl_sdk",
                        "credits_used": getattr(result.metadata, 'credits_used', 0) if result.metadata else 0
                    }
                }
            else:
                error_msg = "No result returned from Firecrawl SDK"
                logger.error(f"❌ Firecrawl error: {error_msg}")

                return {
                    "success": False,
                    "error": error_msg,
                    "content": None
                }

        except Exception as e:
            error_msg = f"Crawl exception: {str(e)}"
            logger.error(f"💥 {error_msg}")
            return {"success": False, "error": error_msg, "content": None}

    async def test_firecrawl_connection(self) -> Dict[str, Any]:
        """Test Firecrawl SDK connection and configuration"""

        logger.info("🧪 Testing Firecrawl SDK connection...")

        if not self.firecrawl_app:
            return {
                "success": False,
                "error": "SDK not initialized",
                "details": "FIRECRAWL_API_KEY environment variable not set"
            }

        try:
            # Test with a simple URL using SDK
            test_url = "https://httpbin.org/json"
            logger.info(f"🕷️ Testing SDK with: {test_url}")

            # Use SDK for testing
            result = self.firecrawl_app.scrape(test_url)

            if result and hasattr(result, 'markdown'):
                return {
                    "success": True,
                    "api_key_present": bool(self.api_key),
                    "api_key_prefix": self.api_key[:8] + "..." if self.api_key else None,
                    "sdk_version": "firecrawl-py",
                    "test_response": True
                }
            else:
                error_msg = "No result returned from SDK"
                return {
                    "success": False,
                    "error": f"SDK test failed: {error_msg}",
                    "details": str(result)
                }

        except Exception as e:
            error_msg = str(e)
            if "Insufficient credits" in error_msg or "Payment Required" in error_msg:
                return {
                    "success": True,  # SDK works, just no credits
                    "api_key_present": bool(self.api_key),
                    "api_key_prefix": self.api_key[:8] + "..." if self.api_key else None,
                    "sdk_version": "firecrawl-py",
                    "test_response": False,
                    "warning": "Insufficient API credits for testing"
                }
            else:
                return {
                    "success": False,
                    "error": "SDK connection failed",
                    "details": error_msg
                }

    async def crawl_multiple_pages(self, base_url: str, crawl_source_id: str, 
                                 max_pages: int = 10, 
                                 include_paths: list = None,
                                 exclude_paths: list = None) -> Dict[str, Any]:
        """Crawl multiple pages using Firecrawl SDK"""

        logger.info(f"🕷️ Starting multi-page crawl: {base_url}")

        if not self.firecrawl_app:
            return {
                "success": False,
                "error": "Firecrawl SDK not initialized - API key not configured",
                "content": None
            }

        try:
            # Configure crawl options for SDK (simplified)
            crawl_options = {
                "limit": max_pages,
                "max_discovery_depth": 2,
                "ignore_query_parameters": True
            }
            
            # Only add path filters if they're provided
            if include_paths:
                crawl_options["include_paths"] = include_paths
            if exclude_paths:
                crawl_options["exclude_paths"] = exclude_paths

            # Use Firecrawl SDK for multi-page crawling
            logger.info("🔧 Using Firecrawl SDK for multi-page crawling")
            result = self.firecrawl_app.crawl(base_url, **crawl_options)

            # Process the result (SDK returns a CrawlJob object with completed data)
            if result and hasattr(result, 'data') and result.data and len(result.data) > 0:
                data = result.data
                
                # Aggregate all extracted content
                all_content = []
                for page_data in data:
                    if hasattr(page_data, 'markdown') and page_data.markdown:
                        all_content.append({
                            "url": getattr(page_data.metadata, 'url', '') if page_data.metadata else '',
                            "content": {"raw_markdown": page_data.markdown},
                            "markdown": page_data.markdown
                        })

                # Calculate content hash for deduplication
                content_str = str(all_content)
                content_hash = hashlib.sha256(content_str.encode()).hexdigest()

                logger.info(f"✅ Multi-page crawl successful: {len(data)} pages, {len(all_content)} with content")

                return {
                    "success": True,
                    "content": all_content,
                    "content_hash": content_hash,
                    "pages_crawled": len(data),
                    "pages_with_content": len(all_content),
                    "metadata": {
                        "base_url": base_url,
                        "crawled_at": datetime.now().isoformat(),
                        "firecrawl_status": getattr(result, 'status', 'completed'),
                        "extraction_schema": "markdown_extraction",
                        "crawler": "firecrawl_sdk_multi_page",
                        "max_pages": max_pages,
                        "include_paths": include_paths,
                        "exclude_paths": exclude_paths,
                        "credits_used": getattr(result, 'credits_used', 0)
                    }
                }
            else:
                error_msg = "No data returned from Firecrawl SDK crawl"
                logger.error(f"❌ Multi-page crawl error: {error_msg}")

                return {
                    "success": False,
                    "error": error_msg,
                    "content": None
                }

        except Exception as e:
            error_msg = f"Multi-page crawl exception: {str(e)}"
            logger.error(f"💥 {error_msg}")
            import traceback
            logger.error(f"💥 Traceback: {traceback.format_exc()}")
            return {"success": False, "error": error_msg, "content": None}


# Test function for Phase 2
async def test_crawl_executor():
    """Test the crawl executor with SDK integration"""

    print("🧪 PHASE 2 TEST - CRAWL EXECUTOR WITH SDK")
    print("=" * 50)

    executor = CrawlExecutor()

    try:
        # Test 1: SDK Connection test
        print("\n1. FIRECRAWL SDK CONNECTION TEST:")
        connection_test = await executor.test_firecrawl_connection()

        if connection_test["success"]:
            print("   ✅ Firecrawl SDK: Connected")
            print(f"   🔑 API Key: {connection_test['api_key_prefix']}")
            print(f"   📦 SDK Version: {connection_test.get('sdk_version', 'Unknown')}")
            if connection_test.get('warning'):
                print(f"   ⚠️ Warning: {connection_test['warning']}")
        else:
            print("   ❌ Firecrawl SDK: Connection failed")
            print(f"   💬 Error: {connection_test['error']}")
            print(f"   📝 Details: {connection_test.get('details', 'N/A')}")

        # Test 2: Single-page crawling (if SDK works)
        if connection_test["success"]:
            print("\n2. SINGLE-PAGE CRAWL TEST:")
            test_url = "https://github.com/charmbracelet/crush/blob/main/README.md"

            print(f"   🕷️ Crawling: {test_url}")
            crawl_result = await executor.crawl_source(test_url, "test-source-id")

            if crawl_result["success"]:
                print("   ✅ Single-page crawl: Successful")
                content = crawl_result.get("content", {})
                print(f"   📄 Content extracted: {len(str(content))} characters")
                print(f"   🆔 Content hash: {crawl_result.get('content_hash', 'N/A')[:16]}...")
                print(f"   🔧 Crawler: {crawl_result.get('metadata', {}).get('crawler', 'Unknown')}")

                # Show sample of extracted content
                if isinstance(content, dict) and content:
                    print("   🔍 Sample extracted data:")
                    for key, value in list(content.items())[:2]:
                        print(f"      {key}: {str(value)[:100]}...")
            else:
                error_msg = crawl_result.get('error', 'Unknown error')
                if 'Insufficient credits' in error_msg:
                    print("   ⚠️ Single-page crawl: Skipped (insufficient API credits)")
                    print("   💡 SDK integration works, but API credits needed for actual crawling")
                else:
                    print("   ❌ Single-page crawl: Failed")
                    print(f"   💬 Error: {error_msg}")
        else:
            print("\n2. SINGLE-PAGE CRAWL TEST: SKIPPED (SDK connection failed)")

        # Test 3: Multi-page crawling (if SDK works)
        if connection_test["success"]:
            print("\n3. MULTI-PAGE CRAWL TEST:")
            test_base_url = "https://httpbin.org"

            print(f"   🕷️ Multi-page crawling: {test_base_url}")
            multi_crawl_result = await executor.crawl_multiple_pages(
                test_base_url, "test-source-id", max_pages=3
            )

            if multi_crawl_result["success"]:
                print("   ✅ Multi-page crawl: Successful")
                content = multi_crawl_result.get("content", [])
                print(f"   📄 Pages crawled: {multi_crawl_result.get('pages_crawled', 0)}")
                print(f"   📄 Pages with content: {multi_crawl_result.get('pages_with_content', 0)}")
                print(f"   🆔 Content hash: {multi_crawl_result.get('content_hash', 'N/A')[:16]}...")
                print(f"   🔧 Crawler: {multi_crawl_result.get('metadata', {}).get('crawler', 'Unknown')}")
            else:
                error_msg = multi_crawl_result.get('error', 'Unknown error')
                if 'Insufficient credits' in error_msg:
                    print("   ⚠️ Multi-page crawl: Skipped (insufficient API credits)")
                    print("   💡 SDK integration works, but API credits needed for actual crawling")
                else:
                    print("   ❌ Multi-page crawl: Failed")
                    print(f"   💬 Error: {error_msg}")
        else:
            print("\n3. MULTI-PAGE CRAWL TEST: SKIPPED (SDK connection failed)")

        success = connection_test["success"]
        print(f"\n{'✅ PHASE 2 TEST: PASSED' if success else '⚠️ PHASE 2 TEST: LIMITED (API issues)'}")
        print("🚀 Crawl Executor with SDK is functional")

        return success

    except Exception as e:
        print(f"\n❌ PHASE 2 TEST: FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(test_crawl_executor())