"""OpenRouter adapter implementing BaseLLMClient via OpenAI-compatible SDK."""

import json
import time
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


def _clean_json_content(content: str) -> str:
    """Safely strip markdown code blocks and surrounding whitespace from JSON content."""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # Remove opening fence (e.g. ```json or ```)
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        # Remove closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


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
        error_name = type(exc).__name__
        logger.error("OpenRouter provider error: %s", error_name)
        if isinstance(exc, openai.APITimeoutError):
            raise LLMTimeoutError(
                f"OpenRouter request timed out after {self.timeout}s",
                details={"timeout": self.timeout, "provider_error": error_name},
            ) from exc
        if isinstance(exc, openai.RateLimitError):
            raise LLMQuotaExceededError(
                "OpenRouter rate limit or quota exceeded",
                details={"message": str(exc), "provider_error": error_name},
            ) from exc
        if isinstance(exc, openai.AuthenticationError):
            raise AuthenticationError(
                "Invalid or missing OpenRouter API key",
                details={"provider_error": error_name},
            ) from exc
        if isinstance(exc, openai.APIConnectionError):
            raise LLMProviderError(
                "Failed to connect to OpenRouter gateway",
                details={"provider_error": error_name},
            ) from exc
        if isinstance(exc, openai.BadRequestError):
            raise LLMProviderError(
                f"OpenRouter bad request: {exc.message}",
                details={"code": exc.code, "provider_error": error_name},
            ) from exc
        if isinstance(exc, openai.InternalServerError):
            raise LLMProviderError(
                f"OpenRouter internal server error: {exc.message}",
                details={"status_code": exc.status_code, "provider_error": error_name},
            ) from exc
        if isinstance(exc, openai.APIError):
            raise LLMProviderError(
                f"OpenRouter returned API error: {exc.message}",
                details={"code": exc.code, "provider_error": error_name},
            ) from exc
        raise LLMProviderError(
            f"Unexpected LLM failure: {exc}",
            details={"provider_error": error_name},
        ) from exc

    async def generate_response(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        """Generate a standard conversational text response via OpenRouter."""
        self._ensure_configured()
        target_model = model or self.default_model
        eff_temperature = (
            temperature if temperature is not None else self.settings.openrouter_temperature
        )
        eff_max_tokens = (
            max_tokens if max_tokens is not None else self.settings.openrouter_max_tokens
        )

        start_time = time.perf_counter()
        try:
            create_kwargs: dict[str, Any] = {
                "model": target_model,
                "messages": self._convert_messages(messages),
                "temperature": eff_temperature,
            }
            if eff_max_tokens is not None:
                create_kwargs["max_tokens"] = eff_max_tokens

            logger.info("Dispatching OpenRouter request to model '%s'", target_model)
            response = await self._client.chat.completions.create(**create_kwargs)
            duration_ms = (time.perf_counter() - start_time) * 1000

            choice = response.choices[0]
            usage = self._extract_usage(response.usage)
            logger.info(
                "OpenRouter response received in %.1fms (tokens: prompt=%d, completion=%d, total=%d)",
                duration_ms,
                usage.prompt_tokens,
                usage.completion_tokens,
                usage.total_tokens,
            )

            return LLMResponse(
                content=choice.message.content,
                tool_calls=[],
                usage=usage,
                finish_reason=choice.finish_reason or "stop",
                model=response.model or target_model,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            self._handle_exception(exc)
            raise  # Unreachable, kept for mypy

    async def generate_structured_response(
        self,
        messages: list[LLMMessage],
        response_model: type[T],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> StructuredLLMResponse[T]:
        """Generate structured response validated against a target Pydantic schema."""
        self._ensure_configured()
        target_model = model or self.default_model
        eff_temperature = temperature if temperature is not None else 0.1
        eff_max_tokens = (
            max_tokens if max_tokens is not None else self.settings.openrouter_max_tokens
        )

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

        start_time = time.perf_counter()
        try:
            create_kwargs: dict[str, Any] = {
                "model": target_model,
                "messages": self._convert_messages(augmented_messages),
                "temperature": eff_temperature,
                "response_format": {"type": "json_object"},
            }
            if eff_max_tokens is not None:
                create_kwargs["max_tokens"] = eff_max_tokens

            logger.info("Dispatching structured OpenRouter request to model '%s'", target_model)
            response = await self._client.chat.completions.create(**create_kwargs)
            duration_ms = (time.perf_counter() - start_time) * 1000

            choice = response.choices[0]
            raw_content = choice.message.content or "{}"
            cleaned_content = _clean_json_content(raw_content)

            try:
                parsed_data = response_model.model_validate_json(cleaned_content)
            except Exception as parse_exc:
                logger.warning(
                    "Model output failed schema validation for %s: %s",
                    response_model.__name__,
                    parse_exc,
                )
                raise LLMResponseParsingError(
                    f"Failed to parse LLM response into schema {response_model.__name__}",
                    details={"raw_content": raw_content, "error": str(parse_exc)},
                ) from parse_exc

            usage = self._extract_usage(response.usage)
            logger.info("Structured OpenRouter response parsed in %.1fms", duration_ms)

            return StructuredLLMResponse(
                parsed=parsed_data,
                raw_content=raw_content,
                usage=usage,
                model=response.model or target_model,
                duration_ms=duration_ms,
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
        temperature: float | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        """Evaluate messages against available tool definitions and return tool calls."""
        self._ensure_configured()
        target_model = model or self.default_model
        eff_temperature = (
            temperature if temperature is not None else self.settings.openrouter_temperature
        )

        start_time = time.perf_counter()
        try:
            create_kwargs: dict[str, Any] = {
                "model": target_model,
                "messages": self._convert_messages(messages),
                "tools": self._convert_tools(tools),
                "tool_choice": "auto",
                "temperature": eff_temperature,
            }
            if self.settings.openrouter_max_tokens is not None:
                create_kwargs["max_tokens"] = self.settings.openrouter_max_tokens

            response = await self._client.chat.completions.create(**create_kwargs)
            duration_ms = (time.perf_counter() - start_time) * 1000

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
                duration_ms=duration_ms,
            )
        except Exception as exc:
            self._handle_exception(exc)
            raise
