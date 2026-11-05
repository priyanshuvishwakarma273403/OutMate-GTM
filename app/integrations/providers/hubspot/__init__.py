"""HubSpot CRM integration provider package."""

from app.integrations.providers.hubspot.adapter import HubSpotAdapter
from app.integrations.providers.hubspot.capabilities import (
    HUBSPOT_COMPANY_PROPERTIES,
    HUBSPOT_CONTACT_PROPERTIES,
    HUBSPOT_DEAL_PROPERTIES,
    HUBSPOT_READ_SCOPES,
)
from app.integrations.providers.hubspot.normalizers import (
    normalize_company,
    normalize_contact,
    normalize_deal,
)

__all__ = [
    "HUBSPOT_COMPANY_PROPERTIES",
    "HUBSPOT_CONTACT_PROPERTIES",
    "HUBSPOT_DEAL_PROPERTIES",
    "HUBSPOT_READ_SCOPES",
    "HubSpotAdapter",
    "normalize_company",
    "normalize_contact",
    "normalize_deal",
]

