"""Unit tests for OpenRouter client and LLM service layer with mocked HTTP boundaries."""

from unittest.mock import AsyncMock, MagicMock

import openai
import pytest
from pydantic import BaseModel, Field

from app.core.config import AppSettings
from app.core.exceptions import (
    AuthenticationError,
    ConfigurationError,
    LLMQuotaExceededError,
    LLMResponseParsingError,
    LLMTimeoutError,
)
from app.llm.openrouter import OpenRouterClient, _clean_json_content
from app.services.llm import LLMService


# --- Fixtures & Dummy Models ---
class DummyPerson(BaseModel):
    name: str = Field(...)
    role: str = Field(...)
    confidence: float = Field(default=1.0)


def create_mock_openai_response(
    content: str | None = "This is a test completion.",
    model: str = "anthropic/claude-3.5-sonnet",
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
    finish_reason: str = "stop",
) -> MagicMock:
    """Helper creating a mock ChatCompletion response object."""
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_choice.message.tool_calls = None
    mock_choice.finish_reason = finish_reason

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = prompt_tokens
    mock_usage.completion_tokens = completion_tokens
    mock_usage.total_tokens = prompt_tokens + completion_tokens

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage
    mock_response.model = model
    return mock_response


# --- Unit Tests ---


def test_clean_json_content_helper() -> None:
    """Verify markdown fences and whitespace are stripped from raw JSON strings."""
    assert _clean_json_content('{"key": "value"}') == '{"key": "value"}'
    assert _clean_json_content('```json\n{"key": "value"}\n```') == '{"key": "value"}'
    assert _clean_json_content('```\n{"key": "value"}\n```') == '{"key": "value"}'


def test_missing_api_key_raises_configuration_error() -> None:
    """Verify that calling OpenRouter without configured API key raises ConfigurationError."""
    settings = AppSettings(OPENROUTER_API_KEY=None)
    client = OpenRouterClient(settings=settings)

    with pytest.raises(ConfigurationError, match="OPENROUTER_API_KEY is required"):
        client._ensure_configured()


def test_openrouter_configuration_validation() -> None:
    """Verify configuration validation for temperature and timeout."""
    settings = AppSettings(
        OPENROUTER_API_KEY="sk-test-key",
        OPENROUTER_MODEL="openai/gpt-4o",
        OPENROUTER_TIMEOUT=45.0,
        OPENROUTER_TEMPERATURE=0.7,
        OPENROUTER_MAX_TOKENS=1024,
    )
    assert settings.openrouter_temperature == 0.7
    assert settings.openrouter_max_tokens == 1024
    assert settings.openrouter_model == "openai/gpt-4o"
    settings.validate_openrouter()


async def test_successful_response_parsing() -> None:
    """Verify successful response parsing and token usage calculation."""
    mock_openai = MagicMock()
    mock_openai.chat.completions.create = AsyncMock(
        return_value=create_mock_openai_response(
            content="GTM strategy drives customer acquisition.",
            model="anthropic/claude-3.5-sonnet",
            prompt_tokens=15,
            completion_tokens=25,
        )
    )

    settings = AppSettings(OPENROUTER_API_KEY="sk-valid-key")
    client = OpenRouterClient(settings=settings, client=mock_openai)
    service = LLMService(client=client, settings=settings)

    response = await service.generate_response("Define GTM")
    assert response.content == "GTM strategy drives customer acquisition."
    assert response.model == "anthropic/claude-3.5-sonnet"
    assert response.usage.prompt_tokens == 15
    assert response.usage.completion_tokens == 25
    assert response.usage.total_tokens == 40
    assert response.duration_ms is not None
    assert response.duration_ms >= 0


async def test_system_prompt_handling() -> None:
    """Verify that system prompts are correctly prepended to message payload."""
    mock_openai = MagicMock()
    mock_openai.chat.completions.create = AsyncMock(
        return_value=create_mock_openai_response(content="Understood.")
    )

    settings = AppSettings(OPENROUTER_API_KEY="sk-valid-key")
    client = OpenRouterClient(settings=settings, client=mock_openai)
    service = LLMService(client=client, settings=settings)

    await service.generate_response(
        prompt="User question",
        system_prompt="You are a helpful assistant.",
    )

    call_args = mock_openai.chat.completions.create.call_args[1]
    messages_payload = call_args["messages"]
    assert len(messages_payload) == 2
    assert messages_payload[0] == {"role": "system", "content": "You are a helpful assistant."}
    assert messages_payload[1] == {"role": "user", "content": "User question"}


