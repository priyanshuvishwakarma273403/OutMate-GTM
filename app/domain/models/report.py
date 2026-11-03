"""Domain models for GTM intelligence reports, relevance scores, and research dossiers."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.domain.models.company import CompanyProfile
from app.domain.models.evidence import utc_now
from app.domain.models.person import DecisionMaker


class RelevanceTier(StrEnum):
    """Normalized relevance rating of a prospect against a GTM query."""

    HIGH = "high"  # Direct buyer / primary decision-maker
    MEDIUM = "medium"  # Influencer / champion / adjacent stakeholder
    LOW = "low"  # Peripheral or unclear buying authority
    IRRELEVANT = "irrelevant"


class RelevanceScore(BaseModel):
    """Detailed relevance assessment computed by the scoring service."""

    overall_score: float = Field(
        ..., ge=0.0, le=100.0, description="Overall match score from 0 to 100"
    )
    tier: RelevanceTier = Field(..., description="Categorical classification of prospect fit")
    seniority_fit: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Alignment with desired decision-maker seniority"
    )
    department_fit: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Alignment with targeted department"
    )
    evidence_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence in employment and title validity"
    )
    rationale: str = Field(
        ..., description="Transparent textual explanation for the assigned score"
    )


class ScoredDecisionMaker(BaseModel):
    """Decision maker bundled with their calculated relevance score."""

    person: DecisionMaker = Field(..., description="Decision maker prospect")
    score: RelevanceScore = Field(..., description="Relevance and fit evaluation")


class GTMReport(BaseModel):
    """Comprehensive Go-To-Market research dossier for a company and its decision-makers."""

    query: str = Field(..., description="Original user research prompt or question")
    company: CompanyProfile = Field(..., description="Researched company profile")
    decision_makers: list[ScoredDecisionMaker] = Field(
        default_factory=list, description="Ranked list of identified decision-makers"
    )
    executive_summary: str = Field(
        ..., description="High-level narrative synthesis of research findings"
    )
    key_findings: list[str] = Field(
        default_factory=list, description="Bullet-point takeaways and strategic insights"
    )
    recommended_outreach_angles: list[str] = Field(
        default_factory=list,
        description="Value proposition hooks aligned with discovered executives",
    )
    generated_at: datetime = Field(
        default_factory=utc_now, description="Timestamp of report compilation"
    )
    execution_mode: str = Field(
        default="standalone_agent",
        description="Execution mode that compiled the report (standalone_agent or mcp_server)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Diagnostic, token usage, and provenance metadata"
    )
