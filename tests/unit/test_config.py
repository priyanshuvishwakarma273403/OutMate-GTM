"""Unit tests for centralized configuration and lazy validation."""

import pytest

from app.core.config import AppSettings
from app.core.exceptions import ConfigurationError


def test_default_config_loading() -> None:
    """Verify default configuration values instantiate without error."""
    settings = AppSettings(
        APP_NAME="Test App",
        APP_ENV="test",
    )
    assert settings.app_name == "Test App"
    assert settings.app_env == "test"
    assert settings.app_host == "127.0.0.1"
    assert settings.app_port == 8000
    assert settings.openrouter_model == "anthropic/claude-3.5-sonnet"


def test_allowed_origins_parsing() -> None:
    """Verify parsing comma-separated origins from environment string."""
    settings = AppSettings(
        ALLOWED_ORIGINS="http://localhost:3000, https://app.outmate.ai",  # type: ignore[arg-type]
    )
    assert settings.allowed_origins == [
        "http://localhost:3000",
        "https://app.outmate.ai",
    ]


def test_openrouter_validation_fails_when_key_missing() -> None:
    """Validate that validate_openrouter raises ConfigurationError when key is None."""
    settings = AppSettings(OPENROUTER_API_KEY=None)
    with pytest.raises(ConfigurationError, match="OPENROUTER_API_KEY is required"):
        settings.validate_openrouter()


def test_openrouter_validation_succeeds_when_key_present() -> None:
    """Validate that validate_openrouter succeeds when key is provided."""
    settings = AppSettings(OPENROUTER_API_KEY="sk-or-test-key")
    settings.validate_openrouter()


def test_nango_validation_fails_when_key_missing() -> None:
    """Validate that validate_nango raises ConfigurationError when key is None."""
    settings = AppSettings(NANGO_SECRET_KEY=None)
    with pytest.raises(ConfigurationError, match="NANGO_SECRET_KEY is required"):
        settings.validate_nango()


def test_nango_validation_succeeds_when_key_present() -> None:
    """Validate that validate_nango succeeds when key is provided."""
    settings = AppSettings(NANGO_SECRET_KEY="test_nango_secret")
    settings.validate_nango()


def test_search_validation() -> None:
    """Validate search provider requires key unless provider is 'mock'."""
    settings_missing = AppSettings(SEARCH_PROVIDER="exa", SEARCH_API_KEY=None)
    with pytest.raises(ConfigurationError, match="SEARCH_API_KEY is required"):
        settings_missing.validate_search()

    settings_mock = AppSettings(SEARCH_PROVIDER="mock", SEARCH_API_KEY=None)
    settings_mock.validate_search()  # Should not raise


def test_mcp_auth_validation() -> None:
    """Validate MCP auth configuration flags."""
    settings_invalid = AppSettings(MCP_AUTH_ENABLED=True, MCP_AUTH_TOKEN=None)
    with pytest.raises(ConfigurationError, match="MCP_AUTH_TOKEN must be specified"):
        settings_invalid.validate_mcp_auth()

    settings_valid = AppSettings(MCP_AUTH_ENABLED=True, MCP_AUTH_TOKEN="secret-token-123")
    settings_valid.validate_mcp_auth()
