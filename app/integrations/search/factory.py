"""Factory for instantiating the configured search provider client."""

from app.core.config import AppSettings, get_settings
from app.core.exceptions import ConfigurationError
from app.core.logging import get_logger
from app.integrations.search.base import BaseSearchClient
from app.integrations.search.providers.mock import MockSearchClient
from app.integrations.search.providers.tavily import TavilySearchClient

logger = get_logger("integrations.search.factory")


def get_search_client(settings: AppSettings | None = None) -> BaseSearchClient:
    """Return an instantiated search provider client based on runtime configuration."""
    cfg = settings or get_settings()
    provider_name = cfg.search_provider.lower()

    if provider_name == "tavily":
        cfg.validate_search()
        logger.debug("Instantiating TavilySearchClient")
        return TavilySearchClient(settings=cfg)

    if provider_name == "mock":
        logger.debug("Instantiating MockSearchClient for offline testing")
        return MockSearchClient()

    if provider_name in ("exa", "serper"):
        raise ConfigurationError(
            f"Search provider '{provider_name}' driver is not configured in this release. "
            "Please configure SEARCH_PROVIDER=tavily."
        )

    raise ConfigurationError(f"Unsupported search provider: '{provider_name}'")
