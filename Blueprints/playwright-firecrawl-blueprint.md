# Playwright × Firecrawl Self‑Hosted Blueprint

> **Purpose:** Combine Playwright’s deterministic, stateful browser automation with Firecrawl’s high‑throughput crawling, normalization, and search→scrape pipelines. This repo‑style blueprint uses Docker Compose, a small router service, and Redis to orchestrate “login once, crawl many” and build RAG‑ready corpora with auditable artifacts.

**Components**
- **Firecrawl (API + worker)** — `/scrape` and `/search` endpoints, Markdown/summary/HTML outputs, screenshots, dynamic‑site handling, caching, rate limits.
- **Playwright workers** — your scripted interactions (auth/MFA/consent flows, tricky SPAs) that enumerate URLs and persist sessions.
- **Router (FastAPI + LangGraph‑style logic)** — routes tasks to Playwright or Firecrawl based on intent.
- **Redis** — queue/state. Truth Engine or other services can share it.
- **(Optional) Firecrawl’s internal Playwright service** — when self‑hosting, you can tune the Playwright tier Firecrawl uses under the hood.

---

## Directory Layout

```
playwright-firecrawl-blueprint/
├─ docker-compose.yml
├─ services/
│  ├─ pw-worker/
│  │  ├─ Dockerfile
│  │  ├─ package.json
│  │  └─ index.js
│  └─ router/
│     ├─ Dockerfile
│     └─ app.py
└─ README.md
```

---

## docker-compose.yml

```yaml
version: "3.9"

services:
  redis:
    image: redis:7-alpine
    command: ["redis-server", "--appendonly", "yes"]
    ports: ["6379:6379"]
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 20

  firecrawl-api:
    image: firecrawl/firecrawl:latest
    environment:
      - NODE_ENV=production
      - PORT=3002
      - REDIS_URL=redis://redis:6379
      # Optional: relax renderer restrictions for tough sites in lab settings
      - FIRECRAWL_ALLOW_UNSAFE_RENDERING=true
    depends_on:
      redis:
        condition: service_healthy
    ports:
      - "3002:3002"

  firecrawl-worker:
    image: firecrawl/firecrawl:latest
    command: ["pnpm", "worker:start"]
    environment:
      - NODE_ENV=production
      - REDIS_URL=redis://redis:6379
    depends_on:
      redis:
        condition: service_healthy

  # Optional: internal Playwright tier for Firecrawl (customize or omit per docs)
  firecrawl-playwright:
    image: mcr.microsoft.com/playwright:v1.55.0-noble
    shm_size: "2gb"
    deploy:
      resources:
        limits:
          cpus: "4"
          memory: 6g

  # Your own Playwright worker pool for scripted login/stateful flows
  pw-worker:
    build:
      context: ./services/pw-worker
      dockerfile: Dockerfile
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

  # Minimal router: decides Playwright (interactive) vs Firecrawl (bulk)
  router:
    build:
      context: ./services/router
      dockerfile: Dockerfile
    environment:
      - REDIS_URL=redis://redis:6379
      - FIRECRAWL_BASE_URL=http://firecrawl-api:3002
    depends_on:
      redis:
        condition: service_healthy
      firecrawl-api:
        condition: service_started
    ports:
      - "8080:8080"

volumes:
  redis-data:
```

> **Apple Silicon note:** All images above are multi‑arch; if Firecrawl’s image tag on your host is missing a platform, build from source and retag. The Playwright `:noble` images include browsers & deps; your app layer installs packages.

---

## services/pw-worker/Dockerfile

```dockerfile
FROM mcr.microsoft.com/playwright:v1.55.0-noble
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
CMD ["node", "index.js"]
```

## services/pw-worker/package.json

```json
{
  "name": "pw-worker",
  "private": true,
  "type": "module",
  "dependencies": {
    "playwright": "^1.55.0",
    "redis": "^4.7.0"
  }
}
```

## services/pw-worker/index.js

```js
import { createClient } from "redis";
import { chromium } from "playwright";

const redis = createClient({ url: process.env.REDIS_URL || "redis://localhost:6379" });
await redis.connect();

while (true) {
  const task = await redis.blPop("pw:tasks", 0); // blocks until job
  const job = JSON.parse(task.element);

  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    storageState: job.storageStatePath || undefined
  });
  const page = await ctx.newPage();

  // Example: scripted interaction before handing off to Firecrawl
  await page.goto(job.url, { waitUntil: "domcontentloaded" });
  // TODO: login/MFA/consent/click flows here; enumerate deep links:
  const links = await page.$$eval("a[href]", as => as.map(a => new URL(a.getAttribute("href"), location.href).href));

  // Enqueue URLs for Firecrawl to scrape in bulk
  for (const url of links.slice(0, 25)) {
    await redis.rPush("fc:targets", JSON.stringify({ url }));
  }

  await ctx.close();
  await browser.close();
}
```

