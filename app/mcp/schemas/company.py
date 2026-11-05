"""Pydantic schemas for company search and intelligence MCP tools."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domain.models.company import CompanyProfile
from app.integrations.search.base import SearchResultItem
from app.schemas.responses import CompanyResearchReport


class SearchCompanyInput(BaseModel):
    """Input parameters for searching company web occurrences and domain discovery."""

    query: str = Field(..., min_length=2, max_length=200, description="Company name or search keywords")
    domain: str | None = Field(default=None, description="Optional target domain filter (e.g. 'vercel.com')")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of search results to retrieve")


class SearchCompanyOutput(BaseModel):
    """Output results from company web search."""

    query: str = Field(..., description="Executed search query")
    results: list[SearchResultItem] = Field(default_factory=list, description="Retrieved search result items")
    total_results: int = Field(..., description="Count of retrieved items")


class ResearchCompanyInput(BaseModel):
    """Input parameters for executing real end-to-end company intelligence research."""

    company_name: str = Field(..., min_length=2, max_length=200, description="Target company commercial name")
    company_domain: str | None = Field(default=None, description="Optional target corporate domain")
    research_depth: Literal["standard", "deep"] = Field(
        default="standard", description="Research depth: standard (5-6 sources) or deep (8-10 sources)"
    )
    requested_fields: list[str] | None = Field(
        default=None, description="Optional explicit fields to emphasize during synthesis"
    )


class ResearchCompanyOutput(BaseModel):
    """Output report from real company intelligence research."""

    report: CompanyResearchReport = Field(..., description="Complete structured company intelligence dossier")


class GetCompanyProfileInput(BaseModel):
    """Input parameters for retrieving an existing company profile by research reference."""

    research_reference: str = Field(..., min_length=1, description="Unique research_id of completed research run")


class GetCompanyProfileOutput(BaseModel):
    """Output containing stored company profile and core findings."""

    research_id: str = Field(..., description="Research report identifier")
    company: CompanyProfile = Field(..., description="Verified company profile")
    findings: list[str] = Field(default_factory=list, description="Core verified findings")
    identity_status: str = Field(..., description="Company identity corroboration status")
