#!/usr/bin/env python3
"""
FREEDOM MLX Proxy Service
Proxy to local MLX server running on host machine
"""

import os
import time
import uuid
import asyncio
import structlog
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List

import uvicorn
import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Configure structured logging
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
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Configuration - connect to host MLX server with fallback
MLX_HOST = os.getenv("MLX_HOST", "host.docker.internal")
MLX_PORT = int(os.getenv("MLX_PORT", "8000"))
MLX_BASE_URL = f"http://{MLX_HOST}:{MLX_PORT}"

# LM Studio fallback configuration
LM_STUDIO_HOST = os.getenv("LM_STUDIO_HOST", "host.docker.internal")
LM_STUDIO_PORT = int(os.getenv("LM_STUDIO_PORT", "1234"))
LM_STUDIO_URL = f"http://{LM_STUDIO_HOST}:{LM_STUDIO_PORT}"

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Metrics - Initialize at startup to avoid conflicts
proxy_requests = None
proxy_duration = None
active_requests = None
mlx_server_status = None

# HTTP client for proxy requests
http_client = None

class ProxyManager:
    """Manages connections to local MLX server with LM Studio fallback"""

    def __init__(self):
        self.primary_url = MLX_BASE_URL
        self.fallback_url = LM_STUDIO_URL
        self.active_url = None  # Will be set based on health checks
        self.using_fallback = False
        self.client = None

    async def initialize(self):
        """Initialize HTTP client"""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
        )
        # Determine which upstream to use
        await self._determine_active_upstream()
        logger.info("Proxy client initialized",
                   primary_url=self.primary_url,
                   fallback_url=self.fallback_url,
                   active_url=self.active_url,
                   using_fallback=self.using_fallback)

    async def close(self):
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()
            logger.info("Proxy client closed")

    async def _determine_active_upstream(self):
        """Determine which upstream server to use based on availability"""
        # Try primary MLX server first
        primary_healthy = await self._check_upstream_health(self.primary_url, "/health")
        if primary_healthy:
            self.active_url = self.primary_url
            self.using_fallback = False
            logger.info("Using primary MLX server", url=self.primary_url)
            return

        # Try LM Studio fallback with /v1/models endpoint
        fallback_healthy = await self._check_upstream_health(self.fallback_url, "/v1/models")
        if fallback_healthy:
            self.active_url = self.fallback_url
            self.using_fallback = True
            logger.info("Using LM Studio fallback", url=self.fallback_url)
            return

        # Default to primary if both are down
        self.active_url = self.primary_url
        self.using_fallback = False
        logger.warning("Both upstreams unavailable, defaulting to primary")

    async def _check_upstream_health(self, url: str, endpoint: str) -> bool:
        """Check if a specific upstream is healthy"""
        try:
            response = await self.client.get(f"{url}{endpoint}", timeout=2.0)
            return response.status_code == 200
        except Exception:
            return False

    async def check_health(self) -> bool:
        """Check if active server is reachable"""
        # Re-determine active upstream
        await self._determine_active_upstream()

        # Check the active upstream
        endpoint = "/v1/models" if self.using_fallback else "/health"
        is_healthy = await self._check_upstream_health(self.active_url, endpoint)

        if mlx_server_status:
            mlx_server_status.set(1 if is_healthy else 0)
        return is_healthy

    async def proxy_request(self, method: str, path: str, **kwargs):
        """Proxy request to active MLX server with automatic fallback"""
        # First try with current active URL
        url = f"{self.active_url}{path}"

        try:
            response = await self.client.request(method, url, **kwargs)

            # If we get a 404 and we're not on fallback, try fallback
            if response.status_code == 404 and not self.using_fallback:
                logger.info("Primary returned 404, trying fallback", path=path)
                await self._determine_active_upstream()
                if self.using_fallback:
                    url = f"{self.active_url}{path}"
                    response = await self.client.request(method, url, **kwargs)

            return response
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            # Try fallback on connection issues
            if not self.using_fallback:
                logger.warning("Primary failed, trying fallback", error=str(e))
                await self._determine_active_upstream()
                if self.using_fallback:
                    try:
                        url = f"{self.active_url}{path}"
                        return await self.client.request(method, url, **kwargs)
                    except Exception:
                        pass

            if isinstance(e, httpx.TimeoutException):
                raise HTTPException(status_code=504, detail="MLX server timeout")
            else:
                raise HTTPException(status_code=503, detail="MLX server unavailable")
        except Exception as e:
            logger.error("Proxy request failed", url=url, error=str(e))
            raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")

# Request/Response models
class InferenceRequest(BaseModel):
    prompt: str = Field(..., description="Input prompt for generation")
    image: Optional[str] = Field(None, description="Image path or URL for vision models")
    max_tokens: int = Field(256, ge=1, le=4096, description="Maximum tokens to generate")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    stream: bool = Field(False, description="Enable streaming response")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status")
    mlx_server_reachable: bool = Field(..., description="Whether MLX server is reachable")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    upstream: str = Field(..., description="Which upstream is being used (primary/fallback)")
    upstream_url: str = Field(..., description="URL of the active upstream")

