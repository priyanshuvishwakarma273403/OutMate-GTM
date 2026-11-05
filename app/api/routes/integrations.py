"""FastAPI endpoints for managing Nango third-party OAuth integrations and Connect Sessions."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.config import AppSettings, get_settings
from app.core.exceptions import ConfigurationError, OutmateError
from app.core.logging import get_logger
from app.services.crm_service import CRMService, get_crm_service

logger = get_logger("api.routes.integrations")

router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations & OAuth"])


class ConnectSessionRequestBody(BaseModel):
    """Payload to initiate a new Nango Connect Session."""

    user_id: str = Field(default="default_user", description="Authenticated user ID")
    organization_id: str | None = Field(
        default=None, description="Optional tenant organization ID for isolation"
    )


class ConnectionVerifyBody(BaseModel):
    """Payload to trigger server-side verification of an integration connection."""

    connection_id: str = Field(..., description="Nango connection ID to verify")


class ConnectionDisconnectBody(BaseModel):
    """Payload to disconnect and revoke an active integration connection."""

    connection_id: str = Field(..., description="Nango connection ID to disconnect")


@router.post(
    "/hubspot/connect-session",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Create a Nango Connect Session for HubSpot OAuth",
    description="Generates an ephemeral Connect Session token to mount the official Nango Connect UI.",
)
async def create_hubspot_connect_session(
    body: ConnectSessionRequestBody = ConnectSessionRequestBody(),
    crm_service: CRMService = Depends(get_crm_service),
) -> dict[str, Any]:
    """Create Nango Connect Session token."""
    try:
        session = await crm_service.initiate_connect_session(
            user_id=body.user_id,
            organization_id=body.organization_id,
            integration_id="hubspot",
        )
        return {
            "success": True,
            "data": session.model_dump(),
        }
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"HubSpot integration unconfigured: {exc.message}",
        ) from exc
    except OutmateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc


@router.get(
    "",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="List available integrations and their connection states",
)
async def list_integrations(
    organization_id: str | None = Query(default=None, description="Filter by organization ID"),
    crm_service: CRMService = Depends(get_crm_service),
    settings: AppSettings = Depends(get_settings),
) -> dict[str, Any]:
    """List supported integrations and current tenant connection status."""
    connections = crm_service.list_connections(organization_id=organization_id)
    hubspot_connected = any(
        c.provider == "hubspot" and c.status == "connected" for c in connections
    )

    integrations_summary = [
        {
            "id": "hubspot",
            "name": "HubSpot CRM",
            "type": "crm",
            "read_only": settings.hubspot_read_only,
            "configured": bool(settings.nango_secret_key),
            "connected": hubspot_connected,
            "active_connections_count": len(
                [c for c in connections if c.provider == "hubspot" and c.status == "connected"]
            ),
        }
    ]

    return {
        "success": True,
        "data": {
            "integrations": integrations_summary,
            "connections": [c.model_dump() for c in connections],
        },
    }


@router.get(
    "/hubspot/status",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get HubSpot connection status",
)
async def get_hubspot_connection_status(
    connection_id: str | None = Query(
        default=None, description="Explicit connection ID to inspect"
    ),
    organization_id: str | None = Query(default=None, description="Tenant organization ID"),
    user_id: str | None = Query(default=None, description="Tenant user ID"),
    crm_service: CRMService = Depends(get_crm_service),
) -> dict[str, Any]:
    """Inspect verified connection status with Nango."""
    try:
        resolved_cid = connection_id or crm_service.resolve_connection_id(
            {"organization_id": organization_id, "user_id": user_id}
        )
        status_info = await crm_service.get_connection_status(resolved_cid, provider="hubspot")
        return {
            "success": True,
            "data": status_info.model_dump(),
        }
    except OutmateError as exc:
        return {
            "success": True,
            "data": {
                "connection_id": connection_id or "unconfigured",
                "integration_id": "hubspot",
                "connected": False,
                "status": "not_connected",
                "provider": "hubspot",
                "details": exc.message,
            },
        }


@router.post(
    "/hubspot/verify",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Verify HubSpot connection after Connect UI completion",
)
async def verify_hubspot_connection(
    body: ConnectionVerifyBody,
    crm_service: CRMService = Depends(get_crm_service),
) -> dict[str, Any]:
    """Verify newly authorized OAuth connection."""
    try:
        status_info = await crm_service.verify_connection(
            connection_id=body.connection_id, provider="hubspot"
        )
        return {
            "success": True,
            "data": status_info.model_dump(),
        }
    except OutmateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc


@router.post(
    "/hubspot/disconnect",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Disconnect and revoke HubSpot CRM connection",
)
async def disconnect_hubspot(
    body: ConnectionDisconnectBody,
    crm_service: CRMService = Depends(get_crm_service),
) -> dict[str, Any]:
    """Revoke integration connection."""
    try:
        success = await crm_service.disconnect(body.connection_id, provider="hubspot")
        return {
            "success": success,
            "message": "HubSpot integration connection revoked successfully",
            "connection_id": body.connection_id,
        }
    except OutmateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
