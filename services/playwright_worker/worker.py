import asyncio
import json
import os
import redis.asyncio as redis
from playwright.async_api import async_playwright
from typing import Optional, Dict, Any
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379")

class PlaywrightWorker:
    """Worker that processes authentication-required crawl tasks using Playwright"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.browser = None
        self.playwright = None

    async def connect_redis(self):
        """Connect to Redis"""
        self.redis_client = await redis.from_url(REDIS_URL)
        await self.redis_client.ping()
        logger.info(f"Connected to Redis at {REDIS_URL}")

    async def setup_browser(self):
        """Initialize Playwright browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        logger.info("Playwright browser initialized")

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single crawl task requiring authentication"""
        url = task.get("url")
        intent = task.get("intent", "")
        credentials = task.get("credentials", {})
        selectors = task.get("selectors", {})

        logger.info(f"Processing task {task.get('id')}: {url}")

        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        try:
            # Navigate to URL
            await page.goto(url, wait_until='networkidle', timeout=30000)

            # Handle authentication if credentials provided
            if credentials:
                username = credentials.get("username")
                password = credentials.get("password")

                # Common login selectors (can be customized via selectors param)
                username_selector = selectors.get("username", "input[name='username'], input[name='email'], input[type='email']")
                password_selector = selectors.get("password", "input[name='password'], input[type='password']")
                submit_selector = selectors.get("submit", "button[type='submit'], input[type='submit'], button:has-text('Login'), button:has-text('Sign in')")

                # Fill credentials
                if username:
                    await page.fill(username_selector, username)
                if password:
                    await page.fill(password_selector, password)

                # Submit form
                await page.click(submit_selector)

                # Wait for navigation or specific element
                wait_for = selectors.get("wait_for", "body")
                await page.wait_for_selector(wait_for, timeout=10000)

                logger.info(f"Authentication completed for {url}")

            # Extract content based on intent
            if "extract" in intent.lower() or "scrape" in intent.lower():
                # Get page content
                content = await page.content()

                # Get text content
                text_content = await page.evaluate("() => document.body.innerText")

                # Take screenshot for verification
                screenshot = await page.screenshot(full_page=True)

                result = {
                    "status": "success",
                    "url": url,
                    "final_url": page.url,
                    "title": await page.title(),
                    "content": {
                        "html": content[:5000],  # Truncate for storage
                        "text": text_content[:5000],
                        "screenshot_available": True
                    },
                    "cookies": await context.cookies(),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # Just navigate and confirm success
                result = {
                    "status": "success",
                    "url": url,
                    "final_url": page.url,
                    "title": await page.title(),
                    "timestamp": datetime.now().isoformat()
                }

            return result

        except Exception as e:
            logger.error(f"Error processing task {task.get('id')}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "url": url,
                "timestamp": datetime.now().isoformat()
            }
        finally:
            await context.close()

    async def run(self):
        """Main worker loop"""
        await self.connect_redis()
        await self.setup_browser()

        logger.info("Playwright worker started, waiting for tasks...")

        while True:
            try:
                # Block waiting for task (timeout after 5 seconds to check health)
                task_data = await self.redis_client.blpop("pw:tasks", timeout=5)

                if task_data:
                    _, task_json = task_data
                    task = json.loads(task_json)

                    # Process the task
                    result = await self.process_task(task)

                    # Store result in Redis
                    task_id = task.get("id")
                    await self.redis_client.setex(
                        f"result:{task_id}",
                        3600,  # Expire after 1 hour
                        json.dumps(result)
                    )

                    logger.info(f"Task {task_id} completed with status: {result['status']}")

            except Exception as e:
                logger.error(f"Worker error: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying

    async def cleanup(self):
        """Cleanup resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        if self.redis_client:
            await self.redis_client.close()

async def main():
    worker = PlaywrightWorker()
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Shutting down worker...")
    finally:
        await worker.cleanup()

if __name__ == "__main__":
    asyncio.run(main())