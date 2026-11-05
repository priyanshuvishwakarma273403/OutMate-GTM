"""Exception hierarchy for Outmate MCP client operations."""

from typing import Any

from app.core.exceptions import OutmateError


class MCPClientError(OutmateError):
    """Base exception for all MCP client errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details)


class MCPConnectionError(MCPClientError):
    """Raised when the client cannot establish a connection to the MCP server."""


class MCPTransportError(MCPClientError):
    """Raised when an active transport fails or disconnects unexpectedly."""


class MCPToolExecutionError(MCPClientError):
    """Raised when an MCP tool invocation returns an error from the server."""

    def __init__(self, tool_name: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(f"Tool '{tool_name}' execution error: {message}", details)
        self.tool_name = tool_name
