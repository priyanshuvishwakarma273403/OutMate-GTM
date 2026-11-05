"""Pydantic schemas for Nango Connect Sessions, connections, and proxy responses."""

from typing import Any

from pydantic import BaseModel, Field


class NangoConnectSession(BaseModel):
    """Ephemeral session token returned by Nango Connect Sessions API."""

    token: str = Field(..., description="Ephemeral session token for Nango Connect UI frontend SDK")
    expires_at: str | None = Field(default=None, description="ISO timestamp when the token expires")
    connect_url: str | None = Field(
        default=None, description="Optional direct hosted authorization URL"
    )


class NangoConnection(BaseModel):
    """Metadata representing an authenticated integration connection in Nango."""

    connection_id: str = Field(..., description="Unique tenant or user identifier in Nango")
    provider_config_key: str = Field(
        ..., description="Identifier for integration provider (e.g. 'hubspot')"
    )
    created: str | None = Field(
        default=None, description="ISO timestamp when connection was created"
    )
    updated: str | None = Field(
        default=None, description="ISO timestamp when connection was last updated"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata stored alongside connection"
    )


class NangoConnectionStatus(BaseModel):
    """Verified status of an external OAuth connection."""

    connection_id: str = Field(..., description="Unique tenant or user identifier")
    integration_id: str = Field(..., description="Target integration provider key")
    connected: bool = Field(
        ..., description="Whether connection is currently active and authorized"
    )
    status: str = Field(
        ..., description="Status string: 'connected', 'not_found', 'expired', 'error'"
    )
    provider: str = Field(..., description="Target integration provider name")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Provider connection metadata"
    )
    details: str | None = Field(default=None, description="Human-readable diagnostics or reason")


class CreateConnectSessionRequest(BaseModel):
    """Request payload to initiate a Nango Connect Session."""

    user_id: str = Field(..., description="Authenticated user initiating the connection")
    organization_id: str | None = Field(
        default=None, description="Optional organization identifier for multi-tenant isolation"
    )
    integration_id: str = Field(
        default="hubspot", description="Target integration provider key (default: hubspot)"
    )


class ConnectSessionResponse(BaseModel):
    """API response providing the Connect Session token and connection metadata."""

    token: str = Field(..., description="Nango Connect UI token")
    connection_id: str = Field(..., description="Resolved tenant connection identifier")
    integration_id: str = Field(..., description="Integration identifier")
    expires_at: str | None = Field(default=None, description="Token expiration timestamp")
