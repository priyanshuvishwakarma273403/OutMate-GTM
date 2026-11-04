"""Live integration tests for real Decision Maker Discovery and Verification.

These tests execute actual network requests against external APIs (Tavily search, OpenRouter LLM,
and public web sources).
They are marked with `@pytest.mark.live` and excluded by default.
Run via:
    pytest -m live tests/integration/test_decision_makers_live.py -v -s
"""

import pytest

from app.core.config import get_settings
from app.domain.models.person import EmploymentStatus
from app.schemas.requests import DecisionMakerResearchRequest
from app.services.people_research import PeopleResearchService

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


@pytest.mark.asyncio
async def test_live_decision_makers_discovery_end_to_end() -> None:
    """Verify live end-to-end decision-maker discovery against a real target (Vercel)."""
    service = PeopleResearchService()

    request = DecisionMakerResearchRequest(
        company_name="Vercel",
        company_domain="vercel.com",
        target_departments=["executive", "engineering"],
        product_context="Next.js developer platform and edge compute infrastructure",
        discovery_limit=5,
    )

    report = await service.discover_decision_makers(request)

    assert report.company_name == "Vercel"
    assert report.company_domain == "vercel.com"
    assert report.overall_status in ("completed", "partially_completed")
    assert report.discovery_summary.sources_retrieved >= 1

    # Check verified decision-makers
    assert len(report.people) >= 1
    assert len(report.scored_people) == len(report.people)
    assert len(report.evidence) >= 1

    # Inspect the primary decision maker
    primary = report.people[0]
    assert len(primary.full_name) > 0
    assert len(primary.title) > 0
    assert primary.employment_status in (
        EmploymentStatus.CURRENT_EMPLOYMENT_VERIFIED,
        EmploymentStatus.CURRENT_EMPLOYMENT_PARTIALLY_VERIFIED,
    )
    assert primary.assessment is not None
    assert len(primary.assessment.decision_influence) > 0
    assert len(primary.evidence) >= 1

    # Zero hallucination check: all evidence records must have valid HTTP sources and text snippets
    for ev in report.evidence:
        assert ev.source_url.startswith("http")
        assert len(ev.snippet) > 0

    # Verify scores are bounded and ranked descending
    scores = [s.score.overall_score for s in report.scored_people]
    for s in scores:
        assert 0.0 <= s <= 100.0
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1]

