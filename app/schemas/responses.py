"""API response schemas for health, readiness, and service outputs."""

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.domain.models.company import CompanyProfile
from app.domain.models.evidence import EvidenceRecord
from app.domain.models.person import DecisionMaker
from app.domain.models.report import ScoredDecisionMaker
from app.llm.base import TokenUsage

T = TypeVar("T")


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(UTC)


class HealthResponse(BaseModel):
    """Liveness probe response model."""

    status: str = Field(default="ok", description="Overall application health status")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Runtime environment")
    timestamp: datetime = Field(default_factory=utc_now, description="Time of health verification")


class DependencyHealth(BaseModel):
    """Health status descriptor for an individual subsystem or external dependency."""

    name: str = Field(..., description="Dependency identifier (e.g. openrouter, nango, search)")
    status: str = Field(
        ..., description="Operational status: 'healthy', 'degraded', 'not_configured', 'unhealthy'"
    )
    details: str | None = Field(default=None, description="Non-sensitive operational details")


class ReadinessResponse(BaseModel):
    """Readiness probe response model reporting dependency readiness without exposing credentials."""

    status: str = Field(..., description="Overall readiness: 'ready', 'degraded', or 'not_ready'")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(default_factory=utc_now, description="Time of readiness evaluation")
    dependencies: dict[str, DependencyHealth] = Field(
        default_factory=dict, description="Status of configured subsystems"
    )


class APIResponse(BaseModel, Generic[T]):
    """Standardized envelope for successful API responses."""

    success: bool = Field(default=True, description="Whether the operation succeeded")
    data: T = Field(..., description="Payload data")
    message: str | None = Field(default=None, description="Optional informational message")
    timestamp: datetime = Field(default_factory=utc_now, description="Timestamp of response")


class ErrorDetail(BaseModel):
    """Structured error payload for failed requests."""

    error_type: str = Field(..., description="Categorical error identifier")
    message: str = Field(..., description="Human-readable explanation of the error")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Contextual debugging information"
    )


class ErrorResponse(BaseModel):
    """Standardized envelope for error responses."""

    success: bool = Field(default=False, description="Always False on error")
    error: ErrorDetail = Field(..., description="Detailed error information")
    timestamp: datetime = Field(
        default_factory=utc_now, description="Timestamp of error occurrence"
    )


class LLMTestResponse(BaseModel):
    """Response model for LLM completion test endpoint."""

    status: str = Field(default="success", description="Status indicator of the completion request")
    model: str = Field(..., description="Model identifier that produced the completion")
    content: str = Field(..., description="Generated text content from the language model")
    usage: TokenUsage = Field(
        default_factory=TokenUsage,
        description="Token consumption metrics for the request",
    )
    duration_ms: float | None = Field(
        default=None,
        description="Round-trip request execution duration in milliseconds",
    )
    timestamp: datetime = Field(
        default_factory=utc_now, description="Timestamp of completion response"
    )


class SourceMetadata(BaseModel):
    """Metadata regarding a discovered public source."""

    url: str = Field(..., description="Canonical source URL")
    title: str = Field(default="", description="Web page or document title")
    source_type: str = Field(default="other", description="Evidence classification")
    retrieved: bool = Field(default=False, description="Whether HTML content was fetched")
    status_code: int = Field(default=0, description="HTTP response status")


class SourceSummary(BaseModel):
    """Overview of source discovery, retrieval, and filtering metrics."""

    sources_discovered: int = Field(default=0, description="Total unique URLs found via search")
    sources_retrieved: int = Field(default=0, description="Count of successfully retrieved pages")
    sources_rejected: int = Field(default=0, description="Count of inaccessible or blocked pages")
    sources: list[SourceMetadata] = Field(
        default_factory=list, description="Detailed list of discovered sources"
    )


