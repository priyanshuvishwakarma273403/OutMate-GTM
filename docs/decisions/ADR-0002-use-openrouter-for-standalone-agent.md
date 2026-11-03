# ADR-0002: Selection of OpenRouter as the LLM Gateway for Mode A

## Status
Accepted

## Context
In Mode A, Outmate operates as an autonomous standalone research agent. Binding the application directly to a single proprietary LLM provider (e.g. OpenAI directly or Anthropic directly) introduces vendor lock-in, inflexible pricing, and vulnerability to provider outages or regional quota restrictions.

## Decision
We chose **OpenRouter** as the unified gateway for the standalone Python AI agent, accessed via an OpenAI-compatible client abstraction (`app/llm/openrouter.py`).

## Consequences

### Positive
- **Dynamic Model Selection**: Supports switching between top-tier models (`anthropic/claude-3.5-sonnet`, `openai/gpt-4o`, `meta-llama/llama-3.3-70b-instruct`) purely through the `OPENROUTER_MODEL` environment variable.
- **Provider-Independent Client Interface**: The agent orchestrator depends on `BaseLLMClient`, not OpenRouter-specific or OpenAI-specific classes.
- **Standardized Function Calling**: OpenRouter fully supports OpenAI tool calling schemas (`tools` and `tool_choice`), enabling seamless tool use with Outmate's MCP registry.
- **Cost & Quota Transparency**: Standardized usage metadata and cost tracking across providers.

### Negative
- Introduces an extra network hop to OpenRouter; however, latency overhead is minimal compared to model generation time.
