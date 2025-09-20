from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os, json, httpx
import redis.asyncio as redis
from typing import Dict, Optional
from datetime import datetime

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379")
app = FastAPI(title="Crawl Router", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

r = None

@app.on_event("startup")
async def startup():
    global r
    r = redis.from_url(REDIS_URL)
    await r.ping()
    print(f"Router connected to Redis at {REDIS_URL}")

@app.on_event("shutdown")
async def shutdown():
    global r
    if r:
        await r.close()

def needs_playwright(task: dict) -> bool:
    """Determine if task requires Playwright for authentication/interaction"""
    intent = (task.get("intent") or "").lower()
    url = task.get("url", "")

    # Keywords that indicate need for browser automation
    auth_keywords = ["login", "signin", "auth", "mfa", "2fa", "consent", "dashboard", "portal"]

    # Check intent
    if any(k in intent for k in auth_keywords):
        return True

    # Check URL patterns
    protected_patterns = ["/login", "/signin", "/auth", "/account", "/dashboard", "/admin"]
    if any(p in url.lower() for p in protected_patterns):
        return True

    return False

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "redis_connected": r is not None
    }

@app.post("/crawl")
async def route_crawl(task: Dict):
    """
    Route crawl tasks to appropriate service

    Examples:
    {"url": "https://docs.python.org", "intent": "scrape"}  -> Direct scrape
    {"url": "https://app.example.com", "intent": "login and extract dashboard"} -> Playwright
    """
    global r

    if not r:
        raise HTTPException(status_code=503, detail="Redis not connected")

    task_id = f"task_{datetime.now().timestamp()}"

    if needs_playwright(task):
        # Queue for Playwright worker
        await r.rpush("pw:tasks", json.dumps({
            "id": task_id,
            "url": task.get("url"),
            "intent": task.get("intent"),
            "credentials": task.get("credentials", {}),
            "selectors": task.get("selectors", {}),
            "created_at": datetime.now().isoformat()
        }))

        return {
            "task_id": task_id,
            "routed_to": "playwright",
            "queued": True,
            "reason": "Authentication or interaction required"
        }
    else:
        # Route to Firecrawl for simple scrapes
        try:
            async with httpx.AsyncClient() as client:
                # Call Firecrawl API
                firecrawl_response = await client.post(
                    "http://firecrawl:8004/scrape",
                    json={"url": task.get("url")},
                    timeout=30.0
                )

                if firecrawl_response.status_code == 200:
                    firecrawl_data = firecrawl_response.json()
                    result = {
                        "url": task.get("url"),
                        "status": "completed",
                        "data": firecrawl_data
                    }
                else:
                    result = {
                        "url": task.get("url"),
                        "status": "error",
                        "error": f"Firecrawl returned {firecrawl_response.status_code}"
                    }

                await r.setex(f"result:{task_id}", 3600, json.dumps(result))

                return {
                    "task_id": task_id,
                    "routed_to": "firecrawl",
                    "status": result["status"],
                    "data": result
                }
        except Exception as e:
            # NO MOCK DATA - PRIME DIRECTIVE: If it doesn't run, it doesn't exist
            result = {
                "url": task.get("url"),
                "status": "error",
                "error": f"Firecrawl service error: {str(e)}"
            }
            await r.setex(f"result:{task_id}", 3600, json.dumps(result))

            return {
                "task_id": task_id,
                "routed_to": "firecrawl",
                "status": "error",
                "error": str(e)
            }

@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Check status of a crawl task"""
    global r

    # Check for completed result
    result = await r.get(f"result:{task_id}")
    if result:
        return {
            "task_id": task_id,
            "status": "completed",
            "data": json.loads(result)
        }

    # Check if in queue
    queue_length = await r.llen("pw:tasks")
    return {
        "task_id": task_id,
        "status": "pending",
        "queue_position": queue_length
    }

@app.get("/stats")
async def get_stats():
    """Get router statistics"""
    global r

    if not r:
        return {"error": "Redis not connected"}

    stats = {
        "playwright_queue_length": await r.llen("pw:tasks"),
        "completed_tasks": await r.dbsize()
    }
    return stats