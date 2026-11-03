"""API and agent orchestration request schemas."""

from pydantic import BaseModel, Field


class ResearchQueryRequest(BaseModel):
    """Natural-language GTM research query request."""

    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        examples=["Who are the decision makers in the company Vercel?"],
        description="Natural language query requesting company or decision-maker intelligence",
    )
    target_seniority: list[str] = Field(
        default_factory=list,
        description="Optional explicit seniority levels to prioritize (e.g., ['c_level', 'vp'])",
    )
    target_departments: list[str] = Field(
        default_factory=list,
        description="Optional explicit departments to prioritize (e.g., ['engineering', 'product'])",
    )
    max_decision_makers: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of decision-maker candidates to return",
    )


class CompanyLookupRequest(BaseModel):
    """Direct company intelligence lookup request."""

    company_name: str = Field(..., min_length=1, description="Company name to investigate")
    domain: str | None = Field(
        default=None, description="Optional known website domain to improve accuracy"
    )
