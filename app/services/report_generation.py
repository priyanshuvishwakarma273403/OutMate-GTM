"""Service interface and foundation for GTM intelligence report synthesis."""

from abc import ABC, abstractmethod

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.domain.models.company import CompanyProfile
from app.domain.models.report import GTMReport, ScoredDecisionMaker
from app.llm.base import BaseLLMClient

logger = get_logger("services.report_generation")


class BaseReportGenerationService(ABC):
    """Contract for compiling structured GTM intelligence dossiers and summaries."""

    @abstractmethod
    async def generate_report(
        self,
        query: str,
        company: CompanyProfile,
        decision_makers: list[ScoredDecisionMaker],
        execution_mode: str = "standalone_agent",
    ) -> GTMReport:
        """Synthesize structured research report with narrative summary and key findings."""
        pass

    @abstractmethod
    def export_markdown(self, report: GTMReport) -> str:
        """Render a GTMReport instance into executive-ready GitHub-flavored markdown."""
        pass


class ReportGenerationService(BaseReportGenerationService):
    """Shared report generation and intelligence synthesis service.

    Utilized identically by both Mode A (Standalone Agent) and Mode B (MCP Server).
    Actual LLM report synthesis and templating are scheduled for Phase 2.
    """

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.settings = settings or get_settings()

    async def generate_report(
        self,
        query: str,
        company: CompanyProfile,
        decision_makers: list[ScoredDecisionMaker],
        execution_mode: str = "standalone_agent",
    ) -> GTMReport:
        """Synthesize structured research report with narrative summary and key findings."""
        logger.info(
            "Generating GTM intelligence report for: %s (mode: %s)",
            company.name,
            execution_mode,
        )
        raise NotImplementedError(
            "ReportGenerationService.generate_report is scheduled for Phase 2 implementation."
        )

    def export_markdown(self, report: GTMReport) -> str:
        """Render a GTMReport instance into executive-ready GitHub-flavored markdown."""
        logger.info("Exporting report for: %s to markdown", report.company.name)
        raise NotImplementedError(
            "ReportGenerationService.export_markdown is scheduled for Phase 2 implementation."
        )
