from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from firecrawl import FirecrawlApp
import os
from typing import Dict, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Firecrawl Service", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Firecrawl with API key
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")
if not FIRECRAWL_API_KEY:
    logger.error("FIRECRAWL_API_KEY not set!")
    raise ValueError("FIRECRAWL_API_KEY environment variable is required")

firecrawl_app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "firecrawl",
        "api_key_configured": bool(FIRECRAWL_API_KEY)
    }

@app.post("/scrape")
async def scrape(request: Dict):
    """
    Scrape a URL using Firecrawl

    Request body:
    {
        "url": "https://example.com",
        "options": {
            "formats": ["markdown", "html"],
            "onlyMainContent": true
        }
    }
    """
    url = request.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    options = request.get("options", {})

    try:
        # Prepare kwargs for scrape method
        scrape_kwargs = {}

        # Map options to correct parameter names
        if 'formats' in options:
            scrape_kwargs['formats'] = options['formats']
        if 'onlyMainContent' in options:
            scrape_kwargs['only_main_content'] = options['onlyMainContent']
        if 'waitFor' in options:
            scrape_kwargs['wait_for'] = options['waitFor']

        logger.info(f"Scraping URL: {url} with params: {scrape_kwargs}")

        # Scrape the URL
        result = firecrawl_app.scrape(
            url,
            **scrape_kwargs
        )

        logger.info(f"Successfully scraped {url}")

        return {
            "success": True,
            "url": url,
            "data": result
        }

    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/crawl")
async def crawl(request: Dict):
    """
    Crawl a website using Firecrawl

    Request body:
    {
        "url": "https://example.com",
        "options": {
            "limit": 10,
            "maxDepth": 2,
            "includePaths": ["/docs/*"],
            "excludePaths": ["/admin/*"]
        }
    }
    """
    url = request.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    options = request.get("options", {})

    try:
        # Prepare kwargs for crawl method
        crawl_kwargs = {}

        if 'limit' in options:
            crawl_kwargs['limit'] = options['limit']
        if 'maxDepth' in options:
            crawl_kwargs['max_depth'] = options['maxDepth']
        if 'includePaths' in options:
            crawl_kwargs['include_paths'] = options['includePaths']
        if 'excludePaths' in options:
            crawl_kwargs['exclude_paths'] = options['excludePaths']

        logger.info(f"Crawling website: {url} with params: {crawl_kwargs}")

        # Start the crawl
        crawl_result = firecrawl_app.crawl(
            url,
            **crawl_kwargs
        )

        logger.info(f"Successfully crawled {url}")

        return {
            "success": True,
            "url": url,
            "data": crawl_result
        }

    except Exception as e:
        logger.error(f"Error crawling {url}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Firecrawl API Service",
        "endpoints": ["/health", "/scrape", "/crawl"],
        "status": "operational"
    }