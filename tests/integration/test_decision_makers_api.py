"""Integration tests for Decision Maker REST API endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes.decision_makers import get_people_service, get_repository
from app.domain.models.evidence import EvidenceRecord, EvidenceSourceType
from app.domain.models.person import (
    ContactCoordinates,
    DecisionInfluenceCategory,
    DecisionMaker,
    DecisionMakerAssessment,
    Department,
    EmploymentStatus,
    RoleCategory,
    SeniorityLevel,
)
from app.domain.models.report import RelevanceScore, RelevanceTier, ScoredDecisionMaker
from app.main import create_app
from app.schemas.responses import (
    DecisionMakerPreviewResponse,
    DecisionMakerReport,
    DiscoverySummary,
)
from app.services.people_research import PeopleResearchService
from app.services.report_storage import InMemoryReportRepository


def _build_mock_report(research_id: str = "dm-report-123") -> DecisionMakerReport:
    ev = EvidenceRecord(
        evidence_id="ev_test_1",
        source_url="https://vercel.com/about",
        source_type=EvidenceSourceType.OFFICIAL_WEBSITE,
        title="About Vercel Leadership",
        snippet="Guillermo Rauch is the CEO and founder of Vercel.",
        confidence=0.95,
    )
    dm = DecisionMaker(
        person_id="dm_rauchg_1",
        full_name="Guillermo Rauch",
        company_name="Vercel",
        company_domain="vercel.com",
        title="CEO and Founder",
        normalized_title="Chief Executive Officer",
        seniority=SeniorityLevel.C_LEVEL,
        department=Department.EXECUTIVE,
        employment_status=EmploymentStatus.CURRENT_EMPLOYMENT_VERIFIED,
        confidence_score=0.95,
        confidence_explanation="Directly verified on official first-party website ('vercel.com').",
        contact_info=ContactCoordinates(
            linkedin_url="https://linkedin.com/in/rauchg",
            twitter_handle="@rauchg",
        ),
        assessment=DecisionMakerAssessment(
            person_id="dm_rauchg_1",
            role_category=RoleCategory.EXECUTIVE,
            decision_influence=DecisionInfluenceCategory.ECONOMIC_BUYER,
            relevant_responsibilities=["Corporate budget allocation and executive sign-off"],
            purchasing_relevance="General organizational leadership role",
            reasoning="Executive with ultimate corporate budget authority.",
            assessment_status="completed",
            supporting_evidence_ids=["ev_test_1"],
        ),
        evidence=[ev],
    )
    score = RelevanceScore(
        overall_score=95.0,
        tier=RelevanceTier.HIGH,
        seniority_fit=1.0,
        department_fit=0.9,
        evidence_confidence=0.95,
        rationale="C-Level executive with verified employment.",
    )
    scored_dm = ScoredDecisionMaker(person=dm, score=score)

    return DecisionMakerReport(
        research_id=research_id,
        company_name="Vercel",
        company_domain="vercel.com",
        people=[dm],
        scored_people=[scored_dm],
        evidence=[ev],
        discovery_summary=DiscoverySummary(
            search_queries_executed=['"Vercel" leadership'],
            sources_retrieved=1,
            candidates_discovered=1,
            candidates_verified=1,
            candidates_excluded=0,
            duplicate_candidates_merged=0,
        ),
        overall_status="completed",
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        duration_ms=125.0,
    )


@pytest.mark.asyncio
async def test_preview_decision_makers_endpoint_success() -> None:
    """Verify POST /api/v1/research/decision-makers/preview returns 200 OK with query plan."""
    app = create_app()

    mock_service = AsyncMock(spec=PeopleResearchService)
    mock_service.preview_discovery.return_value = DecisionMakerPreviewResponse(
        company_name="Vercel",
        company_domain="vercel.com",
        target_departments=["engineering"],
        planned_search_queries=["site:vercel.com leadership", '"Vercel" leadership'],
        estimated_role_targets=["Chief Executive Officer", "VP of Engineering"],
    )

    app.dependency_overrides[get_people_service] = lambda: mock_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/research/decision-makers/preview",
            json={
                "company_name": "Vercel",
                "company_domain": "vercel.com",
                "target_departments": ["engineering"],
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] == "Vercel"
    assert data["company_domain"] == "vercel.com"
    assert len(data["planned_search_queries"]) == 2
    assert "Chief Executive Officer" in data["estimated_role_targets"]


@pytest.mark.asyncio
async def test_discover_decision_makers_endpoint_success() -> None:
    """Verify POST /api/v1/research/decision-makers returns 200 OK and verified report."""
    app = create_app()

    mock_report = _build_mock_report(research_id="dm-test-456")
    mock_service = AsyncMock(spec=PeopleResearchService)
    mock_service.discover_decision_makers.return_value = mock_report

    app.dependency_overrides[get_people_service] = lambda: mock_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/research/decision-makers",
            json={
                "company_name": "Vercel",
                "company_domain": "vercel.com",
                "discovery_limit": 5,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["research_id"] == "dm-test-456"
    assert data["company_name"] == "Vercel"
    assert len(data["people"]) == 1
    assert data["people"][0]["full_name"] == "Guillermo Rauch"
    assert data["people"][0]["seniority"] == "c_level"
    assert data["people"][0]["assessment"]["decision_influence"] == "economic_buyer"


@pytest.mark.asyncio
async def test_get_report_and_person_endpoints() -> None:
    """Verify GET /{id}, GET /{id}/people/{person_id}, and GET /{id}/sources."""
    app = create_app()

    repo = InMemoryReportRepository()
    mock_report = _build_mock_report(research_id="dm-lookup-789")
    repo.save_decision_maker_report(mock_report)

    app.dependency_overrides[get_repository] = lambda: repo

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. GET /{research_id}
        resp1 = await client.get("/api/v1/research/decision-makers/dm-lookup-789")
        assert resp1.status_code == 200
        assert resp1.json()["research_id"] == "dm-lookup-789"

        # 2. GET /{research_id}/people/{person_id}
        resp2 = await client.get(
            "/api/v1/research/decision-makers/dm-lookup-789/people/dm_rauchg_1"
        )
        assert resp2.status_code == 200
        person_data = resp2.json()
        assert person_data["person_id"] == "dm_rauchg_1"
        assert person_data["full_name"] == "Guillermo Rauch"

        # 3. GET /{research_id}/sources
        resp3 = await client.get("/api/v1/research/decision-makers/dm-lookup-789/sources")
        assert resp3.status_code == 200
        sources_data = resp3.json()
        assert len(sources_data) == 1
        assert sources_data[0]["evidence_id"] == "ev_test_1"

        # 4. 404 for nonexistent report
        resp_404 = await client.get("/api/v1/research/decision-makers/nonexistent-id")
        assert resp_404.status_code == 404

        # 5. 404 for nonexistent person in valid report
        resp_person_404 = await client.get(
            "/api/v1/research/decision-makers/dm-lookup-789/people/nonexistent-person"
        )
        assert resp_person_404.status_code == 404


@pytest.mark.asyncio
async def test_discover_decision_makers_validation_failure() -> None:
    """Verify 422 Unprocessable Entity when company_name is missing or invalid."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/research/decision-makers",
            json={"company_name": "", "discovery_limit": 5},
        )
    assert response.status_code == 422
