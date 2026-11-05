"""Model Context Protocol (MCP) configuration models and settings loader."""

import hashlib
from typing import Literal

from pydantic import BaseModel, Field


class MCPConfiguration(BaseModel):
    """Runtime configuration for Outmate MCP Server and Client."""

    server_name: str = Field(default="outmate-gtm-server", description="Declared MCP server identifier")
    server_version: str = Field(default="0.1.0", description="Declared MCP server version")
    transport: Literal["stdio", "streamable_http", "sse"] = Field(
        default="streamable_http", description="Primary server transport"
    )
    host: str = Field(default="127.0.0.1", description="Binding host for remote HTTP transport")
    port: int = Field(default=8001, description="Binding port for remote HTTP transport")
    endpoint: str = Field(default="/mcp", description="Base HTTP endpoint for Streamable HTTP transport")
    auth_mode: Literal["none", "bearer", "oidc"] = Field(
        default="none", description="Authentication mode: none, bearer (token), or oidc (JWT/JWKS)"
    )
    bearer_token: str | None = Field(default=None, description="Static token for personal connector testing")
    bearer_token_hash: str | None = Field(
        default=None, description="SHA256 hash of expected bearer token for secure comparison"
    )
    oauth_issuer_url: str | None = Field(default=None, description="OIDC/OAuth 2.1 authorization server issuer")
    resource_server_url: str | None = Field(
        default=None, description="Declared RFC 8707 resource indicator (e.g., https://api.outmate.ai/mcp)"
    )
    required_scopes: list[str] = Field(
        default_factory=lambda: [
            "company:search",
            "company:research",
            "company:read",
            "people:discover",
            "people:verify",
            "people:read",
            "research:sources:read",
        ],
        description="Global scopes permitted on this resource server",
    )
    request_timeout: float = Field(default=60.0, description="Maximum HTTP request timeout in seconds")
    tool_timeout: float = Field(default=45.0, description="Maximum execution timeout for individual tools in seconds")
    max_concurrent_requests: int = Field(default=30, description="Max concurrent request workers")
    client_timeout: float = Field(default=60.0, description="Default client operation timeout")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Log level for MCP server"
    )

    def get_token_hash(self) -> str | None:
        """Return the configured SHA-256 hash or calculate it from bearer_token."""
        if self.bearer_token_hash:
            return self.bearer_token_hash
        if self.bearer_token:
            return hashlib.sha256(self.bearer_token.encode("utf-8")).hexdigest()
        return None
