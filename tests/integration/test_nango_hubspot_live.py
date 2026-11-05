"""Live integration tests against real Nango API.

CRITICAL REQUIREMENT:
If NANGO_SECRET_KEY is not configured in the active environment, this test must
be marked as BLOCKED with clear diagnostic information, and must NEVER simulate
or fake success with synthetic mock data.
"""

import pytest

from app.core.config import get_settings
from app.integrations.nango.client import NangoClient
from app.integrations.nango.config import NangoConnectionIdentity


@pytest.mark.live
async def test_live_nango_connectivity() -> None:
    """Verify live connectivity and authentication with Nango API when credentials are provided."""
    settings = get_settings()

    if not settings.nango_secret_key:
        pytest.skip(
            "BLOCKED: NANGO_SECRET_KEY is not configured in the environment. "
            "Please provide a valid Nango secret key in .env to run live integration tests."
        )

    client = NangoClient(settings=settings)

    # Attempt to list connections against live Nango API
    try:
        connections = await client.list_connections()
        assert isinstance(connections, list)
    except Exception as exc:
        pytest.fail(f"Live Nango API connection failed: {exc}")


@pytest.mark.live
async def test_live_hubspot_connection_status() -> None:
    """Verify live connection status check with Nango for configured integration."""
    settings = get_settings()

    if not settings.nango_secret_key or not settings.nango_connection_id:
        pytest.skip(
            "BLOCKED: NANGO_SECRET_KEY or NANGO_CONNECTION_ID is not configured in .env. "
            "Cannot execute live HubSpot connection status verification."
        )

    client = NangoClient(settings=settings)
    identity = NangoConnectionIdentity(
        connection_id=settings.nango_connection_id,
        integration_id=settings.nango_integration_id_hubspot,
    )

    status_info = await client.get_connection_status(identity)
    assert status_info.integration_id == settings.nango_integration_id_hubspot
    assert status_info.status in ("connected", "not_found", "expired")

