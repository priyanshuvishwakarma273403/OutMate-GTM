"""Configuration models for Nango OAuth connection and proxy management."""

from pydantic import BaseModel, Field


class NangoConfig(BaseModel):
    """Nango client and environment connection configuration."""

    secret_key: str = Field(..., description="Server-side secret key for Nango API")
    base_url: str = Field(default="https://api.nango.dev", description="Nango API host URL")
    timeout: float = Field(default=30.0, ge=1.0, description="HTTP request timeout in seconds")


class NangoConnectionIdentity(BaseModel):
    """Identifier pairing representing an authenticated third-party connection."""

    connection_id: str = Field(..., description="Unique tenant or user identifier in Nango")
    integration_id: str = Field(
        ..., description="Third-party service identifier (e.g. 'hubspot', 'salesforce')"
    )
