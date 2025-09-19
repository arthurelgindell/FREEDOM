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

# Configuration - connect to host MLX server
MLX_HOST = os.getenv("MLX_HOST", "host.docker.internal")
MLX_PORT = int(os.getenv("MLX_PORT", "8000"))
MLX_BASE_URL = f"http://{MLX_HOST}:{MLX_PORT}"
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
    """Manages connections to local MLX server"""

    def __init__(self):
        self.base_url = MLX_BASE_URL
        self.client = None

    async def initialize(self):
        """Initialize HTTP client"""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
        )
        logger.info("Proxy client initialized", base_url=self.base_url)

    async def close(self):
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()
            logger.info("Proxy client closed")

    async def check_health(self) -> bool:
        """Check if MLX server is reachable"""
        try:
            response = await self.client.get(f"{self.base_url}/health", timeout=5.0)
            is_healthy = response.status_code == 200
            if mlx_server_status:
                mlx_server_status.set(1 if is_healthy else 0)
            return is_healthy
        except Exception as e:
            logger.warning("MLX server health check failed", error=str(e))
            if mlx_server_status:
                mlx_server_status.set(0)
            return False

    async def proxy_request(self, method: str, path: str, **kwargs):
        """Proxy request to MLX server"""
        url = f"{self.base_url}{path}"

        try:
            response = await self.client.request(method, url, **kwargs)
            return response
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="MLX server timeout")
        except httpx.ConnectError:
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
        uptime_seconds=uptime
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
        # Prepare request data for MLX VLM server
        data = {
            "prompt": request.prompt,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature
        }

        if request.image:
            data["image"] = request.image

        # Make request to MLX server
        response = await proxy_manager.proxy_request(
            method="POST",
            path="/v1/chat/completions" if not request.stream else "/v1/chat/completions",
            json=data
        )

        duration = time.time() - start_time
        if proxy_duration:
            proxy_duration.labels(endpoint="inference").observe(duration)
        if proxy_requests:
            proxy_requests.labels(endpoint="inference", status="success").inc()

        # Return response from MLX server
        return response.json()

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