"""API response schemas for health, readiness, and service outputs."""

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.llm.base import TokenUsage

T = TypeVar("T")


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(UTC)


class HealthResponse(BaseModel):
    """Liveness probe response model."""

    status: str = Field(default="ok", description="Overall application health status")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Runtime environment")
    timestamp: datetime = Field(default_factory=utc_now, description="Time of health verification")


class DependencyHealth(BaseModel):
    """Health status descriptor for an individual subsystem or external dependency."""

    name: str = Field(..., description="Dependency identifier (e.g. openrouter, nango, search)")
    status: str = Field(
        ..., description="Operational status: 'healthy', 'degraded', 'not_configured', 'unhealthy'"
    )
    details: str | None = Field(default=None, description="Non-sensitive operational details")


class ReadinessResponse(BaseModel):
    """Readiness probe response model reporting dependency readiness without exposing credentials."""

    status: str = Field(..., description="Overall readiness: 'ready', 'degraded', or 'not_ready'")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(default_factory=utc_now, description="Time of readiness evaluation")
    dependencies: dict[str, DependencyHealth] = Field(
        default_factory=dict, description="Status of configured subsystems"
    )


class APIResponse(BaseModel, Generic[T]):
    """Standardized envelope for successful API responses."""

    success: bool = Field(default=True, description="Whether the operation succeeded")
    data: T = Field(..., description="Payload data")
    message: str | None = Field(default=None, description="Optional informational message")
    timestamp: datetime = Field(default_factory=utc_now, description="Timestamp of response")


class ErrorDetail(BaseModel):
    """Structured error payload for failed requests."""

    error_type: str = Field(..., description="Categorical error identifier")
    message: str = Field(..., description="Human-readable explanation of the error")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Contextual debugging information"
    )


class ErrorResponse(BaseModel):
    """Standardized envelope for error responses."""

    success: bool = Field(default=False, description="Always False on error")
    error: ErrorDetail = Field(..., description="Detailed error information")
    timestamp: datetime = Field(
        default_factory=utc_now, description="Timestamp of error occurrence"
    )


class LLMTestResponse(BaseModel):
    """Response model for LLM completion test endpoint."""

    status: str = Field(default="success", description="Status indicator of the completion request")
    model: str = Field(..., description="Model identifier that produced the completion")
    content: str = Field(..., description="Generated text content from the language model")
    usage: TokenUsage = Field(
        default_factory=TokenUsage,
        description="Token consumption metrics for the request",
    )
    duration_ms: float | None = Field(
        default=None,
        description="Round-trip request execution duration in milliseconds",
    )
    timestamp: datetime = Field(
        default_factory=utc_now, description="Timestamp of completion response"
    )
