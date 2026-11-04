"""Live integration tests for OpenRouter LLM integration.

These tests execute actual HTTP requests against the OpenRouter API gateway.
They are marked with `@pytest.mark.live` and excluded from default test runs.
To run:
    pytest -m live
"""

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.main import create_app
from app.services.llm import LLMService

# Check if a plausible live key is present
_settings = get_settings()
_has_live_key = bool(
    _settings.openrouter_api_key
    and not _settings.openrouter_api_key.startswith("sk-or-v1-placeholder")
    and len(_settings.openrouter_api_key) > 10
)

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not _has_live_key,
        reason="Skipping live test: OPENROUTER_API_KEY is not configured with a valid live key",
    ),
]


class DecisionMakerSample(BaseModel):
    """Schema for live structured output verification."""

    role_title: str = Field(description="Executive title")
    seniority: str = Field(description="Seniority level, e.g., C-Level, VP, Director")


async def test_live_openrouter_generate_response() -> None:
    """Verify live communication with OpenRouter returns a valid text completion."""
    service = LLMService()
    response = await service.generate_response(
        prompt="Respond with only the single word: ACKNOWLEDGED",
        temperature=0.0,
        max_tokens=20,
    )

    assert response.content is not None
    assert len(response.content.strip()) > 0
    assert response.model != ""
    assert response.usage.total_tokens > 0
    assert response.duration_ms is not None
    assert response.duration_ms > 0


async def test_live_openrouter_structured_response() -> None:
    """Verify live structured JSON output parsed into Pydantic schema."""
    service = LLMService()
    prompt = (
        "Extract the executive role and seniority from this description: "
        "'Sarah is the Chief Technology Officer leading infrastructure.'"
    )

    structured_result = await service.generate_structured_response(
        prompt=prompt,
        response_model=DecisionMakerSample,
        temperature=0.0,
        max_tokens=150,
    )

    assert isinstance(structured_result.parsed, DecisionMakerSample)
    assert (
        "cto" in structured_result.parsed.role_title.lower()
        or "chief" in structured_result.parsed.role_title.lower()
    )
    assert structured_result.usage.total_tokens > 0


async def test_live_api_endpoint_post_test() -> None:
    """Verify POST /api/v1/llm/test reaches OpenRouter without mocking."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/llm/test",
            json={
                "message": "Respond with the word 'VERIFIED'",
                "temperature": 0.0,
                "max_tokens": 15,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["model"] != ""
    assert len(data["content"]) > 0
    assert data["usage"]["total_tokens"] > 0
    assert data["duration_ms"] is not None
