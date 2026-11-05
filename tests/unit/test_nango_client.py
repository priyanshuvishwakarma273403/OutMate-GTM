"""Unit tests for Nango integration client abstraction, Connect Sessions, and proxy error handling."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.config import AppSettings
from app.core.exceptions import (
    ConfigurationError,
    NangoConnectionExpiredError,
)
from app.integrations.nango import (
    NangoAuthError,
    NangoClient,
    NangoConnectionIdentity,
    NangoRateLimitError,
)


def test_nango_identity_model() -> None:
    """Verify NangoConnectionIdentity model attributes."""
    identity = NangoConnectionIdentity(
        connection_id="user_tenant_123",
        integration_id="hubspot",
    )
    assert identity.connection_id == "user_tenant_123"
    assert identity.integration_id == "hubspot"


def test_nango_client_missing_credentials_raises_config_error() -> None:
    """Verify NangoClient raises ConfigurationError if secret key is missing when called."""
    client = NangoClient(settings=AppSettings(NANGO_SECRET_KEY=None))
    with pytest.raises(ConfigurationError, match="NANGO_SECRET_KEY is required"):
        client._get_config()


async def test_nango_create_connect_session_success() -> None:
    """Verify successful creation of Nango Connect Session."""
    settings = AppSettings(NANGO_SECRET_KEY="test-secret")
    client = NangoClient(settings=settings)

    mock_resp = httpx.Response(
        status_code=200,
        request=httpx.Request("POST", "https://api.nango.dev/connect/sessions"),
        json={"data": {"token": "sess_token_xyz123", "expires_at": "2026-11-05T12:00:00Z"}},
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        session = await client.create_connect_session(
            connection_id="org_123",
            integration_id="hubspot",
            user_id="usr_456",
            organization_id="org_123",
        )

        assert session.token == "sess_token_xyz123"
        assert session.expires_at == "2026-11-05T12:00:00Z"

        # Verify outgoing payload
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["connection_id"] == "org_123"
        assert kwargs["json"]["integration_id"] == "hubspot"
        assert kwargs["headers"]["Authorization"] == "Bearer test-secret"


async def test_nango_create_connect_session_auth_failure() -> None:
    """Verify 401 on create session maps to NangoAuthError."""
    settings = AppSettings(NANGO_SECRET_KEY="invalid-key")
    client = NangoClient(settings=settings)

    mock_resp = httpx.Response(
        status_code=401,
        request=httpx.Request("POST", "https://api.nango.dev/connect/sessions"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        with pytest.raises(NangoAuthError, match="Invalid Nango secret key"):
            await client.create_connect_session(connection_id="org_123")


async def test_nango_create_connect_session_rate_limit() -> None:
    """Verify 429 on create session maps to NangoRateLimitError."""
    settings = AppSettings(NANGO_SECRET_KEY="test-secret")
    client = NangoClient(settings=settings)

    mock_resp = httpx.Response(
        status_code=429,
        request=httpx.Request("POST", "https://api.nango.dev/connect/sessions"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        with pytest.raises(NangoRateLimitError, match="rate limit exceeded"):
            await client.create_connect_session(connection_id="org_123")


async def test_nango_get_connection_success() -> None:
    """Verify fetching existing connection returns NangoConnection object."""
    settings = AppSettings(NANGO_SECRET_KEY="test-secret")
    client = NangoClient(settings=settings)

    mock_resp = httpx.Response(
        status_code=200,
        request=httpx.Request("GET", "https://api.nango.dev/connection/org_1"),
        json={
            "data": {
                "connection_id": "org_1",
                "provider_config_key": "hubspot",
                "created": "2026-11-01T00:00:00Z",
                "metadata": {"account_name": "Acme Corp"},
            }
        },
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        conn = await client.get_connection("org_1", "hubspot")
        assert conn is not None
        assert conn.connection_id == "org_1"
        assert conn.provider_config_key == "hubspot"
        assert conn.metadata.get("account_name") == "Acme Corp"


async def test_nango_get_connection_not_found_returns_none() -> None:
    """Verify 404 on get_connection returns None without raising."""
    settings = AppSettings(NANGO_SECRET_KEY="test-secret")
    client = NangoClient(settings=settings)

    mock_resp = httpx.Response(
        status_code=404,
        request=httpx.Request("GET", "https://api.nango.dev/connection/org_missing"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        conn = await client.get_connection("org_missing", "hubspot")
        assert conn is None


async def test_nango_delete_connection() -> None:
    """Verify deleting a connection in Nango."""
    settings = AppSettings(NANGO_SECRET_KEY="test-secret")
    client = NangoClient(settings=settings)

    mock_resp = httpx.Response(
        status_code=204,
        request=httpx.Request("DELETE", "https://api.nango.dev/connection/org_1"),
    )

    with patch("httpx.AsyncClient.delete", new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = mock_resp
        res = await client.delete_connection("org_1", "hubspot")
        assert res is True


async def test_nango_proxy_expired_connection_handling() -> None:
    """Verify 401 on proxy request maps to NangoConnectionExpiredError."""
    settings = AppSettings(NANGO_SECRET_KEY="test-secret")
    client = NangoClient(settings=settings)
    identity = NangoConnectionIdentity(
        connection_id="user_1",
        integration_id="hubspot",
    )

    mock_response = httpx.Response(
        status_code=401,
        request=httpx.Request("GET", "https://api.nango.dev/proxy/v1/contacts"),
    )

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        with pytest.raises(NangoConnectionExpiredError, match="expired or revoked"):
            await client.proxy_request(identity, "/v1/contacts")
