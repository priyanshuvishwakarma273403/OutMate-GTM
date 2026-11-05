"""Unit tests for HubSpot CRM v3 object normalizers."""

from app.integrations.providers.hubspot.normalizers import (
    normalize_company,
    normalize_contact,
    normalize_deal,
)


def test_normalize_company_full() -> None:
    """Verify company normalization with all standard properties present."""
    raw = {
        "id": "comp_987",
        "properties": {
            "name": "Stripe, Inc.",
            "domain": "STRIPE.COM",
            "industry": "Financial Services",
            "description": "Financial infrastructure for the internet",
            "annualrevenue": "14000000000",
            "numberofemployees": "8000",
            "city": "South San Francisco",
            "state": "CA",
            "country": "United States",
            "website": "https://stripe.com",
            "createdate": "2024-01-15T10:00:00Z",
            "hs_lastmodifieddate": "2026-10-01T15:30:00Z",
        },
    }

    company = normalize_company(raw, connection_id="org_test")

    assert company.provider == "hubspot"
    assert company.provider_id == "comp_987"
    assert company.name == "Stripe, Inc."
    assert company.domain == "stripe.com"  # Lowercased
    assert company.industry == "Financial Services"
    assert company.annual_revenue == 14000000000.0
    assert company.number_of_employees == 8000
    assert company.city == "South San Francisco"
    assert company.connection_id == "org_test"
    assert company.raw_properties["annualrevenue"] == "14000000000"


def test_normalize_company_missing_optional_fields() -> None:
    """Verify company normalization handles sparse or missing properties safely without fabrication."""
    raw = {
        "id": "comp_sparse",
        "properties": {
            "name": "Acme Widgets",
            "annualrevenue": "",
            "numberofemployees": "invalid_num",
        },
    }

    company = normalize_company(raw, connection_id="org_test")

    assert company.provider_id == "comp_sparse"
    assert company.name == "Acme Widgets"
    assert company.domain is None
    assert company.annual_revenue is None
    assert company.number_of_employees is None
    assert company.city is None


def test_normalize_contact_with_first_and_last_name() -> None:
    """Verify contact normalization with standard name fields."""
    raw = {
        "id": "ct_123",
        "properties": {
            "firstname": "Patrick",
            "lastname": "Collison",
            "email": "PATRICK@STRIPE.COM",
            "jobtitle": "Chief Executive Officer",
            "department": "Executive",
            "phone": "+1-555-0100",
            "associatedcompanyid": "comp_987",
            "lifecyclestage": "customer",
        },
    }

    contact = normalize_contact(raw, connection_id="org_test")

    assert contact.provider == "hubspot"
    assert contact.provider_id == "ct_123"
    assert contact.first_name == "Patrick"
    assert contact.last_name == "Collison"
    assert contact.full_name == "Patrick Collison"
    assert contact.email == "patrick@stripe.com"  # Lowercased
    assert contact.job_title == "Chief Executive Officer"
    assert contact.department == "Executive"
    assert contact.associated_company_id == "comp_987"
    assert contact.connection_id == "org_test"


def test_normalize_contact_fallback_to_email_for_name() -> None:
    """Verify contact full name is synthesized cleanly from email when names are omitted."""
    raw = {
        "id": "ct_email_only",
        "properties": {
            "email": "jane.doe@example.com",
            "jobtitle": "VP Engineering",
        },
    }

    contact = normalize_contact(raw, connection_id="org_test")

    assert contact.first_name is None
    assert contact.last_name is None
    assert contact.full_name == "Jane Doe"
    assert contact.email == "jane.doe@example.com"
    assert contact.job_title == "VP Engineering"


def test_normalize_deal_with_associations() -> None:
    """Verify deal normalization parsing amounts and embedded associations."""
    raw = {
        "id": "deal_555",
        "properties": {
            "dealname": "Enterprise Cloud Expansion 2026",
            "dealstage": "contractsent",
            "amount": "250000.50",
            "pipeline": "enterprise_sales",
            "closedate": "2026-12-31T00:00:00Z",
        },
        "associations": {
            "companies": {"results": [{"id": "comp_987"}]},
            "contacts": {"results": [{"id": "ct_123"}, {"id": "ct_456"}]},
        },
    }

    deal = normalize_deal(raw, connection_id="org_test")

    assert deal.provider == "hubspot"
    assert deal.provider_id == "deal_555"
    assert deal.name == "Enterprise Cloud Expansion 2026"
    assert deal.stage == "contractsent"
    assert deal.amount == 250000.50
    assert deal.associated_company_ids == ["comp_987"]
    assert deal.associated_contact_ids == ["ct_123", "ct_456"]
    assert deal.connection_id == "org_test"

