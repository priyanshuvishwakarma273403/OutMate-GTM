"""Unit tests for HubSpot CRM v3 read-only adapter interacting via Nango proxy."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import AppSettings
from app.integrations.nango.client import NangoClient
from app.integrations.nango.errors import CRMReadOnlyError
from app.integrations.providers.hubspot.adapter import HubSpotAdapter


@pytest.fixture
def mock_nango() -> MagicMock:
    """Fixture providing a mocked NangoClient."""
    client = MagicMock(spec=NangoClient)
    client.proxy_request = AsyncMock()
    return client


def test_hubspot_adapter_assert_read_only(mock_nango: MagicMock) -> None:
    """Verify write operations raise CRMReadOnlyError."""
    adapter = HubSpotAdapter(nango_client=mock_nango, settings=AppSettings())
    with pytest.raises(CRMReadOnlyError, match="strictly read-only"):
        adapter._assert_read_only("create_contact")


async def test_hubspot_search_companies_with_domain(mock_nango: MagicMock) -> None:
    """Verify search_companies uses CRM v3 search endpoint with domain filter."""
    adapter = HubSpotAdapter(nango_client=mock_nango)
    mock_nango.proxy_request.return_value = {
        "results": [
            {
                "id": "comp_1",
                "properties": {"name": "Vercel Inc.", "domain": "vercel.com"},
            }
        ]
    }

    companies = await adapter.search_companies(
        connection_id="org_test",
        domain="vercel.com",
    )

    assert len(companies) == 1
    assert companies[0].name == "Vercel Inc."
    assert companies[0].domain == "vercel.com"

    # Verify Nango proxy request parameters
    args, kwargs = mock_nango.proxy_request.call_args
    assert kwargs["endpoint"] == "/crm/v3/objects/companies/search"
    assert kwargs["method"] == "POST"
    assert kwargs["json_data"]["filterGroups"][0]["filters"][0]["value"] == "vercel.com"


async def test_hubspot_get_company(mock_nango: MagicMock) -> None:
    """Verify get_company retrieves single company record."""
    adapter = HubSpotAdapter(nango_client=mock_nango)
    mock_nango.proxy_request.return_value = {
        "id": "comp_123",
        "properties": {"name": "Supabase Inc.", "domain": "supabase.com"},
    }

    company = await adapter.get_company(connection_id="org_test", company_id="comp_123")
    assert company is not None
    assert company.provider_id == "comp_123"
    assert company.name == "Supabase Inc."

    args, kwargs = mock_nango.proxy_request.call_args
    assert kwargs["endpoint"] == "/crm/v3/objects/companies/comp_123"
    assert kwargs["method"] == "GET"


async def test_hubspot_search_contacts_by_email(mock_nango: MagicMock) -> None:
    """Verify search_contacts by email."""
    adapter = HubSpotAdapter(nango_client=mock_nango)
    mock_nango.proxy_request.return_value = {
        "results": [
            {
                "id": "ct_99",
                "properties": {
                    "firstname": "Guillermo",
                    "lastname": "Rauch",
                    "email": "guillermo@vercel.com",
                    "jobtitle": "CEO",
                },
            }
        ]
    }

    contacts = await adapter.search_contacts(
        connection_id="org_test",
        email="guillermo@vercel.com",
    )

    assert len(contacts) == 1
    assert contacts[0].full_name == "Guillermo Rauch"
    assert contacts[0].job_title == "CEO"

    args, kwargs = mock_nango.proxy_request.call_args
    assert kwargs["endpoint"] == "/crm/v3/objects/contacts/search"
    assert kwargs["json_data"]["filterGroups"][0]["filters"][0]["propertyName"] == "email"


async def test_hubspot_get_company_crm_context_aggregation(mock_nango: MagicMock) -> None:
    """Verify get_company_crm_context aggregates company, contacts, and active deals."""
    adapter = HubSpotAdapter(nango_client=mock_nango)

    # Mock sequence: 1. search company, 2. associations for contacts, 3. get contact, 4. associations for deals, 5. get deal
    async def mock_proxy(identity, endpoint, **kwargs):
        if "companies/search" in endpoint:
            return {
                "results": [
                    {
                        "id": "comp_1",
                        "properties": {
                            "name": "Acme Corp",
                            "domain": "acme.com",
                            "annualrevenue": "5000000",
                        },
                    }
                ]
            }
        if "companies/comp_1/associations/contacts" in endpoint:
            return {"results": [{"id": "ct_1"}]}
        if "contacts/ct_1" in endpoint:
            return {
                "id": "ct_1",
                "properties": {
                    "firstname": "Alice",
                    "lastname": "Smith",
                    "jobtitle": "VP Sales",
                    "email": "alice@acme.com",
                },
            }
        if "companies/comp_1/associations/deals" in endpoint:
            return {"results": [{"id": "deal_1"}]}
        if "deals/deal_1" in endpoint:
            return {
                "id": "deal_1",
                "properties": {
                    "dealname": "Acme SaaS License",
                    "amount": "120000",
                    "dealstage": "presentation",
                },
            }
        return {"results": []}

    mock_nango.proxy_request.side_effect = mock_proxy

    context = await adapter.get_company_crm_context(
        connection_id="org_test",
        company_domain="acme.com",
    )

    assert context.company is not None
    assert context.company.name == "Acme Corp"
    assert len(context.contacts) == 1
    assert context.contacts[0].full_name == "Alice Smith"
    assert len(context.deals) == 1
    assert context.deals[0].name == "Acme SaaS License"
    assert context.total_deal_amount == 120000.0
    assert context.open_deals_count == 1

