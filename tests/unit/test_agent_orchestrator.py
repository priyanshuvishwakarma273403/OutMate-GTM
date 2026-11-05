"""Unit tests for Mode A Agent Orchestrator and Research Planner."""

from unittest.mock import AsyncMock, MagicMock

from app.agent.orchestrator import AgentOrchestrator
from app.agent.planner import ResearchPlanner
from app.domain.models import (
    CompanyProfile,
    DecisionMaker,
    Department,
    EmploymentStatus,
    SeniorityLevel,
)
from app.domain.models.report import GTMReport, RelevanceScore, RelevanceTier, ScoredDecisionMaker
from app.mcp.client import OutmateMCPClient
from app.mcp.schemas.common import MCPToolResult
from app.schemas.requests import ResearchQueryRequest


async def test_planner_heuristic_query_decomposition() -> None:
    """Verify ResearchPlanner extracts company, domain, department, and seniority without LLM."""
    planner = ResearchPlanner()

    # Query with company and domain
    plan1 = await planner.create_plan(
        "Who are the decision makers in the company Vercel (vercel.com)?"
    )
    assert plan1.target_company.lower() == "vercel"
    assert plan1.target_domain == "vercel.com"
    assert "research_company" in plan1.execution_steps

    # Query with engineering and vp
    plan2 = await planner.create_plan("Find VP of Engineering at Stripe")
    assert "stripe" in plan2.target_company.lower()
    assert SeniorityLevel.VP in plan2.target_seniority
    assert Department.ENGINEERING in plan2.target_departments


async def test_agent_orchestrator_execution() -> None:
    """Verify AgentOrchestrator coordinates MCP client to research company and decision makers."""
    mock_mcp_client = MagicMock(spec=OutmateMCPClient)

    # 1. Mock list_tools
    mock_tool1 = MagicMock()
    mock_tool1.name = "research_company"
    mock_tool2 = MagicMock()
    mock_tool2.name = "find_decision_makers"
    mock_mcp_client.list_tools = AsyncMock(return_value=[mock_tool1, mock_tool2])

    # 2. Mock call_tool for research_company and find_decision_makers
    company_profile = CompanyProfile(
        name="Vercel",
        domain="vercel.com",
        description="Frontend cloud platform.",
    )
    mock_person = DecisionMaker(
        person_id="dm_orchestrator_1",
        full_name="Guillermo Rauch",
        company_name="Vercel",
        title="CEO",
        employment_status=EmploymentStatus.CURRENT_EMPLOYMENT_VERIFIED,
    )
    scored_person = ScoredDecisionMaker(
        person=mock_person,
        score=RelevanceScore(overall_score=95.0, tier=RelevanceTier.HIGH, rationale="Key buyer"),
    )

    async def mock_call_tool(tool_name: str, args: dict) -> MCPToolResult:
        if tool_name == "research_company":
            return MCPToolResult(
                data={"report": {"company": company_profile.model_dump()}},
            )
        elif tool_name == "find_decision_makers":
            return MCPToolResult(
                data={"report": {"scored_people": [scored_person.model_dump()]}},
            )
        return MCPToolResult(data={})

    mock_mcp_client.call_tool = AsyncMock(side_effect=mock_call_tool)

    orchestrator = AgentOrchestrator(mcp_client=mock_mcp_client)
    request = ResearchQueryRequest(query="Who are the decision makers in Vercel?")

    report = await orchestrator.run_research(request)

    assert isinstance(report, GTMReport)
    assert report.company.name == "Vercel"
    assert len(report.decision_makers) == 1
    assert report.decision_makers[0].person.full_name == "Guillermo Rauch"
    assert report.execution_mode == "standalone_agent_mcp"
    assert mock_mcp_client.list_tools.awaited
    assert mock_mcp_client.call_tool.await_count == 2
