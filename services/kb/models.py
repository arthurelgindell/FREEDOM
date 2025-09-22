"""
FREEDOM Knowledge Base Data Models
Pydantic models for API requests and responses
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID


class IngestRequest(BaseModel):
    """Request model for ingesting specifications"""
    technology_name: str = Field(..., description="Technology name (e.g., 'kubernetes')")
    version: str = Field(..., description="Technology version")
    component_type: str = Field(..., description="Type of component (e.g., 'api', 'config')")
    component_name: str = Field(..., description="Specific component name")
    specification: Dict[str, Any] = Field(..., description="Technical specification data")
    source_url: str = Field(..., description="Source URL of the specification")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score (0-1)")

    @validator('technology_name', 'component_type', 'component_name')
    def validate_names(cls, v):
        if not v or not v.strip():
            raise ValueError("Name fields cannot be empty")
        return v.strip().lower()

    @validator('source_url')
    def validate_url(cls, v):
        if not v or not v.startswith(('http://', 'https://')):
            raise ValueError("source_url must be a valid HTTP/HTTPS URL")
        return v


class QueryRequest(BaseModel):
    """Request model for querying the knowledge base"""
    query: str = Field(..., description="Natural language query")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity score")
    technology_filter: Optional[str] = Field(default=None, description="Filter by technology name")

    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


class SpecificationResult(BaseModel):
    """Result model for specification data"""
    id: str
    technology_name: str
    version: str
    component_type: str
    component_name: str
    specification: Dict[str, Any]
    source_url: str
    confidence_score: float
    similarity_score: Optional[float] = None
    extracted_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class IngestResponse(BaseModel):
    """Response model for ingest operations"""
    success: bool
    specification_id: Optional[str] = None
    message: str
    processing_time_ms: float


class QueryResponse(BaseModel):
    """Response model for query operations"""
    query: str
    results: List[SpecificationResult]
    total_results: int
    processing_time_ms: float
    similarity_threshold_used: float


class HealthCheckResponse(BaseModel):
    """Response model for health checks"""
    status: str
    database_status: str  # Changed from database_connected to match test expectations
    database_connected: bool  # Keep for backwards compatibility
    pgvector_available: bool
    total_specifications: int
    recent_specifications: int
    timestamp: str
    uptime_seconds: Optional[float] = None


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    timestamp: str