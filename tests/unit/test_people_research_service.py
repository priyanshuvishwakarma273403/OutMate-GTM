"""Unit tests for PeopleResearchService orchestration, grounding verification, and candidate filtering."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.domain.models.person import Department, EmploymentStatus, SeniorityLevel
from app.domain.models.report import RelevanceTier
from app.integrations.search.base import SearchResultItem
from app.integrations.search.providers.mock import MockSearchClient
from app.llm.base import StructuredLLMResponse, TokenUsage
from app.schemas.requests import (
    DecisionMakerPreviewRequest,
    DecisionMakerResearchRequest,
)
from app.services.llm import LLMService
from app.services.people_research import (
    ExtractedCandidateList,
    ExtractedPersonCandidate,
    PeopleResearchService,
)
from app.services.report_storage import get_report_repository
from app.services.source_retrieval import RetrievedSource, SourceRetrievalService


@pytest.mark.asyncio
async def test_preview_discovery_generates_queries_and_roles() -> None:
    """Verify preview_discovery generates search queries and targets without scraping."""
    mock_search = MockSearchClient()
    service = PeopleResearchService(search_client=mock_search)

    preview = await service.preview_discovery(
        DecisionMakerPreviewRequest(
            company_name="Vercel",
            company_domain="vercel.com",
            target_departments=["engineering", "product"],
        )
    )

    assert preview.company_name == "Vercel"
    assert preview.company_domain == "vercel.com"
    assert len(preview.planned_search_queries) >= 3
    assert any("site:vercel.com" in q for q in preview.planned_search_queries)
    assert any("engineering" in q for q in preview.planned_search_queries)
    assert "Head of Engineering" in preview.estimated_role_targets


@pytest.mark.asyncio
async def test_discover_decision_makers_grounding_verification() -> None:
    """Verify candidates citing valid evidence are accepted while hallucinated evidence IDs are rejected."""
    mock_search = AsyncMock()
    mock_search.search.return_value = [
        SearchResultItem(
            url="https://vercel.com/about",
            title="About Vercel Leadership",
            snippet="Guillermo Rauch is the CEO and founder of Vercel.",
            score=0.95,
        )
    ]

    mock_retrieval = AsyncMock(spec=SourceRetrievalService)
    mock_retrieval.fetch_source.return_value = RetrievedSource(
        url="https://vercel.com/about",
        final_url="https://vercel.com/about",
        is_accessible=True,
        raw_html="""
        <html>
            <body>
                <h1>Vercel Leadership</h1>
                <p>Guillermo Rauch is the CEO and founder of Vercel, leading frontend cloud architecture.</p>
            </body>
        </html>
        """,
        status_code=200,
        content_type="text/html",
        retrieved_at=datetime.now(UTC),
    )

    mock_llm = AsyncMock(spec=LLMService)

    # We make mock_llm return two candidates:
    # 1. Valid: citing the real evidence passed in prompt
    # 2. Hallucinated: citing a fake evidence_id "ev_fake123"
    async def fake_structured_response(*args, **kwargs):
        prompt = kwargs.get("prompt", "")
        # Extract the real evidence id generated in the prompt
        real_ev_id = "ev_unknown"
        for line in prompt.split("\n"):
            if "[EVIDENCE_ID:" in line:
                real_ev_id = line.split("[EVIDENCE_ID:")[1].split("|")[0].strip()
                break

        return StructuredLLMResponse(
            parsed=ExtractedCandidateList(
                candidates=[
                    ExtractedPersonCandidate(
                        full_name="Guillermo Rauch",
                        raw_job_title="CEO and Founder",
                        department_hint="executive",
                        biography_excerpt="Guillermo Rauch is the CEO and founder of Vercel.",
                        supporting_evidence_ids=[real_ev_id],
                        is_current_employee_hint=True,
                    ),
                    ExtractedPersonCandidate(
                        full_name="Fake Phantom",
                        raw_job_title="Chief Hallucination Officer",
                        department_hint="engineering",
                        supporting_evidence_ids=["ev_fake_hallucinated_id"],
                        is_current_employee_hint=True,
                    ),
                ]
            ),
            raw_content="{}",
            model="openai/gpt-4o-mini",
            usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )

    mock_llm.generate_structured_response.side_effect = fake_structured_response

    service = PeopleResearchService(
        search_client=mock_search,
        retrieval_service=mock_retrieval,
        llm_service=mock_llm,
    )

    report = await service.discover_decision_makers(
        DecisionMakerResearchRequest(
            company_name="Vercel",
            company_domain="vercel.com",
            discovery_limit=5,
        )
    )

    assert report.company_name == "Vercel"
    # Grounding check: Fake Phantom must have been rejected because ev_fake_hallucinated_id did not exist!
    assert len(report.people) == 1
    verified_person = report.people[0]
    assert verified_person.full_name == "Guillermo Rauch"
    assert verified_person.seniority == SeniorityLevel.C_LEVEL
    assert verified_person.department == Department.EXECUTIVE
    assert verified_person.employment_status == EmploymentStatus.CURRENT_EMPLOYMENT_VERIFIED
    assert verified_person.assessment is not None
    assert len(verified_person.evidence) >= 1

    # Check persistence in repository
    repo = get_report_repository()
    stored = repo.get_decision_maker_report(report.research_id)
    assert stored is not None
    assert stored.research_id == report.research_id


@pytest.mark.asyncio
async def test_historical_employee_filtering() -> None:
    """Verify former employees are excluded when include_former_employees=False."""
    mock_search = AsyncMock()
    mock_search.search.return_value = [
        SearchResultItem(
            url="https://techcrunch.com/article",
            title="Executive Departure",
            snippet="Former VP John Exleft departed the company last year.",
            score=0.90,
        )
    ]

    mock_retrieval = AsyncMock(spec=SourceRetrievalService)

    async def mock_fetch(url: str) -> RetrievedSource:
        if "techcrunch" in url:
            return RetrievedSource(
                url=url,
                final_url=url,
                is_accessible=True,
                raw_html="""
                <html>
                    <body>
                        <p>Former VP John Exleft departed the company last year and stepped down from his executive role.</p>
                    </body>
                </html>
                """,
                status_code=200,
                content_type="text/html",
                retrieved_at=datetime.now(UTC),
            )
        return RetrievedSource(
            url=url,
            final_url=url,
            is_accessible=False,
            error="Page not found",
        )

    mock_retrieval.fetch_source.side_effect = mock_fetch

    mock_llm = AsyncMock(spec=LLMService)

    async def fake_structured_response(*args, **kwargs):
        prompt = kwargs.get("prompt", "")
        real_ev_id = "ev_unknown"
        for line in prompt.split("\n"):
            if "[EVIDENCE_ID:" in line:
                real_ev_id = line.split("[EVIDENCE_ID:")[1].split("|")[0].strip()
                break

        return StructuredLLMResponse(
            parsed=ExtractedCandidateList(
                candidates=[
                    ExtractedPersonCandidate(
                        full_name="John Exleft",
                        raw_job_title="Former VP of Engineering",
                        department_hint="engineering",
                        biography_excerpt="Departed the company last year.",
                        supporting_evidence_ids=[real_ev_id],
                        is_current_employee_hint=False,
                        departure_note="Stepped down last year.",
                    )
                ]
            ),
            raw_content="{}",
            model="openai/gpt-4o-mini",
            usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )

    mock_llm.generate_structured_response.side_effect = fake_structured_response

    service = PeopleResearchService(
        search_client=mock_search,
        retrieval_service=mock_retrieval,
        llm_service=mock_llm,
    )

    # 1. With include_former_employees = False (default)
    report_exclude = await service.discover_decision_makers(
        DecisionMakerResearchRequest(
            company_name="Acme",
            company_domain="acme.com",
            include_former_employees=False,
        )
    )
    assert len(report_exclude.people) == 0
    assert report_exclude.discovery_summary.candidates_excluded == 1
    assert len(report_exclude.excluded_candidates_summary) == 1
    assert "John Exleft" in report_exclude.excluded_candidates_summary[0]
