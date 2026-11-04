"""Unit tests for CompanyResearchService orchestration."""

from unittest.mock import AsyncMock

import pytest

from app.integrations.search.base import SearchResultItem
from app.integrations.search.providers.mock import MockSearchClient
from app.llm.base import StructuredLLMResponse, TokenUsage
from app.schemas.requests import CompanyPreviewRequest, CompanyResearchRequest
from app.services.company_research import (
    CompanyResearchService,
    ExtractedCompanyData,
)
from app.services.content_extraction import ContentExtractionService
from app.services.llm import LLMService
from app.services.source_retrieval import RetrievedSource, SourceRetrievalService
from app.services.verification import VerificationService


@pytest.mark.asyncio
async def test_preview_research() -> None:
    """Verify preview_research resolves identity and generates query plan without scraping."""
    mock_search = MockSearchClient()
    service = CompanyResearchService(search_client=mock_search)

    preview = await service.preview_research(
        CompanyPreviewRequest(company_name="Vercel Inc", website_domain="vercel.com")
    )

    assert preview.company_name == "Vercel Inc"
    assert preview.normalized_name == "Vercel"
    assert preview.resolved_domain == "vercel.com"
    assert preview.resolution_status == "resolved"
    assert len(preview.planned_search_queries) >= 2


@pytest.mark.asyncio
async def test_research_company_orchestration_mocked() -> None:
    """Verify full research workflow execution with mocked dependencies."""
    mock_search_results = [
        SearchResultItem(
            url="https://vercel.com/about",
            title="About Vercel Leadership",
            snippet="Vercel is the frontend cloud platform.",
            score=0.98,
        ),
        SearchResultItem(
            url="https://techcrunch.com/vercel-series-d",
            title="TechCrunch Vercel Coverage",
            snippet="Vercel is headquartered in San Francisco with Next.js framework.",
            score=0.85,
        ),
    ]
    mock_search = MockSearchClient(predefined_results=mock_search_results)

    # Mock Source Retrieval
    mock_retrieval = AsyncMock(spec=SourceRetrievalService)
    mock_retrieval.fetch_source.return_value = RetrievedSource(
        url="https://vercel.com/about",
        final_url="https://vercel.com/about",
        status_code=200,
        raw_html="<html><body><p>Vercel is a developer cloud platform for Next.js.</p></body></html>",
        is_accessible=True,
    )

    # Mock LLM Service
    mock_llm = AsyncMock(spec=LLMService)
    extracted_data = ExtractedCompanyData(
        legal_name="Vercel Inc.",
        description="Vercel is the frontend cloud platform.",
        industry="cloud_infrastructure",
        headquarters="San Francisco, CA",
        estimated_headcount=500,
        founded_year=2015,
        funding_stage="series_c_plus",
        tech_stack=["Next.js", "React", "TypeScript"],
        key_findings=["Frontend cloud platform pioneer.", "Creators of Next.js."],
    )
    mock_llm.generate_structured_response.return_value = StructuredLLMResponse(
        parsed=extracted_data,
        raw_content="{}",
        model="openai/gpt-4o-mini",
        usage=TokenUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80),
    )

    service = CompanyResearchService(
        search_client=mock_search,
        llm_service=mock_llm,
        retrieval_service=mock_retrieval,
        extraction_service=ContentExtractionService(),
        verification_service=VerificationService(),
    )

    report = await service.research_company(
        CompanyResearchRequest(company_name="Vercel", website_domain="vercel.com")
    )

    assert report.company.name == "Vercel"
    assert report.company.domain == "vercel.com"
    assert report.company.legal_name == "Vercel Inc."
    assert report.company.headquarters == "San Francisco, CA"
    assert report.company.founded_year == 2015
    assert len(report.company.tech_stack) == 3
    assert len(report.findings) >= 2
    assert report.overall_status == "completed"
    assert report.source_summary.sources_retrieved >= 1

    # Verify repository storage
    retrieved_from_repo = service.repo.get(report.research_id)
    assert retrieved_from_repo is not None
    assert retrieved_from_repo.research_id == report.research_id
