"""Shared GTM research and intelligence service layer."""

from app.services.company_identity import (
    CompanyIdentityResolution,
    CompanyIdentityResolutionService,
    IdentityResolutionStatus,
)
from app.services.company_research import (
    CompanyResearchService,
)
from app.services.content_extraction import (
    ContentExtractionService,
    ExtractedPageContent,
)
from app.services.llm import LLMService
from app.services.people_research import (
    BasePeopleResearchService,
    PeopleResearchService,
)
from app.services.report_generation import (
    BaseReportGenerationService,
    ReportGenerationService,
)
from app.services.report_storage import (
    InMemoryReportRepository,
    get_report_repository,
)
from app.services.scoring import BaseScoringService, ScoringService
from app.services.source_normalization import (
    classify_source_type,
    deduplicate_urls,
    extract_domain_from_url,
    normalize_url,
)
from app.services.source_retrieval import (
    RetrievedSource,
    SourceRetrievalService,
)
from app.services.verification import VerificationService

__all__ = [
    "BasePeopleResearchService",
    "BaseReportGenerationService",
    "BaseScoringService",
    "CompanyIdentityResolution",
    "CompanyIdentityResolutionService",
    "CompanyResearchService",
    "ContentExtractionService",
    "ExtractedPageContent",
    "IdentityResolutionStatus",
    "InMemoryReportRepository",
    "LLMService",
    "PeopleResearchService",
    "ReportGenerationService",
    "RetrievedSource",
    "ScoringService",
    "SourceRetrievalService",
    "VerificationService",
    "classify_source_type",
    "deduplicate_urls",
    "extract_domain_from_url",
    "get_report_repository",
    "normalize_url",
]
