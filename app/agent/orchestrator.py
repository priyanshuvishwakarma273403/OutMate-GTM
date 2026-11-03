"""Agent orchestrator coordinating the research lifecycle in Mode A (Standalone Agent)."""

from abc import ABC, abstractmethod

from app.agent.planner import BasePlanner, ResearchPlanner
from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.domain.models.report import GTMReport
from app.llm.base import BaseLLMClient
from app.mcp.client import OutmateMCPClient
from app.schemas.requests import ResearchQueryRequest

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
    and executes tools via MCP Client or shared services.
    """

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        mcp_client: OutmateMCPClient | None = None,
        planner: BasePlanner | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.mcp_client = mcp_client or OutmateMCPClient()
        self.planner = planner or ResearchPlanner(llm_client=llm_client, settings=settings)
        self.settings = settings or get_settings()

    async def run_research(self, request: ResearchQueryRequest) -> GTMReport:
        """Execute autonomous end-to-end company and decision-maker research."""
        logger.info("Starting Mode A agent research run for query: '%s'", request.query)
        raise NotImplementedError(
            "AgentOrchestrator.run_research is scheduled for Phase 2 implementation."
        )
