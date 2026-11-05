"""Authentication and authorization primitives for Outmate MCP."""

from mcp.server.auth.provider import AccessToken

from app.mcp.auth.authorization import require_scope
from app.mcp.auth.tenant_context import validate_tenant_access
from app.mcp.auth.verifier import OIDCTokenVerifier, StaticBearerTokenVerifier

__all__ = [
    "AccessToken",
    "OIDCTokenVerifier",
    "StaticBearerTokenVerifier",
    "require_scope",
    "validate_tenant_access",
]
