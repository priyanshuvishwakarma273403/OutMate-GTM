"""In-memory research report storage repository for active application sessions."""

from typing import Protocol

from app.schemas.responses import CompanyResearchReport


class ReportRepositoryProtocol(Protocol):
    """Contract for persisting and retrieving research reports."""

    def save(self, report: CompanyResearchReport) -> None:
        """Store a completed research report."""
        ...

    def get(self, research_id: str) -> CompanyResearchReport | None:
        """Retrieve a research report by ID."""
        ...


class InMemoryReportRepository:
    """Thread-safe in-memory report store for single-process deployments."""

    def __init__(self, max_size: int = 1000) -> None:
        self._reports: dict[str, CompanyResearchReport] = {}
        self.max_size = max_size

    def save(self, report: CompanyResearchReport) -> None:
        """Store a completed report; evicts oldest if capacity exceeded."""
        if len(self._reports) >= self.max_size:
            # Evict first key
            first_key = next(iter(self._reports))
            del self._reports[first_key]
        self._reports[report.research_id] = report

    def get(self, research_id: str) -> CompanyResearchReport | None:
        """Retrieve report by research_id."""
        return self._reports.get(research_id)


_global_report_repo = InMemoryReportRepository()


def get_report_repository() -> InMemoryReportRepository:
    """Provide singleton report repository instance."""
    return _global_report_repo

