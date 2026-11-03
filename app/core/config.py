"""Centralized application configuration using Pydantic v2 Settings.

Configuration is organized into modular sections and validates secrets lazily
when their respective subsystems (OpenRouter, Nango, Search) are initialized.
"""

from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.exceptions import ConfigurationError


class AppSettings(BaseSettings):
    """Core application environment configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application metadata
    app_name: str = Field(default="Outmate GTM", alias="APP_NAME")
    app_env: Literal["development", "staging", "production", "test"] = Field(
        default="development", alias="APP_ENV"
    )
    app_host: str = Field(default="127.0.0.1", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", alias="LOG_LEVEL"
    )

    # OpenRouter LLM Configuration (Mode A: Standalone AI Agent)
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL"
    )
    openrouter_model: str = Field(default="anthropic/claude-3.5-sonnet", alias="OPENROUTER_MODEL")
    openrouter_timeout: float = Field(default=60.0, alias="OPENROUTER_TIMEOUT")
    openrouter_max_retries: int = Field(default=3, alias="OPENROUTER_MAX_RETRIES")

    # Nango Integration Configuration (OAuth Connection & Third-Party Proxy)
    nango_secret_key: str | None = Field(default=None, alias="NANGO_SECRET_KEY")
    nango_base_url: str = Field(default="https://api.nango.dev", alias="NANGO_BASE_URL")
    nango_connection_id: str | None = Field(default=None, alias="NANGO_CONNECTION_ID")
    nango_integration_id: str | None = Field(default=None, alias="NANGO_INTEGRATION_ID")
    nango_timeout: float = Field(default=30.0, alias="NANGO_TIMEOUT")

    # Research / Search Provider Configuration
    search_provider: Literal["exa", "serper", "tavily", "mock"] = Field(
        default="exa", alias="SEARCH_PROVIDER"
    )
    search_api_key: str | None = Field(default=None, alias="SEARCH_API_KEY")
    search_api_base_url: str | None = Field(default=None, alias="SEARCH_API_BASE_URL")
    search_timeout: float = Field(default=30.0, alias="SEARCH_TIMEOUT")

    # Model Context Protocol (MCP) Configuration (Mode B: Claude.ai Connector & Local)
    mcp_transport: Literal["stdio", "sse", "http"] = Field(default="sse", alias="MCP_TRANSPORT")
    mcp_host: str = Field(default="127.0.0.1", alias="MCP_HOST")
    mcp_port: int = Field(default=8001, alias="MCP_PORT")
    mcp_server_name: str = Field(default="outmate-mcp-server", alias="MCP_SERVER_NAME")
    mcp_auth_enabled: bool = Field(default=False, alias="MCP_AUTH_ENABLED")
    mcp_auth_token: str | None = Field(default=None, alias="MCP_AUTH_TOKEN")

    # Security & Networking
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        alias="ALLOWED_ORIGINS",
    )
    api_key_required: bool = Field(default=False, alias="API_KEY_REQUIRED")

    # Testing & Development Flags
    testing: bool = Field(default=False, alias="TESTING")

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> list[str]:
        """Parse comma-separated origins from environment variables."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, list):
            return [str(origin).strip() for origin in v]
        return ["*"] if v == "*" else []

    # Subsystem Validation Methods (Explicit & Lazy)
    def validate_openrouter(self) -> None:
        """Validate that OpenRouter configuration is present when Mode A agent starts."""
        if not self.openrouter_api_key:
            raise ConfigurationError(
                "OPENROUTER_API_KEY is required for standalone OpenRouter agent execution."
            )
        if not self.openrouter_model:
            raise ConfigurationError("OPENROUTER_MODEL must be configured.")

    def validate_nango(self) -> None:
        """Validate Nango credentials when third-party OAuth proxy calls are initiated."""
        if not self.nango_secret_key:
            raise ConfigurationError(
                "NANGO_SECRET_KEY is required for Nango-mediated third-party integrations."
            )

    def validate_search(self) -> None:
        """Validate search provider configuration when research services execute."""
        if self.search_provider != "mock" and not self.search_api_key:
            raise ConfigurationError(
                f"SEARCH_API_KEY is required when SEARCH_PROVIDER is '{self.search_provider}'."
            )

    def validate_mcp_auth(self) -> None:
        """Validate remote MCP security configuration when remote auth is enabled."""
        if self.mcp_auth_enabled and not self.mcp_auth_token:
            raise ConfigurationError(
                "MCP_AUTH_TOKEN must be specified when MCP_AUTH_ENABLED is True."
            )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return a cached singleton instance of application settings."""
    return AppSettings()
