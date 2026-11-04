"""Mock search provider for isolated unit testing and offline development."""

from app.integrations.search.base import BaseSearchClient, SearchQuery, SearchResultItem


class MockSearchClient(BaseSearchClient):
    """Deterministic mock search client for offline testing."""

    def __init__(self, predefined_results: list[SearchResultItem] | None = None) -> None:
        self.predefined_results = predefined_results or []
        self.recorded_queries: list[SearchQuery] = []

    async def search(self, query: SearchQuery) -> list[SearchResultItem]:
        """Record the search query and return predefined or synthetic deterministic results."""
        self.recorded_queries.append(query)
        if self.predefined_results:
            return self.predefined_results[: query.max_results]

        # Default synthetic result for tests
        return [
            SearchResultItem(
                url="https://example.com/about",
                title=f"About {query.query}",
                snippet=f"Official corporate information and overview for {query.query}.",
                score=0.95,
                raw_payload={"query": query.query, "mock": True},
            )
        ]
