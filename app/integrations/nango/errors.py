"""Typed exceptions for Nango integration and proxy layer."""

from typing import Any

from app.core.exceptions import NangoConnectionExpiredError, NangoIntegrationError, OutmateError


class NangoError(NangoIntegrationError):
    """Base exception for all Nango-related operations."""


class NangoAuthError(NangoError):
    """Raised when Nango secret key is missing, invalid, or rejected (HTTP 401)."""


class NangoConnectionNotFoundError(NangoError):
    """Raised when a specified connection_id does not exist in Nango (HTTP 404)."""


class NangoExpiredConnectionError(NangoConnectionExpiredError):
    """Raised when an OAuth connection exists but access is revoked or expired."""


class NangoRateLimitError(NangoError):
    """Raised when Nango API or downstream provider rate limits are exceeded (HTTP 429)."""


class NangoProxyError(NangoError):
    """Raised when an authenticated proxy request through Nango fails."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged_details = details or {}
        if status_code is not None:
            merged_details["status_code"] = status_code
        if response_body is not None:
            merged_details["response_body"] = response_body
        super().__init__(message, merged_details)
        self.status_code = status_code
        self.response_body = response_body


class CRMReadOnlyError(OutmateError):
    """Raised when an operation attempts to write, mutate, or delete CRM records."""

