"""Tenant isolation guardrails and ownership validation."""

from typing import Any

from app.core.logging import get_logger
from app.mcp.context import get_current_principal
from app.mcp.errors import MCPAuthorizationError

logger = get_logger("mcp.auth.tenant_context")


def validate_tenant_access(resource_metadata: dict[str, Any] | None, resource_id: str) -> None:
    """Ensure that the requested resource belongs to the current principal's tenant.

    Raises:
        MCPAuthorizationError: If cross-tenant access is attempted.
    """
    principal = get_current_principal()

    # If unauthenticated local dev, all local resources are accessible
    if not principal.is_authenticated and principal.auth_mode == "none":
        return

    if not resource_metadata:
        return

    resource_tenant = resource_metadata.get("tenant_id")
    # If resource has a tagged tenant and it mismatches the caller's tenant
    if resource_tenant and resource_tenant != principal.tenant_id:
        logger.warning(
            "Cross-tenant access violation: principal tenant '%s' attempted to access resource '%s' owned by tenant '%s'",
            principal.tenant_id,
            resource_id,
            resource_tenant,
        )
        raise MCPAuthorizationError(
            f"Access denied to resource '{resource_id}': tenant mismatch",
            details={"resource_id": resource_id, "caller_tenant": principal.tenant_id},
        )