async def test_structured_output_validation_success() -> None:
    """Verify structured response parses correctly into target Pydantic model."""
    json_output = '{"name": "Guillermo Rauch", "role": "CEO", "confidence": 0.99}'
    mock_openai = MagicMock()
    mock_openai.chat.completions.create = AsyncMock(
        return_value=create_mock_openai_response(content=json_output)
    )

    settings = AppSettings(OPENROUTER_API_KEY="sk-valid-key")
    client = OpenRouterClient(settings=settings, client=mock_openai)
    service = LLMService(client=client, settings=settings)

    result = await service.generate_structured_response(
        prompt="Extract person",
        response_model=DummyPerson,
    )

    assert isinstance(result.parsed, DummyPerson)
    assert result.parsed.name == "Guillermo Rauch"
    assert result.parsed.role == "CEO"
    assert result.parsed.confidence == 0.99


async def test_structured_output_validation_failure() -> None:
    """Verify LLMResponseParsingError is raised when model returns malformed JSON."""
    invalid_json = "This is not JSON at all"
    mock_openai = MagicMock()
    mock_openai.chat.completions.create = AsyncMock(
        return_value=create_mock_openai_response(content=invalid_json)
    )

    settings = AppSettings(OPENROUTER_API_KEY="sk-valid-key")
    client = OpenRouterClient(settings=settings, client=mock_openai)
    service = LLMService(client=client, settings=settings)

    with pytest.raises(LLMResponseParsingError, match="Failed to parse LLM response into schema"):
        await service.generate_structured_response(
            prompt="Extract person",
            response_model=DummyPerson,
        )


async def test_authentication_failure_handling() -> None:
    """Verify 401 AuthenticationError maps to Outmate AuthenticationError."""
    mock_openai = MagicMock()
    mock_response = MagicMock(status_code=401, headers={})
    mock_openai.chat.completions.create = AsyncMock(
        side_effect=openai.AuthenticationError(
            message="Incorrect API key provided",
            response=mock_response,
            body=None,
        )
    )

    settings = AppSettings(OPENROUTER_API_KEY="sk-bad-key")
    client = OpenRouterClient(settings=settings, client=mock_openai)
    service = LLMService(client=client, settings=settings)

    with pytest.raises(AuthenticationError, match="Invalid or missing OpenRouter API key"):
        await service.generate_response("Hello")


async def test_rate_limit_handling() -> None:
    """Verify 429 RateLimitError maps to Outmate LLMQuotaExceededError."""
    mock_openai = MagicMock()
    mock_response = MagicMock(status_code=429, headers={})
    mock_openai.chat.completions.create = AsyncMock(
        side_effect=openai.RateLimitError(
            message="Rate limit exceeded",
            response=mock_response,
            body=None,
        )
    )

    settings = AppSettings(OPENROUTER_API_KEY="sk-valid-key")
    client = OpenRouterClient(settings=settings, client=mock_openai)
    service = LLMService(client=client, settings=settings)

    with pytest.raises(LLMQuotaExceededError, match="rate limit or quota exceeded"):
        await service.generate_response("Hello")


async def test_network_timeout_handling() -> None:
    """Verify APITimeoutError maps to Outmate LLMTimeoutError."""
    mock_openai = MagicMock()
    mock_openai.chat.completions.create = AsyncMock(
        side_effect=openai.APITimeoutError(request=MagicMock())
    )

    settings = AppSettings(OPENROUTER_API_KEY="sk-valid-key")
    client = OpenRouterClient(settings=settings, client=mock_openai)
    service = LLMService(client=client, settings=settings)

    with pytest.raises(LLMTimeoutError, match="timed out"):
        await service.generate_response("Hello")
