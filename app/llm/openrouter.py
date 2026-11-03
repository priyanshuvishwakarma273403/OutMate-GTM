"""OpenRouter adapter implementing BaseLLMClient via OpenAI-compatible SDK."""

import json
from typing import Any, TypeVar

import openai
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import AppSettings, get_settings
from app.core.exceptions import (
    AuthenticationError,
    LLMProviderError,
    LLMQuotaExceededError,
    LLMResponseParsingError,
    LLMTimeoutError,
)
from app.core.logging import get_logger
from app.llm.base import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    StructuredLLMResponse,
    TokenUsage,
    ToolCallRequest,
    ToolDefinition,
)

logger = get_logger("llm.openrouter")

T = TypeVar("T", bound=BaseModel)


class OpenRouterClient(BaseLLMClient):
    """Adapter for OpenRouter inference gateway adhering to BaseLLMClient interface."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.default_model = self.settings.openrouter_model
        self.timeout = self.settings.openrouter_timeout

        if client is not None:
            self._client = client
        else:
            # Client is initialized only if api_key is present or on-demand
            api_key = self.settings.openrouter_api_key or "not-set"
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=self.settings.openrouter_base_url,
                timeout=self.timeout,
                max_retries=self.settings.openrouter_max_retries,
                default_headers={
                    "HTTP-Referer": "https://outmate.ai",
                    "X-Title": "Outmate GTM Intelligence Platform",
                },
            )

    def _ensure_configured(self) -> None:
        """Validate credentials before making live API requests."""
        self.settings.validate_openrouter()

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict[str, Any]]:
        """Convert internal LLMMessage list to OpenAI-compatible message dictionaries."""
        payload: list[dict[str, Any]] = []
        for msg in messages:
            entry: dict[str, Any] = {"role": msg.role.value, "content": msg.content}
            if msg.name:
                entry["name"] = msg.name
            if msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
            payload.append(entry)
        return payload

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        """Convert internal ToolDefinition list to OpenAI function schema format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]

    def _extract_usage(self, response_usage: Any) -> TokenUsage:
        """Extract TokenUsage from OpenAI response usage object."""
        if not response_usage:
            return TokenUsage()
        return TokenUsage(
            prompt_tokens=getattr(response_usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(response_usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(response_usage, "total_tokens", 0) or 0,
        )

    def _handle_exception(self, exc: Exception) -> None:
        """Centralized exception handling for OpenAI/OpenRouter client errors."""
        logger.error("OpenRouter API error encountered: %s", type(exc).__name__)
        if isinstance(exc, openai.APITimeoutError):
            raise LLMTimeoutError(
                f"OpenRouter request timed out after {self.timeout}s",
                details={"timeout": self.timeout},
            ) from exc
        if isinstance(exc, openai.RateLimitError):
            raise LLMQuotaExceededError(
                "OpenRouter rate limit or quota exceeded",
                details={"message": str(exc)},
            ) from exc
        if isinstance(exc, openai.AuthenticationError):
            raise AuthenticationError(
                "Invalid or missing OpenRouter API key",
                details={"message": str(exc)},
            ) from exc
        if isinstance(exc, openai.APIConnectionError):
            raise LLMProviderError(
                "Failed to connect to OpenRouter gateway",
                details={"message": str(exc)},
            ) from exc
        if isinstance(exc, openai.APIError):
            raise LLMProviderError(
                f"OpenRouter returned API error: {exc.message}",
                details={"code": exc.code, "message": exc.message},
            ) from exc
        raise LLMProviderError(f"Unexpected LLM failure: {exc}") from exc

    async def generate_response(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        """Generate a standard conversational text response via OpenRouter."""
        self._ensure_configured()
        target_model = model or self.default_model

        try:
            create_kwargs: dict[str, Any] = {
                "model": target_model,
                "messages": self._convert_messages(messages),
                "temperature": temperature,
            }
            if max_tokens is not None:
                create_kwargs["max_tokens"] = max_tokens

            response = await self._client.chat.completions.create(**create_kwargs)
            choice = response.choices[0]
            return LLMResponse(
                content=choice.message.content,
                tool_calls=[],
                usage=self._extract_usage(response.usage),
                finish_reason=choice.finish_reason or "stop",
                model=response.model or target_model,
            )
        except Exception as exc:
            self._handle_exception(exc)
            raise  # Unreachable, kept for mypy

    async def generate_structured_response(
        self,
        messages: list[LLMMessage],
        response_model: type[T],
        *,
        temperature: float = 0.1,
        model: str | None = None,
    ) -> StructuredLLMResponse[T]:
        """Generate structured response validated against a target Pydantic schema."""
        self._ensure_configured()
        target_model = model or self.default_model

        # Inject JSON schema constraint instruction in system/user prompt
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        guidance_message = LLMMessage(
            role=messages[0].role,
            content=(
                f"{messages[0].content}\n\n"
                f"CRITICAL: Respond ONLY with valid JSON matching this schema:\n{schema_json}"
            ),
        )
        augmented_messages = [guidance_message] + messages[1:]

        try:
            create_kwargs: dict[str, Any] = {
                "model": target_model,
                "messages": self._convert_messages(augmented_messages),
                "temperature": temperature,
                "response_format": {"type": "json_object"},
            }
            response = await self._client.chat.completions.create(**create_kwargs)
            choice = response.choices[0]
            raw_content = choice.message.content or "{}"
            try:
                parsed_data = response_model.model_validate_json(raw_content)
            except Exception as parse_exc:
                raise LLMResponseParsingError(
                    f"Failed to parse LLM response into schema {response_model.__name__}",
                    details={"raw_content": raw_content, "error": str(parse_exc)},
                ) from parse_exc

            return StructuredLLMResponse(
                parsed=parsed_data,
                raw_content=raw_content,
                usage=self._extract_usage(response.usage),
                model=response.model or target_model,
            )
        except Exception as exc:
            if not isinstance(exc, LLMResponseParsingError):
                self._handle_exception(exc)
            raise

    async def generate_tool_calls(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition],
        *,
        temperature: float = 0.2,
        model: str | None = None,
    ) -> LLMResponse:
        """Evaluate messages against available tool definitions and return tool calls."""
        self._ensure_configured()
        target_model = model or self.default_model

        try:
            create_kwargs: dict[str, Any] = {
                "model": target_model,
                "messages": self._convert_messages(messages),
                "tools": self._convert_tools(tools),
                "tool_choice": "auto",
                "temperature": temperature,
            }
            response = await self._client.chat.completions.create(**create_kwargs)
            choice = response.choices[0]
            tool_calls: list[ToolCallRequest] = []

            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    arguments_dict: dict[str, Any] = {}
                    if tc.function.arguments:
                        try:
                            arguments_dict = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            arguments_dict = {"raw": tc.function.arguments}

                    tool_calls.append(
                        ToolCallRequest(
                            id=tc.id,
                            name=tc.function.name,
                            arguments=arguments_dict,
                        )
                    )

            return LLMResponse(
                content=choice.message.content,
                tool_calls=tool_calls,
                usage=self._extract_usage(response.usage),
                finish_reason=choice.finish_reason or "tool_calls",
                model=response.model or target_model,
            )
        except Exception as exc:
            self._handle_exception(exc)
            raise
