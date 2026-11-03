# Outmate GTM — Architectural Integration Boundaries

To prevent architectural drift and system coupling, this document defines the exact, non-negotiable boundaries of each core technology in Outmate GTM.

---

## 1. Responsibility Matrix

| Technology | Permitted Responsibilities | Prohibited Responsibilities |
|---|---|---|
| **Python Backend** | Core business logic, data modeling, scoring heuristics, verification algorithms, API serving, CLI execution. | Direct third-party OAuth token storage. |
| **OpenRouter** | LLM gateway for Mode A standalone agent (model routing, token usage, fallback models). | Never used in Mode B (Claude.ai uses Anthropic infrastructure directly). |
| **Nango** | Third-party OAuth connection lifecycle & authorized API proxy calls (e.g. HubSpot CRM). | **NEVER** used for AI orchestration, agent workflows, or MCP hosting. |
| **Model Context Protocol (MCP)** | Standardized tool registration, discovery, parameter validation, and RPC transport. | Never implements business or scraping logic directly (dispatches to Services). |
| **Claude.ai** | Conversational UI, user prompt evaluation, and client-side tool invocation for Mode B. | Does not govern Mode A standalone agent workflows. |

---

## 2. In-Depth Boundary Specifications

### A. OpenRouter Gateway (Mode A Only)
- **Role**: OpenRouter acts as an OpenAI-compatible gateway providing configurable model selection (e.g., `anthropic/claude-3.5-sonnet`, `openai/gpt-4o`, `meta-llama/llama-3.3-70b-instruct`) without code changes.
- **Constraints**:
  - OpenRouter is accessed exclusively through `app.llm.openrouter.OpenRouterClient` implementing `BaseLLMClient`.
  - Model names must never be hardcoded across business logic; they must be injected via `AppSettings.openrouter_model`.
  - Mode B (Claude.ai) does NOT communicate with OpenRouter. Claude.ai utilizes Anthropic's native execution pipeline.

### B. Nango (OAuth & Proxy Only)
- **Role**: Nango eliminates the need for homemade token refresh engines, encrypted database token stores, and provider-specific OAuth callback logic.
- **Strict Constraints**:
  - Nango is **NOT** an AI agent framework or orchestration engine.
  - Nango is **NOT** an MCP server.
  - The Python application never fetches raw third-party access tokens from Nango to store locally.
  - When Outmate exports a GTM dossier to HubSpot, it issues an authorized request to Nango's `/proxy` endpoint, passing tenant `Connection-Id` and `Provider-Config-Key`.

### C. Model Context Protocol (MCP)
- **Role**: MCP provides a clean protocol boundary between LLM reasoning and deterministic tools.
- **Strict Constraints**:
  - The MCP layer (`app/mcp/`) contains only schemas, registrations, and transport runners.
  - Tool handlers must call methods on shared services (`CompanyResearchService`, `PeopleResearchService`, etc.).
  - Both stdio (local) and SSE (remote) transports reuse the exact same `MCPToolRegistry`.

### D. Python Application Kernel
- **Role**: The source of truth for all domain entities, validation logic, scoring algorithms, and evidence corroboration.
- **Strict Constraints**:
  - Domain models in `app/domain/models/` must not import external provider SDKs (`openai`, `nango`, `mcp`).
  - Services must not depend on FastAPI `Request` objects or HTTP transport contexts.

### E. Claude.ai Integration (Mode B Only)
- **Role**: Claude.ai serves as an intelligent host that invokes Outmate tools over remote SSE.
- **Strict Constraints**:
  - Claude.ai interacts with Outmate solely as an external MCP client.
  - The remote MCP endpoint verifies caller authorization using Bearer token authentication before allowing tool execution.
