"""Custom domain and infrastructure exceptions for Outmate GTM."""

from typing import Any


class OutmateError(Exception):
    """Base exception for all Outmate GTM application errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to structured dictionary representation."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


# Configuration Errors
class ConfigurationError(OutmateError):
    """Raised when environment or runtime configuration is invalid or missing."""


# Authentication & Authorization Errors
class AuthenticationError(OutmateError):
    """Raised when authentication credentials are missing, expired, or invalid."""


class AuthorizationError(OutmateError):
    """Raised when access to a resource or tool is forbidden."""


# LLM Provider Errors
class LLMProviderError(OutmateError):
    """Base exception for errors during LLM inference or provider interactions."""


class LLMTimeoutError(LLMProviderError):
    """Raised when an LLM provider request exceeds the configured timeout."""


class LLMQuotaExceededError(LLMProviderError):
    """Raised when rate limits or usage quotas are exceeded at the LLM gateway."""


class LLMResponseParsingError(LLMProviderError):
    """Raised when the LLM response cannot be parsed into expected structured schema."""


# MCP Protocol Errors
class MCPError(OutmateError):
    """Base exception for Model Context Protocol interactions."""


class MCPToolNotFoundError(MCPError):
    """Raised when an unknown tool name is invoked."""


class MCPValidationError(MCPError):
    """Raised when tool input parameters fail schema validation."""


class MCPExecutionError(MCPError):
    """Raised when a tool handler encounters an unhandled runtime error."""


# Integration Errors (Nango, Search Providers)
class IntegrationError(OutmateError):
    """Base exception for third-party integrations."""


class NangoIntegrationError(IntegrationError):
    """Raised when interacting with Nango OAuth proxy service."""


class NangoConnectionExpiredError(NangoIntegrationError):
    """Raised when an OAuth connection is revoked, expired, or disconnected in Nango."""


class SearchProviderError(IntegrationError):
    """Raised when external public search providers fail or return invalid data."""


# Service & Domain Errors
class ServiceError(OutmateError):
    """Base exception for business service failures."""


class EntityNotFoundError(ServiceError):
    """Raised when a requested company or decision-maker entity is not found."""


class VerificationError(ServiceError):
    """Raised when evidence verification fails or confidence thresholds are not met."""
