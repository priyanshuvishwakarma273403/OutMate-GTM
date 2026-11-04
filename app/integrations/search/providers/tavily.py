"""Tavily search provider client implementation."""

import asyncio
import time
from datetime import datetime
from typing import Any

import httpx

from app.core.config import AppSettings, get_settings
from app.core.exceptions import (
    ConfigurationError,
    SearchAuthenticationError,
    SearchProviderError,
    SearchQuotaExceededError,
    SearchTimeoutError,
)
from app.core.logging import get_logger
from app.integrations.search.base import BaseSearchClient, SearchQuery, SearchResultItem

logger = get_logger("integrations.search.tavily")


class TavilySearchClient(BaseSearchClient):
    """Production search client using official Tavily Search REST API."""

    DEFAULT_BASE_URL = "https://api.tavily.com"
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 0.5

    def __init__(
        self,
        settings: AppSettings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._custom_client = http_client
        self.api_key = self.settings.tavily_api_key or self.settings.search_api_key
        self.base_url = (
            self.settings.search_api_base_url
            if self.settings.search_api_base_url
            else self.DEFAULT_BASE_URL
        ).rstrip("/")
        self.timeout = self.settings.search_timeout

    def _ensure_configured(self) -> str:
        """Validate that Tavily API key is available."""
        if not self.api_key or not self.api_key.strip():
            raise ConfigurationError(
                "TAVILY_API_KEY or SEARCH_API_KEY is required for Tavily search provider."
            )
        return self.api_key.strip()

    def _parse_published_date(self, date_val: Any) -> datetime | None:
        """Safely parse published date string from provider."""
        if not date_val or not isinstance(date_val, str):
            return None
        # Try common ISO formats
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_val, fmt)
            except ValueError:
                continue
        return None

    async def search(self, query: SearchQuery) -> list[SearchResultItem]:
        """Execute Tavily search query with retries, timeout, and response normalization."""
        api_key = self._ensure_configured()
        url = f"{self.base_url}/search"

        payload: dict[str, Any] = {
            "api_key": api_key,
            "query": query.query,
            "max_results": query.max_results,
            "search_depth": "basic",
            "include_raw_content": False,
        }

        if query.domains_included:
            payload["include_domains"] = query.domains_included
        if query.domains_excluded:
            payload["exclude_domains"] = query.domains_excluded

        logger.info(
            "Dispatching Tavily search request (query='%s', max_results=%d)",
            query.query,
            query.max_results,
        )

        headers = {"Content-Type": "application/json"}
        last_error: Exception | None = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                start_time = time.perf_counter()
                if self._custom_client:
                    response = await self._custom_client.post(
                        url,
                        json=payload,
                        headers=headers,
                        timeout=self.timeout,
                    )
                else:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.post(
                            url,
                            json=payload,
                            headers=headers,
                        )

                duration_ms = (time.perf_counter() - start_time) * 1000.0

                if response.status_code == 200:
                    data = response.json()
                    raw_results = data.get("results", [])
                    logger.info(
                        "Tavily search completed in %.1fms (retrieved %d items)",
                        duration_ms,
                        len(raw_results),
                    )

                    normalized_items: list[SearchResultItem] = []
                    for r in raw_results:
                        item_url = r.get("url")
                        if not item_url:
                            continue
                        normalized_items.append(
                            SearchResultItem(
                                url=item_url,
                                title=r.get("title", ""),
                                snippet=r.get("content", ""),
                                score=float(r.get("score", 0.0)),
                                published_date=self._parse_published_date(r.get("published_date")),
                                raw_payload=r,
                            )
                        )
                    return normalized_items

                if response.status_code in (401, 403):
                    logger.error("Tavily authentication failure (status=%d)", response.status_code)
                    raise SearchAuthenticationError(
                        "Invalid or unauthorized Tavily API key",
                        details={"status_code": response.status_code},
                    )

                if response.status_code in (402, 429):
                    logger.warning(
                        "Tavily rate limit or quota exceeded (status=%d)", response.status_code
                    )
                    if attempt < self.MAX_RETRIES:
                        await asyncio.sleep(self.INITIAL_BACKOFF * (2 ** (attempt - 1)))
                        continue
                    raise SearchQuotaExceededError(
                        "Tavily API quota or rate limit exceeded",
                        details={"status_code": response.status_code},
                    )

                # Transient server errors: 500, 502, 503, 504
                if response.status_code >= 500:
                    logger.warning(
                        "Tavily provider server error (status=%d, attempt %d/%d)",
                        response.status_code,
                        attempt,
                        self.MAX_RETRIES,
                    )
                    if attempt < self.MAX_RETRIES:
                        await asyncio.sleep(self.INITIAL_BACKOFF * (2 ** (attempt - 1)))
                        continue
                    raise SearchProviderError(
                        f"Tavily server error: HTTP {response.status_code}",
                        details={"status_code": response.status_code, "body": response.text[:200]},
                    )

                # Other HTTP errors
                raise SearchProviderError(
                    f"Tavily API returned unexpected status {response.status_code}",
                    details={"status_code": response.status_code, "body": response.text[:200]},
                )

            except httpx.TimeoutException as exc:
                logger.warning(
                    "Tavily search timeout on attempt %d/%d (timeout=%.1fs)",
                    attempt,
                    self.MAX_RETRIES,
                    self.timeout,
                )
                last_error = exc
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(self.INITIAL_BACKOFF * (2 ** (attempt - 1)))
                    continue
                raise SearchTimeoutError(
                    f"Tavily search request timed out after {self.timeout}s"
                ) from exc

            except httpx.RequestError as exc:
                logger.warning(
                    "Tavily network request error on attempt %d/%d: %s",
                    attempt,
                    self.MAX_RETRIES,
                    str(exc),
                )
                last_error = exc
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(self.INITIAL_BACKOFF * (2 ** (attempt - 1)))
                    continue
                raise SearchProviderError(f"Tavily network connection failed: {exc}") from exc

        if last_error:
            raise SearchProviderError(f"Tavily search failed after {self.MAX_RETRIES} retries")
        return []

