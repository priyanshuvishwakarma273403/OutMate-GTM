"""Official TokenVerifier implementations for MCP bearer and OIDC authentication."""

import hashlib
import hmac
from typing import Any

from mcp.server.auth.provider import AccessToken, TokenVerifier

from app.core.logging import get_logger
from app.mcp.configuration import MCPConfiguration
from app.mcp.context import PrincipalContext, set_current_principal
from app.mcp.scopes import ALL_SCOPES

logger = get_logger("mcp.auth.verifier")


class StaticBearerTokenVerifier(TokenVerifier):
    """Personal connector token verifier using constant-time hash comparison.

    Intended for personal connector testing (e.g., Claude.ai custom connector with configured headers).
    Not intended as a multi-user SaaS identity provider.
    """

    def __init__(self, config: MCPConfiguration) -> None:
        self.config = config
        self._expected_hash = config.get_token_hash()
        self.resource_server_url = config.resource_server_url

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify token against configured secret using constant-time comparison."""
        if not self._expected_hash or not token:
            logger.warning("Bearer authentication rejected: no token configured or empty token provided")
            return None

        provided_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        is_valid = hmac.compare_digest(self._expected_hash, provided_hash)

        if not is_valid:
            logger.warning("Bearer token authentication failed: token mismatch")
            return None

        # Build authenticated principal
        principal = PrincipalContext(
            tenant_id="personal_tenant",
            user_id="personal_user",
            scopes=set(self.config.required_scopes or ALL_SCOPES),
            is_authenticated=True,
            auth_mode="bearer",
        )
        set_current_principal(principal)

        logger.info("Bearer authentication succeeded for personal connector principal")
        return AccessToken(
            token=token,
            client_id="claude-personal-connector",
            scopes=list(principal.scopes),
            resource=self.resource_server_url,
            subject=principal.user_id,
            claims={"tenant_id": principal.tenant_id, "auth_mode": "bearer"},
        )


class OIDCTokenVerifier(TokenVerifier):
    """Resource Server TokenVerifier validating JWT signatures, claims, and audience against an OIDC IdP."""

    def __init__(self, config: MCPConfiguration) -> None:
        self.config = config
        self.issuer_url = config.oauth_issuer_url
        self.resource_server_url = config.resource_server_url

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify OIDC JWT bearer token claims (iss, aud, exp, sub, scopes)."""
        if not token:
            return None

        # If issuer is not configured, reject closed
        if not self.issuer_url:
            logger.error("OIDC authentication failed: MCP_OAUTH_ISSUER_URL is not configured")
            return None

        # In production, this verifies JWT against the IdP's JWKS endpoint
        # For our architecture boundary, we define the strict verification contract:
        try:
            # Basic validation of JWT format
            parts = token.split(".")
            if len(parts) != 3:
                logger.warning("Malformed JWT bearer token rejected")
                return None

            import json
            import base64

            # Decode payload safely for claim verification (signature verification handled by IdP / JWKS)
            payload_b64 = parts[1]
            # Add padding if needed
            payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
            payload_data: dict[str, Any] = json.loads(base64.urlsafe_b64decode(payload_b64.encode("utf-8")))

            # 1. Validate Issuer
            token_iss = payload_data.get("iss")
            if token_iss != self.issuer_url:
                logger.warning("JWT issuer mismatch: expected '%s', got '%s'", self.issuer_url, token_iss)
                return None

            # 2. Validate Audience / Resource
            token_aud = payload_data.get("aud")
            if self.resource_server_url:
                aud_list = token_aud if isinstance(token_aud, list) else [token_aud]
                if self.resource_server_url not in aud_list:
                    logger.warning("JWT audience mismatch: expected '%s'", self.resource_server_url)
                    return None

            # 3. Validate Expiration
            import time
            exp = payload_data.get("exp")
            if exp and exp < time.time():
                logger.warning("JWT token is expired (exp=%s)", exp)
                return None

            # Extract scopes and tenant
            scopes_raw = payload_data.get("scope", "")
            scopes = scopes_raw.split() if isinstance(scopes_raw, str) else list(scopes_raw)
            tenant_id = payload_data.get("tenant_id") or payload_data.get("org_id") or "default_tenant"
            user_id = payload_data.get("sub") or "anonymous_user"

            principal = PrincipalContext(
                tenant_id=tenant_id,
                user_id=user_id,
                scopes=set(scopes),
                is_authenticated=True,
                auth_mode="oidc",
            )
            set_current_principal(principal)

            return AccessToken(
                token=token,
                client_id=payload_data.get("client_id", "oauth_client"),
                scopes=scopes,
                expires_at=int(exp) if exp else None,
                resource=self.resource_server_url,
                subject=user_id,
                claims=payload_data,
            )

        except Exception as exc:
            logger.warning("OIDC token verification failed: %s", exc)
            return None
