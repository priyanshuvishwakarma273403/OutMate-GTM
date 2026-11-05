"""Unit tests for CRMService tenant isolation, lifecycle management, and research corroboration."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import AppSettings
from app.core.exceptions import AuthorizationError
from app.domain.models.crm import CRMCompany, CRMContact, CRMContextSummary
from app.domain.models.evidence import EvidenceSourceType, VerificationStatus
from app.integrations.nango.client import NangoClient
from app.integrations.nango.schemas import NangoConnectionStatus, NangoConnectSession
from app.integrations.providers.hubspot.adapter import HubSpotAdapter
from app.services.crm_service import CRMService
from app.services.crm_storage import ConnectionRecord, CRMStorageService


@pytest.fixture
def mock_nango() -> MagicMock:
    client = MagicMock(spec=NangoClient)
    client.create_connect_session = AsyncMock()
    client.get_connection_status = AsyncMock()
    client.delete_connection = AsyncMock()
    return client


@pytest.fixture
def mock_hubspot() -> MagicMock:
    adapter = MagicMock(spec=HubSpotAdapter)
    adapter.search_companies = AsyncMock()
    adapter.get_company = AsyncMock()
    adapter.search_contacts = AsyncMock()
    adapter.get_contact = AsyncMock()
    adapter.search_deals = AsyncMock()
    adapter.get_deal = AsyncMock()
    adapter.get_company_crm_context = AsyncMock()
    return adapter


@pytest.fixture
def storage() -> CRMStorageService:
    return CRMStorageService()


@pytest.fixture
def crm_service(
    mock_nango: MagicMock, mock_hubspot: MagicMock, storage: CRMStorageService
) -> CRMService:
    settings = AppSettings(
        NANGO_SECRET_KEY="test-key",
        HUBSPOT_INTEGRATION_ENABLED=True,
    )
    return CRMService(
        settings=settings,
        nango_client=mock_nango,
        hubspot_adapter=mock_hubspot,
        storage=storage,
    )


def test_resolve_connection_id(crm_service: CRMService, storage: CRMStorageService) -> None:
    """Verify tenant connection resolution based on context or storage."""
    # From explicit connection_id in context
    assert crm_service.resolve_connection_id({"connection_id": "custom_conn_1"}) == "custom_conn_1"

    # From organization_id in context
    assert crm_service.resolve_connection_id({"organization_id": "tenant_abc"}) == "org_tenant_abc"

    # From storage lookup
    storage.save_connection(
        ConnectionRecord(
            connection_id="conn_stored",
            organization_id="tenant_stored",
            user_id="user_1",
            status="connected",
        )
    )
    assert crm_service.resolve_connection_id({"organization_id": "tenant_stored"}) == "conn_stored"


def test_validate_tenant_ownership_blocks_cross_tenant_leak(
    crm_service: CRMService, storage: CRMStorageService
) -> None:
    """Verify cross-tenant access violation raises AuthorizationError."""
    storage.save_connection(
        ConnectionRecord(
            connection_id="org_victim_conn",
            organization_id="tenant_victim",
            user_id="user_victim",
            status="connected",
        )
    )

    # Attacker tenant trying to query victim connection
    with pytest.raises(AuthorizationError, match="Cross-tenant access violation"):
        crm_service.validate_tenant_ownership(
            connection_id="org_victim_conn",
            tenant_context={"organization_id": "tenant_attacker"},
        )


async def test_initiate_connect_session(
    crm_service: CRMService, mock_nango: MagicMock, storage: CRMStorageService
) -> None:
    """Verify initiating connect session creates pending record and returns token."""
    mock_nango.create_connect_session.return_value = NangoConnectSession(
        token="test_token_abc",
        expires_at="2026-11-05T12:00:00Z",
    )

    res = await crm_service.initiate_connect_session(
        user_id="usr_1",
        organization_id="org_1",
    )

    assert res.token == "test_token_abc"
    assert res.connection_id == "org_1"

    # Verify pending state in storage
    record = storage.get_connection("org_1")
    assert record is not None
    assert record.status == "pending"


async def test_verify_connection(
    crm_service: CRMService, mock_nango: MagicMock, storage: CRMStorageService
) -> None:
    """Verify server-side connection verification updates storage to connected."""
    mock_nango.get_connection_status.return_value = NangoConnectionStatus(
        connection_id="org_1",
        integration_id="hubspot",
        connected=True,
        status="connected",
        provider="hubspot",
        metadata={"hub_id": "12345"},
    )

    status = await crm_service.verify_connection("org_1", "hubspot")
    assert status.connected is True

    record = storage.get_connection("org_1")
    assert record is not None
    assert record.status == "connected"
    assert record.last_verified_at is not None


async def test_corroborate_research_with_crm(
    crm_service: CRMService, mock_hubspot: MagicMock
) -> None:
    """Verify corroborating research with CRM yields verified EvidenceRecords."""
    mock_hubspot.get_company_crm_context.return_value = CRMContextSummary(
        company=CRMCompany(
            provider="hubspot",
            provider_id="comp_1",
            name="Vercel",
            domain="vercel.com",
            industry="Software",
            annual_revenue=100000000.0,
            number_of_employees=500,
            connection_id="org_1",
        ),
        contacts=[
            CRMContact(
                provider="hubspot",
                provider_id="ct_1",
                full_name="Guillermo Rauch",
                job_title="CEO",
                email="guillermo@vercel.com",
                connection_id="org_1",
            )
        ],
        deals=[],
        total_deal_amount=0.0,
        open_deals_count=0,
        connection_id="org_1",
    )

    evidence = await crm_service.corroborate_research_with_crm(
        company_name="Vercel",
        domain="vercel.com",
        tenant_context={"organization_id": "org_1"},
    )

    assert len(evidence) == 2
    assert evidence[0].source_type == EvidenceSourceType.HUBSPOT_CRM
    assert evidence[0].source_url == "hubspot://company/comp_1"
    assert evidence[0].verification_status == VerificationStatus.VERIFIED
    assert evidence[1].source_type == EvidenceSourceType.HUBSPOT_CRM
    assert evidence[1].source_url == "hubspot://contact/ct_1"
