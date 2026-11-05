"""Pydantic input and output schemas for MCP CRM tools."""

from typing import Any

from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# Tool Input Schemas
# ------------------------------------------------------------------------------
class ListIntegrationsInput(BaseModel):
    """Input payload for listing available and connected integrations."""

    organization_id: str | None = Field(
        default=None, description="Optional tenant organization ID to filter connections"
    )


class GetIntegrationStatusInput(BaseModel):
    """Input payload for checking integration connection status."""

    integration_id: str = Field(
        default="hubspot", description="Target provider configuration key (e.g. 'hubspot')"
    )
    connection_id: str | None = Field(
        default=None, description="Explicit Nango connection ID to query"
    )


class SearchCRMCompaniesInput(BaseModel):
    """Input payload for searching companies in connected CRM."""

    query: str | None = Field(default=None, description="Company name search string")
    domain: str | None = Field(
        default=None, description="Exact web domain filter (e.g. 'vercel.com')"
    )
    limit: int = Field(
        default=10, ge=1, le=100, description="Maximum number of companies to return"
    )


class GetCRMCompanyInput(BaseModel):
    """Input payload for retrieving a specific CRM company by provider ID."""

    company_id: str = Field(..., description="Provider's internal object ID for the company")


class SearchCRMContactsInput(BaseModel):
    """Input payload for searching contacts in connected CRM."""

    query: str | None = Field(default=None, description="Contact name or designation query")
    email: str | None = Field(default=None, description="Exact contact email address")
    company_id: str | None = Field(default=None, description="Associated company provider ID")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of contacts to return")


class GetCRMContactInput(BaseModel):
    """Input payload for retrieving a specific CRM contact by provider ID."""

    contact_id: str = Field(..., description="Provider's internal object ID for the contact")


class SearchCRMDealsInput(BaseModel):
    """Input payload for searching business deals / opportunities in connected CRM."""

    company_id: str | None = Field(
        default=None, description="Filter deals associated with this company provider ID"
    )
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of deals to return")


class GetCRMDealInput(BaseModel):
    """Input payload for retrieving a specific CRM deal by provider ID."""

    deal_id: str = Field(..., description="Provider's internal object ID for the deal")


class GetCompanyCRMContextInput(BaseModel):
    """Input payload for retrieving aggregated CRM context for an account."""

    company_id: str | None = Field(
        default=None, description="Direct company provider ID if already known"
    )
    domain: str | None = Field(
        default=None, description="Web domain of the company (e.g. 'stripe.com')"
    )
    name: str | None = Field(default=None, description="Company name to search and match in CRM")


# ------------------------------------------------------------------------------
# Tool Output Schemas
# ------------------------------------------------------------------------------
class ListIntegrationsOutput(BaseModel):
    """Output payload for list_connected_integrations tool."""

    integrations: list[dict[str, Any]] = Field(default_factory=list)
    connections: list[dict[str, Any]] = Field(default_factory=list)


class GetIntegrationStatusOutput(BaseModel):
    """Output payload for get_integration_status tool."""

    connection_id: str
    integration_id: str
    connected: bool
    status: str
    provider: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    details: str | None = None


class SearchCRMCompaniesOutput(BaseModel):
    """Output payload for search_crm_companies tool."""

    companies: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class GetCRMCompanyOutput(BaseModel):
    """Output payload for get_crm_company tool."""

    company: dict[str, Any] = Field(default_factory=dict)


class SearchCRMContactsOutput(BaseModel):
    """Output payload for search_crm_contacts tool."""

    contacts: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class GetCRMContactOutput(BaseModel):
    """Output payload for get_crm_contact tool."""

    contact: dict[str, Any] = Field(default_factory=dict)


class SearchCRMDealsOutput(BaseModel):
    """Output payload for search_crm_deals tool."""

    deals: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class GetCRMDealOutput(BaseModel):
    """Output payload for get_crm_deal tool."""

    deal: dict[str, Any] = Field(default_factory=dict)


class GetCompanyCRMContextOutput(BaseModel):
    """Output payload for get_company_crm_context tool."""

    context: dict[str, Any] = Field(default_factory=dict)
