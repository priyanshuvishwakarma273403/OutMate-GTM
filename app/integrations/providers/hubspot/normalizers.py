"""Normalizers translating raw HubSpot CRM v3 API JSON objects into normalized domain models."""

from typing import Any

from app.domain.models.crm import CRMCompany, CRMContact, CRMDeal


def _parse_float(val: Any) -> float | None:
    """Safely parse float from string or number."""
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _parse_int(val: Any) -> int | None:
    """Safely parse integer from string or number."""
    if val is None or val == "":
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def normalize_company(raw: dict[str, Any], connection_id: str) -> CRMCompany:
    """Normalize a raw HubSpot company JSON payload into CRMCompany."""
    props = raw.get("properties", {})
    provider_id = str(raw.get("id") or props.get("hs_object_id") or "")

    name = props.get("name") or "Unnamed Company"
    domain = props.get("domain") or None
    if domain:
        domain = domain.lower().strip()

    return CRMCompany(
        provider="hubspot",
        provider_id=provider_id,
        name=name,
        domain=domain,
        industry=props.get("industry") or None,
        description=props.get("description") or None,
        annual_revenue=_parse_float(props.get("annualrevenue")),
        number_of_employees=_parse_int(props.get("numberofemployees")),
        city=props.get("city") or None,
        state=props.get("state") or None,
        country=props.get("country") or None,
        website=props.get("website") or None,
        created_at=props.get("createdate") or raw.get("createdAt") or None,
        updated_at=props.get("hs_lastmodifieddate") or raw.get("updatedAt") or None,
        connection_id=connection_id,
        raw_properties=props,
    )


def normalize_contact(raw: dict[str, Any], connection_id: str) -> CRMContact:
    """Normalize a raw HubSpot contact JSON payload into CRMContact."""
    props = raw.get("properties", {})
    provider_id = str(raw.get("id") or props.get("hs_object_id") or "")

    first_name = props.get("firstname") or None
    last_name = props.get("lastname") or None
    email = props.get("email") or None
    if email:
        email = email.lower().strip()

    name_parts = [part for part in [first_name, last_name] if part]
    if name_parts:
        full_name = " ".join(name_parts)
    elif email:
        full_name = email.split("@")[0].replace(".", " ").title()
    else:
        full_name = "Unnamed Contact"

    return CRMContact(
        provider="hubspot",
        provider_id=provider_id,
        first_name=first_name,
        last_name=last_name,
        full_name=full_name,
        email=email,
        job_title=props.get("jobtitle") or None,
        department=props.get("department") or None,
        phone=props.get("phone") or None,
        mobile_phone=props.get("mobilephone") or None,
        associated_company_id=str(props.get("associatedcompanyid") or "") or None,
        lifecycle_stage=props.get("lifecyclestage") or None,
        lead_status=props.get("hs_lead_status") or None,
        created_at=props.get("createdate") or raw.get("createdAt") or None,
        updated_at=props.get("lastmodifieddate") or raw.get("updatedAt") or None,
        connection_id=connection_id,
        raw_properties=props,
    )


def normalize_deal(raw: dict[str, Any], connection_id: str) -> CRMDeal:
    """Normalize a raw HubSpot deal JSON payload into CRMDeal."""
    props = raw.get("properties", {})
    provider_id = str(raw.get("id") or props.get("hs_object_id") or "")

    name = props.get("dealname") or "Unnamed Opportunity"
    stage = props.get("dealstage") or "unknown"
    amount = _parse_float(props.get("amount"))

    # Extract associations if present in raw envelope
    associated_companies: list[str] = []
    associated_contacts: list[str] = []
    associations = raw.get("associations", {})

    if "companies" in associations:
        for c in associations["companies"].get("results", []):
            cid = str(c.get("id", ""))
            if cid:
                associated_companies.append(cid)

    if "contacts" in associations:
        for ct in associations["contacts"].get("results", []):
            ctid = str(ct.get("id", ""))
            if ctid:
                associated_contacts.append(ctid)

    return CRMDeal(
        provider="hubspot",
        provider_id=provider_id,
        name=name,
        stage=stage,
        amount=amount,
        currency="USD",
        close_date=props.get("closedate") or None,
        pipeline=props.get("pipeline") or None,
        associated_company_ids=associated_companies,
        associated_contact_ids=associated_contacts,
        created_at=props.get("createdate") or raw.get("createdAt") or None,
        updated_at=props.get("hs_lastmodifieddate") or raw.get("updatedAt") or None,
        connection_id=connection_id,
        raw_properties=props,
    )

