"""Unit tests for MCP authentication, authorization, and tenant isolation."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import jwt
import pytest

from app.domain.models.metadata import TenantContext
from app.mcp.auth import (
    AccessToken,
    MCPScopes,
    OIDCTokenVerifier,
    PrincipalContext,
    StaticBearerTokenVerifier,
    get_current_principal,
    require_scope,
    set_current_principal,
    validate_tenant_access,
)
from app.mcp.configuration import MCPAuthMode, MCPConfiguration
from app.mcp.errors import MCPAuthenticationError, MCPAuthorizationError


def test_static_bearer_verifier_valid_token() -> None:
    """Verify StaticBearerTokenVerifier accepts the matching static token."""
    config = MCPConfiguration(
        auth_mode=MCPAuthMode.BEARER_STATIC,
        static_token="secret_test_token_12345",
    )
    verifier = StaticBearerTokenVerifier(config=config)

    token_info = verifier.verify_token("secret_test_token_12345")
    assert token_info is not None
    assert token_info.token == "secret_test_token_12345"
    assert token_info.client_id == "claude-client"
    assert "company:search" in token_info.scopes


def test_static_bearer_verifier_invalid_token() -> None:
    """Verify StaticBearerTokenVerifier rejects mismatched tokens."""
    config = MCPConfiguration(
        auth_mode=MCPAuthMode.BEARER_STATIC,
        static_token="secret_test_token_12345",
    )
    verifier = StaticBearerTokenVerifier(config=config)

    assert verifier.verify_token("wrong_token") is None
    assert verifier.verify_token("") is None


def test_static_bearer_verifier_disabled_when_empty() -> None:
    """Verify StaticBearerTokenVerifier returns None when configured without a token."""
    config = MCPConfiguration(auth_mode=MCPAuthMode.NONE, static_token=None)
    verifier = StaticBearerTokenVerifier(config=config)

    assert verifier.verify_token("any_token") is None


def test_oidc_verifier_valid_jwt() -> None:
    """Verify OIDCTokenVerifier parses and validates valid JWT claims."""
    config = MCPConfiguration(
        auth_mode=MCPAuthMode.OIDC_OAUTH2,
        oidc_issuer="https://auth.example.com",
        oidc_audience="https://gtm.example.com/mcp",
    )
    verifier = OIDCTokenVerifier(config=config)

    payload = {
        "sub": "user_principal_99",
        "iss": "https://auth.example.com",
        "aud": "https://gtm.example.com/mcp",
        "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp(),
        "scope": "company:search company:research",
        "tenant_id": "tenant_abc",
    }
    encoded = jwt.encode(payload, "secret-key", algorithm="HS256")

    with patch.object(verifier, "_get_signing_key", return_value="secret-key"):
        token_info = verifier.verify_token(encoded)

    assert token_info is not None
    assert token_info.client_id == "user_principal_99"
    assert "company:search" in token_info.scopes
    assert "company:research" in token_info.scopes


def test_require_scope_enforcement() -> None:
    """Verify require_scope allows permitted scopes and denies missing scopes."""
    principal = PrincipalContext(
        principal_id="user_1",
        scopes={"company:search", "company:read"},
        tenant_context=TenantContext(tenant_id="tenant_1"),
    )
    set_current_principal(principal)

    # Permitted scope
    require_scope(MCPScopes.COMPANY_SEARCH)

    # Forbidden scope
    with pytest.raises(MCPAuthorizationError, match="Missing required scope"):
        require_scope(MCPScopes.COMPANY_RESEARCH)

    # Cleanup
    set_current_principal(None)


def test_tenant_isolation_validation() -> None:
    """Verify validate_tenant_access prevents cross-tenant data access."""
    # Context with tenant_1
    set_current_principal(
        PrincipalContext(
            principal_id="user_1",
            scopes={"company:read"},
            tenant_context=TenantContext(tenant_id="tenant_1"),
        )
    )

    # Same tenant passes
    validate_tenant_access({"tenant_id": "tenant_1"}, "res_123")

    # Mismatched tenant fails
    with pytest.raises(MCPAuthorizationError, match="Cross-tenant access denied"):
        validate_tenant_access({"tenant_id": "tenant_OTHER"}, "res_123")

    # Cleanup
    set_current_principal(None)
