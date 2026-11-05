"""Application CRM service coordinating tenant isolation, HubSpot data access, and research corroboration."""

from typing import Any

from app.core.config import AppSettings, get_settings
from app.core.exceptions import AuthorizationError
from app.core.logging import get_logger
from app.domain.models.crm import CRMCompany, CRMContact, CRMContextSummary, CRMDeal, utc_now_iso
from app.domain.models.evidence import EvidenceRecord, EvidenceSourceType, VerificationStatus
from app.integrations.nango.client import NangoClient
from app.integrations.nango.config import NangoConnectionIdentity
from app.integrations.nango.errors import NangoConnectionNotFoundError
from app.integrations.nango.schemas import ConnectSessionResponse, NangoConnectionStatus
from app.integrations.providers.hubspot.adapter import HubSpotAdapter
from app.services.crm_storage import ConnectionRecord, CRMStorageService, get_crm_storage

logger = get_logger("services.crm")


class CRMService:
    """Enterprise CRM service providing secure, tenant-isolated CRM intelligence access."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        nango_client: NangoClient | None = None,
        hubspot_adapter: HubSpotAdapter | None = None,
        storage: CRMStorageService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.nango = nango_client or NangoClient(settings=self.settings)
        self.hubspot = hubspot_adapter or HubSpotAdapter(
            nango_client=self.nango, settings=self.settings
        )
        self.storage = storage or get_crm_storage()

    # --------------------------------------------------------------------------
    # Tenant Resolution & Ownership Validation
    # --------------------------------------------------------------------------
    def resolve_connection_id(self, tenant_context: dict[str, Any] | None = None) -> str:
        """Resolve the active Nango connection_id for the current tenant context.

        Raises:
            NangoConnectionNotFoundError if no active connection exists for the tenant.
        """
        ctx = tenant_context or {}
        explicit_cid = ctx.get("connection_id")
        if explicit_cid:
            return str(explicit_cid)

        org_id = ctx.get("organization_id") or ctx.get("tenant_id")
        user_id = ctx.get("user_id")

        # Check storage for established tenant connection
        record = self.storage.get_tenant_connection(
            organization_id=org_id,
            user_id=user_id,
            provider=self.settings.nango_integration_id_hubspot,
        )
        if record and record.status in ("connected", "pending"):
            return record.connection_id

        # Fallback to configured default connection ID in single-tenant / local development mode
        if self.settings.nango_connection_id:
            return self.settings.nango_connection_id

        if org_id:
            return f"org_{org_id}"
        if user_id:
            return f"usr_{user_id}"

        raise NangoConnectionNotFoundError(
            "No CRM connection configured or found for current tenant context",
            details={"context": ctx},
        )

    def validate_tenant_ownership(
        self, connection_id: str, tenant_context: dict[str, Any] | None = None
    ) -> None:
        """Ensure the requesting tenant owns the target connection_id."""
        if not tenant_context:
            return

        expected_org = tenant_context.get("organization_id") or tenant_context.get("tenant_id")
        expected_user = tenant_context.get("user_id")

        record = self.storage.get_connection(connection_id)
        if record:
            if expected_org and record.organization_id and record.organization_id != expected_org:
                raise AuthorizationError(
                    f"Cross-tenant access violation: tenant {expected_org} does not own connection {connection_id}"
                )
            if (
                expected_user
                and record.user_id
                and record.user_id != expected_user
                and not expected_org
            ):
                raise AuthorizationError(
                    f"User {expected_user} does not have authorization to access connection {connection_id}"
                )

    def _log_audit(
        self, action: str, connection_id: str, object_type: str, status: str = "success"
    ) -> None:
        """Structured security audit log for CRM data access."""
        logger.info(
            "[CRM-AUDIT] action=%s connection_id=%s object_type=%s status=%s",
            action,
            connection_id,
            object_type,
            status,
        )

    # --------------------------------------------------------------------------
    # OAuth Connection Lifecycle
    # --------------------------------------------------------------------------
    async def initiate_connect_session(
        self,
        user_id: str,
        organization_id: str | None = None,
        integration_id: str = "hubspot",
    ) -> ConnectSessionResponse:
        """Initiate OAuth flow by generating a secure Nango Connect Session token."""
        self.settings.validate_hubspot_integration()
        if organization_id:
            connection_id = (
                organization_id if organization_id.startswith("org_") else f"org_{organization_id}"
            )
        else:
            connection_id = user_id if user_id.startswith("usr_") else f"usr_{user_id}"

        session = await self.nango.create_connect_session(
            connection_id=connection_id,
            integration_id=integration_id,
            user_id=user_id,
            organization_id=organization_id,
        )

        # Store pending record in connection registry
        self.storage.save_connection(
            ConnectionRecord(
                connection_id=connection_id,
                organization_id=organization_id,
                user_id=user_id,
                provider=integration_id,
                status="pending",
            )
        )
        self._log_audit("connect_session_created", connection_id, "session")

        return ConnectSessionResponse(
            token=session.token,
            connection_id=connection_id,
            integration_id=integration_id,
            expires_at=session.expires_at,
        )

    async def verify_connection(
        self, connection_id: str, provider: str = "hubspot"
    ) -> NangoConnectionStatus:
        """Verify server-side with Nango that an OAuth connection is authorized and healthy."""
        identity = NangoConnectionIdentity(connection_id=connection_id, integration_id=provider)
        status = await self.nango.get_connection_status(identity)

        if status.connected:
            existing = self.storage.get_connection(connection_id)
            if existing:
                self.storage.update_status(
                    connection_id=connection_id,
                    status="connected",
                    verified_at=utc_now_iso(),
                    metadata=status.metadata,
                )
            else:
                self.storage.save_connection(
                    ConnectionRecord(
                        connection_id=connection_id,
                        user_id="system",
                        provider=provider,
                        status="connected",
                        last_verified_at=utc_now_iso(),
                        metadata=status.metadata,
                    )
                )
            self._log_audit("connection_verified", connection_id, "connection", status="connected")
        else:
            existing = self.storage.get_connection(connection_id)
            if existing:
                self.storage.update_status(
                    connection_id=connection_id,
                    status=status.status,
                )
            else:
                self.storage.save_connection(
                    ConnectionRecord(
                        connection_id=connection_id,
                        user_id="system",
                        provider=provider,
                        status=status.status,
                    )
                )
            self._log_audit(
                "connection_verify_failed", connection_id, "connection", status=status.status
            )

        return status

    async def disconnect(self, connection_id: str, provider: str = "hubspot") -> bool:
        """Revoke and delete OAuth connection in Nango and local registry."""
        success = await self.nango.delete_connection(
            connection_id=connection_id, provider_config_key=provider
        )
        self.storage.update_status(connection_id=connection_id, status="disconnected")
        self._log_audit("connection_disconnected", connection_id, "connection")
        return success

    async def get_connection_status(
        self, connection_id: str, provider: str = "hubspot"
    ) -> NangoConnectionStatus:
        """Check live connection status."""
        identity = NangoConnectionIdentity(connection_id=connection_id, integration_id=provider)
        return await self.nango.get_connection_status(identity)

    def list_connections(self, organization_id: str | None = None) -> list[ConnectionRecord]:
        """List active connections recorded for this tenant."""
        return self.storage.list_connections(organization_id=organization_id)

    # --------------------------------------------------------------------------
    # CRM Data Queries (Strictly Read-Only)
    # --------------------------------------------------------------------------
    async def search_companies(
        self,
        tenant_context: dict[str, Any] | None = None,
        *,
        query: str | None = None,
        domain: str | None = None,
        limit: int = 10,
    ) -> list[CRMCompany]:
        """Search companies within caller's tenant CRM."""
        cid = self.resolve_connection_id(tenant_context)
        self.validate_tenant_ownership(cid, tenant_context)
        self._log_audit("search_companies", cid, "company")
        return await self.hubspot.search_companies(
            connection_id=cid, query=query, domain=domain, limit=limit
        )

    async def get_company(
        self,
        company_id: str,
        tenant_context: dict[str, Any] | None = None,
    ) -> CRMCompany | None:
        """Fetch a specific company by provider ID."""
        cid = self.resolve_connection_id(tenant_context)
        self.validate_tenant_ownership(cid, tenant_context)
        self._log_audit("get_company", cid, "company")
        return await self.hubspot.get_company(connection_id=cid, company_id=company_id)

    async def search_contacts(
        self,
        tenant_context: dict[str, Any] | None = None,
        *,
        query: str | None = None,
        email: str | None = None,
        company_id: str | None = None,
        limit: int = 20,
    ) -> list[CRMContact]:
        """Search contacts within caller's tenant CRM."""
        cid = self.resolve_connection_id(tenant_context)
        self.validate_tenant_ownership(cid, tenant_context)
        self._log_audit("search_contacts", cid, "contact")
        return await self.hubspot.search_contacts(
            connection_id=cid, query=query, email=email, company_id=company_id, limit=limit
        )

    async def get_contact(
        self,
        contact_id: str,
        tenant_context: dict[str, Any] | None = None,
    ) -> CRMContact | None:
        """Fetch a specific contact by provider ID."""
        cid = self.resolve_connection_id(tenant_context)
        self.validate_tenant_ownership(cid, tenant_context)
        self._log_audit("get_contact", cid, "contact")
        return await self.hubspot.get_contact(connection_id=cid, contact_id=contact_id)

    async def search_deals(
        self,
        tenant_context: dict[str, Any] | None = None,
        *,
        company_id: str | None = None,
        limit: int = 20,
    ) -> list[CRMDeal]:
        """Search deals within caller's tenant CRM."""
        cid = self.resolve_connection_id(tenant_context)
        self.validate_tenant_ownership(cid, tenant_context)
        self._log_audit("search_deals", cid, "deal")
        return await self.hubspot.search_deals(
            connection_id=cid, company_id=company_id, limit=limit
        )

    async def get_deal(
        self,
        deal_id: str,
        tenant_context: dict[str, Any] | None = None,
    ) -> CRMDeal | None:
        """Fetch a specific deal by provider ID."""
        cid = self.resolve_connection_id(tenant_context)
        self.validate_tenant_ownership(cid, tenant_context)
        self._log_audit("get_deal", cid, "deal")
        return await self.hubspot.get_deal(connection_id=cid, deal_id=deal_id)

    async def get_company_crm_context(
        self,
        tenant_context: dict[str, Any] | None = None,
        *,
        company_id: str | None = None,
        domain: str | None = None,
        name: str | None = None,
    ) -> CRMContextSummary:
        """Retrieve full aggregated CRM context for a company."""
        cid = self.resolve_connection_id(tenant_context)
        self.validate_tenant_ownership(cid, tenant_context)
        self._log_audit("get_company_crm_context", cid, "context")
        return await self.hubspot.get_company_crm_context(
            connection_id=cid,
            company_id=company_id,
            company_domain=domain,
            company_name=name,
        )

    # --------------------------------------------------------------------------
    # Research Corroboration with CRM Data
    # --------------------------------------------------------------------------
    async def corroborate_research_with_crm(
        self,
        company_name: str,
        domain: str | None = None,
        tenant_context: dict[str, Any] | None = None,
    ) -> list[EvidenceRecord]:
        """Cross-reference public company research with internal CRM records to generate evidence."""
        try:
            summary = await self.get_company_crm_context(
                tenant_context=tenant_context,
                domain=domain,
                name=company_name,
            )
        except Exception as exc:
            logger.info("CRM corroboration skipped (no active connection or query failed: %s)", exc)
            return []

        if not summary.company:
            return []

        comp = summary.company
        evidence: list[EvidenceRecord] = []

        # Corroborate company identity and domain
        evidence.append(
            EvidenceRecord(
                source_url=f"hubspot://company/{comp.provider_id}",
                source_type=EvidenceSourceType.HUBSPOT_CRM,
                title=f"HubSpot CRM Account: {comp.name}",
                claim_type="identity",
                claim=f"Internal CRM account matches company name '{comp.name}' (domain: {comp.domain})",
                snippet=(
                    f"Found internal CRM company '{comp.name}' with domain '{comp.domain}' and "
                    f"industry '{comp.industry or 'N/A'}'. Recorded annual revenue: ${comp.annual_revenue or 0:,.2f}."
                ),
                confidence=0.95,
                verification_status=VerificationStatus.VERIFIED,
                metadata={
                    "provider": "hubspot",
                    "provider_id": comp.provider_id,
                    "connection_id": comp.connection_id,
                    "annual_revenue": comp.annual_revenue,
                    "number_of_employees": comp.number_of_employees,
                },
            )
        )

        # Corroborate recorded contacts / decision-makers
        for contact in summary.contacts:
            evidence.append(
                EvidenceRecord(
                    source_url=f"hubspot://contact/{contact.provider_id}",
                    source_type=EvidenceSourceType.HUBSPOT_CRM,
                    title=f"HubSpot CRM Contact: {contact.full_name}",
                    claim_type="employment",
                    claim=f"Contact {contact.full_name} is listed in CRM as {contact.job_title or 'Employee'}",
                    snippet=(
                        f"Contact {contact.full_name} ({contact.email or 'no email'}) holds role "
                        f"'{contact.job_title or 'N/A'}' under department '{contact.department or 'N/A'}'."
                    ),
                    confidence=0.90,
                    verification_status=VerificationStatus.VERIFIED,
                    metadata={
                        "provider": "hubspot",
                        "provider_id": contact.provider_id,
                        "email": contact.email,
                        "job_title": contact.job_title,
                    },
                )
            )

        return evidence


# Global singleton service instance
_global_crm_service: CRMService | None = None


def get_crm_service() -> CRMService:
    """Retrieve global CRMService singleton."""
    global _global_crm_service
    if _global_crm_service is None:
        _global_crm_service = CRMService()
    return _global_crm_service
