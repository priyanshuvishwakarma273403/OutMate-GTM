# ADR-0001: Selection of Python as the Core Language and Runtime

## Status
Accepted

## Context
Outmate GTM requires an asynchronous backend platform capable of handling LLM inference, web intelligence discovery, protocol execution (Model Context Protocol), and structured data modeling with strict validation.

We considered Node.js/TypeScript, Go, and Python.

## Decision
We chose **Python (3.11+)** with **FastAPI**, **Pydantic v2**, and modern async primitives (`asyncio`, `httpx`).

## Consequences

### Positive
- **Official MCP SDK**: The official Python MCP SDK provides native support for `MCPServer`, Streamable HTTP, SSE, and stdio transports.
- **Data Modeling & Validation**: Pydantic v2 offers unmatched JSON schema extraction, strict validation, and high performance via its compiled `pydantic-core` Rust engine.
- **AI Ecosystem Compatibility**: Python is the lingua franca of AI engineering, allowing seamless integration with OpenAI SDK, OpenRouter, and research algorithms.
- **Tooling**: Astral's `ruff` and `uv` provide sub-second linting, formatting, and dependency resolution.

### Negative
- CPU-intensive tasks require careful handling to avoid blocking the event loop; however, Outmate is almost entirely I/O-bound (HTTP search queries and LLM API requests).

