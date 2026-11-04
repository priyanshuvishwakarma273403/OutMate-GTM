"""Reusable LLM service providing structured and conversational completions."""

from typing import TypeVar

from pydantic import BaseModel

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.llm import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    MessageRole,
    OpenRouterClient,
    StructuredLLMResponse,
)

logger = get_logger("services.llm")

T = TypeVar("T", bound=BaseModel)


class LLMService:
    """Enterprise service layer encapsulating LLM inference, formatting, and structured parsing."""

    def __init__(
        self,
        client: BaseLLMClient | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client: BaseLLMClient = client or OpenRouterClient(settings=self.settings)

    def _build_messages(
        self,
        prompt: str | list[LLMMessage],
        system_prompt: str | None = None,
    ) -> list[LLMMessage]:
        """Normalize input prompt and optional system instructions into LLMMessage objects."""
        if isinstance(prompt, list):
            messages = list(prompt)
            if system_prompt and not (messages and messages[0].role == MessageRole.SYSTEM):
                messages.insert(0, LLMMessage(role=MessageRole.SYSTEM, content=system_prompt))
            return messages

        messages = []
        if system_prompt:
            messages.append(LLMMessage(role=MessageRole.SYSTEM, content=system_prompt))
        messages.append(LLMMessage(role=MessageRole.USER, content=prompt))
        return messages

    async def generate_response(
        self,
        prompt: str | list[LLMMessage],
        *,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        """Generate conversational text response from the configured LLM provider."""
        messages = self._build_messages(prompt, system_prompt=system_prompt)
        target_model = model or self.settings.openrouter_model
        logger.info(
            "Executing LLM generation with %d message(s) [model=%s]",
            len(messages),
            target_model,
        )

        return await self.client.generate_response(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            model=target_model,
        )

    async def generate_structured_response(
        self,
        prompt: str | list[LLMMessage],
        response_model: type[T],
        *,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> StructuredLLMResponse[T]:
        """Generate and validate a structured response matching a target Pydantic schema."""
        messages = self._build_messages(prompt, system_prompt=system_prompt)
        target_model = model or self.settings.openrouter_model
        logger.info(
            "Executing structured LLM generation for schema %s [model=%s]",
            response_model.__name__,
            target_model,
        )

        return await self.client.generate_structured_response(
            messages=messages,
            response_model=response_model,
            temperature=temperature,
            max_tokens=max_tokens,
            model=target_model,
        )
