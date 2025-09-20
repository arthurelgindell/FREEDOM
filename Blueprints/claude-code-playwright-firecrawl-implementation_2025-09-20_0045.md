# Claude Code Implementation Prompt: Playwright × Firecrawl Integration

## Mission
Implement a **FUNCTIONAL** Playwright × Firecrawl integration for the FREEDOM Platform that enables authenticated web scraping with "login once, crawl many" capabilities.

## Prime Directive
**"If it doesn't run, it doesn't exist."** Every component must be verifiable through actual execution. No scaffolding or mockups.

## Current State (VERIFIED 2025-09-20)
- ✅ FREEDOM Platform: 6 Docker containers running (API Gateway, MLX, KB, TechKnowledge, Castle GUI, PostgreSQL)
- ✅ Redis: Available on port 6379
- ✅ Firecrawl MCP: Configured but not containerized
- ✅ TechKnowledge: Has crawler code but not activated
- ❌ Playwright Workers: NOT EXIST
- ❌ Router Service: NOT EXIST
- ❌ Firecrawl Containers: NOT EXIST

## Implementation Tasks

### Phase 1: Firecrawl Container Integration

#### 1.1 Update docker-compose.yml
Add these services to `/Volumes/DATA/FREEDOM/docker-compose.yml`:

```yaml
  # Firecrawl API Service
  firecrawl-api:
    image: firecrawl/firecrawl:latest
    container_name: freedom-firecrawl-api
    environment:
      - NODE_ENV=production
      - PORT=3002
      - REDIS_URL=redis://redis:6379
      - FIRECRAWL_ALLOW_UNSAFE_RENDERING=true
    depends_on:
      redis:
        condition: service_healthy
    ports:
      - "3002:3002"
    networks:
      - freedom_default
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3002/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # Firecrawl Worker
  firecrawl-worker:
    image: firecrawl/firecrawl:latest
    container_name: freedom-firecrawl-worker
    command: ["pnpm", "worker:start"]
    environment:
      - NODE_ENV=production
      - REDIS_URL=redis://redis:6379
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - freedom_default
    restart: unless-stopped

  # Redis (if not already present)
  redis:
    image: redis:7-alpine
    container_name: freedom-redis
    command: ["redis-server", "--appendonly", "yes"]
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - freedom_default
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 20
    restart: unless-stopped
```

#### 1.2 Verify Firecrawl Services
```bash
# Start new services
docker compose up -d firecrawl-api firecrawl-worker redis

# Verify health
curl http://localhost:3002/health

# Test scraping
curl -X POST http://localhost:3002/v1/scrape \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com","formats":[{"type":"markdown"}]}'
```

### Phase 2: Create Router Service

#### 2.1 Create Directory Structure
```bash
mkdir -p /Volumes/DATA/FREEDOM/services/router
```

#### 2.2 Create `/Volumes/DATA/FREEDOM/services/router/Dockerfile`
```dockerfile
FROM python:3.13-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn redis httpx
COPY app.py .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8003"]
```

#### 2.3 Create `/Volumes/DATA/FREEDOM/services/router/app.py`
```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os, json, httpx
import redis.asyncio as redis
from typing import Dict, Optional
from datetime import datetime

FIRECRAWL = os.environ.get("FIRECRAWL_BASE_URL", "http://firecrawl-api:3002")
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
        "redis_connected": r is not None,
        "firecrawl_url": FIRECRAWL
    }

@app.post("/crawl")
async def route_crawl(task: Dict):
    """
    Route crawl tasks to appropriate service
    
    Examples:
    {"url": "https://docs.python.org", "intent": "scrape"}  -> Firecrawl
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
        # Direct to Firecrawl
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "url": task.get("url"),
                "formats": [{"type": "markdown"}],
                "includeHtml": False,
                "screenshot": task.get("screenshot", False)
            }
            
            try:
                res = await client.post(f"{FIRECRAWL}/v1/scrape", json=payload)
                res.raise_for_status()
                
                # Store result in Redis
                result = res.json()
                await r.setex(f"result:{task_id}", 3600, json.dumps(result))
                
                return {
                    "task_id": task_id,
                    "routed_to": "firecrawl",
                    "status": "completed",
                    "data": result.get("data", {})
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

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
    
    stats = {
        "playwright_queue_length": await r.llen("pw:tasks"),
        "firecrawl_queue_length": await r.llen("fc:targets"),
        "completed_tasks": await r.dbsize()
    }
    return stats
```

