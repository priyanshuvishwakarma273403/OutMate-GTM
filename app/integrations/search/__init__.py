"""Search integration module contracts, factory, and provider implementations."""

from app.integrations.search.base import BaseSearchClient, SearchQuery, SearchResultItem
from app.integrations.search.config import SearchConfig
from app.integrations.search.factory import get_search_client
from app.integrations.search.providers.mock import MockSearchClient
from app.integrations.search.providers.tavily import TavilySearchClient

__all__ = [
    "BaseSearchClient",
    "MockSearchClient",
    "SearchConfig",
    "SearchQuery",
    "SearchResultItem",
    "TavilySearchClient",
    "get_search_client",
]
