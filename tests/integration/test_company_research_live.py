"""Live integration tests for real Tavily search, source retrieval, and end-to-end research.

These tests execute actual network requests against external APIs and public web sources.
They are marked with `@pytest.mark.live` and excluded by default.
Run via:
    pytest -m live tests/integration/test_company_research_live.py -v -s
"""

import pytest

from app.core.config import get_settings
from app.integrations.search.base import SearchQuery
from app.integrations.search.providers.tavily import TavilySearchClient
from app.schemas.requests import CompanyResearchRequest
from app.services.company_research import CompanyResearchService
from app.services.content_extraction import ContentExtractionService
from app.services.source_retrieval import SourceRetrievalService

_settings = get_settings()
_has_live_credentials = bool(
    (_settings.tavily_api_key or _settings.search_api_key)
    and _settings.openrouter_api_key
    and not _settings.openrouter_api_key.startswith("sk-or-v1-placeholder")
)

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not _has_live_credentials,
        reason="Skipping live test: live SEARCH_API_KEY and OPENROUTER_API_KEY required",
    ),
]


async def test_live_tavily_search() -> None:
    """Verify live communication with Tavily API returns valid real search results."""
    client = TavilySearchClient()
    results = await client.search(
        SearchQuery(query="Vercel cloud platform overview", max_results=3)
    )

    assert len(results) > 0
    assert any("vercel" in r.url.lower() or "vercel" in r.title.lower() for r in results)
    for r in results:
        assert r.url.startswith("http")
        assert len(r.title) > 0


async def test_live_source_retrieval_and_extraction() -> None:
    """Verify real HTTP retrieval and content extraction against a safe public destination."""
    retriever = SourceRetrievalService()
    extractor = ContentExtractionService()

    # Public safe reference URL
    source = await retriever.fetch_source("https://example.com")
    assert source.is_accessible is True
    assert source.status_code == 200
    assert "Example Domain" in source.raw_html

    content = extractor.extract(source.raw_html, fallback_url=source.url)
    assert "Example Domain" in content.title or "Example Domain" in content.main_text
    assert len(content.paragraphs) >= 1


async def test_live_company_research_end_to_end() -> None:
    """Verify complete end-to-end research pipeline on a real corporate target (Vercel)."""
    service = CompanyResearchService()
    report = await service.research_company(
        CompanyResearchRequest(
            company_name="Vercel",
            website_domain="vercel.com",
            research_depth="standard",
        )
    )

    assert report.company.name == "Vercel"
    assert report.company.domain == "vercel.com"
    assert report.overall_status in ("completed", "partially_completed")
    assert report.source_summary.sources_retrieved >= 1
    assert len(report.findings) >= 1
    assert len(report.evidence) >= 1

    # Verify every evidence record contains a real valid HTTP URL and text snippet
    for ev in report.evidence:
        assert ev.source_url.startswith("http")
        assert len(ev.snippet) > 0
        assert ev.verification_status is not None

