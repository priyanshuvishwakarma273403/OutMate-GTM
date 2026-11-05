"""Pydantic schemas for decision-maker discovery, verification, and profile MCP tools."""

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.models.person import DecisionMaker
from app.schemas.responses import DecisionMakerReport


class FindDecisionMakersInput(BaseModel):
    """Input parameters for evidence-backed decision-maker discovery."""

    company_name: str = Field(..., min_length=2, max_length=200, description="Target company name")
    company_domain: str | None = Field(default=None, description="Optional target corporate domain")
    product_context: str | None = Field(
        default=None,
        description="Commercial solution or product context for purchasing persona alignment",
    )
    target_departments: list[str] = Field(
        default_factory=list, description="Targeted departments (e.g. ['engineering', 'executive'])"
    )
    target_roles: list[str] = Field(
        default_factory=list, description="Specific job roles targeted (e.g. ['VP of Engineering'])"
    )
    seniority_levels: list[str] = Field(
        default_factory=list,
        description="Targeted seniority tiers (e.g. ['c_level', 'vp', 'head'])",
    )
    discovery_limit: int = Field(
        default=10, ge=1, le=50, description="Maximum number of prospects to return"
    )
    research_depth: Literal["standard", "deep"] = Field(
        default="standard", description="Search and retrieval depth"
    )


class FindDecisionMakersOutput(BaseModel):
    """Output report from decision-maker discovery."""

    report: DecisionMakerReport = Field(..., description="Complete decision-maker discovery report")


class VerifyPersonInput(BaseModel):
    """Input parameters for verifying a discovered person's employment and identity."""

    research_reference: str = Field(
        ..., min_length=1, description="Research run ID where person was discovered"
    )
    person_reference: str = Field(
        ..., min_length=1, description="Unique person_id of the candidate"
    )


class VerifyPersonOutput(BaseModel):
    """Output results from employment and identity verification."""

    person_id: str = Field(..., description="Unique person identifier")
    full_name: str = Field(..., description="Verified full name")
    company_name: str = Field(..., description="Target company")
    employment_status: str = Field(..., description="Verified employment status")
    confidence_score: float = Field(..., description="Verification confidence score (0.0 - 1.0)")
    confidence_explanation: str = Field(..., description="Grounded verification rationale")
    verification_status: str = Field(..., description="Overall corroboration status")


class GetPersonDetailsInput(BaseModel):
    """Input parameters for retrieving full evidence-backed profile of a discovered decision-maker."""

    research_reference: str = Field(
        ..., min_length=1, description="Research run ID where person was discovered"
    )
    person_reference: str = Field(
        ..., min_length=1, description="Unique person_id of the candidate"
    )


class GetPersonDetailsOutput(BaseModel):
    """Detailed profile, buying assessment, and evidence citations for a decision-maker."""

    person: DecisionMaker = Field(..., description="Full verified decision-maker entity")
