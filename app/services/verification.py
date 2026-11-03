"""Service interface and foundation for cross-source corroboration and verification."""

from abc import ABC, abstractmethod

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.domain.models.person import DecisionMaker
from app.integrations.search.base import BaseSearchClient

logger = get_logger("services.verification")


class BaseVerificationService(ABC):
    """Contract for verifying employment claims, titles, and public evidence."""

    @abstractmethod
    async def verify_person(
        self,
        person: DecisionMaker,
        company_name: str,
    ) -> DecisionMaker:
        """Cross-examine public sources to corroborate title, company affiliation, and activity."""
        pass


class VerificationService(BaseVerificationService):
    """Shared prospect verification and evidence corroboration service.

    Utilized identically by both Mode A (Standalone Agent) and Mode B (MCP Server).
    Actual cross-source verification logic is scheduled for Phase 2.
    """

    def __init__(
        self,
        search_client: BaseSearchClient | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self.search_client = search_client
        self.settings = settings or get_settings()

    async def verify_person(
        self,
        person: DecisionMaker,
        company_name: str,
    ) -> DecisionMaker:
        """Cross-examine public sources to corroborate title, company affiliation, and activity."""
        logger.info("Verifying employment status for %s at %s", person.full_name, company_name)
        raise NotImplementedError(
            "VerificationService.verify_person is scheduled for Phase 2 implementation."
        )
