"""Domain models representing discovered decision-makers and business prospects."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.domain.models.evidence import EvidenceRecord, VerificationStatus, utc_now


class SeniorityLevel(StrEnum):
    """Hierarchical seniority classifications for GTM prospect targeting."""

    C_LEVEL = "c_level"  # CEO, CTO, CRO, CMO, CFO, CPO, CIO, CISO
    VP = "vp"  # VP, SVP, EVP
    HEAD = "head"  # Head of Engineering, Head of Sales, etc.
    DIRECTOR = "director"  # Director of Infrastructure, Director of Growth
    MANAGER = "manager"  # Engineering Manager, Team Lead
    INDIVIDUAL_CONTRIBUTOR = "ic"  # Staff Engineer, Account Executive
    UNKNOWN = "unknown"


class Department(StrEnum):
    """Standardized departmental functions for B2B targeting."""

    EXECUTIVE = "executive"
    ENGINEERING = "engineering"
    PRODUCT = "product"
    SALES = "sales"
    MARKETING = "marketing"
    FINANCE = "finance"
    SECURITY = "security"
    OPERATIONS = "operations"
    HUMAN_RESOURCES = "human_resources"
    LEGAL = "legal"
    OTHER = "other"


class ContactCoordinates(BaseModel):
    """Contact reference data identified from public disclosures."""

    email: str | None = Field(default=None, description="Public or corporate contact email")
    phone: str | None = Field(default=None, description="Public corporate phone number")
    linkedin_url: str | None = Field(default=None, description="Public LinkedIn profile URL")
    twitter_handle: str | None = Field(default=None, description="Public Twitter/X handle")
    github_username: str | None = Field(default=None, description="Public GitHub handle")


class DecisionMaker(BaseModel):
    """Core domain model representing a decision-maker prospect in a target account."""

    full_name: str = Field(..., description="Full professional name of the person")
    company_name: str = Field(
        ..., description="Target company where person is currently affiliated"
    )
    company_domain: str | None = Field(
        default=None, description="Target company primary domain name"
    )
    title: str = Field(..., description="Exact discovered job title")
    seniority: SeniorityLevel = Field(
        default=SeniorityLevel.UNKNOWN, description="Normalized seniority tier"
    )
    department: Department = Field(
        default=Department.OTHER, description="Normalized departmental role"
    )
    location: str | None = Field(
        default=None, description="Disclosed city, region, or remote status"
    )
    contact_info: ContactCoordinates = Field(
        default_factory=ContactCoordinates, description="Discovered contact coordinates"
    )
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED, description="Current verification level"
    )
    evidence: list[EvidenceRecord] = Field(
        default_factory=list,
        description="Public evidence supporting the person's current role and title",
    )
    first_identified_at: datetime = Field(
        default_factory=utc_now, description="Timestamp when entity was discovered"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional role-specific research metadata"
    )
