"""Client abstraction for Nango OAuth connection management and authorized proxying.

IMPORTANT ARCHITECTURAL BOUNDARY:
Nango is strictly used for:
1. Third-party authentication and OAuth connection lifecycle management.
2. Generating Connect Session tokens for frontend OAuth onboarding.
3. Secure third-party API proxy requests (e.g. HubSpot CRM reads).

Nango is NOT used for:
- AI orchestration or agent logic.
- Model Context Protocol (MCP) server hosting.
- Core research workflows.
"""

import asyncio
from typing import Any

import httpx

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.integrations.nango.config import NangoConfig, NangoConnectionIdentity
from app.integrations.nango.errors import (
    NangoAuthError,
    NangoConnectionNotFoundError,
    NangoError,
    NangoExpiredConnectionError,
    NangoProxyError,
    NangoRateLimitError,
)
from app.integrations.nango.schemas import (
    NangoConnection,
    NangoConnectionStatus,
    NangoConnectSession,
)

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
            base_url=self.settings.nango_base_url.rstrip("/"),
            timeout=self.settings.nango_timeout,
        )

    def _get_headers(self, config: NangoConfig) -> dict[str, str]:
        """Generate server-side authentication headers for Nango API."""
        return {
            "Authorization": f"Bearer {config.secret_key}",
            "Content-Type": "application/json",
        }

    async def create_connect_session(
        self,
        connection_id: str,
        integration_id: str = "hubspot",
        user_id: str | None = None,
        organization_id: str | None = None,
    ) -> NangoConnectSession:
        """Create an ephemeral Connect Session token for the Nango Connect UI frontend SDK.

        Args:
            connection_id: Unique tenant or user identifier in Outmate.
            integration_id: Provider configuration key (default: 'hubspot').
            user_id: Optional user identifier.
            organization_id: Optional organization identifier.

        Returns:
            NangoConnectSession containing the session token.
        """
        config = self._get_config()
        url = f"{config.base_url}/connect/sessions"
        payload: dict[str, Any] = {
            "connection_id": connection_id,
            "integration_id": integration_id,
        }
        if user_id or organization_id:
            payload["metadata"] = {}
            if user_id:
                payload["metadata"]["user_id"] = user_id
            if organization_id:
                payload["metadata"]["organization_id"] = organization_id

        async with httpx.AsyncClient(timeout=config.timeout) as client:
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(config),
                )
                if response.status_code == 401:
                    raise NangoAuthError("Invalid Nango secret key provided (HTTP 401)")
                if response.status_code == 429:
                    raise NangoRateLimitError("Nango rate limit exceeded creating connect session")

                response.raise_for_status()
                data = response.json()

                # Extract token from data envelope or root
                token_data = data.get("data", data)
                token = token_data.get("token")
                if not token:
                    raise NangoError(
                        "Nango did not return a session token in response",
                        details={"response": data},
                    )

                return NangoConnectSession(
                    token=token,
                    expires_at=token_data.get("expires_at"),
                    connect_url=token_data.get("connect_url"),
                )
            except httpx.HTTPStatusError as exc:
                logger.error("Nango create connect session failed: %s", exc)
                raise NangoError(
                    f"Failed to create Nango connect session: {exc}",
                    details={"status_code": exc.response.status_code, "text": exc.response.text},
                ) from exc
            except httpx.RequestError as exc:
                logger.error("Network error creating Nango connect session: %s", exc)
                raise NangoError(f"Network error contacting Nango: {exc}") from exc

    async def get_connection(
        self, connection_id: str, provider_config_key: str = "hubspot"
    ) -> NangoConnection | None:
        """Fetch connection details from Nango for a specific tenant and provider."""
        config = self._get_config()
        url = f"{config.base_url}/connection/{connection_id}"
        params = {"provider_config_key": provider_config_key}

        async with httpx.AsyncClient(timeout=config.timeout) as client:
            try:
                response = await client.get(
                    url,
                    params=params,
                    headers=self._get_headers(config),
                )
                if response.status_code == 401:
                    raise NangoAuthError("Invalid Nango secret key provided (HTTP 401)")
                if response.status_code == 404:
                    return None
                if response.status_code == 429:
                    raise NangoRateLimitError("Nango rate limit exceeded checking connection")

                response.raise_for_status()
                data = response.json()
                conn_data = data.get("data", data)

                return NangoConnection(
                    connection_id=connection_id,
                    provider_config_key=provider_config_key,
                    created=conn_data.get("created"),
                    updated=conn_data.get("updated"),
                    metadata=conn_data.get("metadata", {}),
                )
            except httpx.HTTPStatusError as exc:
                logger.error("Nango connection fetch failed: %s", exc)
                raise NangoError(
                    f"Failed to fetch Nango connection: {exc}",
                    details={"status_code": exc.response.status_code},
                ) from exc
            except httpx.RequestError as exc:
                logger.error("Network error fetching Nango connection: %s", exc)
                raise NangoError(f"Network error contacting Nango: {exc}") from exc

    async def list_connections(self, connection_id: str | None = None) -> list[NangoConnection]:
        """List active connections, optionally filtered by connection_id."""
        config = self._get_config()
        url = f"{config.base_url}/connection"
        params: dict[str, Any] = {}
        if connection_id:
            params["connection_id"] = connection_id

        async with httpx.AsyncClient(timeout=config.timeout) as client:
            try:
                response = await client.get(
                    url,
                    params=params,
                    headers=self._get_headers(config),
                )
                if response.status_code == 401:
                    raise NangoAuthError("Invalid Nango secret key provided (HTTP 401)")
                if response.status_code == 429:
                    raise NangoRateLimitError("Nango rate limit exceeded listing connections")

                response.raise_for_status()
                data = response.json()
                raw_list = data.get("data", data.get("connections", []))
                if isinstance(raw_list, dict):
                    raw_list = [raw_list]

                results: list[NangoConnection] = []
                for item in raw_list:
                    if isinstance(item, dict):
                        cid = item.get("connection_id", "")
                        provider = item.get("provider_config_key", "")
                        if cid and provider:
                            results.append(
                                NangoConnection(
                                    connection_id=cid,
                                    provider_config_key=provider,
                                    created=item.get("created"),
                                    updated=item.get("updated"),
                                    metadata=item.get("metadata", {}),
                                )
                            )
                return results
            except httpx.HTTPStatusError as exc:
                logger.error("Nango list connections failed: %s", exc)
                raise NangoError(
                    f"Failed to list Nango connections: {exc}",
                    details={"status_code": exc.response.status_code},
                ) from exc
            except httpx.RequestError as exc:
                logger.error("Network error listing Nango connections: %s", exc)
                raise NangoError(f"Network error contacting Nango: {exc}") from exc

    async def delete_connection(
        self, connection_id: str, provider_config_key: str = "hubspot"
    ) -> bool:
        """Delete an authorized connection in Nango (disconnect integration)."""
        config = self._get_config()
        url = f"{config.base_url}/connection/{connection_id}"
        params = {"provider_config_key": provider_config_key}

        async with httpx.AsyncClient(timeout=config.timeout) as client:
            try:
                response = await client.delete(
                    url,
                    params=params,
                    headers=self._get_headers(config),
                )
                if response.status_code == 401:
                    raise NangoAuthError("Invalid Nango secret key provided (HTTP 401)")
                if response.status_code == 404:
                    return False
                response.raise_for_status()
                return True
            except httpx.HTTPStatusError as exc:
                logger.error("Nango delete connection failed: %s", exc)
                raise NangoError(
                    f"Failed to delete Nango connection: {exc}",
                    details={"status_code": exc.response.status_code},
                ) from exc
            except httpx.RequestError as exc:
                logger.error("Network error deleting Nango connection: %s", exc)
                raise NangoError(f"Network error contacting Nango: {exc}") from exc

    async def get_connection_status(
        self, identity: NangoConnectionIdentity
    ) -> NangoConnectionStatus:
        """Check whether a third-party OAuth connection is active, expired, or disconnected."""
        try:
            conn = await self.get_connection(
                connection_id=identity.connection_id,
                provider_config_key=identity.integration_id,
            )
            if conn is None:
                return NangoConnectionStatus(
                    connection_id=identity.connection_id,
                    integration_id=identity.integration_id,
                    connected=False,
                    status="not_found",
                    provider=identity.integration_id,
                    details="Connection does not exist in Nango",
                )
            return NangoConnectionStatus(
                connection_id=identity.connection_id,
                integration_id=identity.integration_id,
                connected=True,
                status="connected",
                provider=identity.integration_id,
                metadata=conn.metadata,
                details="Active authorized connection verified",
            )
        except NangoAuthError:
            raise
        except Exception as exc:
            logger.error("Connection status check encountered error: %s", exc)
            return NangoConnectionStatus(
                connection_id=identity.connection_id,
                integration_id=identity.integration_id,
                connected=False,
                status="error",
                provider=identity.integration_id,
                details=str(exc),
            )

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
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        proxy_url = f"{config.base_url}/proxy{clean_endpoint}"

        proxy_headers = self._get_headers(config)
        proxy_headers["Connection-Id"] = identity.connection_id
        proxy_headers["Provider-Config-Key"] = identity.integration_id
        if headers:
            proxy_headers.update(headers)

        max_retries = max(1, self.settings.integration_max_retries)
        last_error: Exception | None = None

        for attempt in range(max_retries):
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
                        raise NangoExpiredConnectionError(
                            f"OAuth connection for {identity.integration_id} expired or revoked",
                            details={"connection_id": identity.connection_id},
                        )
                    if response.status_code == 404:
                        raise NangoConnectionNotFoundError(
                            f"Resource or connection not found on {endpoint}",
                            details={"status_code": 404, "endpoint": endpoint},
                        )
                    if response.status_code == 429:
                        raise NangoRateLimitError(
                            f"Rate limit exceeded on third-party API for {identity.integration_id}",
                            details={"endpoint": endpoint},
                        )

                    response.raise_for_status()
                    return response.json()  # type: ignore[no-any-return]

                except (
                    NangoExpiredConnectionError,
                    NangoConnectionNotFoundError,
                    NangoRateLimitError,
                ):
                    raise
                except httpx.HTTPStatusError as exc:
                    logger.error(
                        "Nango proxy HTTP error: %s (status %d)", exc, exc.response.status_code
                    )
                    raise NangoProxyError(
                        f"Third-party API request failed via Nango proxy: {exc}",
                        status_code=exc.response.status_code,
                        response_body=exc.response.text,
                    ) from exc
                except httpx.RequestError as exc:
                    last_error = exc
                    logger.warning(
                        "Nango proxy network attempt %d/%d failed: %s",
                        attempt + 1,
                        max_retries,
                        exc,
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5 * (2**attempt))
                        continue
                    raise NangoProxyError(
                        f"Network failure calling Nango proxy after {max_retries} attempts: {exc}"
                    ) from exc

        raise NangoProxyError(f"Proxy request failed: {last_error}")
