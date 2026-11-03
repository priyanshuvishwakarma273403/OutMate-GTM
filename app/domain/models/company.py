"""Domain models representing companies and corporate intelligence."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.domain.models.evidence import EvidenceRecord, utc_now


class IndustryCategory(StrEnum):
    """High-level B2B industry classifications."""

    SAAS_SOFTWARE = "saas_software"
    FINTECH = "fintech"
    AI_ML = "ai_ml"
    CYBERSECURITY = "cybersecurity"
    CLOUD_INFRASTRUCTURE = "cloud_infrastructure"
    E_COMMERCE = "e_commerce"
    HEALTHCARE_TECH = "healthcare_tech"
    ENTERPRISE_SERVICES = "enterprise_services"
    OTHER = "other"


class CompanyFundingStage(StrEnum):
    """Corporate funding stages."""

    BOOTSTRAPPED = "bootstrapped"
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C_PLUS = "series_c_plus"
    PUBLIC = "public"
    ACQUIRED = "acquired"
    UNKNOWN = "unknown"


class CompanyProfile(BaseModel):
    """Core domain model representing a researched target company."""

    name: str = Field(..., description="Canonical name of the company")
    domain: str = Field(..., description="Primary corporate domain name, e.g. 'vercel.com'")
    legal_name: str | None = Field(default=None, description="Registered legal corporate name")
    description: str | None = Field(
        default=None, description="Concise summary of business activities and value proposition"
    )
    industry: IndustryCategory = Field(
        default=IndustryCategory.OTHER, description="Primary industry categorization"
    )
    headquarters: str | None = Field(
        default=None, description="Primary office city, state, and country"
    )
    estimated_headcount: int | None = Field(
        default=None, ge=1, description="Estimated total number of employees"
    )
    founded_year: int | None = Field(
        default=None, ge=1800, le=2100, description="Year company was founded"
    )
    funding_stage: CompanyFundingStage = Field(
        default=CompanyFundingStage.UNKNOWN, description="Known funding stage"
    )
    tech_stack: list[str] = Field(
        default_factory=list, description="Publicly identified developer or software tools used"
    )
    evidence: list[EvidenceRecord] = Field(
        default_factory=list,
        description="Collection of evidence records backing this company profile",
    )
    last_researched_at: datetime = Field(
        default_factory=utc_now, description="Timestamp of most recent research pass"
    )
    raw_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extensible metadata from intelligence sources"
    )
