"""Connection metadata storage tracking integration states without storing OAuth tokens.

SECURITY DIRECTIVE:
OAuth credentials, access tokens, and refresh tokens are strictly managed by Nango.
This storage service strictly persists non-sensitive tenant connection identifiers,
timestamps, status flags, and provider metadata.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    """Return timezone-aware current UTC datetime formatted as ISO 8601 string."""
    return datetime.now(UTC).isoformat()


class ConnectionRecord(BaseModel):
    """Metadata record for a tenant integration connection."""

    connection_id: str = Field(..., description="Unique Nango connection identifier")
    organization_id: str | None = Field(default=None, description="Owning organization ID")
    user_id: str = Field(..., description="User ID who created or owns the connection")
    provider: str = Field(default="hubspot", description="Third-party service provider")
    status: str = Field(
        default="pending", description="Status: pending, connected, expired, disconnected"
    )
    created_at: str = Field(default_factory=utc_now_iso, description="Record creation timestamp")
    last_verified_at: str | None = Field(
        default=None, description="Last successful verification timestamp"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Safe public metadata from provider"
    )


class CRMStorageService:
    """In-memory connection registry ensuring safe persistence of connection states."""

    def __init__(self) -> None:
        self._connections: dict[str, ConnectionRecord] = {}

    def save_connection(self, record: ConnectionRecord) -> None:
        """Store or update a connection record."""
        self._connections[record.connection_id] = record

    def get_connection(self, connection_id: str) -> ConnectionRecord | None:
        """Fetch connection record by ID."""
        return self._connections.get(connection_id)

    def get_tenant_connection(
        self,
        organization_id: str | None = None,
        user_id: str | None = None,
        provider: str = "hubspot",
    ) -> ConnectionRecord | None:
        """Find active connection matching organization or user identity."""
        for rec in self._connections.values():
            if rec.provider != provider:
                continue
            if organization_id and rec.organization_id == organization_id:
                return rec
            if user_id and rec.user_id == user_id:
                return rec
        return None

    def list_connections(self, organization_id: str | None = None) -> list[ConnectionRecord]:
        """List connections, optionally filtered by organization."""
        if organization_id:
            return [c for c in self._connections.values() if c.organization_id == organization_id]
        return list(self._connections.values())

    def delete_connection(self, connection_id: str) -> bool:
        """Remove connection record from registry."""
        if connection_id in self._connections:
            del self._connections[connection_id]
            return True
        return False

    def update_status(
        self,
        connection_id: str,
        status: str,
        verified_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update connection lifecycle status."""
        rec = self._connections.get(connection_id)
        if rec:
            rec.status = status
            if verified_at:
                rec.last_verified_at = verified_at
            if metadata:
                rec.metadata.update(metadata)


# Global singleton storage instance
_global_crm_storage: CRMStorageService | None = None


def get_crm_storage() -> CRMStorageService:
    """Retrieve global CRM storage singleton."""
    global _global_crm_storage
    if _global_crm_storage is None:
        _global_crm_storage = CRMStorageService()
    return _global_crm_storage