class CompanyResearchReport(BaseModel):
    """Machine-readable comprehensive corporate research dossier."""

    research_id: str = Field(..., description="Unique UUID for this research run")
    company: CompanyProfile = Field(..., description="Researched company profile")
    identity_status: str = Field(..., description="Status of identity and domain resolution")
    findings: list[str] = Field(
        default_factory=list, description="Key factual findings corroborated by evidence"
    )
    evidence: list[EvidenceRecord] = Field(
        default_factory=list, description="Traceable evidence items with original citations"
    )
    source_summary: SourceSummary = Field(
        default_factory=SourceSummary, description="Audit trail of discovered and fetched sources"
    )
    limitations: list[str] = Field(
        default_factory=list, description="Documented knowledge gaps and limitations"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Ambiguity or conflict warnings identified during research",
    )
    overall_status: str = Field(
        default="completed", description="Execution status: completed, partially_completed, failed"
    )
    created_at: datetime = Field(
        default_factory=utc_now, description="Timestamp when research initiated"
    )
    completed_at: datetime = Field(
        default_factory=utc_now, description="Timestamp when research completed"
    )
    duration_ms: float = Field(default=0.0, description="Total research duration in milliseconds")


class CompanyPreviewResponse(BaseModel):
    """Response payload for company preview request."""

    company_name: str = Field(..., description="Original company name queried")
    normalized_name: str = Field(..., description="Normalized corporate search token")
    supplied_domain: str | None = Field(
        default=None, description="User supplied domain if provided"
    )
    resolved_domain: str | None = Field(default=None, description="Discovered official domain")
    official_website: str | None = Field(default=None, description="Discovered homepage URL")
    resolution_status: str = Field(..., description="Resolved, Ambiguous, or Unresolved")
    confidence: float = Field(..., description="Confidence score in identity resolution")
    planned_search_queries: list[str] = Field(
        default_factory=list, description="Targeted queries generated for the research plan"
    )
    candidate_domains: list[str] = Field(
        default_factory=list, description="Candidate domains discovered"
    )


class DiscoverySummary(BaseModel):
    """Metrics and statistics summarizing the decision-maker discovery run."""

    search_queries_executed: list[str] = Field(
        default_factory=list, description="List of search queries dispatched"
    )
    sources_retrieved: int = Field(default=0, description="Total web sources retrieved")
    candidates_discovered: int = Field(
        default=0, description="Raw candidates identified in source text"
    )
    candidates_verified: int = Field(
        default=0, description="Candidates with verified or partially verified employment"
    )
    candidates_excluded: int = Field(
        default=0, description="Candidates excluded due to departure or insufficient evidence"
    )
    duplicate_candidates_merged: int = Field(
        default=0, description="Count of duplicate candidate profiles merged"
    )


class DecisionMakerReport(BaseModel):
    """Comprehensive evidence-backed decision-maker research dossier."""

    research_id: str = Field(..., description="Unique UUID for this discovery run")
    company_name: str = Field(..., description="Target corporate name")
    company_domain: str = Field(..., description="Corporate primary domain")
    people: list[DecisionMaker] = Field(
        default_factory=list, description="Identified and verified decision-maker prospects"
    )
    scored_people: list[ScoredDecisionMaker] = Field(
        default_factory=list, description="Prospects ranked by GTM purchasing relevance"
    )
    evidence: list[EvidenceRecord] = Field(
        default_factory=list, description="All supporting public evidence records"
    )
    discovery_summary: DiscoverySummary = Field(
        default_factory=DiscoverySummary, description="Audit metrics of the research pass"
    )
    limitations: list[str] = Field(
        default_factory=list, description="Documented knowledge gaps and limitations"
    )
    excluded_candidates_summary: list[str] = Field(
        default_factory=list, description="Summary of excluded historical or ambiguous candidates"
    )
    warnings: list[str] = Field(
        default_factory=list, description="Ambiguity and data quality warnings"
    )
    overall_status: str = Field(
        default="completed", description="Execution status: completed, partially_completed, failed"
    )
    created_at: datetime = Field(
        default_factory=utc_now, description="Timestamp when discovery initiated"
    )
    completed_at: datetime = Field(
        default_factory=utc_now, description="Timestamp when discovery completed"
    )
    duration_ms: float = Field(default=0.0, description="Execution duration in milliseconds")


class DecisionMakerPreviewResponse(BaseModel):
    """Preview response outlining decision-maker search strategy."""

    company_name: str = Field(..., description="Target company name")
    company_domain: str | None = Field(default=None, description="Resolved corporate domain")
    target_departments: list[str] = Field(
        default_factory=list, description="Departments prioritized for discovery"
    )
    planned_search_queries: list[str] = Field(
        default_factory=list, description="Search queries formulated for the plan"
    )
    estimated_role_targets: list[str] = Field(
        default_factory=list, description="Job titles and personas targeted"
    )
