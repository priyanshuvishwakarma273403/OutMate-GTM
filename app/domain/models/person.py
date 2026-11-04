"""Domain models representing discovered decision-makers and business prospects."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.domain.models.evidence import EvidenceRecord, VerificationStatus, utc_now


def generate_person_id() -> str:
    """Generate a unique identifier for a decision-maker entity."""
    return f"dm_{uuid.uuid4().hex[:12]}"


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


class EmploymentStatus(StrEnum):
    """Corroborated current employment state of a prospect."""

    CURRENT_EMPLOYMENT_VERIFIED = "current_employment_verified"
    CURRENT_EMPLOYMENT_PARTIALLY_VERIFIED = "current_employment_partially_verified"
    HISTORICAL_EMPLOYMENT = "historical_employment"
    EMPLOYMENT_NOT_VERIFIED = "employment_not_verified"
    CONFLICTING_EMPLOYMENT_EVIDENCE = "conflicting_employment_evidence"
    IDENTITY_AMBIGUOUS = "identity_ambiguous"


class DecisionInfluenceCategory(StrEnum):
    """Buying persona and purchasing influence classifications."""

    ECONOMIC_BUYER = "economic_buyer"
    TECHNICAL_DECISION_MAKER = "technical_decision_maker"
    BUSINESS_DECISION_MAKER = "business_decision_maker"
    CHAMPION = "champion"
    INFLUENCER = "influencer"
    EVALUATOR = "evaluator"
    PROCUREMENT_STAKEHOLDER = "procurement_stakeholder"
    EXECUTIVE_SPONSOR = "executive_sponsor"
    UNKNOWN = "unknown"


class RoleCategory(StrEnum):
    """High-level taxonomy category for GTM prospect roles."""

    EXECUTIVE = "executive"
    TECHNOLOGY = "technology"
    PROCUREMENT_FINANCE = "procurement_finance"
    PRODUCT_BUSINESS = "product_business"
    OTHER = "other"


class DecisionMakerAssessment(BaseModel):
    """Explainable decision influence and buying power evaluation."""

    person_id: str = Field(..., description="Target person identifier")
    role_category: RoleCategory = Field(
        default=RoleCategory.OTHER, description="Taxonomy classification"
    )
    decision_influence: DecisionInfluenceCategory = Field(
        default=DecisionInfluenceCategory.UNKNOWN,
        description="Purchasing role classification",
    )
    relevant_responsibilities: list[str] = Field(
        default_factory=list, description="Publicly documented responsibilities"
    )
    purchasing_relevance: str = Field(
        default="", description="Alignment with the specific purchasing scenario"
    )
    reasoning: str = Field(
        default="", description="Explainable factual rationale for the assigned influence"
    )
    assessment_status: str = Field(default="completed", description="Assessment completion status")
    supporting_evidence_ids: list[str] = Field(
        default_factory=list, description="IDs of evidence records corroborating this assessment"
    )


class ContactCoordinates(BaseModel):
    """Contact reference data identified from public disclosures."""

    email: str | None = Field(default=None, description="Public corporate contact email")
    phone: str | None = Field(default=None, description="Public corporate phone number")
    linkedin_url: str | None = Field(default=None, description="Public professional profile URL")
    twitter_handle: str | None = Field(default=None, description="Public Twitter/X handle")
    github_username: str | None = Field(default=None, description="Public GitHub handle")


class DecisionMaker(BaseModel):
    """Core domain model representing a decision-maker prospect in a target account."""

    person_id: str = Field(
        default_factory=generate_person_id,
        description="Stable unique identifier for this prospect",
    )
    full_name: str = Field(..., description="Full professional name of the person")
    company_name: str = Field(
        ..., description="Target company where person is currently affiliated"
    )
    company_domain: str | None = Field(
        default=None, description="Target company primary domain name"
    )
    title: str = Field(..., description="Exact discovered job title")
    normalized_title: str | None = Field(
        default=None, description="Clean normalized title mapped to organizational taxonomy"
    )
    seniority: SeniorityLevel = Field(
        default=SeniorityLevel.UNKNOWN, description="Normalized seniority tier"
    )
    department: Department = Field(
        default=Department.OTHER, description="Normalized departmental role"
    )
    employment_status: EmploymentStatus = Field(
        default=EmploymentStatus.EMPLOYMENT_NOT_VERIFIED,
        description="Corroborated current employment state",
    )
    location: str | None = Field(
        default=None, description="Disclosed city, region, or remote status"
    )
    biography: str | None = Field(
        default=None, description="Summary of public professional background"
    )
    biography_url: str | None = Field(
        default=None, description="URL of official biography or announcement"
    )
    contact_info: ContactCoordinates = Field(
        default_factory=ContactCoordinates, description="Discovered public contact coordinates"
    )
    assessment: DecisionMakerAssessment | None = Field(
        default=None, description="Decision influence and purchasing relevance assessment"
    )
    confidence_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall evidence confidence score"
    )
    confidence_explanation: str = Field(
        default="", description="Explainable breakdown of evidence backing this candidate"
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
