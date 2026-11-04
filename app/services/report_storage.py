"""In-memory research report storage repository for active application sessions."""

from typing import Protocol

from app.domain.models.person import DecisionMaker
from app.schemas.responses import CompanyResearchReport, DecisionMakerReport


class ReportRepositoryProtocol(Protocol):
    """Contract for persisting and retrieving research reports."""

    def save(self, report: CompanyResearchReport) -> None:
        """Store a completed company research report."""
        ...

    def get(self, research_id: str) -> CompanyResearchReport | None:
        """Retrieve a company research report by ID."""
        ...


class InMemoryReportRepository:
    """Thread-safe in-memory report store for single-process deployments."""

    def __init__(self, max_size: int = 1000) -> None:
        self._reports: dict[str, CompanyResearchReport] = {}
        self._dm_reports: dict[str, DecisionMakerReport] = {}
        self.max_size = max_size

    def save(self, report: CompanyResearchReport) -> None:
        """Store a completed company report; evicts oldest if capacity exceeded."""
        if len(self._reports) >= self.max_size:
            first_key = next(iter(self._reports))
            del self._reports[first_key]
        self._reports[report.research_id] = report

    def get(self, research_id: str) -> CompanyResearchReport | None:
        """Retrieve company report by research_id."""
        return self._reports.get(research_id)

    def save_decision_maker_report(self, report: DecisionMakerReport) -> None:
        """Store a completed decision-maker report."""
        if len(self._dm_reports) >= self.max_size:
            first_key = next(iter(self._dm_reports))
            del self._dm_reports[first_key]
        self._dm_reports[report.research_id] = report

    def get_decision_maker_report(self, research_id: str) -> DecisionMakerReport | None:
        """Retrieve decision-maker report by research_id."""
        return self._dm_reports.get(research_id)

    def get_person(self, research_id: str, person_id: str) -> DecisionMaker | None:
        """Retrieve a specific discovered person within a research report."""
        report = self.get_decision_maker_report(research_id)
        if not report:
            return None
        for person in report.people:
            if person.person_id == person_id:
                return person
        return None


_global_report_repo = InMemoryReportRepository()


def get_report_repository() -> InMemoryReportRepository:
    """Provide singleton report repository instance."""
    return _global_report_repo
