"""Search provider configuration models."""

from pydantic import BaseModel, Field


class SearchConfig(BaseModel):
    """Configuration for web research and discovery search providers."""

    provider: str = Field(default="exa", description="Search provider engine (exa, serper, tavily)")
    api_key: str = Field(..., description="API key for external search provider")
    base_url: str | None = Field(default=None, description="Optional custom base URL")
    timeout: float = Field(default=30.0, ge=1.0, description="Search request timeout")
