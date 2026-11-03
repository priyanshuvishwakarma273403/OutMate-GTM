"""Typed input and output schemas for all Model Context Protocol (MCP) GTM tools."""

from pydantic import BaseModel, Field

from app.domain.models.company import CompanyProfile
from app.domain.models.person import DecisionMaker, Department, SeniorityLevel
from app.domain.models.report import GTMReport, ScoredDecisionMaker


# 1. search_company
class SearchCompanyInput(BaseModel):
    """Input parameters for search_company MCP tool."""

    company_name: str = Field(
        ...,
        min_length=1,
        description="Target business name to investigate, e.g. 'Vercel' or 'Datadog'",
    )
    domain: str | None = Field(
        default=None,
        description="Optional primary website domain (e.g. 'vercel.com') to constrain discovery",
    )


class SearchCompanyOutput(BaseModel):
    """Output contract for search_company MCP tool."""

    company: CompanyProfile = Field(..., description="Researched company intelligence profile")


# 2. find_decision_makers
class FindDecisionMakersInput(BaseModel):
    """Input parameters for find_decision_makers MCP tool."""

    company_name: str = Field(..., min_length=1, description="Company where decision-makers work")
    company_domain: str | None = Field(default=None, description="Optional company web domain")
    target_seniority: list[SeniorityLevel] = Field(
        default_factory=list,
        description="Target seniority tiers (e.g. ['c_level', 'vp', 'head', 'director'])",
    )
    target_departments: list[Department] = Field(
        default_factory=list,
        description="Target departments (e.g. ['engineering', 'product', 'security'])",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of candidate decision-makers to return",
    )


class FindDecisionMakersOutput(BaseModel):
    """Output contract for find_decision_makers MCP tool."""

    decision_makers: list[DecisionMaker] = Field(
        default_factory=list, description="List of discovered decision-makers"
    )
    total_found: int = Field(..., ge=0, description="Count of identified decision-makers")


# 3. get_person_details
class GetPersonDetailsInput(BaseModel):
    """Input parameters for get_person_details MCP tool."""

    full_name: str = Field(..., min_length=1, description="Full name of the target professional")
    company_name: str = Field(..., min_length=1, description="Affiliated company name")
    linkedin_url: str | None = Field(
        default=None, description="Optional public LinkedIn profile URL to resolve identity"
    )


class GetPersonDetailsOutput(BaseModel):
    """Output contract for get_person_details MCP tool."""

    person: DecisionMaker = Field(..., description="Comprehensive profile of the requested person")


# 4. verify_person
class VerifyPersonInput(BaseModel):
    """Input parameters for verify_person MCP tool."""

    person_name: str = Field(..., min_length=1, description="Name of the person to verify")
    company_name: str = Field(
        ..., min_length=1, description="Company affiliation claimed for the person"
    )
    title: str = Field(..., min_length=1, description="Discovered job title to corroborate")
    linkedin_url: str | None = Field(
        default=None, description="Optional LinkedIn URL for identity resolution"
    )


class VerifyPersonOutput(BaseModel):
    """Output contract for verify_person MCP tool."""

    person: DecisionMaker = Field(
        ..., description="Decision maker record updated with verification status and evidence"
    )
    is_verified: bool = Field(..., description="Whether public evidence corroborates the title")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Calculated verification confidence"
    )


# 5. generate_gtm_report
class GenerateGTMReportInput(BaseModel):
    """Input parameters for generate_gtm_report MCP tool."""

    query: str = Field(
        ..., min_length=3, description="Original GTM research query or campaign objective"
    )
    company: CompanyProfile = Field(
        ..., description="Researched company profile to feature in report"
    )
    decision_makers: list[ScoredDecisionMaker] = Field(
        default_factory=list,
        description="Ranked list of evaluated decision-makers with relevance scores",
    )
    include_outreach_angles: bool = Field(
        default=True, description="Whether to generate targeted outreach recommendations"
    )


class GenerateGTMReportOutput(BaseModel):
    """Output contract for generate_gtm_report MCP tool."""

    report: GTMReport = Field(..., description="Complete compiled GTM intelligence dossier")
    markdown_content: str = Field(
        ..., description="Formatted executive markdown dossier ready for review"
    )
