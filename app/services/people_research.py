"""Service interface and foundation for executive and decision-maker discovery."""

from abc import ABC, abstractmethod

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.domain.models.person import DecisionMaker, Department, SeniorityLevel
from app.integrations.search.base import BaseSearchClient

logger = get_logger("services.people_research")


class BasePeopleResearchService(ABC):
    """Contract for discovering and investigating business decision-makers."""

    @abstractmethod
    async def find_decision_makers(
        self,
        company_name: str,
        company_domain: str | None = None,
        target_seniority: list[SeniorityLevel] | None = None,
        target_departments: list[Department] | None = None,
        limit: int = 10,
    ) -> list[DecisionMaker]:
        """Discover key decision-makers affiliated with target company."""
        pass

    @abstractmethod
    async def get_person_details(
        self,
        full_name: str,
        company_name: str,
        linkedin_url: str | None = None,
    ) -> DecisionMaker:
        """Retrieve detailed background, contact coordinates, and evidence for a specific person."""
        pass


class PeopleResearchService(BasePeopleResearchService):
    """Shared executive and decision-maker research service.

    Utilized identically by both Mode A (Standalone Agent) and Mode B (MCP Server).
    Actual prospect discovery heuristics are scheduled for Phase 2.
    """

    def __init__(
        self,
        search_client: BaseSearchClient | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self.search_client = search_client
        self.settings = settings or get_settings()

    async def find_decision_makers(
        self,
        company_name: str,
        company_domain: str | None = None,
        target_seniority: list[SeniorityLevel] | None = None,
        target_departments: list[Department] | None = None,
        limit: int = 10,
    ) -> list[DecisionMaker]:
        """Discover key decision-makers affiliated with target company."""
        logger.info("Executing decision-maker discovery for company: %s", company_name)
        raise NotImplementedError(
            "PeopleResearchService.find_decision_makers is scheduled for Phase 2 implementation."
        )

    async def get_person_details(
        self,
        full_name: str,
        company_name: str,
        linkedin_url: str | None = None,
    ) -> DecisionMaker:
        """Retrieve detailed background, contact coordinates, and evidence for a specific person."""
        logger.info("Retrieving details for person: %s at %s", full_name, company_name)
        raise NotImplementedError(
            "PeopleResearchService.get_person_details is scheduled for Phase 2 implementation."
        )
