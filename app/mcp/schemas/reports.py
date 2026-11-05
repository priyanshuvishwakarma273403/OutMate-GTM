"""Pydantic schemas for evidence sources and research report retrieval MCP tools."""

from typing import Any

from pydantic import BaseModel, Field

from app.domain.models.evidence import EvidenceRecord


class GetResearchSourcesInput(BaseModel):
    """Input parameters for retrieving public evidence backing a company research run."""

    research_reference: str = Field(..., min_length=1, description="Research run ID")


class GetResearchSourcesOutput(BaseModel):
    """Output containing public evidence records and provenance audit trail."""

    research_reference: str = Field(..., description="Research run ID")
    total_sources: int = Field(..., description="Count of retrieved evidence items")
    sources: list[EvidenceRecord] = Field(
        default_factory=list, description="Verifiable public evidence citations"
    )


class GetDecisionMakerSourcesInput(BaseModel):
    """Input parameters for retrieving sources backing decision-maker discovery."""

    research_reference: str = Field(..., min_length=1, description="Decision-maker research run ID")
    person_reference: str | None = Field(
        default=None, description="Optional person_id to filter evidence for"
    )


class GetDecisionMakerSourcesOutput(BaseModel):
    """Output containing public evidence backing decision-makers or a specific prospect."""

    research_reference: str = Field(..., description="Research run ID")
    person_reference: str | None = Field(default=None, description="Target person_id if filtered")
    total_sources: int = Field(..., description="Count of retrieved evidence items")
    sources: list[EvidenceRecord] = Field(
        default_factory=list, description="Supporting evidence citations"
    )


class GetResearchReportInput(BaseModel):
    """Input parameters for retrieving a completed research report by ID."""

    research_reference: str = Field(..., min_length=1, description="Unique research run ID")


class GetResearchReportOutput(BaseModel):
    """Output containing the full completed research report."""

    research_id: str = Field(..., description="Report unique identifier")
    report_type: str = Field(..., description="Type of report: 'company' or 'decision_maker'")
    data: dict[str, Any] = Field(..., description="Serialized report payload")


class GenerateGTMReportInput(BaseModel):
    """Input parameters for generate_gtm_report MCP tool."""

    query: str = Field(
        ..., min_length=3, description="Original GTM research query or campaign objective"
    )
    company: dict[str, Any] = Field(
        ..., description="Researched company profile to feature in report"
    )
    decision_makers: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Ranked list of evaluated decision-makers with relevance scores",
    )
    include_outreach_angles: bool = Field(
        default=True, description="Whether to generate targeted outreach recommendations"
    )


class GenerateGTMReportOutput(BaseModel):
    """Output contract for generate_gtm_report MCP tool."""

    report: dict[str, Any] = Field(..., description="Compiled GTM intelligence dossier")
    markdown_content: str = Field(..., description="Formatted executive markdown dossier")