#### 2.4 Add Router to docker-compose.yml
```yaml
  router:
    build:
      context: ./services/router
      dockerfile: Dockerfile
    container_name: freedom-router
    environment:
      - REDIS_URL=redis://redis:6379
      - FIRECRAWL_BASE_URL=http://firecrawl-api:3002
    depends_on:
      redis:
        condition: service_healthy
      firecrawl-api:
        condition: service_healthy
    ports:
      - "8003:8003"
    networks:
      - freedom_default
    restart: unless-stopped
```

### Phase 3: Create Playwright Workers

#### 3.1 Create Directory Structure
```bash
mkdir -p /Volumes/DATA/FREEDOM/services/pw-worker
```

#### 3.2 Create `/Volumes/DATA/FREEDOM/services/pw-worker/Dockerfile`
```dockerfile
FROM mcr.microsoft.com/playwright:v1.48.0-noble
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
CMD ["node", "index.js"]
```

#### 3.3 Create `/Volumes/DATA/FREEDOM/services/pw-worker/package.json`
```json
{
  "name": "pw-worker",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "dependencies": {
    "playwright": "^1.48.0",
    "redis": "^4.7.0"
  }
}
```

#### 3.4 Create `/Volumes/DATA/FREEDOM/services/pw-worker/index.js`
```javascript
import { createClient } from "redis";
import { chromium } from "playwright";
import { promises as fs } from "fs";

const redis = createClient({ url: process.env.REDIS_URL || "redis://localhost:6379" });
await redis.connect();

console.log("Playwright worker started, waiting for tasks...");

// Worker loop
while (true) {
  try {
    // Block until task available
    const task = await redis.blPop("pw:tasks", 0);
    if (!task) continue;
    
    const job = JSON.parse(task.element);
    console.log(`Processing task ${job.id}: ${job.url}`);
    
    const browser = await chromium.launch({ 
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    // Load or create context
    const ctx = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    });
    
    const page = await ctx.newPage();
    
    try {
      // Navigate to URL
      await page.goto(job.url, { waitUntil: "domcontentloaded", timeout: 30000 });
      
      // Handle authentication if credentials provided
      if (job.credentials && job.credentials.username) {
        console.log("Attempting login...");
        
        // Common login selectors (customize per site)
        const usernameSelectors = ['#username', '#email', 'input[name="username"]', 'input[type="email"]'];
        const passwordSelectors = ['#password', 'input[name="password"]', 'input[type="password"]'];
        const submitSelectors = ['button[type="submit"]', 'input[type="submit"]', 'button:has-text("Sign in")'];
        
        // Try username field
        for (const selector of usernameSelectors) {
          if (await page.locator(selector).count() > 0) {
            await page.fill(selector, job.credentials.username);
            break;
          }
        }
        
        // Try password field
        for (const selector of passwordSelectors) {
          if (await page.locator(selector).count() > 0) {
            await page.fill(selector, job.credentials.password);
            break;
          }
        }
        
        // Submit form
        for (const selector of submitSelectors) {
          if (await page.locator(selector).count() > 0) {
            await page.click(selector);
            await page.waitForLoadState("networkidle", { timeout: 10000 });
            break;
          }
        }
        
        // Save authentication state
        const storageState = await ctx.storageState();
        await redis.setEx(`auth:${new URL(job.url).hostname}`, 3600, JSON.stringify(storageState));
      }
      
      // Extract links for Firecrawl
      const links = await page.$$eval("a[href]", anchors => 
        anchors.map(a => {
          const href = a.getAttribute("href");
          if (!href || href.startsWith("#") || href.startsWith("javascript:")) return null;
          try {
            return new URL(href, window.location.href).href;
          } catch {
            return null;
          }
        }).filter(Boolean)
      );
      
      // Take screenshot for evidence
      const screenshot = await page.screenshot({ fullPage: true });
      
      // Store results
      const result = {
        task_id: job.id,
        url: job.url,
        links_found: links.length,
        links_sample: links.slice(0, 10),
        screenshot_size: screenshot.length,
        completed_at: new Date().toISOString()
      };
      
      await redis.setEx(`result:${job.id}`, 3600, JSON.stringify(result));
      
      // Queue discovered links for Firecrawl
      for (const link of links.slice(0, 50)) {
        await redis.rPush("fc:targets", JSON.stringify({ 
          url: link,
          parent: job.url,
          discovered_at: new Date().toISOString()
        }));
      }
      
      console.log(`Task ${job.id} completed: ${links.length} links discovered`);
      
    } catch (error) {
      console.error(`Task ${job.id} failed:`, error.message);
      await redis.setEx(`error:${job.id}`, 3600, JSON.stringify({
        task_id: job.id,
        error: error.message,
        failed_at: new Date().toISOString()
      }));
    } finally {
      await ctx.close();
      await browser.close();
    }
    
  } catch (error) {
    console.error("Worker error:", error);
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
}
```