# Global proxy manager
proxy_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    global proxy_manager, proxy_requests, proxy_duration, active_requests, mlx_server_status

    # Startup
    start_time = time.time()
    app.state.start_time = start_time

    # Initialize metrics
    proxy_requests = Counter("mlx_proxy_requests_total", "Total proxy requests", ["endpoint", "status"])
    proxy_duration = Histogram("mlx_proxy_duration_seconds", "Proxy request duration", ["endpoint"])
    active_requests = Gauge("mlx_proxy_active_requests", "Currently active proxy requests")
    mlx_server_status = Gauge("mlx_server_reachable", "MLX server reachability")

    logger.info("Starting MLX Proxy Service",
                mlx_host=MLX_HOST,
                mlx_port=MLX_PORT,
                host=HOST,
                port=PORT)

    # Initialize proxy manager
    proxy_manager = ProxyManager()
    await proxy_manager.initialize()

    # Check initial connectivity
    is_reachable = await proxy_manager.check_health()
    if is_reachable:
        logger.info("MLX server is reachable")
    else:
        logger.warning("MLX server is not reachable at startup")

    logger.info("MLX Proxy Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down MLX Proxy Service")
    if proxy_manager:
        await proxy_manager.close()

# Create FastAPI app
app = FastAPI(
    title="FREEDOM MLX Proxy Service",
    description="Proxy service to local MLX server",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    uptime = time.time() - app.state.start_time
    mlx_reachable = await proxy_manager.check_health()

    return HealthResponse(
        status="healthy" if mlx_reachable else "degraded",
        mlx_server_reachable=mlx_reachable,
        uptime_seconds=uptime,
        upstream="fallback" if proxy_manager.using_fallback else "primary",
        upstream_url=proxy_manager.active_url
    )

@app.post("/inference")
async def inference_endpoint(request: InferenceRequest):
    """Proxy inference requests to MLX server"""
    request_id = str(uuid.uuid4())
    start_time = time.time()

    logger.info("Proxying inference request",
                request_id=request_id,
                prompt_length=len(request.prompt),
                max_tokens=request.max_tokens)

    if active_requests:
        active_requests.inc()

    try:
        # Different endpoints and formats for primary vs fallback
        if proxy_manager.using_fallback:
            # LM Studio uses OpenAI-compatible format
            data = {
                "messages": [{"role": "user", "content": request.prompt}],
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "model": "ui-tars"  # Use UI-TARS model in LM Studio
            }
            path = "/v1/chat/completions"
        else:
            # Primary MLX server format
            data = {
                "prompt": request.prompt,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature
            }
            if request.image:
                data["image"] = request.image
            path = "/generate"

        response = await proxy_manager.proxy_request(
            method="POST",
            path=path,
            json=data
        )

        duration = time.time() - start_time
        if proxy_duration:
            proxy_duration.labels(endpoint="inference").observe(duration)
        if proxy_requests:
            proxy_requests.labels(endpoint="inference", status="success").inc()

        # Parse response based on upstream format
        result = response.json()

        # Transform LM Studio OpenAI format to MLX format if using fallback
        if proxy_manager.using_fallback and "choices" in result:
            # OpenAI-style response from LM Studio
            transformed_result = {
                "text": result["choices"][0]["message"]["content"],
                "model": result.get("model", "ui-tars"),
                "usage": {
                    "input_tokens": result.get("usage", {}).get("prompt_tokens", 0),
                    "output_tokens": result.get("usage", {}).get("completion_tokens", 0),
                    "total_tokens": result.get("usage", {}).get("total_tokens", 0),
                    "prompt_tps": 0,  # LM Studio doesn't provide this
                    "generation_tps": 0,  # LM Studio doesn't provide this
                    "peak_memory": 0  # LM Studio doesn't provide this
                }
            }
            return transformed_result

        # Return as-is for primary MLX server
        return result

    except HTTPException:
        if proxy_requests:
            proxy_requests.labels(endpoint="inference", status="error").inc()
        raise
    except Exception as e:
        if proxy_requests:
            proxy_requests.labels(endpoint="inference", status="error").inc()
        logger.error("Inference proxy failed", request_id=request_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")
    finally:
        if active_requests:
            active_requests.dec()

@app.get("/v1/models")
async def list_models():
    """Proxy models list request"""
    try:
        response = await proxy_manager.proxy_request("GET", "/v1/models")
        return response.json()
    except Exception as e:
        logger.error("Models list proxy failed", error=str(e))
        return {"models": []}

@app.get("/models")
async def list_models_alias():
    """Alias for /v1/models to support API Gateway"""
    try:
        # Always use /v1/models endpoint regardless of upstream
        response = await proxy_manager.proxy_request("GET", "/v1/models")
        return response.json()
    except Exception as e:
        logger.error("Models list proxy failed", error=str(e))
        return {"models": []}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Catch-all proxy for other endpoints
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_all(request: Request, path: str):
    """Proxy all other requests to MLX server"""
    try:
        # Get request data
        body = await request.body()

        # Proxy the request
        response = await proxy_manager.proxy_request(
            method=request.method,
            path=f"/{path}",
            content=body,
            headers=dict(request.headers),
            params=dict(request.query_params)
        )

        # Return response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Proxy request failed", path=path, error=str(e))
        raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info"
    )