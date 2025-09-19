"""
FREEDOM API Gateway Service
Production-ready FastAPI gateway with security, monitoring, and KB integration
"""

import os
import time
import uuid
import asyncio
import structlog
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List

import httpx
from fastapi import FastAPI, HTTPException, status, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

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

# Configuration from environment
API_KEY = os.getenv("FREEDOM_API_KEY", "dev-key-change-in-production")
KB_SERVICE_URL = os.getenv("KB_SERVICE_URL", "http://kb-service:8000")
MLX_SERVICE_URL = os.getenv("MLX_SERVICE_URL", "http://mlx-server:8000")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://castle-gui:3000").split(",")
RATE_LIMIT = os.getenv("RATE_LIMIT", "100/minute")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Prometheus metrics
REQUEST_COUNT = Counter(
    'gateway_requests_total',
    'Total number of requests processed',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'gateway_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

KB_REQUESTS = Counter(
    'gateway_kb_requests_total',
    'Total KB service requests',
    ['operation', 'status']
)

KB_CACHE_HITS = Counter(
    'gateway_kb_cache_hits_total',
    'KB cache hits vs misses',
    ['type']
)

MLX_REQUESTS = Counter(
    'gateway_mlx_requests_total',
    'Total MLX inference requests',
    ['operation', 'status']
)

MLX_INFERENCE_DURATION = Histogram(
    'gateway_mlx_inference_duration_seconds',
    'MLX inference duration in seconds',
    ['model']
)

ACTIVE_CONNECTIONS = Gauge(
    'gateway_active_connections',
    'Number of active connections'
)

# Service startup time
service_start_time = time.time()

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

# API Key security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# HTTP client for KB service communication
http_client: Optional[httpx.AsyncClient] = None


class CorrelationIdMiddleware:
    """Middleware to add correlation IDs to all requests"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Generate correlation ID
            correlation_id = str(uuid.uuid4())
            scope["correlation_id"] = correlation_id

            # Add to headers for downstream services
            headers = dict(scope.get("headers", []))
            headers[b"x-correlation-id"] = correlation_id.encode()
            scope["headers"] = list(headers.items())

        await self.app(scope, receive, send)


class LoggingMiddleware:
    """Middleware for structured request/response logging"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        correlation_id = scope.get("correlation_id", "unknown")
        request_logger = logger.bind(correlation_id=correlation_id)

        # Log request
        request_logger.info(
            "Request started",
            method=scope.get("method"),
            path=scope.get("path"),
            client=scope.get("client")
        )

        # Track response
        response_data = {}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                response_data["status_code"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            request_logger.error(
                "Request failed",
                error=str(e),
                processing_time_ms=(time.time() - start_time) * 1000
            )
            raise
        finally:
            # Log response
            processing_time = (time.time() - start_time) * 1000
            request_logger.info(
                "Request completed",
                status_code=response_data.get("status_code"),
                processing_time_ms=processing_time
            )


class PrometheusMiddleware:
    """Middleware for Prometheus metrics collection"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/unknown")

        # Normalize path for metrics (remove dynamic parts)
        endpoint = self._normalize_path(path)

        ACTIVE_CONNECTIONS.inc()

        response_data = {}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                response_data["status_code"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            ACTIVE_CONNECTIONS.dec()

            # Record metrics
            status = response_data.get("status_code", 500)
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()

            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(time.time() - start_time)

    def _normalize_path(self, path: str) -> str:
        """Normalize path for consistent metrics"""
        if path.startswith("/kb/"):
            return "/kb/*"
        elif path == "/health":
            return "/health"
        elif path == "/metrics":
            return "/metrics"
        else:
            return "/other"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global http_client

    logger.info("Starting FREEDOM API Gateway", version="1.0.0")

    # Initialize HTTP client for KB service
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
    )

    # Test KB service connectivity
    try:
        response = await http_client.get(f"{KB_SERVICE_URL}/health")
        if response.status_code == 200:
            logger.info("KB service connectivity verified")
        else:
            logger.warning("KB service health check failed", status=response.status_code)
    except Exception as e:
        logger.error("Failed to connect to KB service", error=str(e))

    yield

    # Cleanup
    if http_client:
        await http_client.aclose()
    logger.info("FREEDOM API Gateway shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="FREEDOM API Gateway",
    description="Production-ready API Gateway for FREEDOM Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware stack (order matters!)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Trusted host middleware for security
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure based on deployment
)


# Pydantic models
class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: str
    uptime_seconds: float
    version: str
    kb_service_status: str
    kb_service_response_time_ms: Optional[float] = None
    mlx_service_status: str
    mlx_service_response_time_ms: Optional[float] = None


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    timestamp: str
    correlation_id: Optional[str] = None


class QueryRequest(BaseModel):
    """Query request model"""
    query: str = Field(..., description="Natural language query")
    limit: int = Field(default=10, ge=1, le=50)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    technology_filter: Optional[str] = None


class IngestRequest(BaseModel):
    """Ingest request model"""
    technology_name: str
    version: str
    component_type: str
    component_name: str
    specification: Dict[str, Any]
    source_url: str
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)


class InferenceRequest(BaseModel):
    """MLX inference request model"""
    prompt: str = Field(..., description="Input prompt for generation")
    model: Optional[str] = Field(None, description="Model path override")
    adapter_path: Optional[str] = Field(None, description="Adapter path for fine-tuned models")
    image_urls: Optional[List[str]] = Field(None, description="Image URLs for vision models")
    max_tokens: int = Field(256, ge=1, le=4096, description="Maximum tokens to generate")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    stream: bool = Field(False, description="Enable streaming response")


class InferenceResponse(BaseModel):
    """MLX inference response model"""
    id: str = Field(..., description="Request ID")
    model: str = Field(..., description="Model used for generation")
    content: str = Field(..., description="Generated content")
    usage: Dict[str, int] = Field(..., description="Token usage statistics")
    created: int = Field(..., description="Unix timestamp")
    correlation_id: Optional[str] = None


# Security dependency
async def verify_api_key(api_key: Optional[str] = Depends(api_key_header)):
    """Verify API key authentication"""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Include X-API-Key header."
        )

    if api_key != API_KEY:
        logger.warning("Invalid API key attempt", provided_key=api_key[:8] + "...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return api_key


# Helper function to get correlation ID
def get_correlation_id(request: Request) -> str:
    """Extract correlation ID from request"""
    return getattr(request.scope, "correlation_id", "unknown")


# Routes
@app.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """
    Comprehensive health check endpoint
    Tests API Gateway and downstream KB service health
    """
    correlation_id = get_correlation_id(request)
    start_time = time.time()

    logger.info("Health check requested", correlation_id=correlation_id)

    # Check KB service health
    kb_status = "unknown"
    kb_response_time = None

    try:
        kb_start = time.time()
        response = await http_client.get(
            f"{KB_SERVICE_URL}/health",
            headers={"x-correlation-id": correlation_id}
        )
        kb_response_time = (time.time() - kb_start) * 1000

        if response.status_code == 200:
            kb_status = "healthy"
            KB_REQUESTS.labels(operation="health", status="success").inc()
        else:
            kb_status = "unhealthy"
            KB_REQUESTS.labels(operation="health", status="error").inc()
    except Exception as e:
        logger.error("KB service health check failed", error=str(e), correlation_id=correlation_id)
        kb_status = "unreachable"
        KB_REQUESTS.labels(operation="health", status="error").inc()

    # Check MLX service health
    mlx_status = "unknown"
    mlx_response_time = None

    try:
        mlx_start = time.time()
        response = await http_client.get(
            f"{MLX_SERVICE_URL}/health",
            headers={"x-correlation-id": correlation_id}
        )
        mlx_response_time = (time.time() - mlx_start) * 1000

        if response.status_code == 200:
            mlx_status = "healthy"
            MLX_REQUESTS.labels(operation="health", status="success").inc()
        else:
            mlx_status = "unhealthy"
            MLX_REQUESTS.labels(operation="health", status="error").inc()
    except Exception as e:
        logger.error("MLX service health check failed", error=str(e), correlation_id=correlation_id)
        mlx_status = "unreachable"
        MLX_REQUESTS.labels(operation="health", status="error").inc()

    uptime = time.time() - service_start_time

    response_data = HealthResponse(
        status="healthy" if kb_status in ["healthy", "unknown"] and mlx_status in ["healthy", "unknown"] else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=uptime,
        version="1.0.0",
        kb_service_status=kb_status,
        kb_service_response_time_ms=kb_response_time,
        mlx_service_status=mlx_status,
        mlx_service_response_time_ms=mlx_response_time
    )

    logger.info(
        "Health check completed",
        correlation_id=correlation_id,
        status=response_data.status,
        kb_status=kb_status,
        processing_time_ms=(time.time() - start_time) * 1000
    )

    return response_data


@app.post("/kb/query")
@limiter.limit(RATE_LIMIT)
async def query_knowledge_base(
    request: Request,
    query_request: QueryRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Query the knowledge base
    Requires valid API key authentication
    """
    correlation_id = get_correlation_id(request)
    start_time = time.time()

    logger.info(
        "KB query requested",
        correlation_id=correlation_id,
        query_length=len(query_request.query),
        limit=query_request.limit
    )

    try:
        # Forward request to KB service
        response = await http_client.post(
            f"{KB_SERVICE_URL}/query",
            json=query_request.dict(),
            headers={
                "x-correlation-id": correlation_id,
                "content-type": "application/json"
            }
        )

        if response.status_code == 200:
            result = response.json()
            KB_REQUESTS.labels(operation="query", status="success").inc()

            # Track cache metrics based on results
            if result.get("total_results", 0) > 0:
                KB_CACHE_HITS.labels(type="hit").inc()
            else:
                KB_CACHE_HITS.labels(type="miss").inc()

            logger.info(
                "KB query completed",
                correlation_id=correlation_id,
                results_count=result.get("total_results", 0),
                processing_time_ms=(time.time() - start_time) * 1000
            )

            return result
        else:
            KB_REQUESTS.labels(operation="query", status="error").inc()
            logger.error(
                "KB service query failed",
                correlation_id=correlation_id,
                status_code=response.status_code,
                response=response.text
            )
            raise HTTPException(
                status_code=response.status_code,
                detail=f"KB service error: {response.text}"
            )

    except httpx.RequestError as e:
        KB_REQUESTS.labels(operation="query", status="error").inc()
        logger.error("KB service connection failed", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge base service unavailable"
        )


@app.post("/kb/ingest")
@limiter.limit("10/minute")  # More restrictive for ingest
async def ingest_specification(
    request: Request,
    ingest_request: IngestRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Ingest specification into knowledge base
    Requires valid API key authentication
    """
    correlation_id = get_correlation_id(request)
    start_time = time.time()

    logger.info(
        "KB ingest requested",
        correlation_id=correlation_id,
        technology=ingest_request.technology_name,
        component=ingest_request.component_name
    )

    try:
        # Forward request to KB service
        response = await http_client.post(
            f"{KB_SERVICE_URL}/ingest",
            json=ingest_request.dict(),
            headers={
                "x-correlation-id": correlation_id,
                "content-type": "application/json"
            }
        )

        if response.status_code == 200:
            result = response.json()
            KB_REQUESTS.labels(operation="ingest", status="success").inc()

            logger.info(
                "KB ingest completed",
                correlation_id=correlation_id,
                specification_id=result.get("specification_id"),
                processing_time_ms=(time.time() - start_time) * 1000
            )

            return result
        else:
            KB_REQUESTS.labels(operation="ingest", status="error").inc()
            logger.error(
                "KB service ingest failed",
                correlation_id=correlation_id,
                status_code=response.status_code,
                response=response.text
            )
            raise HTTPException(
                status_code=response.status_code,
                detail=f"KB service error: {response.text}"
            )

    except httpx.RequestError as e:
        KB_REQUESTS.labels(operation="ingest", status="error").inc()
        logger.error("KB service connection failed", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge base service unavailable"
        )


@app.post("/inference", response_model=InferenceResponse)
@limiter.limit(RATE_LIMIT)
async def inference_endpoint(
    request: Request,
    inference_request: InferenceRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    MLX Local Inference Endpoint
    Performs text generation using local MLX models
    Requires valid API key authentication
    """
    correlation_id = get_correlation_id(request)
    start_time = time.time()

    logger.info(
        "MLX inference requested",
        correlation_id=correlation_id,
        prompt_length=len(inference_request.prompt),
        max_tokens=inference_request.max_tokens,
        model=inference_request.model,
        stream=inference_request.stream
    )

    try:
        # Forward request to MLX service
        mlx_request_data = inference_request.dict()

        if inference_request.stream:
            # Handle streaming response
            MLX_REQUESTS.labels(operation="inference", status="streaming").inc()

            try:
                async with http_client.stream(
                    "POST",
                    f"{MLX_SERVICE_URL}/inference",
                    json=mlx_request_data,
                    headers={"x-correlation-id": correlation_id},
                    timeout=300.0  # Extended timeout for inference
                ) as response:
                    if response.status_code != 200:
                        MLX_REQUESTS.labels(operation="inference", status="error").inc()
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"MLX service error: {response.text}"
                        )

                    # Stream the response back to client
                    async def stream_generator():
                        async for chunk in response.aiter_text():
                            yield chunk

                    return StreamingResponse(
                        stream_generator(),
                        media_type="text/event-stream",
                        headers={"X-Correlation-ID": correlation_id}
                    )

            except httpx.RequestError as e:
                MLX_REQUESTS.labels(operation="inference", status="error").inc()
                logger.error("MLX service connection failed", error=str(e), correlation_id=correlation_id)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="MLX inference service unavailable"
                )
        else:
            # Handle non-streaming response
            response = await http_client.post(
                f"{MLX_SERVICE_URL}/inference",
                json=mlx_request_data,
                headers={"x-correlation-id": correlation_id},
                timeout=300.0  # Extended timeout for inference
            )

            duration = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                result["correlation_id"] = correlation_id

                # Record metrics
                model_name = result.get("model", "unknown")
                MLX_INFERENCE_DURATION.labels(model=model_name).observe(duration)
                MLX_REQUESTS.labels(operation="inference", status="success").inc()

                logger.info(
                    "MLX inference completed",
                    correlation_id=correlation_id,
                    model=model_name,
                    tokens_generated=result.get("usage", {}).get("completion_tokens", 0),
                    processing_time_ms=duration * 1000
                )

                return InferenceResponse(**result)
            else:
                MLX_REQUESTS.labels(operation="inference", status="error").inc()
                logger.error(
                    "MLX service inference failed",
                    correlation_id=correlation_id,
                    status_code=response.status_code,
                    response=response.text
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"MLX service error: {response.text}"
                )

    except httpx.RequestError as e:
        MLX_REQUESTS.labels(operation="inference", status="error").inc()
        logger.error("MLX service connection failed", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MLX inference service unavailable"
        )
    except Exception as e:
        MLX_REQUESTS.labels(operation="inference", status="error").inc()
        logger.error("MLX inference failed", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference failed: {str(e)}"
        )


@app.post("/inference/models")
@limiter.limit(RATE_LIMIT)
async def list_models_endpoint(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """
    List available MLX models
    """
    correlation_id = get_correlation_id(request)

    try:
        response = await http_client.get(
            f"{MLX_SERVICE_URL}/models",
            headers={"x-correlation-id": correlation_id}
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"MLX service error: {response.text}"
            )

    except httpx.RequestError as e:
        logger.error("MLX service connection failed", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MLX inference service unavailable"
        )


@app.post("/inference/load_model")
@limiter.limit("10/minute")  # More restrictive rate limit for model operations
async def load_model_endpoint(
    request: Request,
    model_path: str,
    adapter_path: Optional[str] = None,
    api_key: str = Depends(verify_api_key)
):
    """
    Load a specific MLX model
    """
    correlation_id = get_correlation_id(request)

    logger.info(
        "Model load requested",
        correlation_id=correlation_id,
        model_path=model_path,
        adapter_path=adapter_path
    )

    try:
        load_data = {"model_path": model_path}
        if adapter_path:
            load_data["adapter_path"] = adapter_path

        response = await http_client.post(
            f"{MLX_SERVICE_URL}/load_model",
            params=load_data,
            headers={"x-correlation-id": correlation_id},
            timeout=300.0  # Extended timeout for model loading
        )

        if response.status_code == 200:
            result = response.json()
            logger.info("Model loaded successfully", correlation_id=correlation_id, model_path=model_path)
            return result
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"MLX service error: {response.text}"
            )

    except httpx.RequestError as e:
        logger.error("MLX service connection failed", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MLX inference service unavailable"
        )


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint
    Returns metrics in Prometheus format
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    correlation_id = get_correlation_id(request)

    logger.error(
        "Unhandled exception",
        error=str(exc),
        correlation_id=correlation_id,
        path=request.url.path,
        method=request.method
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail="An unexpected error occurred",
            timestamp=datetime.utcnow().isoformat(),
            correlation_id=correlation_id
        ).dict()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        log_level=LOG_LEVEL.lower(),
        access_log=True
    )