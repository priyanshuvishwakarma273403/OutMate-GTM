"""Domain models for normalized CRM entities, associations, and intelligence contexts."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    """Return timezone-aware current UTC datetime formatted as ISO 8601 string."""
    return datetime.now(UTC).isoformat()


class CRMCompany(BaseModel):
    """Normalized CRM company record originating from third-party provider (HubSpot)."""

    provider: str = Field(default="hubspot", description="CRM provider name")
    provider_id: str = Field(..., description="Provider's internal object ID")
    name: str = Field(..., description="Company name recorded in CRM")
    domain: str | None = Field(default=None, description="Primary web domain (e.g. acme.com)")
    industry: str | None = Field(default=None, description="Industry sector classification")
    description: str | None = Field(default=None, description="Company overview / notes")
    annual_revenue: float | None = Field(default=None, description="Reported annual revenue")
    number_of_employees: int | None = Field(default=None, description="Recorded employee headcount")
    city: str | None = Field(default=None, description="City location")
    state: str | None = Field(default=None, description="State or province")
    country: str | None = Field(default=None, description="Country location")
    website: str | None = Field(default=None, description="Primary website URL")
    created_at: str | None = Field(default=None, description="Creation timestamp in CRM")
    updated_at: str | None = Field(default=None, description="Last update timestamp in CRM")
    connection_id: str = Field(..., description="Outmate tenant connection ID that owns this data")
    raw_properties: dict[str, Any] = Field(
        default_factory=dict, description="Raw provider properties preserved for reference"
    )


class CRMContact(BaseModel):
    """Normalized CRM contact / person record originating from third-party provider."""

    provider: str = Field(default="hubspot", description="CRM provider name")
    provider_id: str = Field(..., description="Provider's internal object ID")
    first_name: str | None = Field(default=None, description="Contact first name")
    last_name: str | None = Field(default=None, description="Contact last name")
    full_name: str = Field(..., description="Normalized full name")
    email: str | None = Field(default=None, description="Primary email address")
    job_title: str | None = Field(default=None, description="Current job title / designation")
    department: str | None = Field(default=None, description="Department name if recorded")
    phone: str | None = Field(default=None, description="Primary business phone number")
    mobile_phone: str | None = Field(default=None, description="Mobile contact number")
    associated_company_id: str | None = Field(
        default=None, description="Provider ID of associated company"
    )
    lifecycle_stage: str | None = Field(
        default=None, description="Lifecycle stage (lead, customer)"
    )
    lead_status: str | None = Field(default=None, description="Sales lead status")
    created_at: str | None = Field(default=None, description="Creation timestamp in CRM")
    updated_at: str | None = Field(default=None, description="Last update timestamp in CRM")
    connection_id: str = Field(..., description="Outmate tenant connection ID that owns this data")
    raw_properties: dict[str, Any] = Field(
        default_factory=dict, description="Raw provider properties preserved for reference"
    )


class CRMDeal(BaseModel):
    """Normalized CRM deal or business opportunity record."""

    provider: str = Field(default="hubspot", description="CRM provider name")
    provider_id: str = Field(..., description="Provider's internal deal ID")
    name: str = Field(..., description="Deal or opportunity title")
    stage: str = Field(..., description="Pipeline deal stage name or ID")
    amount: float | None = Field(default=None, description="Monetary value of the deal")
    currency: str = Field(default="USD", description="Currency code (e.g. USD, EUR)")
    close_date: str | None = Field(default=None, description="Projected or actual close date")
    pipeline: str | None = Field(default=None, description="Pipeline identifier")
    associated_company_ids: list[str] = Field(
        default_factory=list, description="IDs of associated companies"
    )
    associated_contact_ids: list[str] = Field(
        default_factory=list, description="IDs of associated contacts"
    )
    created_at: str | None = Field(default=None, description="Creation timestamp in CRM")
    updated_at: str | None = Field(default=None, description="Last update timestamp in CRM")
    connection_id: str = Field(..., description="Outmate tenant connection ID that owns this data")
    raw_properties: dict[str, Any] = Field(
        default_factory=dict, description="Raw provider properties preserved for reference"
    )


class CRMAssociation(BaseModel):
    """Relationship between two CRM objects (e.g. company to contact, company to deal)."""

    source_type: str = Field(..., description="Source object type: company, contact, deal")
    source_id: str = Field(..., description="Source object provider ID")
    target_type: str = Field(..., description="Target object type: company, contact, deal")
    target_id: str = Field(..., description="Target object provider ID")
    association_type: str = Field(default="primary", description="Association relationship type")


class CRMContextSummary(BaseModel):
    """Aggregated CRM intelligence report for a company within a specific tenant context."""

    company: CRMCompany | None = Field(
        default=None, description="Matched CRM company record if found"
    )
    contacts: list[CRMContact] = Field(
        default_factory=list, description="List of contacts affiliated with this company"
    )
    deals: list[CRMDeal] = Field(
        default_factory=list, description="Deals associated with this account"
    )
    total_deal_amount: float = Field(default=0.0, description="Sum of deal values")
    open_deals_count: int = Field(default=0, description="Count of open deals")
    connection_id: str = Field(..., description="Tenant connection ID providing this context")
    retrieved_at: str = Field(
        default_factory=utc_now_iso, description="UTC ISO timestamp when data was fetched"
    )
