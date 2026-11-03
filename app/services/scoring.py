"""Service interface and foundation for decision-maker relevance scoring."""

from abc import ABC, abstractmethod

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.domain.models.person import DecisionMaker, Department, SeniorityLevel
from app.domain.models.report import RelevanceScore, ScoredDecisionMaker

logger = get_logger("services.scoring")


class BaseScoringService(ABC):
    """Contract for calculating prospect relevance scores based on GTM query criteria."""

    @abstractmethod
    async def score_decision_maker(
        self,
        person: DecisionMaker,
        query_context: str,
        target_seniority: list[SeniorityLevel] | None = None,
        target_departments: list[Department] | None = None,
    ) -> RelevanceScore:
        """Compute multi-dimensional relevance score (0-100) for a candidate."""
        pass

    @abstractmethod
    async def rank_decision_makers(
        self,
        people: list[DecisionMaker],
        query_context: str,
        target_seniority: list[SeniorityLevel] | None = None,
        target_departments: list[Department] | None = None,
    ) -> list[ScoredDecisionMaker]:
        """Score and sort decision-makers in descending order of buying relevance."""
        pass


class ScoringService(BaseScoringService):
    """Shared decision-maker relevance and persona alignment scoring service.

    Utilized identically by both Mode A (Standalone Agent) and Mode B (MCP Server).
    Actual scoring heuristics and weights are scheduled for Phase 2.
    """

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or get_settings()

    async def score_decision_maker(
        self,
        person: DecisionMaker,
        query_context: str,
        target_seniority: list[SeniorityLevel] | None = None,
        target_departments: list[Department] | None = None,
    ) -> RelevanceScore:
        """Compute multi-dimensional relevance score (0-100) for a candidate."""
        logger.info("Computing relevance score for: %s", person.full_name)
        raise NotImplementedError(
            "ScoringService.score_decision_maker is scheduled for Phase 2 implementation."
        )

    async def rank_decision_makers(
        self,
        people: list[DecisionMaker],
        query_context: str,
        target_seniority: list[SeniorityLevel] | None = None,
        target_departments: list[Department] | None = None,
    ) -> list[ScoredDecisionMaker]:
        """Score and sort decision-makers in descending order of buying relevance."""
        logger.info("Ranking %d decision-makers against query context", len(people))
        raise NotImplementedError(
            "ScoringService.rank_decision_makers is scheduled for Phase 2 implementation."
        )
