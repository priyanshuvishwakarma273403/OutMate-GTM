"""Unit tests for the 9 production Outmate GTM MCP tool handlers."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.domain.models import (
    CompanyProfile,
    DecisionMaker,
    Department,
    EmploymentStatus,
    SeniorityLevel,
)
from app.domain.models.evidence import EvidenceRecord, EvidenceSourceType
from app.domain.models.report import RelevanceScore, RelevanceTier, ScoredDecisionMaker
from app.integrations.search.base import BaseSearchClient, SearchResultItem
from app.mcp.errors import MCPResourceNotFoundError
from app.mcp.tools.company_tools import (
    get_company_profile_tool,
    research_company_tool,
    search_company_tool,
)
from app.mcp.tools.decision_maker_tools import (
    find_decision_makers_tool,
    get_person_details_tool,
    verify_person_tool,
)
from app.mcp.tools.report_tools import (
    get_decision_maker_sources_tool,
    get_research_report_tool,
    get_research_sources_tool,
)
from app.schemas.responses import CompanyResearchReport, DecisionMakerReport, DiscoverySummary
from app.services.company_research import CompanyResearchService
from app.services.employment_verification import EmploymentVerificationService
from app.services.people_research import PeopleResearchService
from app.services.report_storage import InMemoryReportRepository


@pytest.fixture
def mock_evidence() -> EvidenceRecord:
    return EvidenceRecord(
        source_url="https://vercel.com/about",
        source_type=EvidenceSourceType.OFFICIAL_WEBSITE,
        title="About Vercel",
        snippet="Vercel provides developer platform tools.",
    )


@pytest.fixture
def mock_company_profile() -> CompanyProfile:
    return CompanyProfile(
        name="Vercel",
        domain="vercel.com",
        legal_name="Vercel Inc.",
        description="Frontend cloud platform.",
    )


@pytest.fixture
def mock_decision_maker(mock_evidence: EvidenceRecord) -> DecisionMaker:
    return DecisionMaker(
        person_id="dm_test123",
        full_name="Guillermo Rauch",
        company_name="Vercel",
        title="CEO",
        seniority=SeniorityLevel.C_LEVEL,
        department=Department.EXECUTIVE,
        employment_status=EmploymentStatus.CURRENT_EMPLOYMENT_VERIFIED,
        evidence=[mock_evidence],
    )


# --- 1. search_company_tool ---
async def test_search_company_tool_success() -> None:
    mock_search = MagicMock(spec=BaseSearchClient)
    mock_search.search = AsyncMock(
        return_value=[
            SearchResultItem(
                title="Vercel: Build and deploy",
                url="https://vercel.com",
                snippet="Develop. Preview. Ship.",
            )
        ]
    )

    args = {"query": "Vercel", "domain": "vercel.com", "limit": 5}
    result = await search_company_tool(args, search_client=mock_search)

    assert result["total_results"] == 1
    assert result["results"][0]["title"] == "Vercel: Build and deploy"
    mock_search.search.assert_awaited_once()


async def test_search_company_tool_validation_error() -> None:
    with pytest.raises(ValidationError):
        await search_company_tool({"query": "a"})  # query too short (min_length=2)


# --- 2. research_company_tool ---
async def test_research_company_tool_success(
    mock_company_profile: CompanyProfile, mock_evidence: EvidenceRecord
) -> None:
    mock_service = MagicMock(spec=CompanyResearchService)
    report = CompanyResearchReport(
        research_id="res_comp_123",
        company=mock_company_profile,
        identity_status="resolved",
        findings=["Corroborated deployment platform."],
        evidence=[mock_evidence],
    )
    mock_service.research_company = AsyncMock(return_value=report)

    args = {"company_name": "Vercel", "company_domain": "vercel.com"}
    result = await research_company_tool(args, research_service=mock_service)

    assert result["report"]["research_id"] == "res_comp_123"
    assert result["report"]["company"]["name"] == "Vercel"
    mock_service.research_company.assert_awaited_once()


# --- 3. get_company_profile_tool ---
async def test_get_company_profile_tool_found(
    mock_company_profile: CompanyProfile, mock_evidence: EvidenceRecord
) -> None:
    repo = InMemoryReportRepository()
    report = CompanyResearchReport(
        research_id="res_comp_123",
        company=mock_company_profile,
        identity_status="resolved",
        findings=["Fast edge delivery."],
        evidence=[mock_evidence],
    )
    repo.save_report(report)

    result = await get_company_profile_tool({"research_reference": "res_comp_123"}, repo=repo)
    assert result["research_id"] == "res_comp_123"
    assert result["company"]["name"] == "Vercel"
    assert "Fast edge delivery." in result["findings"]


async def test_get_company_profile_tool_not_found() -> None:
    repo = InMemoryReportRepository()
    with pytest.raises(MCPResourceNotFoundError):
        await get_company_profile_tool({"research_reference": "non_existent"}, repo=repo)


# --- 4. find_decision_makers_tool ---
async def test_find_decision_makers_tool_success(
    mock_decision_maker: DecisionMaker, mock_evidence: EvidenceRecord
) -> None:
    mock_service = MagicMock(spec=PeopleResearchService)
    scored = ScoredDecisionMaker(
        person=mock_decision_maker,
        score=RelevanceScore(
            overall_score=95.0,
            tier=RelevanceTier.HIGH,
            rationale="Executive buyer",
        ),
    )
    report = DecisionMakerReport(
        research_id="dm_res_123",
        company_name="Vercel",
        company_domain="vercel.com",
        people=[mock_decision_maker],
        scored_people=[scored],
        evidence=[mock_evidence],
        discovery_summary=DiscoverySummary(),
    )
    mock_service.discover_decision_makers = AsyncMock(return_value=report)

    args = {
        "company_name": "Vercel",
        "target_departments": ["executive"],
        "seniority_levels": ["c_level"],
        "discovery_limit": 5,
    }
    result = await find_decision_makers_tool(args, people_service=mock_service)

    assert result["report"]["company_name"] == "Vercel"
    assert len(result["report"]["people"]) == 1
    assert result["report"]["people"][0]["full_name"] == "Guillermo Rauch"


# --- 5. verify_person_tool ---
async def test_verify_person_tool_success(
    mock_decision_maker: DecisionMaker, mock_evidence: EvidenceRecord
) -> None:
    repo = InMemoryReportRepository()
    report = DecisionMakerReport(
        research_id="dm_res_123",
        company_name="Vercel",
        company_domain="vercel.com",
        people=[mock_decision_maker],
        evidence=[mock_evidence],
        discovery_summary=DiscoverySummary(),
    )
    repo.save_decision_maker_report(report)

    mock_emp = MagicMock(spec=EmploymentVerificationService)
    mock_emp.verify_employment.return_value = (
        EmploymentStatus.CURRENT_EMPLOYMENT_VERIFIED,
        0.98,
        "Confirmed via company website.",
    )

    args = {"research_reference": "dm_res_123", "person_reference": "dm_test123"}
    result = await verify_person_tool(args, repo=repo, employment_service=mock_emp)

    assert result["full_name"] == "Guillermo Rauch"
    assert result["employment_status"] == EmploymentStatus.CURRENT_EMPLOYMENT_VERIFIED.value
    assert result["confidence_score"] == 0.98


# --- 6. get_person_details_tool ---
async def test_get_person_details_tool_success(
    mock_decision_maker: DecisionMaker, mock_evidence: EvidenceRecord
) -> None:
    repo = InMemoryReportRepository()
    report = DecisionMakerReport(
        research_id="dm_res_123",
        company_name="Vercel",
        company_domain="vercel.com",
        people=[mock_decision_maker],
        evidence=[mock_evidence],
        discovery_summary=DiscoverySummary(),
    )
    repo.save_decision_maker_report(report)

    args = {"research_reference": "dm_res_123", "person_reference": "dm_test123"}
    result = await get_person_details_tool(args, repo=repo)

    assert result["person"]["full_name"] == "Guillermo Rauch"
    assert result["person"]["title"] == "CEO"
    assert len(result["person"]["evidence"]) == 1


# --- 7. get_research_sources_tool ---
async def test_get_research_sources_tool(
    mock_company_profile: CompanyProfile, mock_evidence: EvidenceRecord
) -> None:
    repo = InMemoryReportRepository()
    report = CompanyResearchReport(
        research_id="res_comp_123",
        company=mock_company_profile,
        identity_status="resolved",
        findings=[],
        evidence=[mock_evidence],
    )
    repo.save_report(report)

    result = await get_research_sources_tool({"research_reference": "res_comp_123"}, repo=repo)
    assert result["total_sources"] == 1
    assert result["sources"][0]["source_url"] == "https://vercel.com/about"


# --- 8. get_decision_maker_sources_tool ---
async def test_get_decision_maker_sources_tool(
    mock_decision_maker: DecisionMaker, mock_evidence: EvidenceRecord
) -> None:
    repo = InMemoryReportRepository()
    report = DecisionMakerReport(
        research_id="dm_res_123",
        company_name="Vercel",
        company_domain="vercel.com",
        people=[mock_decision_maker],
        evidence=[mock_evidence],
        discovery_summary=DiscoverySummary(),
    )
    repo.save_decision_maker_report(report)

    result = await get_decision_maker_sources_tool({"research_reference": "dm_res_123"}, repo=repo)
    assert result["total_sources"] == 1
    assert result["sources"][0]["source_url"] == "https://vercel.com/about"


# --- 9. get_research_report_tool ---
async def test_get_research_report_tool_both_types(
    mock_company_profile: CompanyProfile,
    mock_decision_maker: DecisionMaker,
    mock_evidence: EvidenceRecord,
) -> None:
    repo = InMemoryReportRepository()
    comp_report = CompanyResearchReport(
        research_id="res_comp_123",
        company=mock_company_profile,
        identity_status="resolved",
        findings=["Global edge CDN."],
        evidence=[mock_evidence],
    )
    dm_report = DecisionMakerReport(
        research_id="dm_res_123",
        company_name="Vercel",
        company_domain="vercel.com",
        people=[mock_decision_maker],
        evidence=[mock_evidence],
        discovery_summary=DiscoverySummary(),
    )
    repo.save_report(comp_report)
    repo.save_decision_maker_report(dm_report)

    # Fetch company report
    c_res = await get_research_report_tool({"research_reference": "res_comp_123"}, repo=repo)
    assert c_res["report_type"] == "company"
    assert c_res["data"]["company"]["name"] == "Vercel"

    # Fetch DM report
    d_res = await get_research_report_tool({"research_reference": "dm_res_123"}, repo=repo)
    assert d_res["report_type"] == "decision_maker"
    assert d_res["data"]["company_name"] == "Vercel"
