"""Unit tests for provider-independent LLM abstractions and OpenRouter adapter."""

from unittest.mock import MagicMock

import openai
import pytest

from app.core.config import AppSettings
from app.core.exceptions import (
    AuthenticationError,
    LLMQuotaExceededError,
    LLMTimeoutError,
)
from app.llm import (
    LLMMessage,
    MessageRole,
    OpenRouterClient,
    ToolDefinition,
)


def test_llm_message_data_model() -> None:
    """Verify LLMMessage structures and role serialization."""
    msg = LLMMessage(role=MessageRole.USER, content="Who is the CTO of Vercel?")
    assert msg.role == MessageRole.USER
    assert msg.role.value == "user"
    assert msg.content == "Who is the CTO of Vercel?"


def test_tool_definition_model() -> None:
    """Verify ToolDefinition schema specification."""
    tool = ToolDefinition(
        name="search_company",
        description="Search company intelligence",
        parameters={
            "type": "object",
            "properties": {"company_name": {"type": "string"}},
            "required": ["company_name"],
        },
    )
    assert tool.name == "search_company"
    assert "company_name" in tool.parameters["properties"]


def test_openrouter_client_initialization() -> None:
    """Verify OpenRouterClient correctly consumes AppSettings without making requests."""
    settings = AppSettings(
        OPENROUTER_API_KEY="sk-or-test-key",
        OPENROUTER_MODEL="anthropic/claude-3.5-sonnet",
        OPENROUTER_TIMEOUT=45.0,
    )
    client = OpenRouterClient(settings=settings)
    assert client.default_model == "anthropic/claude-3.5-sonnet"
    assert client.timeout == 45.0


def test_openrouter_message_conversion() -> None:
    """Verify translation of internal LLMMessages to OpenAI dictionary payloads."""
    client = OpenRouterClient(settings=AppSettings(OPENROUTER_API_KEY="sk-or-test-key"))
    messages = [
        LLMMessage(role=MessageRole.SYSTEM, content="You are a research agent."),
        LLMMessage(role=MessageRole.USER, content="Find decision makers."),
    ]
    converted = client._convert_messages(messages)
    assert len(converted) == 2
    assert converted[0] == {"role": "system", "content": "You are a research agent."}
    assert converted[1] == {"role": "user", "content": "Find decision makers."}


def test_openrouter_timeout_exception_mapping() -> None:
    """Verify OpenAI APITimeoutError is mapped to Outmate LLMTimeoutError."""
    client = OpenRouterClient(settings=AppSettings(OPENROUTER_API_KEY="sk-test"))
    req = MagicMock()
    with pytest.raises(LLMTimeoutError, match="timed out"):
        client._handle_exception(openai.APITimeoutError(request=req))


def test_openrouter_rate_limit_exception_mapping() -> None:
    """Verify OpenAI RateLimitError is mapped to LLMQuotaExceededError."""
    client = OpenRouterClient(settings=AppSettings(OPENROUTER_API_KEY="sk-test"))
    response = MagicMock(status_code=429, headers={})
    with pytest.raises(LLMQuotaExceededError, match="rate limit"):
        client._handle_exception(
            openai.RateLimitError(
                message="Quota exceeded",
                response=response,
                body=None,
            )
        )


def test_openrouter_auth_exception_mapping() -> None:
    """Verify OpenAI AuthenticationError is mapped to domain AuthenticationError."""
    client = OpenRouterClient(settings=AppSettings(OPENROUTER_API_KEY="sk-test"))
    response = MagicMock(status_code=401, headers={})
    with pytest.raises(AuthenticationError, match="Invalid or missing OpenRouter API key"):
        client._handle_exception(
            openai.AuthenticationError(
                message="Unauthorized",
                response=response,
                body=None,
            )
        )
