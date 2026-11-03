"""Service interface and foundation for company intelligence research."""

from abc import ABC, abstractmethod

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.domain.models.company import CompanyProfile
from app.integrations.search.base import BaseSearchClient

logger = get_logger("services.company_research")


class BaseCompanyResearchService(ABC):
    """Contract for researching company background, domain, headcount, and tech stack."""

    @abstractmethod
    async def research_company(
        self,
        company_name: str,
        domain: str | None = None,
    ) -> CompanyProfile:
        """Conduct comprehensive public research on a target company."""
        pass


class CompanyResearchService(BaseCompanyResearchService):
    """Shared company intelligence research service.

    Utilized identically by both Mode A (Standalone Agent) and Mode B (MCP Server).
    Actual multi-source search and entity resolution is scheduled for Phase 2.
    """

    def __init__(
        self,
        search_client: BaseSearchClient | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self.search_client = search_client
        self.settings = settings or get_settings()

    async def research_company(
        self,
        company_name: str,
        domain: str | None = None,
    ) -> CompanyProfile:
        """Conduct comprehensive public research on a target company."""
        logger.info("Executing company research for: %s (domain: %s)", company_name, domain)
        raise NotImplementedError(
            "CompanyResearchService.research_company is scheduled for Phase 2 implementation."
        )
