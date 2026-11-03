"""External integration boundary (Nango, Search Providers)."""

from app.integrations.nango.client import NangoClient
from app.integrations.search.base import BaseSearchClient

__all__ = ["BaseSearchClient", "NangoClient"]
