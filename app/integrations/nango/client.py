"""Client abstraction for Nango OAuth connection management and authorized proxying.

IMPORTANT ARCHITECTURAL BOUNDARY:
Nango is strictly used for:
1. Third-party authentication and OAuth connection management.
2. Secure third-party API proxy requests (e.g. HubSpot CRM export).

Nango is NOT used for:
- AI orchestration or agent logic.
- Model Context Protocol (MCP) server hosting.
- Core research workflows.
"""

from typing import Any

import httpx

from app.core.config import AppSettings, get_settings
from app.core.exceptions import (
    AuthenticationError,
    NangoConnectionExpiredError,
    NangoIntegrationError,
)
from app.core.logging import get_logger
from app.integrations.nango.config import NangoConfig, NangoConnectionIdentity

logger = get_logger("integrations.nango")


class NangoClient:
    """Enterprise client managing authorized third-party connections via Nango."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._http_client = http_client

    def _get_config(self) -> NangoConfig:
        """Retrieve and validate Nango configuration lazily."""
        self.settings.validate_nango()
        assert self.settings.nango_secret_key is not None
        return NangoConfig(
            secret_key=self.settings.nango_secret_key,
            base_url=self.settings.nango_base_url,
            timeout=self.settings.nango_timeout,
        )

    def _get_headers(self, config: NangoConfig) -> dict[str, str]:
        """Generate server-side authentication headers for Nango API."""
        return {
            "Authorization": f"Bearer {config.secret_key}",
            "Content-Type": "application/json",
        }

    async def get_connection_status(self, identity: NangoConnectionIdentity) -> dict[str, Any]:
        """Check whether a third-party OAuth connection is active, expired, or disconnected."""
        config = self._get_config()
        url = f"{config.base_url}/connection/{identity.connection_id}"
        params = {"provider_config_key": identity.integration_id}

        async with httpx.AsyncClient(timeout=config.timeout) as client:
            try:
                response = await client.get(url, params=params, headers=self._get_headers(config))
                if response.status_code == 401:
                    raise AuthenticationError(
                        "Invalid Nango secret key provided",
                        details={"status_code": 401},
                    )
                if response.status_code == 404:
                    return {
                        "status": "not_found",
                        "connected": False,
                        "details": "Connection does not exist in Nango",
                    }
                response.raise_for_status()
                data = response.json()
                return {
                    "status": "connected",
                    "connected": True,
                    "provider": identity.integration_id,
                    "metadata": data.get("metadata", {}),
                }
            except httpx.HTTPStatusError as exc:
                logger.error("Nango connection check failed: %s", exc)
                raise NangoIntegrationError(
                    f"Failed to verify Nango connection: {exc}",
                    details={"status_code": exc.response.status_code},
                ) from exc
            except httpx.RequestError as exc:
                logger.error("Nango network error: %s", exc)
                raise NangoIntegrationError(f"Network error contacting Nango: {exc}") from exc

    async def proxy_request(
        self,
        identity: NangoConnectionIdentity,
        endpoint: str,
        *,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute an authorized third-party API request proxied securely through Nango.

        No raw third-party access tokens are fetched or stored in application memory.
        """
        config = self._get_config()
        proxy_url = f"{config.base_url}/proxy{endpoint}"

        proxy_headers = self._get_headers(config)
        proxy_headers["Connection-Id"] = identity.connection_id
        proxy_headers["Provider-Config-Key"] = identity.integration_id
        if headers:
            proxy_headers.update(headers)

        async with httpx.AsyncClient(timeout=config.timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=proxy_url,
                    params=params,
                    json=json_data,
                    headers=proxy_headers,
                )
                if response.status_code == 401:
                    raise NangoConnectionExpiredError(
                        f"OAuth connection for {identity.integration_id} expired or revoked",
                        details={"connection_id": identity.connection_id},
                    )
                response.raise_for_status()
                return response.json()  # type: ignore[no-any-return]
            except httpx.HTTPStatusError as exc:
                logger.error("Nango proxy request failed: %s", exc)
                raise NangoIntegrationError(
                    f"Third-party API request failed via Nango proxy: {exc}",
                    details={
                        "status_code": exc.response.status_code,
                        "response_text": exc.response.text,
                    },
                ) from exc
            except httpx.RequestError as exc:
                logger.error("Nango proxy network failure: %s", exc)
                raise NangoIntegrationError(f"Network failure calling Nango proxy: {exc}") from exc
