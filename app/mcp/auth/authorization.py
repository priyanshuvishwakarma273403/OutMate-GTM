"""Authorization enforcement and scope check utilities for MCP tool executions."""

from app.core.logging import get_logger
from app.mcp.context import get_current_principal
from app.mcp.errors import MCPAuthorizationError

logger = get_logger("mcp.auth.authorization")


def require_scope(required_scope: str) -> None:
    """Validate that the active principal possesses the required permission scope.

    Raises:
        MCPAuthorizationError: If the caller is not authorized for the requested scope.
    """
    principal = get_current_principal()

    if not principal.has_scope(required_scope):
        logger.warning(
            "Access denied: principal '%s' (tenant: '%s') lacks required scope '%s'",
            principal.user_id,
            principal.tenant_id,
            required_scope,
        )
        raise MCPAuthorizationError(
            f"Permission denied: missing required scope '{required_scope}'",
            details={
                "required_scope": required_scope,
                "principal_id": principal.user_id,
                "tenant_id": principal.tenant_id,
            },
        )
