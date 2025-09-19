"""
FREEDOM API Response Models
Pydantic models for API response serialization and validation
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    """Agent availability status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class AgentInfo(BaseModel):
    """Agent information model"""

    name: str = Field(..., description="Agent name")
    model: str = Field(..., description="Model identifier")
    status: AgentStatus = Field(..., description="Current status")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    temperature: float = Field(..., description="Current temperature setting")
    max_tokens: int = Field(..., description="Maximum token limit")
    last_active: Optional[datetime] = Field(None, description="Last activity timestamp")


class AgentResponse(BaseModel):
    """Individual agent response"""

    agent_name: str = Field(..., description="Responding agent name")
    response: str = Field(..., description="Agent's response text")
    tokens_used: Optional[int] = Field(None, description="Tokens consumed")
    processing_time: float = Field(..., description="Processing time in seconds")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Response confidence")


class CouncilResponse(BaseModel):
    """AI Council query response"""

    conversation_id: str = Field(..., description="Unique conversation identifier")
    query: str = Field(..., description="Original query")
    agent_responses: List[AgentResponse] = Field(..., description="All agent responses")
    consensus: str = Field(..., description="Council consensus")
    final_response: str = Field(..., description="Selected best response")
    total_processing_time: float = Field(..., description="Total processing time")
    participating_agents: int = Field(..., description="Number of participating agents")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class DirectAgentResponse(BaseModel):
    """Direct agent query response"""

    agent_name: str = Field(..., description="Agent name")
    query: str = Field(..., description="Original query")
    response: str = Field(..., description="Agent response")
    tokens_used: Optional[int] = Field(None, description="Tokens consumed")
    processing_time: float = Field(..., description="Processing time in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    model_info: Dict[str, Any] = Field(default_factory=dict, description="Model metadata")


class ConversationHistory(BaseModel):
    """Conversation session history"""

    conversation_id: str = Field(..., description="Unique conversation identifier")
    messages: List[Dict[str, Any]] = Field(..., description="Conversation messages")
    participants: List[str] = Field(..., description="Participating agents")
    created_at: datetime = Field(..., description="Session creation time")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    message_count: int = Field(..., description="Total message count")
    consensus_history: List[str] = Field(default_factory=list, description="Consensus decisions")


class BatchStatus(BaseModel):
    """Batch processing status"""

    class Status(str, Enum):
        PENDING = "pending"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"

    batch_id: str = Field(..., description="Batch identifier")
    status: Status = Field(..., description="Current batch status")
    total_queries: int = Field(..., description="Total number of queries")
    completed_queries: int = Field(default=0, description="Number of completed queries")
    failed_queries: int = Field(default=0, description="Number of failed queries")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Batch creation time")
    started_at: Optional[datetime] = Field(None, description="Processing start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    results: List[CouncilResponse] = Field(default_factory=list, description="Query results")
    errors: List[str] = Field(default_factory=list, description="Error messages")


class HealthStatus(BaseModel):
    """System health status"""

    status: str = Field(..., description="Overall system status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    agents: List[AgentInfo] = Field(..., description="Agent status details")
    system_metrics: Dict[str, Any] = Field(default_factory=dict, description="System metrics")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Dependency status")


class APIError(BaseModel):
    """Standard API error response"""

    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Error description")
    path: Optional[str] = Field(None, description="Request path")
    method: Optional[str] = Field(None, description="HTTP method")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")


class WebSocketResponse(BaseModel):
    """WebSocket message response"""

    class EventType(str, Enum):
        AGENT_RESPONSE = "agent_response"
        COUNCIL_RESULT = "council_result"
        STATUS_UPDATE = "status_update"
        ERROR = "error"
        HEARTBEAT = "heartbeat"

    type: EventType = Field(..., description="Event type")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event payload")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")


class FreedomResponse(BaseModel):
    """FREEDOM workflow initiation response"""

    run_id: str = Field(..., description="Unique run identifier")
    status: str = Field(..., description="Initial run status")
    conversation_id: str = Field(..., description="Conversation identifier")
    message: str = Field(..., description="Status message")
    estimated_duration: int = Field(..., description="Estimated completion time in seconds")


class FreedomRunStatus(BaseModel):
    """FREEDOM run status response"""

    run_id: str = Field(..., description="Unique run identifier")
    status: str = Field(..., description="Current status")
    conversation_id: str = Field(..., description="Conversation identifier")
    objective: str = Field(..., description="Original objective")
    progress: Dict[str, Any] = Field(..., description="Progress information")
    execution_log: List[str] = Field(..., description="Execution log entries")
    created_at: str = Field(..., description="Run creation timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    result: Optional[Dict[str, Any]] = Field(None, description="Final result if completed")


class FreedomRunResult(BaseModel):
    """FREEDOM run final result response"""

    run_id: str = Field(..., description="Unique run identifier")
    success: bool = Field(..., description="Whether the run succeeded")
    objective: str = Field(..., description="Original objective")
    final_artifacts: Dict[str, Any] = Field(..., description="Generated artifacts")
    truth_score: float = Field(..., ge=0.0, le=1.0, description="Truth verification score")
    iterations: int = Field(..., description="Number of iterations")
    execution_time: float = Field(..., description="Total execution time in seconds")
    total_cost: float = Field(..., description="Total cost in USD")
    model_used: str = Field(..., description="Primary model used")
    execution_log: List[str] = Field(..., description="Complete execution log")
    error: Optional[str] = Field(None, description="Error message if failed")


class FreedomStats(BaseModel):
    """FREEDOM orchestrator statistics"""

    total_runs: int = Field(..., description="Total runs processed")
    active_runs: int = Field(..., description="Currently active runs")
    completed_runs: int = Field(..., description="Completed runs")
    status_breakdown: Dict[str, int] = Field(..., description="Run status counts")
    available_agents: List[str] = Field(..., description="Available agent names")
    agent_health: Dict[str, str] = Field(..., description="Agent health status")
    healthy_agents: int = Field(..., description="Number of healthy agents")
    graph_compiled: bool = Field(..., description="Whether the orchestration graph is ready")


class FreedomAgentInfo(BaseModel):
    """FREEDOM agent information"""

    name: str = Field(..., description="Agent name")
    model: str = Field(..., description="Model identifier")
    status: str = Field(..., description="Agent status")
    capabilities: List[str] = Field(..., description="Agent capabilities")
    response_time: Optional[float] = Field(None, description="Last response time in seconds")
    cost_per_request: float = Field(..., description="Estimated cost per request")
    specialization: str = Field(..., description="Agent specialization description")


class SessionMetrics(BaseModel):
    """Session performance metrics"""

    conversation_id: str = Field(..., description="Session identifier")
    total_queries: int = Field(..., description="Total queries processed")
    avg_response_time: float = Field(..., description="Average response time")
    agent_utilization: Dict[str, int] = Field(..., description="Agent usage counts")
    token_consumption: Dict[str, int] = Field(..., description="Token usage by agent")
    quality_scores: Dict[str, float] = Field(default_factory=dict, description="Response quality metrics")