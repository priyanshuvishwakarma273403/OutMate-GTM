"""HubSpot CRM v3 read-only adapter interacting through Nango authorized proxy.

STRICT READ-ONLY GUARANTEE:
This adapter strictly implements READ queries (GET, search POST). It never creates,
modifies, updates, or deletes CRM objects, preserving client data integrity.
"""

from typing import Any

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.domain.models.crm import CRMCompany, CRMContact, CRMContextSummary, CRMDeal
from app.integrations.nango.client import NangoClient
from app.integrations.nango.config import NangoConnectionIdentity
from app.integrations.nango.errors import (
    CRMReadOnlyError,
    NangoConnectionNotFoundError,
)
from app.integrations.providers.hubspot.capabilities import (
    HUBSPOT_COMPANY_PROPERTIES,
    HUBSPOT_CONTACT_PROPERTIES,
    HUBSPOT_DEAL_PROPERTIES,
)
from app.integrations.providers.hubspot.normalizers import (
    normalize_company,
    normalize_contact,
    normalize_deal,
)

logger = get_logger("integrations.hubspot.adapter")


class HubSpotAdapter:
    """Read-only HubSpot CRM API client interacting exclusively through Nango proxy."""

    def __init__(
        self,
        nango_client: NangoClient | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.nango = nango_client or NangoClient(settings=self.settings)
        self.provider_config_key = self.settings.nango_integration_id_hubspot

    def _get_identity(self, connection_id: str) -> NangoConnectionIdentity:
        """Construct Nango connection identity tuple."""
        return NangoConnectionIdentity(
            connection_id=connection_id,
            integration_id=self.provider_config_key,
        )

    def _assert_read_only(self, action: str) -> None:
        """Enforce strict read-only constraint."""
        if not self.settings.hubspot_read_only:
            logger.warning(
                "HubSpot read-only flag is disabled, but write operations remain prohibited."
            )
        raise CRMReadOnlyError(
            f"Operation '{action}' prohibited: Outmate GTM CRM access is strictly read-only."
        )

    # --------------------------------------------------------------------------
    # Companies API
    # --------------------------------------------------------------------------
    async def search_companies(
        self,
        connection_id: str,
        *,
        query: str | None = None,
        domain: str | None = None,
        limit: int = 10,
    ) -> list[CRMCompany]:
        """Search or list companies from HubSpot CRM."""
        identity = self._get_identity(connection_id)
        props = ",".join(HUBSPOT_COMPANY_PROPERTIES)

        try:
            # If search filter is requested, use HubSpot CRM v3 search endpoint
            if domain or query:
                search_payload: dict[str, Any] = {
                    "properties": HUBSPOT_COMPANY_PROPERTIES,
                    "limit": min(limit, 100),
                }
                filters: list[dict[str, Any]] = []
                if domain:
                    filters.append(
                        {
                            "propertyName": "domain",
                            "operator": "EQ",
                            "value": domain.lower().strip(),
                        }
                    )
                elif query:
                    filters.append(
                        {
                            "propertyName": "name",
                            "operator": "CONTAINS_TOKEN",
                            "value": query.strip(),
                        }
                    )
                search_payload["filterGroups"] = [{"filters": filters}]

                data = await self.nango.proxy_request(
                    identity=identity,
                    endpoint="/crm/v3/objects/companies/search",
                    method="POST",
                    json_data=search_payload,
                )
            else:
                data = await self.nango.proxy_request(
                    identity=identity,
                    endpoint="/crm/v3/objects/companies",
                    method="GET",
                    params={"properties": props, "limit": min(limit, 100)},
                )

            results = data.get("results", [])
            return [normalize_company(item, connection_id) for item in results]
        except NangoConnectionNotFoundError:
            return []

    async def get_company(self, connection_id: str, company_id: str) -> CRMCompany | None:
        """Retrieve a specific company by provider ID."""
        identity = self._get_identity(connection_id)
        props = ",".join(HUBSPOT_COMPANY_PROPERTIES)

        try:
            data = await self.nango.proxy_request(
                identity=identity,
                endpoint=f"/crm/v3/objects/companies/{company_id}",
                method="GET",
                params={"properties": props},
            )
            return normalize_company(data, connection_id)
        except NangoConnectionNotFoundError:
            return None

    # --------------------------------------------------------------------------
    # Contacts API
    # --------------------------------------------------------------------------
    async def search_contacts(
        self,
        connection_id: str,
        *,
        query: str | None = None,
        email: str | None = None,
        company_id: str | None = None,
        limit: int = 20,
    ) -> list[CRMContact]:
        """Search or list contacts from HubSpot CRM."""
        identity = self._get_identity(connection_id)
        props = ",".join(HUBSPOT_CONTACT_PROPERTIES)

        try:
            if email or query or company_id:
                search_payload: dict[str, Any] = {
                    "properties": HUBSPOT_CONTACT_PROPERTIES,
                    "limit": min(limit, 100),
                }
                filters: list[dict[str, Any]] = []
                if email:
                    filters.append(
                        {
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": email.lower().strip(),
                        }
                    )
                elif company_id:
                    filters.append(
                        {
                            "propertyName": "associatedcompanyid",
                            "operator": "EQ",
                            "value": str(company_id),
                        }
                    )
                elif query:
                    filters.append(
                        {
                            "propertyName": "lastname",
                            "operator": "CONTAINS_TOKEN",
                            "value": query.strip(),
                        }
                    )
                search_payload["filterGroups"] = [{"filters": filters}]

                data = await self.nango.proxy_request(
                    identity=identity,
                    endpoint="/crm/v3/objects/contacts/search",
                    method="POST",
                    json_data=search_payload,
                )
            else:
                data = await self.nango.proxy_request(
                    identity=identity,
                    endpoint="/crm/v3/objects/contacts",
                    method="GET",
                    params={"properties": props, "limit": min(limit, 100)},
                )

            results = data.get("results", [])
            return [normalize_contact(item, connection_id) for item in results]
        except NangoConnectionNotFoundError:
            return []

    async def get_contact(self, connection_id: str, contact_id: str) -> CRMContact | None:
        """Retrieve a specific contact by provider ID."""
        identity = self._get_identity(connection_id)
        props = ",".join(HUBSPOT_CONTACT_PROPERTIES)

        try:
            data = await self.nango.proxy_request(
                identity=identity,
                endpoint=f"/crm/v3/objects/contacts/{contact_id}",
                method="GET",
                params={"properties": props},
            )
            return normalize_contact(data, connection_id)
        except NangoConnectionNotFoundError:
            return None

    # --------------------------------------------------------------------------
    # Deals API
    # --------------------------------------------------------------------------
    async def search_deals(
        self,
        connection_id: str,
        *,
        company_id: str | None = None,
        limit: int = 20,
    ) -> list[CRMDeal]:
        """Search or list deals from HubSpot CRM."""
        identity = self._get_identity(connection_id)
        props = ",".join(HUBSPOT_DEAL_PROPERTIES)

        try:
            data = await self.nango.proxy_request(
                identity=identity,
                endpoint="/crm/v3/objects/deals",
                method="GET",
                params={
                    "properties": props,
                    "limit": min(limit, 100),
                    "associations": "companies,contacts",
                },
            )
            results = data.get("results", [])
            deals = [normalize_deal(item, connection_id) for item in results]

            if company_id:
                deals = [d for d in deals if str(company_id) in d.associated_company_ids]

            return deals
        except NangoConnectionNotFoundError:
            return []

    async def get_deal(self, connection_id: str, deal_id: str) -> CRMDeal | None:
        """Retrieve a specific deal by provider ID."""
        identity = self._get_identity(connection_id)
        props = ",".join(HUBSPOT_DEAL_PROPERTIES)

        try:
            data = await self.nango.proxy_request(
                identity=identity,
                endpoint=f"/crm/v3/objects/deals/{deal_id}",
                method="GET",
                params={"properties": props, "associations": "companies,contacts"},
            )
            return normalize_deal(data, connection_id)
        except NangoConnectionNotFoundError:
            return None

    # --------------------------------------------------------------------------
    # Associations API
    # --------------------------------------------------------------------------
    async def get_company_associations(
        self, connection_id: str, company_id: str, to_object_type: str = "contacts"
    ) -> list[str]:
        """Retrieve IDs of associated records (e.g. contacts or deals) for a company."""
        identity = self._get_identity(connection_id)
        try:
            data = await self.nango.proxy_request(
                identity=identity,
                endpoint=f"/crm/v3/objects/companies/{company_id}/associations/{to_object_type}",
                method="GET",
            )
            results = data.get("results", [])
            return [str(item.get("id")) for item in results if item.get("id")]
        except NangoConnectionNotFoundError:
            return []

    # --------------------------------------------------------------------------
    # Aggregated CRM Intelligence Context
    # --------------------------------------------------------------------------
    async def get_company_crm_context(
        self,
        connection_id: str,
        *,
        company_id: str | None = None,
        company_domain: str | None = None,
        company_name: str | None = None,
    ) -> CRMContextSummary:
        """Retrieve aggregated CRM intelligence for a company."""
        matched_company: CRMCompany | None = None

        if company_id:
            matched_company = await self.get_company(connection_id, company_id)
        elif company_domain:
            companies = await self.search_companies(connection_id, domain=company_domain, limit=1)
            if companies:
                matched_company = companies[0]
        elif company_name:
            companies = await self.search_companies(connection_id, query=company_name, limit=1)
            if companies:
                matched_company = companies[0]

        if not matched_company:
            return CRMContextSummary(
                company=None,
                contacts=[],
                deals=[],
                total_deal_amount=0.0,
                open_deals_count=0,
                connection_id=connection_id,
            )

        cid = matched_company.provider_id

        # Fetch associated contacts
        associated_contact_ids = await self.get_company_associations(
            connection_id, cid, to_object_type="contacts"
        )
        contacts: list[CRMContact] = []
        for ct_id in associated_contact_ids[:10]:
            ct = await self.get_contact(connection_id, ct_id)
            if ct:
                contacts.append(ct)

        # If association endpoint returned none, try contact search by associatedcompanyid
        if not contacts:
            contacts = await self.search_contacts(connection_id, company_id=cid, limit=10)

        # Fetch associated deals
        associated_deal_ids = await self.get_company_associations(
            connection_id, cid, to_object_type="deals"
        )
        deals: list[CRMDeal] = []
        for dl_id in associated_deal_ids[:10]:
            dl = await self.get_deal(connection_id, dl_id)
            if dl:
                deals.append(dl)

        if not deals:
            deals = await self.search_deals(connection_id, company_id=cid, limit=10)

        total_amount = sum(d.amount or 0.0 for d in deals)
        open_deals = [d for d in deals if "closed" not in d.stage.lower()]

        return CRMContextSummary(
            company=matched_company,
            contacts=contacts,
            deals=deals,
            total_deal_amount=total_amount,
            open_deals_count=len(open_deals),
            connection_id=connection_id,
        )
