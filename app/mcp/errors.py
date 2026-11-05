"""Domain exceptions and protocol error translators for Outmate MCP."""

from typing import Any

from app.core.exceptions import OutmateError


class MCPError(OutmateError):
    """Base exception for all MCP-specific failures."""

    def __init__(
        self,
        message: str,
        code: int = -32603,  # Standard JSON-RPC Internal Error
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.code = code


class MCPAuthenticationError(MCPError):
    """Raised when authentication credentials are missing, invalid, or expired."""

    def __init__(self, message: str = "Authentication required", details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code=-32001, details=details)


class MCPAuthorizationError(MCPError):
    """Raised when the authenticated caller lacks required permission scopes or tenant access."""

    def __init__(self, message: str = "Permission denied", details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code=-32003, details=details)


class MCPToolNotFoundError(MCPError):
    """Raised when requested tool name is not registered."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(f"Tool '{tool_name}' not found", code=-32601, details={"tool_name": tool_name})


class MCPValidationError(MCPError):
    """Raised when tool arguments fail Pydantic schema validation."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code=-32602, details=details)


class MCPResourceNotFoundError(MCPError):
    """Raised when a referenced entity or research report does not exist."""

    def __init__(self, resource_type: str, resource_id: str) -> None:
        super().__init__(
            f"{resource_type} '{resource_id}' was not found",
            code=-32004,
            details={"resource_type": resource_type, "resource_id": resource_id},
        )
