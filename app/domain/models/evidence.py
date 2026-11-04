"""Domain models for public-source evidence and verification records."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(UTC)


def generate_evidence_id() -> str:
    """Generate a unique identifier for an evidence record."""
    return f"ev_{uuid.uuid4().hex[:12]}"


class EvidenceSourceType(StrEnum):
    """Categorized origins of research evidence."""

    OFFICIAL_WEBSITE = "official_website"
    PRESS_RELEASE = "press_release"
    SEC_FILING = "sec_filing"
    LINKEDIN_PUBLIC = "linkedin_public"
    NEWS_ARTICLE = "news_article"
    JOB_POSTING = "job_posting"
    CONFERENCE_TALK = "conference_talk"
    PUBLIC_REGISTRY = "public_registry"
    OTHER = "other"


class VerificationStatus(StrEnum):
    """Status indicating corroboration level of evidence."""

    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    NOT_VERIFIED = "not_verified"
    CONFLICTING = "conflicting"
    UNAVAILABLE = "unavailable"
    UNVERIFIED = "unverified"
    DISPUTED = "disputed"
    OBSOLETE = "obsolete"


class EvidenceRecord(BaseModel):
    """A granular piece of verifiable evidence corroborating a company or person attribute."""

    evidence_id: str = Field(
        default_factory=generate_evidence_id, description="Unique identifier for this evidence record"
    )
    source_url: str = Field(..., description="Canonical URL where the evidence was found")
    source_type: EvidenceSourceType = Field(
        default=EvidenceSourceType.OTHER, description="Classification of the data source"
    )
    title: str | None = Field(default=None, description="Title of the source page or document")
    claim_type: str | None = Field(
        default=None, description="Category of claim (identity, employment, role, responsibilities)"
    )
    claim: str | None = Field(default=None, description="Factual claim or attribute corroborated")
    snippet: str = Field(..., description="Exact textual excerpt supporting the finding")
    captured_at: datetime = Field(
        default_factory=utc_now, description="Timestamp when evidence was retrieved"
    )
    publication_date: datetime | None = Field(
        default=None, description="Discovered original publication date"
    )
    confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence score for this specific piece of evidence (0.0 - 1.0)",
    )
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED,
        description="Verification state after cross-source corroboration",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional provider-specific metadata"
    )
