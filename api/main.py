"""
FREEDOM FastAPI Application
Main application entry point with production-ready configuration
"""

import sys
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from api.core.config import get_settings
from api.core.dependencies import cleanup_resources
from api.routers import council, health, websocket, freedom, castle, knowledge, unified_knowledge, simple_query
from api.middleware.logging import RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    print("🚀 FREEDOM API starting up...")
    yield
    # Shutdown
    print("🛑 FREEDOM API shutting down...")
    await cleanup_resources()


# Initialize FastAPI app
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="""
    FREEDOM AI Council API - High-performance REST and WebSocket interface
    for collaborative AI agent orchestration.

    Features:
    - Multi-agent AI Council queries
    - Real-time WebSocket streaming
    - Session management and history
    - Individual agent direct access
    - Production-ready monitoring and security
    """,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Security Middleware
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure appropriately in production
    )

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Request Logging
app.add_middleware(RequestLoggingMiddleware)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with structured error responses"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
            "path": str(request.url.path),
            "method": request.method
        }
    )

# Health check endpoint
@app.get("/health", tags=["Health"])
async def root_health():
    """Root health check"""
    return {"status": "healthy", "service": "FREEDOM AI Council API"}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to FREEDOM Platform API",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health"
    }

# Include routers
app.include_router(health.router, prefix=settings.api_v1_prefix, tags=["Health"])
app.include_router(council.router, prefix=settings.api_v1_prefix, tags=["AI Council"])
app.include_router(freedom.router, prefix=settings.api_v1_prefix, tags=["FREEDOM Orchestration"])
app.include_router(castle.router, prefix=settings.api_v1_prefix, tags=["Castle Command Center"])
app.include_router(knowledge.router, prefix=settings.api_v1_prefix, tags=["Knowledge System"])
app.include_router(unified_knowledge.router, prefix=settings.api_v1_prefix, tags=["Unified Knowledge"])
app.include_router(simple_query.router, prefix=settings.api_v1_prefix, tags=["Simple Query"])
app.include_router(websocket.router, prefix=settings.api_v1_prefix, tags=["WebSocket"])

# Development server runner
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
        access_log=True
    )