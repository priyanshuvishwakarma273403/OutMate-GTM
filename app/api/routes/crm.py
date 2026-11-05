"""FastAPI endpoints for read-only CRM data access (companies, contacts, deals, contexts)."""

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.core.exceptions import OutmateError
from app.core.logging import get_logger
from app.services.crm_service import CRMService, get_crm_service

logger = get_logger("api.routes.crm")

router = APIRouter(prefix="/api/v1/crm", tags=["CRM Data (Read-Only)"])


def get_tenant_context(
    x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
    connection_id: str | None = Query(default=None, description="Explicit connection ID override"),
) -> dict[str, Any]:
    """Extract tenant isolation context from HTTP headers and query params."""
    return {
        "organization_id": x_organization_id,
        "user_id": x_user_id,
        "connection_id": connection_id or x_connection_id,
    }


# ------------------------------------------------------------------------------
# CRM Companies
# ------------------------------------------------------------------------------
@router.get(
    "/companies",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Search or list CRM companies",
)
async def search_crm_companies(
    query: str | None = Query(default=None, description="Company name query"),
    domain: str | None = Query(default=None, description="Domain filter (e.g. vercel.com)"),
    limit: int = Query(default=10, ge=1, le=100, description="Max results"),
    tenant_context: dict[str, Any] = Depends(get_tenant_context),
    crm_service: CRMService = Depends(get_crm_service),
) -> dict[str, Any]:
    """Search companies in connected CRM."""
    try:
        companies = await crm_service.search_companies(
            tenant_context=tenant_context,
            query=query,
            domain=domain,
            limit=limit,
        )
        return {
            "success": True,
            "data": [c.model_dump() for c in companies],
            "total": len(companies),
        }
    except OutmateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


@router.get(
    "/companies/{company_id}",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get a CRM company by provider ID",
)
async def get_crm_company(
    company_id: str,
    tenant_context: dict[str, Any] = Depends(get_tenant_context),
    crm_service: CRMService = Depends(get_crm_service),
) -> dict[str, Any]:
    """Retrieve specific company record."""
    try:
        company = await crm_service.get_company(
            company_id=company_id, tenant_context=tenant_context
        )
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID '{company_id}' not found in CRM",
            )
        return {"success": True, "data": company.model_dump()}
    except OutmateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


# ------------------------------------------------------------------------------
# CRM Contacts
# ------------------------------------------------------------------------------
@router.get(
    "/contacts",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Search or list CRM contacts",
)
async def search_crm_contacts(
    query: str | None = Query(default=None, description="Contact name query"),
    email: str | None = Query(default=None, description="Exact contact email"),
    company_id: str | None = Query(default=None, description="Associated company provider ID"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
    tenant_context: dict[str, Any] = Depends(get_tenant_context),
    crm_service: CRMService = Depends(get_crm_service),
) -> dict[str, Any]:
    """Search contacts in connected CRM."""
    try:
        contacts = await crm_service.search_contacts(
            tenant_context=tenant_context,
            query=query,
            email=email,
            company_id=company_id,
            limit=limit,
        )
        return {
            "success": True,
            "data": [c.model_dump() for c in contacts],
            "total": len(contacts),
        }
    except OutmateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


@router.get(
    "/contacts/{contact_id}",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get a CRM contact by provider ID",
)
async def get_crm_contact(
    contact_id: str,
    tenant_context: dict[str, Any] = Depends(get_tenant_context),
    crm_service: CRMService = Depends(get_crm_service),
) -> dict[str, Any]:
    """Retrieve specific contact record."""
    try:
        contact = await crm_service.get_contact(
            contact_id=contact_id, tenant_context=tenant_context
        )
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contact with ID '{contact_id}' not found in CRM",
            )
        return {"success": True, "data": contact.model_dump()}
    except OutmateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


# ------------------------------------------------------------------------------
# CRM Deals
# ------------------------------------------------------------------------------
@router.get(
    "/deals",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Search or list CRM deals / opportunities",
)
async def search_crm_deals(
    company_id: str | None = Query(default=None, description="Associated company ID"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
    tenant_context: dict[str, Any] = Depends(get_tenant_context),
    crm_service: CRMService = Depends(get_crm_service),
) -> dict[str, Any]:
    """Search deals in connected CRM."""
    try:
        deals = await crm_service.search_deals(
            tenant_context=tenant_context,
            company_id=company_id,
            limit=limit,
        )
        return {
            "success": True,
            "data": [d.model_dump() for d in deals],
            "total": len(deals),
        }
    except OutmateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


@router.get(
    "/deals/{deal_id}",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get a CRM deal by provider ID",
)
async def get_crm_deal(
    deal_id: str,
    tenant_context: dict[str, Any] = Depends(get_tenant_context),
    crm_service: CRMService = Depends(get_crm_service),
) -> dict[str, Any]:
    """Retrieve specific deal record."""
    try:
        deal = await crm_service.get_deal(deal_id=deal_id, tenant_context=tenant_context)
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deal with ID '{deal_id}' not found in CRM",
            )
        return {"success": True, "data": deal.model_dump()}
    except OutmateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


# ------------------------------------------------------------------------------
# Company CRM Intelligence Context
# ------------------------------------------------------------------------------
@router.get(
    "/companies/{company_id}/context",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get aggregated CRM intelligence context for a company",
)
async def get_company_crm_context(
    company_id: str,
    tenant_context: dict[str, Any] = Depends(get_tenant_context),
    crm_service: CRMService = Depends(get_crm_service),
) -> dict[str, Any]:
    """Get aggregated CRM context (company + associated contacts + deals)."""
    try:
        context_summary = await crm_service.get_company_crm_context(
            tenant_context=tenant_context,
            company_id=company_id,
        )
        return {"success": True, "data": context_summary.model_dump()}
    except OutmateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
