"""Integration tests for FastAPI /api/v1/integrations and /api/v1/crm endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.domain.models.crm import CRMCompany, CRMContact, CRMDeal
from app.integrations.nango.schemas import NangoConnectionStatus
from app.main import app
from app.services.crm_service import get_crm_service


@pytest.fixture
def client() -> TestClient:
    """Fixture providing TestClient instance."""
    return TestClient(app)


def test_get_integrations_html_page(client: TestClient) -> None:
    """Verify GET /integrations returns the management UI HTML page."""
    response = client.get("/integrations")
    assert response.status_code == status.HTTP_200_OK
    assert "Outmate GTM — Integrations Management" in response.text
    assert "HubSpot CRM" in response.text


def test_list_integrations_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/integrations returns supported integrations list."""
    response = client.get("/api/v1/integrations")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    integrations = data["data"]["integrations"]
    assert any(i["id"] == "hubspot" for i in integrations)


def test_hubspot_connect_session_endpoint(client: TestClient) -> None:
    """Verify POST /api/v1/integrations/hubspot/connect-session initiates session."""
    crm_service = get_crm_service()
    with patch.object(
        crm_service,
        "initiate_connect_session",
        new_callable=AsyncMock,
    ) as mock_init:
        from app.integrations.nango.schemas import ConnectSessionResponse

        mock_init.return_value = ConnectSessionResponse(
            token="sess_token_123",
            connection_id="org_test",
            integration_id="hubspot",
            expires_at="2026-11-05T12:00:00Z",
        )

        response = client.post(
            "/api/v1/integrations/hubspot/connect-session",
            json={"user_id": "usr_1", "organization_id": "org_test"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["token"] == "sess_token_123"
        assert data["data"]["connection_id"] == "org_test"


def test_hubspot_verify_endpoint(client: TestClient) -> None:
    """Verify POST /api/v1/integrations/hubspot/verify triggers server verification."""
    crm_service = get_crm_service()
    with patch.object(
        crm_service,
        "verify_connection",
        new_callable=AsyncMock,
    ) as mock_verify:
        mock_verify.return_value = NangoConnectionStatus(
            connection_id="org_test",
            integration_id="hubspot",
            connected=True,
            status="connected",
            provider="hubspot",
            metadata={"portal_id": "9999"},
        )

        response = client.post(
            "/api/v1/integrations/hubspot/verify",
            json={"connection_id": "org_test"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["connected"] is True


def test_hubspot_disconnect_endpoint(client: TestClient) -> None:
    """Verify POST /api/v1/integrations/hubspot/disconnect revokes connection."""
    crm_service = get_crm_service()
    with patch.object(
        crm_service,
        "disconnect",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = client.post(
            "/api/v1/integrations/hubspot/disconnect",
            json={"connection_id": "org_test"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True


def test_crm_search_companies_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/crm/companies returns company records."""
    crm_service = get_crm_service()
    with patch.object(
        crm_service,
        "search_companies",
        new_callable=AsyncMock,
    ) as mock_search:
        mock_search.return_value = [
            CRMCompany(
                provider="hubspot",
                provider_id="comp_1",
                name="HashiCorp",
                domain="hashicorp.com",
                connection_id="org_test",
            )
        ]

        response = client.get(
            "/api/v1/crm/companies?query=HashiCorp",
            headers={"X-Organization-Id": "org_test"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "HashiCorp"


def test_crm_search_contacts_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/crm/contacts returns contact records."""
    crm_service = get_crm_service()
    with patch.object(
        crm_service,
        "search_contacts",
        new_callable=AsyncMock,
    ) as mock_search:
        mock_search.return_value = [
            CRMContact(
                provider="hubspot",
                provider_id="ct_1",
                full_name="Mitchell Hashimoto",
                job_title="Co-Founder",
                connection_id="org_test",
            )
        ]

        response = client.get(
            "/api/v1/crm/contacts?query=Mitchell",
            headers={"X-Organization-Id": "org_test"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"][0]["full_name"] == "Mitchell Hashimoto"


def test_crm_search_deals_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/crm/deals returns deal records."""
    crm_service = get_crm_service()
    with patch.object(
        crm_service,
        "search_deals",
        new_callable=AsyncMock,
    ) as mock_search:
        mock_search.return_value = [
            CRMDeal(
                provider="hubspot",
                provider_id="deal_1",
                name="Vault Enterprise Subscription",
                stage="closedwon",
                amount=75000.0,
                connection_id="org_test",
            )
        ]

        response = client.get(
            "/api/v1/crm/deals",
            headers={"X-Organization-Id": "org_test"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"][0]["name"] == "Vault Enterprise Subscription"
        assert data["data"][0]["amount"] == 75000.0
