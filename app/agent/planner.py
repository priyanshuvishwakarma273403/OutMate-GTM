"""Research planning and query decomposition for the standalone AI agent."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.domain.models.person import Department, SeniorityLevel
from app.llm.base import BaseLLMClient

logger = get_logger("agent.planner")


class ResearchPlan(BaseModel):
    """Structured execution plan formulated from a natural-language research query."""

    original_query: str = Field(..., description="Original user prompt")
    target_company: str = Field(..., description="Extracted company name")
    target_domain: str | None = Field(default=None, description="Inferred or extracted domain")
    target_seniority: list[SeniorityLevel] = Field(
        default_factory=list, description="Targeted seniority tiers"
    )
    target_departments: list[Department] = Field(
        default_factory=list, description="Targeted department functions"
    )
    execution_steps: list[str] = Field(
        default_factory=list, description="Sequential tool execution steps planned"
    )


class BasePlanner(ABC):
    """Contract for decomposing queries into executable research plans."""

    @abstractmethod
    async def create_plan(self, query: str) -> ResearchPlan:
        """Decompose a natural language query into a structured ResearchPlan."""
        pass


class ResearchPlanner(BasePlanner):
    """Planner analyzing queries and formulating structured GTM execution plans."""

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.settings = settings or get_settings()

    async def create_plan(self, query: str) -> ResearchPlan:
        """Decompose a natural language query into a structured ResearchPlan."""
        logger.info("Formulating research plan for query: '%s'", query)
        raise NotImplementedError(
            "ResearchPlanner.create_plan is scheduled for Phase 2 implementation."
        )
