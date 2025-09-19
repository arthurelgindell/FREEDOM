"""
FREEDOM API Request Models
Pydantic models for API request validation and serialization
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum


class CouncilQueryRequest(BaseModel):
    """Request model for AI Council queries"""

    query: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The query to submit to the AI Council",
        example="How should I implement authentication in my FastAPI application?"
    )

    conversation_id: Optional[str] = Field(
        None,
        description="Optional conversation ID to continue an existing session"
    )

    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional context for the query"
    )

    streaming: bool = Field(
        default=False,
        description="Whether to stream responses in real-time"
    )

    include_metadata: bool = Field(
        default=True,
        description="Include agent metadata in responses"
    )

    @validator('query')
    def query_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()


class DirectAgentRequest(BaseModel):
    """Request model for direct agent queries"""

    query: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The query to submit to a specific agent"
    )

    agent_name: str = Field(
        ...,
        pattern=r"^(qwen|claude|gpt4|gemini)$",
        description="Target agent name"
    )

    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional context for the query"
    )

    temperature: Optional[float] = Field(
        None,
        ge=0.0,
        le=2.0,
        description="Override temperature for this request"
    )


class BatchQueryRequest(BaseModel):
    """Request model for batch query processing"""

    queries: List[str] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="List of queries to process"
    )

    batch_id: Optional[str] = Field(
        None,
        description="Optional batch identifier"
    )

    parallel_execution: bool = Field(
        default=True,
        description="Execute queries in parallel"
    )

    webhook_url: Optional[str] = Field(
        None,
        description="URL to notify when batch is complete"
    )


class AgentConfigUpdate(BaseModel):
    """Request model for updating agent configuration"""

    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=8000)
    role: Optional[str] = Field(None, max_length=500)
    capabilities: Optional[List[str]] = Field(None)


class SessionFilterRequest(BaseModel):
    """Request model for filtering conversation sessions"""

    start_date: Optional[str] = Field(
        None,
        description="Start date filter (ISO format)"
    )

    end_date: Optional[str] = Field(
        None,
        description="End date filter (ISO format)"
    )

    agent_name: Optional[str] = Field(
        None,
        pattern=r"^(qwen|claude|gpt4|gemini)$",
        description="Filter by agent participation"
    )

    min_messages: Optional[int] = Field(
        None,
        ge=1,
        description="Minimum number of messages"
    )

    limit: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum number of sessions to return"
    )

    offset: int = Field(
        default=0,
        ge=0,
        description="Number of sessions to skip"
    )


class FreedomRequest(BaseModel):
    """Request model for FREEDOM orchestration"""

    objective: str = Field(
        ...,
        min_length=5,
        max_length=5000,
        description="The objective to accomplish through FREEDOM orchestration",
        example="Create a Python function that calculates Fibonacci numbers"
    )

    conversation_id: Optional[str] = Field(
        None,
        description="Optional conversation ID to continue an existing session"
    )

    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional context for the objective"
    )

    timeout: Optional[int] = Field(
        default=300,
        ge=30,
        le=1800,
        description="Maximum execution time in seconds (30s-30min)"
    )

    priority: Optional[str] = Field(
        default="normal",
        pattern=r"^(low|normal|high|urgent)$",
        description="Task priority level"
    )

    @validator('objective')
    def objective_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Objective cannot be empty')
        return v.strip()


class FreedomRunStatusRequest(BaseModel):
    """Request model for checking FREEDOM run status"""

    include_logs: bool = Field(
        default=True,
        description="Include execution logs in response"
    )

    log_limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of log entries to return"
    )


class WebSocketMessage(BaseModel):
    """WebSocket message structure"""

    class MessageType(str, Enum):
        QUERY = "query"
        SUBSCRIBE = "subscribe"
        UNSUBSCRIBE = "unsubscribe"
        PING = "ping"

    type: MessageType = Field(..., description="Message type")
    data: Dict[str, Any] = Field(default_factory=dict, description="Message payload")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")