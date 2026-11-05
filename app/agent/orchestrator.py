"""Agent orchestrator coordinating the research lifecycle in Mode A (Standalone Agent)."""

from abc import ABC, abstractmethod

from app.agent.planner import BasePlanner, ResearchPlanner
from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.domain.models.company import CompanyProfile
from app.domain.models.report import GTMReport, ScoredDecisionMaker
from app.llm.base import BaseLLMClient
from app.mcp.client import OutmateMCPClient
from app.schemas.requests import ResearchQueryRequest
from app.services.report_generation import ReportGenerationService

logger = get_logger("agent.orchestrator")


class BaseAgentOrchestrator(ABC):
    """Contract for coordinating the autonomous research agent workflow."""

    @abstractmethod
    async def run_research(self, request: ResearchQueryRequest) -> GTMReport:
        """Execute autonomous end-to-end company and decision-maker research."""
        pass


class AgentOrchestrator(BaseAgentOrchestrator):
    """Coordinates autonomous research agent workflow in Mode A.

    Utilizes OpenRouter for model reasoning, decomposes queries with the Planner,
    and executes tools via OutmateMCPClient.
    """

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        mcp_client: OutmateMCPClient | None = None,
        planner: BasePlanner | None = None,
        report_service: ReportGenerationService | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm_client = llm_client
        self.mcp_client = mcp_client or OutmateMCPClient()
        self.planner = planner or ResearchPlanner(llm_client=llm_client, settings=self.settings)
        self.report_service = report_service or ReportGenerationService(settings=self.settings)

    async def run_research(self, request: ResearchQueryRequest) -> GTMReport:
        """Execute autonomous end-to-end company and decision-maker research via MCP."""
        logger.info("Starting Mode A agent research run for query: '%s'", request.query)

        # 1. Discover available tools from MCP
        tools = await self.mcp_client.list_tools()
        tool_names = {t.name for t in tools}
        logger.info("Discovered %d MCP tools for research execution: %s", len(tools), tool_names)

        # 2. Formulate execution plan
        plan = await self.planner.create_plan(request.query)
        logger.info("Created research plan for target company '%s'", plan.target_company)

        # 3. Execute company intelligence research tool
        company_profile: CompanyProfile | None = None
        if "research_company" in tool_names:
            logger.info("Executing MCP tool 'research_company' for '%s'", plan.target_company)
            company_args = {
                "company_name": plan.target_company,
                "company_domain": plan.target_domain,
                "research_depth": "standard",
            }
            res = await self.mcp_client.call_tool("research_company", company_args)
            report_data = res.data.get("report", {}) if isinstance(res.data, dict) else {}
            comp_data = report_data.get("company")
            if comp_data:
                try:
                    company_profile = CompanyProfile.model_validate(comp_data)
                except Exception as exc:
                    logger.warning("Failed to validate company profile: %s", exc)

        if not company_profile:
            domain = plan.target_domain or f"{plan.target_company.lower().replace(' ', '')}.com"
            company_profile = CompanyProfile(
                name=plan.target_company,
                domain=domain,
            )

        # 4. Execute decision-maker discovery tool
        scored_decision_makers: list[ScoredDecisionMaker] = []
        if "find_decision_makers" in tool_names:
            logger.info("Executing MCP tool 'find_decision_makers' for '%s'", plan.target_company)
            target_departments = [
                d.value if hasattr(d, "value") else str(d) for d in plan.target_departments
            ]
            if request.target_departments:
                target_departments.extend(request.target_departments)

            seniority_levels = [
                s.value if hasattr(s, "value") else str(s) for s in plan.target_seniority
            ]
            if request.target_seniority:
                seniority_levels.extend(request.target_seniority)

            dm_args = {
                "company_name": plan.target_company,
                "company_domain": company_profile.domain,
                "target_departments": list(set(target_departments)) or None,
                "seniority_levels": list(set(seniority_levels)) or None,
                "discovery_limit": request.max_decision_makers,
            }
            dm_res = await self.mcp_client.call_tool("find_decision_makers", dm_args)
            dm_report = dm_res.data.get("report", {}) if isinstance(dm_res.data, dict) else {}
            raw_scored = dm_report.get("scored_people", [])
            for item in raw_scored:
                try:
                    scored_decision_makers.append(ScoredDecisionMaker.model_validate(item))
                except Exception as exc:
                    logger.warning("Failed to validate scored decision maker: %s", exc)

        # 5. Synthesize final GTM intelligence report
        gtm_report = await self.report_service.generate_report(
            query=request.query,
            company=company_profile,
            decision_makers=scored_decision_makers,
            execution_mode="standalone_agent_mcp",
        )
        logger.info(
            "Completed Mode A research for '%s': %d decision-makers verified",
            company_profile.name,
            len(scored_decision_makers),
        )
        return gtm_report
