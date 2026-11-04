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


class LLMTestRequest(BaseModel):
    """Request payload for testing OpenRouter LLM completions."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        examples=["Explain what a Go-To-Market strategy is in one sentence."],
        description="User message or prompt to send to the model",
    )
    system_prompt: str | None = Field(
        default=None,
        description="Optional system instruction for guiding model behavior",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature; defaults to configured environment value",
    )
    max_tokens: int | None = Field(
        default=None,
        ge=1,
        le=8192,
        description="Maximum completion tokens to generate",
    )
    model: str | None = Field(
        default=None,
        description="Optional model override; defaults to OPENROUTER_MODEL",
    )


class CompanyResearchRequest(BaseModel):
    """Request payload for executing deep real company research."""

    company_name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        examples=["Vercel"],
        description="Name of the company to research",
    )
    website_domain: str | None = Field(
        default=None,
        examples=["vercel.com"],
        description="Optional corporate domain to eliminate ambiguity",
    )
    research_depth: str = Field(
        default="standard",
        description="Research breadth and search intensity: 'standard' or 'deep'",
    )
    requested_fields: list[str] = Field(
        default_factory=list,
        description="Optional specific corporate fields to prioritize (e.g. ['tech_stack', 'headcount'])",
    )


class CompanyPreviewRequest(BaseModel):
    """Request payload for previewing company identity resolution and research query plan."""

    company_name: str = Field(..., min_length=2, max_length=200, description="Target company name")
    website_domain: str | None = Field(
        default=None, description="Optional corporate domain to evaluate"
    )
