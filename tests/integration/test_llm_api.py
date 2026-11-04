"""Integration tests for the LLM API endpoint POST /api/v1/llm/test."""

from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient

from app.api.routes.llm import get_llm_service
from app.core.exceptions import AuthenticationError, LLMTimeoutError
from app.llm.base import LLMResponse, TokenUsage
from app.main import create_app
from app.services.llm import LLMService


async def test_llm_endpoint_success() -> None:
    """Verify POST /api/v1/llm/test returns 200 OK and expected response structure."""
    app = create_app()

    mock_service = AsyncMock(spec=LLMService)
    mock_service.generate_response.return_value = LLMResponse(
        content="OpenRouter integration is operating correctly.",
        model="openai/gpt-4o-mini",
        usage=TokenUsage(prompt_tokens=12, completion_tokens=8, total_tokens=20),
        duration_ms=250.0,
    )

    app.dependency_overrides[get_llm_service] = lambda: mock_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {
            "message": "Ping",
            "system_prompt": "Respond briefly.",
            "temperature": 0.1,
            "max_tokens": 50,
        }
        response = await client.post("/api/v1/llm/test", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["model"] == "openai/gpt-4o-mini"
    assert data["content"] == "OpenRouter integration is operating correctly."
    assert data["usage"]["total_tokens"] == 20
    assert data["usage"]["prompt_tokens"] == 12
    assert data["usage"]["completion_tokens"] == 8
    assert data["duration_ms"] == 250.0


async def test_llm_endpoint_validation_error_empty_message() -> None:
    """Verify POST /api/v1/llm/test returns 422 when message is empty."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Empty message
        response = await client.post("/api/v1/llm/test", json={"message": ""})
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["error_type"] == "ValidationError"

        # Missing message
        response_missing = await client.post("/api/v1/llm/test", json={})
        assert response_missing.status_code == 422


async def test_llm_endpoint_auth_error_handling() -> None:
    """Verify POST /api/v1/llm/test returns 400 Bad Request when auth error occurs."""
    app = create_app()

    mock_service = AsyncMock(spec=LLMService)
    mock_service.generate_response.side_effect = AuthenticationError(
        "Invalid or missing OpenRouter API key"
    )

    app.dependency_overrides[get_llm_service] = lambda: mock_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/llm/test", json={"message": "Test prompt"})

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["error_type"] == "AuthenticationError"
    assert "Invalid or missing OpenRouter API key" in data["error"]["message"]


async def test_llm_endpoint_timeout_error_handling() -> None:
    """Verify POST /api/v1/llm/test returns 400 Bad Request when request times out."""
    app = create_app()

    mock_service = AsyncMock(spec=LLMService)
    mock_service.generate_response.side_effect = LLMTimeoutError(
        "OpenRouter request timed out after 30.0s"
    )

    app.dependency_overrides[get_llm_service] = lambda: mock_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/llm/test", json={"message": "Test prompt"})

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["error_type"] == "LLMTimeoutError"
