"""Unit tests for MCP authentication, authorization, and tenant isolation."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.mcp.auth import (
    OIDCTokenVerifier,
    StaticBearerTokenVerifier,
    require_scope,
    validate_tenant_access,
)
from app.mcp.configuration import MCPAuthMode, MCPConfiguration
from app.mcp.context import (
    PrincipalContext,
    set_current_principal,
)
from app.mcp.errors import MCPAuthorizationError
from app.mcp.scopes import MCPScopes


async def test_static_bearer_verifier_valid_token() -> None:
    """Verify StaticBearerTokenVerifier accepts the matching static token."""
    config = MCPConfiguration(
        auth_mode=MCPAuthMode.BEARER,
        bearer_token="secret_test_token_12345",
    )
    verifier = StaticBearerTokenVerifier(config=config)

    token_info = await verifier.verify_token("secret_test_token_12345")
    assert token_info is not None
    assert token_info.token == "secret_test_token_12345"
    assert token_info.client_id == "claude-personal-connector"
    assert "company:search" in token_info.scopes


async def test_static_bearer_verifier_invalid_token() -> None:
    """Verify StaticBearerTokenVerifier rejects mismatched tokens."""
    config = MCPConfiguration(
        auth_mode=MCPAuthMode.BEARER,
        bearer_token="secret_test_token_12345",
    )
    verifier = StaticBearerTokenVerifier(config=config)

    assert await verifier.verify_token("wrong_token") is None
    assert await verifier.verify_token("") is None


async def test_static_bearer_verifier_disabled_when_empty() -> None:
    """Verify StaticBearerTokenVerifier returns None when configured without a token."""
    config = MCPConfiguration(auth_mode=MCPAuthMode.NONE, bearer_token=None)
    verifier = StaticBearerTokenVerifier(config=config)

    assert await verifier.verify_token("any_token") is None


async def test_oidc_verifier_valid_jwt() -> None:
    """Verify OIDCTokenVerifier parses and validates valid JWT claims."""
    config = MCPConfiguration(
        auth_mode=MCPAuthMode.OIDC,
        oauth_issuer_url="https://auth.example.com",
        resource_server_url="https://gtm.example.com/mcp",
    )
    verifier = OIDCTokenVerifier(config=config)

    payload = {
        "sub": "user_principal_99",
        "iss": "https://auth.example.com",
        "aud": "https://gtm.example.com/mcp",
        "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp(),
        "scope": "company:search company:research",
        "tenant_id": "tenant_abc",
        "client_id": "user_principal_99",
    }
    encoded = jwt.encode(payload, "secret-key", algorithm="HS256")

    token_info = await verifier.verify_token(encoded)

    assert token_info is not None
    assert token_info.client_id == "user_principal_99"
    assert "company:search" in token_info.scopes
    assert "company:research" in token_info.scopes


def test_require_scope_enforcement() -> None:
    """Verify require_scope allows permitted scopes and denies missing scopes."""
    principal = PrincipalContext(
        tenant_id="tenant_1",
        user_id="user_1",
        scopes={"company:search", "company:read"},
        is_authenticated=True,
        auth_mode="bearer",
    )
    set_current_principal(principal)

    try:
        # Permitted scope
        require_scope(MCPScopes.COMPANY_SEARCH)

        # Forbidden scope
        with pytest.raises(MCPAuthorizationError, match="missing required scope"):
            require_scope(MCPScopes.COMPANY_RESEARCH)
    finally:
        set_current_principal(PrincipalContext())


def test_tenant_isolation_validation() -> None:
    """Verify validate_tenant_access prevents cross-tenant data access."""
    # Context with tenant_1
    set_current_principal(
        PrincipalContext(
            tenant_id="tenant_1",
            user_id="user_1",
            scopes={"company:read"},
            is_authenticated=True,
            auth_mode="bearer",
        )
    )

    try:
        # Same tenant passes
        validate_tenant_access({"tenant_id": "tenant_1"}, "res_123")

        # Mismatched tenant fails
        with pytest.raises(MCPAuthorizationError, match="tenant mismatch"):
            validate_tenant_access({"tenant_id": "tenant_OTHER"}, "res_123")
    finally:
        set_current_principal(PrincipalContext())