#### 3.5 Add Playwright Worker to docker-compose.yml
```yaml
  pw-worker:
    build:
      context: ./services/pw-worker
      dockerfile: Dockerfile
    container_name: freedom-pw-worker
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      redis:
        condition: service_healthy
    shm_size: "2gb"
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: "4"
          memory: 6g
    networks:
      - freedom_default
    restart: unless-stopped
```

### Phase 4: Update TechKnowledge Integration

#### 4.1 Update `/Volumes/DATA/FREEDOM/services/techknowledge/techknowledge/extraction/crawler.py`
Modify the Firecrawl base URL to use the containerized service:

```python
# Line ~30 - Update initialization
def __init__(self):
    """Initialize with API configuration"""
    self.api_key = TechKnowledgeConfig.FIRECRAWL_API_KEY
    # Use local containerized Firecrawl
    self.base_url = os.environ.get('FIRECRAWL_URL', 'http://firecrawl-api:3002/v1')
    self.decontaminator = TechnicalDecontaminator()
    self.db = get_db()
```

#### 4.2 Update TechKnowledge Environment
Add to TechKnowledge service in docker-compose:

```yaml
  techknowledge:
    # ... existing config ...
    environment:
      - FIRECRAWL_URL=http://firecrawl-api:3002/v1
      - REDIS_URL=redis://redis:6379
      - USE_LOCAL_FIRECRAWL=true
```

### Phase 5: Verification & Testing

#### 5.1 Health Check Script
Create `/Volumes/DATA/FREEDOM/scripts/verify_crawl_stack.sh`:

```bash
#!/bin/bash
set -e

echo "🔍 Verifying Crawl Stack..."

# Check Redis
echo -n "Redis: "
redis-cli ping > /dev/null 2>&1 && echo "✅ HEALTHY" || echo "❌ FAILED"

# Check Firecrawl API
echo -n "Firecrawl API: "
curl -s http://localhost:3002/health > /dev/null 2>&1 && echo "✅ HEALTHY" || echo "❌ FAILED"

# Check Router
echo -n "Router: "
curl -s http://localhost:8003/health > /dev/null 2>&1 && echo "✅ HEALTHY" || echo "❌ FAILED"

# Check queue stats
echo -e "\n📊 Queue Statistics:"
curl -s http://localhost:8003/stats | python3 -m json.tool

# Test simple scrape
echo -e "\n🧪 Testing Firecrawl scrape..."
curl -s -X POST http://localhost:3002/v1/scrape \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com","formats":[{"type":"markdown"}]}' \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"✅ Success: {len(d.get('data',{}).get('markdown',''))} chars scraped\")" \
  || echo "❌ Scrape failed"

# Test router
echo -e "\n🧪 Testing Router..."
curl -s -X POST http://localhost:8003/crawl \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com","intent":"scrape"}' \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"✅ Routed to: {d.get('routed_to')}\")" \
  || echo "❌ Router failed"

echo -e "\n✅ Verification complete!"
```

Make it executable:
```bash
chmod +x /Volumes/DATA/FREEDOM/scripts/verify_crawl_stack.sh
```

#### 5.2 Integration Test
Create `/Volumes/DATA/FREEDOM/tests/integration/test_crawl_integration.py`:

```python
import pytest
import httpx
import asyncio
import json
from datetime import datetime

BASE_ROUTER_URL = "http://localhost:8003"
BASE_FIRECRAWL_URL = "http://localhost:3002"

@pytest.mark.asyncio
async def test_firecrawl_health():
    """Test Firecrawl API is healthy"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_FIRECRAWL_URL}/health")
        assert response.status_code == 200
        assert "status" in response.json()

@pytest.mark.asyncio
async def test_router_health():
    """Test Router service is healthy"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_ROUTER_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["redis_connected"] == True

@pytest.mark.asyncio
async def test_simple_scrape_routing():
    """Test routing a simple scrape to Firecrawl"""
    async with httpx.AsyncClient() as client:
        task = {
            "url": "https://example.com",
            "intent": "scrape"
        }
        response = await client.post(f"{BASE_ROUTER_URL}/crawl", json=task)
        assert response.status_code == 200
        data = response.json()
        assert data["routed_to"] == "firecrawl"
        assert "task_id" in data

@pytest.mark.asyncio
async def test_auth_routing():
    """Test routing authentication task to Playwright"""
    async with httpx.AsyncClient() as client:
        task = {
            "url": "https://app.example.com/login",
            "intent": "login and extract dashboard"
        }
        response = await client.post(f"{BASE_ROUTER_URL}/crawl", json=task)
        assert response.status_code == 200
        data = response.json()
        assert data["routed_to"] == "playwright"
        assert data["queued"] == True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### Phase 6: Deploy & Verify

#### Commands to Execute:
```bash
# 1. Build and start all services
cd /Volumes/DATA/FREEDOM
docker compose build router pw-worker
docker compose up -d

# 2. Wait for services to be healthy
sleep 30

# 3. Check all services
docker ps --format "table {{.Names}}\t{{.Status}}"

# 4. Run verification script
./scripts/verify_crawl_stack.sh

# 5. Run integration tests
pytest tests/integration/test_crawl_integration.py -v

# 6. Check logs for any errors
docker compose logs --tail=50 router
docker compose logs --tail=50 pw-worker
docker compose logs --tail=50 firecrawl-api
```

## Success Criteria

### ✅ Definition of FUNCTIONAL:
1. **Router Service**: Returns 200 on `/health` endpoint
2. **Firecrawl API**: Successfully scrapes https://example.com
3. **Playwright Worker**: Processes tasks from Redis queue
4. **Redis Queues**: `pw:tasks` and `fc:targets` accepting messages
5. **Integration Test**: All tests in `test_crawl_integration.py` pass

### Evidence Generation:
After successful deployment, generate evidence file:

```python
# Generate evidence file
import json
from datetime import datetime
import subprocess

evidence = {
    "component": "playwright-firecrawl-integration",
    "deployed_at": datetime.now().isoformat(),
    "services": {
        "router": subprocess.check_output("curl -s http://localhost:8003/health", shell=True).decode(),
        "firecrawl": subprocess.check_output("curl -s http://localhost:3002/health", shell=True).decode(),
        "redis": subprocess.check_output("redis-cli ping", shell=True).decode().strip()
    },
    "docker_containers": subprocess.check_output("docker ps --format json", shell=True).decode(),
    "verification": "FUNCTIONAL",
    "tests_passed": True
}

with open(f"/Volumes/DATA/FREEDOM/documents/reports/EVIDENCE_playwright_firecrawl_{datetime.now().strftime('%Y-%m-%d_%H%M')}.json", "w") as f:
    json.dump(evidence, f, indent=2)
```

## Troubleshooting

### Common Issues & Solutions:

1. **Firecrawl image not found**:
   - Build from source: `git clone https://github.com/mendableai/firecrawl && cd firecrawl && docker build -t firecrawl/firecrawl:latest .`

2. **Redis connection refused**:
   - Check Redis is running: `docker ps | grep redis`
   - Test connection: `redis-cli ping`

3. **Playwright browser crashes**:
   - Ensure `shm_size: "2gb"` is set in docker-compose
   - Check memory allocation: `docker stats`

4. **Router can't reach Firecrawl**:
   - Verify network: `docker network ls`
   - Check DNS: `docker exec freedom-router nslookup firecrawl-api`

## Final Notes

- **ONE file per function** - Each service has a single main file
- **Test immediately** - Run verification after each phase
- **Evidence required** - Generate JSON evidence for each success
- **Rollback on failure** - Keep working version, delete failed attempts

Remember: **"If it doesn't run, it doesn't exist."**