"""Provider-independent web search interface and result contracts."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    """Normalized search result retrieved from an external research engine."""

    url: str = Field(..., description="Target web page URL")
    title: str = Field(..., description="Title of the search result")
    snippet: str = Field(..., description="Relevant textual snippet matching the query")
    score: float = Field(default=0.0, ge=0.0, le=1.0, description="Relevance rank score")
    published_date: datetime | None = Field(default=None, description="Publication timestamp")
    raw_payload: dict[str, Any] = Field(
        default_factory=dict, description="Original unparsed provider payload"
    )


class SearchQuery(BaseModel):
    """Normalized research search query."""

    query: str = Field(..., min_length=2, description="Search terms or natural language question")
    max_results: int = Field(default=10, ge=1, le=50, description="Max results to fetch")
    domains_included: list[str] = Field(
        default_factory=list, description="Restrict search to specific domains"
    )
    domains_excluded: list[str] = Field(
        default_factory=list, description="Exclude unwanted domains"
    )


class BaseSearchClient(ABC):
    """Abstract interface defining required capabilities for web research search engines."""

    @abstractmethod
    async def search(self, query: SearchQuery) -> list[SearchResultItem]:
        """Execute web search and return normalized result items."""
        pass