---

## services/router/Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn redis httpx
COPY app.py .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

## services/router/app.py

```python
from fastapi import FastAPI
import os, json, httpx
import redis.asyncio as redis

FIRECRAWL = os.environ.get("FIRECRAWL_BASE_URL", "http://localhost:3002")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
r = redis.from_url(REDIS_URL)
app = FastAPI()

def needs_playwright(task: dict) -> bool:
    intent = (task.get("intent") or "").lower()
    return any(k in intent for k in ("login", "mfa", "consent", "click", "form", "dashboard"))

@app.post("/ingest")
async def ingest(task: dict):
    # Example payloads:
    # {"intent": "login then crawl", "url": "https://example.com/portal"}
    # {"url": "https://example.com/docs"}  # simple scrape
    # {"search": {"q": "site:langchain.com langgraph quickstart", "maxResults": 5}}
    if needs_playwright(task):
        await r.rpush("pw:tasks", json.dumps({
            "url": task["url"],
            "storageStatePath": "/app/state.json"
        }))
        return {"routed": "playwright"}

    async with httpx.AsyncClient() as client:
        if task.get("search"):
            payload = {
                "query": task["search"]["q"],
                "scrapeOptions": {"formats": [{"type": "markdown"}]}
            }
            res = await client.post(f"{FIRECRAWL}/v1/search", json=payload, timeout=None)
            return res.json()
        else:
            payload = {
                "url": task["url"],
                "formats": [{"type": "markdown"}],
                "includeHtml": False,
                "includeRawHtml": False,
                "screenshot": True
            }
            res = await client.post(f"{FIRECRAWL}/v1/scrape", json=payload, timeout=None)
            return res.json()
```

---

## Quickstart

```bash
# Build and run
docker compose build
docker compose up -d

# Smoke test Firecrawl: scrape single page → Markdown (+screenshot)
curl -s http://localhost:3002/v1/scrape \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com","formats":[{"type":"markdown"}],"screenshot":true}' | jq .

# Search → scrape in one call
curl -s http://localhost:3002/v1/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"site:langchain.com langgraph quickstart","scrapeOptions":{"formats":[{"type":"markdown"}]}}' | jq .

# Route via the minimal router (scrape path)
curl -s http://localhost:8080/ingest \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://docs.firecrawl.dev/features/scrape"}' | jq .

# Route an interactive task (goes to Playwright queue)
curl -s http://localhost:8080/ingest \
  -H 'Content-Type: application/json' \
  -d '{"intent":"login then crawl","url":"https://example.com/portal"}' | jq .
```

---

## Ops Tips

- **Pin versions:** Use fixed tags for Playwright (e.g., `v1.55.*`) and for your Firecrawl image/commit. Check release notes before upgrades.
- **Playwright shm size:** Keep `--shm-size=2g` or similar to avoid Chromium crashes in Docker.
- **Self‑host gotcha:** If Firecrawl references an internal Playwright image you don’t have, build it locally or point to `mcr.microsoft.com/playwright:*` and wire the integration per your Firecrawl version.
- **RAG pipeline:** Persist Firecrawl Markdown + metadata; embed in your vector store. Keep Playwright traces/videos separately for reproducibility.
- **Truth Engine:** Diff newest Markdown vs prior captures; alert on significant changes (content hash, title changes, price deltas, etc.).

---

## Why This Combination

- Firecrawl handles dynamic sites, caching, rate limits, and produces LLM‑ready Markdown/structured data. Its `/search` can discover then scrape targets in a single API call.
- Playwright excels at deterministic, stateful interactions (logins, consent banners, SPAs, multi‑tab flows) and session persistence (“login once, crawl many”).
- Together: Use Playwright to breach the “interaction barrier”, then hand URLs to Firecrawl for high‑throughput harvest and normalization.

---

## References

- Firecrawl Docs — **Scrape** feature and API reference: https://docs.firecrawl.dev/features/scrape , https://docs.firecrawl.dev/api-reference/endpoint/scrape  
- Firecrawl Docs — **Search** feature and API reference: https://docs.firecrawl.dev/features/search , https://docs.firecrawl.dev/api-reference/endpoint/search  
- Firecrawl Docs — **Self‑host / Docker Compose**: https://docs.firecrawl.dev/contributing/guide , https://docs.firecrawl.dev/contributing/self-host  
- Firecrawl — **Search announcement** (search→scrape in one): https://www.firecrawl.dev/blog/introducing-search-endpoint  
- Advanced Scraping Guide: https://docs.firecrawl.dev/advanced-scraping-guide  
- Playwright — **Docker** docs and official images: https://playwright.dev/docs/docker , https://hub.docker.com/r/microsoft/playwright  
- Playwright — Release notes (pinning versions): https://playwright.dev/docs/release-notes
```
