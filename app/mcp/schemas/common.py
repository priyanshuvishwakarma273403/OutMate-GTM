"""Common schemas and envelope primitives for MCP tool interactions."""

from typing import Any

from pydantic import BaseModel, Field


class MCPToolResult(BaseModel):
    """Standardized tool response envelope containing human-readable text and structured data."""

    success: bool = Field(default=True, description="Indicates whether tool execution succeeded")
    message: str = Field(
        default="Tool executed successfully",
        description="Concise human-readable summary of the outcome",
    )
    data: dict[str, Any] = Field(default_factory=dict, description="Structured result payload")
    error: str | None = Field(default=None, description="Error category or message if unsuccessful")

    @property
    def is_error(self) -> bool:
        """Convenience property matching MCP SDK CallToolResult.is_error semantics."""
        return not self.success or self.error is not None

    def __getitem__(self, item: str) -> Any:
        if item in ("success", "message", "data", "error"):
            return getattr(self, item)
        return self.data[item]
