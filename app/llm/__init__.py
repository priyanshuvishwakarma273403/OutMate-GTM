"""LLM Gateway abstraction and OpenRouter adapter."""

from app.llm.base import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    MessageRole,
    StructuredLLMResponse,
    TokenUsage,
    ToolCallRequest,
    ToolDefinition,
)
from app.llm.openrouter import OpenRouterClient

__all__ = [
    "BaseLLMClient",
    "LLMMessage",
    "LLMResponse",
    "MessageRole",
    "OpenRouterClient",
    "StructuredLLMResponse",
    "TokenUsage",
    "ToolCallRequest",
    "ToolDefinition",
]
