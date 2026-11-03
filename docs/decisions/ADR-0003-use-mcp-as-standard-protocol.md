# ADR-0003: Adoption of the Model Context Protocol (MCP) as the Standard Protocol

## Status
Accepted

## Context
Claude.ai supports external integrations through custom connectors using the Model Context Protocol (MCP). Additionally, custom tool-calling mechanisms in AI applications often suffer from fragmented schema definitions, non-standard error structures, and tight coupling to specific prompt formats.

## Decision
We adopted the official **Model Context Protocol (MCP)** SDK (`mcp`) to standardize tool definitions, parameter validation, and RPC execution across the entire Outmate platform.

## Consequences

### Positive
- **First-Class Claude.ai Integration (Mode B)**: Claude.ai can discover and invoke Outmate's GTM tools via remote Streamable HTTP/SSE without custom frontend code.
- **Unified Tool Contracts**: The same five tools (`search_company`, `find_decision_makers`, `get_person_details`, `verify_person`, `generate_gtm_report`) are registered once and shared between Mode A (OpenRouter agent) and Mode B (Claude.ai).
- **Transport Flexibility**: MCP supports both stdio (for local developer tooling and desktop clients) and SSE/Streamable HTTP (for remote cloud deployment).
- **Strict Schema Validation**: Tool parameters are strictly validated using Pydantic v2 schemas before handler execution.

### Negative
- Requires maintaining compliance with the evolving MCP specification.
