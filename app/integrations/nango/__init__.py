"""Nango integration boundary for OAuth connection management and proxy requests."""

from app.integrations.nango.client import NangoClient
from app.integrations.nango.config import NangoConfig, NangoConnectionIdentity
from app.integrations.nango.errors import (
    CRMReadOnlyError,
    NangoAuthError,
    NangoConnectionNotFoundError,
    NangoError,
    NangoExpiredConnectionError,
    NangoProxyError,
    NangoRateLimitError,
)
from app.integrations.nango.schemas import (
    ConnectSessionResponse,
    CreateConnectSessionRequest,
    NangoConnection,
    NangoConnectionStatus,
    NangoConnectSession,
)

__all__ = [
    "CRMReadOnlyError",
    "ConnectSessionResponse",
    "CreateConnectSessionRequest",
    "NangoAuthError",
    "NangoClient",
    "NangoConfig",
    "NangoConnection",
    "NangoConnectionIdentity",
    "NangoConnectionNotFoundError",
    "NangoConnectionStatus",
    "NangoConnectSession",
    "NangoError",
    "NangoExpiredConnectionError",
    "NangoProxyError",
    "NangoRateLimitError",
]
