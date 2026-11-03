"""Unit tests for Nango integration client abstraction and error handling."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.config import AppSettings
from app.core.exceptions import (
    ConfigurationError,
    NangoConnectionExpiredError,
)
from app.integrations.nango import NangoClient, NangoConnectionIdentity


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
