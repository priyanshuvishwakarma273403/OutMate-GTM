"""Search provider integrations and contracts."""

from app.integrations.search.base import BaseSearchClient, SearchQuery, SearchResultItem
from app.integrations.search.config import SearchConfig

__all__ = ["BaseSearchClient", "SearchConfig", "SearchQuery", "SearchResultItem"]
