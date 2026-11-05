"""Common schemas and envelope primitives for MCP tool interactions."""

from typing import Any

from pydantic import BaseModel, Field


class MCPToolResult(BaseModel):
    """Standardized tool response envelope containing human-readable text and structured data."""

    success: bool = Field(default=True, description="Indicates whether tool execution succeeded")
    message: str = Field(..., description="Concise human-readable summary of the outcome")
    data: dict[str, Any] = Field(default_factory=dict, description="Structured result payload")
    error: str | None = Field(default=None, description="Error category or message if unsuccessful")
