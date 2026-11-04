# Outmate GTM

> **AI-Powered Go-To-Market (GTM) Intelligence and Decision-Maker Research Platform**

Outmate GTM is an enterprise-grade AI research engine that automates company intelligence research and identifies high-value business decision-makers from natural-language queries (e.g., *"Who are the decision-makers in the company Vercel?"*).

The platform is architected for dual-execution:
1. **Mode A — Standalone Python AI Agent**: Autonomous research agent powered by OpenRouter (OpenAI-compatible client abstraction) with tool calling and structured evidence compilation.
2. **Mode B — Remote Model Context Protocol (MCP) Server**: Connects directly to **Claude.ai** via custom connector over Streamable HTTP/SSE transport.

Both execution modes share the exact same domain models, service layer, verification logic, scoring algorithms, and report generation engines.

---

## Current Project Status

> **Phase 2: Production-Ready Real Company Research Engine** (Active)
>
> Phase 1 (OpenRouter LLM Integration) and Phase 2 (Real Company Research Engine) are completed and verified against live services. The engine uses Tavily Search API, strict SSRF-protected page retrieval, BeautifulSoup extraction, evidence-constrained LLM inference, and multi-source corroboration verification. Decision-maker discovery and MCP server hosting will be implemented in Phase 3.

---

## Key Features Planned

- **Company Intelligence Research**: Automated discovery of corporate domains, industry taxonomy, headcount, business models, and tech stacks.
- **Decision-Maker Discovery**: Role-based identification of C-suite executives, VPs, and department heads based on targeted GTM personas.
- **Evidence Collection & Cross-Verification**: Multi-source corroboration of prospect titles and corporate affiliations from public sources.
- **Relevance Scoring**: Multi-dimensional scoring evaluating persona fit, seniority, department alignment, and evidence confidence.
- **Structured GTM Reports**: Comprehensive markdown and JSON executive dossiers summarizing company context and decision-maker profiles.
- **Enterprise Integrations via Nango**: Seamless OAuth management and proxy requests for CRM systems like HubSpot.

---

## Architectural Highlights

- **Dual Execution Modes**: Standalone OpenRouter agent and Claude.ai MCP server running off a shared service kernel.
- **Strict Layered Separation**: Domain models do not depend on external SDKs; API routes do not contain business logic; services are protocol-agnostic.
- **Strict Role for Nango**: Nango handles only third-party OAuth connections and authorized proxy calls—never AI orchestration or MCP hosting.
- **Standard MCP Implementation**: Built using the official Python MCP SDK with stdio and HTTP/SSE transports.
- **Zero Heavyweight Bloat**: Lightweight and async-first using FastAPI, Pydantic v2, HTTPX, and standard library primitives.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Runtime & Language** | Python 3.11+ (Python 3.12 recommended) |
| **Web Framework & API** | FastAPI, Uvicorn, Starlette |
| **Data Validation & Settings** | Pydantic v2, Pydantic Settings |
| **LLM Gateway (Mode A)** | OpenRouter via OpenAI Python SDK |
| **Protocol Integration (Mode B)** | Official Python MCP SDK (`mcp`) |
| **HTTP & Networking** | HTTPX (async client with retry and timeout policies) |
| **OAuth & CRM Proxy** | Nango Cloud / Self-hosted API proxy |
| **Quality & Tooling** | Ruff (lint & format), mypy (strict type checking), pytest |

---

## Architecture Summary

```
                       ┌────────────────────────────────┐
                       │        Claude.ai Client        │
                       └───────────────┬────────────────┘
                                       │ (Mode B: MCP / HTTP-SSE)
                                       ▼
┌──────────────────────┐      ┌─────────────────────────┐
│ Standalone AI Agent  │      │    Remote MCP Server    │
│ (Mode A: OpenRouter) │      │  (app/mcp/server.py)    │
└──────────┬───────────┘      └────────────┬────────────┘
           │                               │
           └───────────────┬───────────────┘
                           │
                           ▼
          ┌──────────────────────────────────┐
          │      Shared Services Layer       │
          │   (Company, People, Scoring,     │
          │    Verification, Reporting)      │
          └────────────────┬─────────────────┘
                           │
       ┌───────────────────┴───────────────────┐
       ▼                                       ▼
┌──────────────┐                       ┌──────────────┐
│ Domain Layer │                       │ Integrations │
│  (Pydantic)  │                       │   (Nango)    │
└──────────────┘                       └──────────────┘
```

See [docs/architecture/system-architecture.md](docs/architecture/system-architecture.md) for full diagrams and specifications.

---

## Prerequisites

- **Python**: Version 3.11 or 3.12
- **uv** (recommended) or **pip**: Fast Python package installer
- **Make** (optional, for convenience scripts)
- **Docker & Docker Compose** (optional, for containerized execution)

---

## Quickstart

### 1. Clone & Set Up Environment

```bash
# Clone the repository
git clone https://github.com/your-org/outmate-gtm.git
cd outmate-gtm

# Copy environment template
cp .env.example .env
```

### 2. Install Dependencies

Using `uv`:
```bash
uv venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

uv pip install -e ".[dev]"
```

Using standard `pip`:
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

Or using Makefile:
```bash
make install
```

### 3. Run the Development Server

```bash
# Start FastAPI and MCP endpoints
make run
# or directly:
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify the health check:
```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

### 4. Test OpenRouter LLM Gateway Endpoint

Once `OPENROUTER_API_KEY` is configured in `.env`, test the real endpoint:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/llm/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain B2B Go-To-Market in one sentence."}'
```

Example response:
```json
{
  "status": "success",
  "model": "anthropic/claude-3.5-sonnet",
  "content": "A B2B Go-To-Market strategy is a comprehensive plan defining how a business targets, acquires, and retains commercial accounts.",
  "usage": {
    "prompt_tokens": 18,
    "completion_tokens": 24,
    "total_tokens": 42
  },
  "duration_ms": 780.2
}
```

### 5. Execute Real Company Research

Preview research plan:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/research/company/preview \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Vercel"}'
```

Execute full live evidence-backed research:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/research/company \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Vercel", "website_domain": "vercel.com", "research_depth": "standard"}'
```

Retrieve completed report and audit sources:
```bash
curl http://127.0.0.1:8000/api/v1/research/<research_id>
curl http://127.0.0.1:8000/api/v1/research/<research_id>/sources
```

---

## OpenRouter LLM Integration Architecture

The LLM layer is built for high reliability, strict credential protection, and modular reuse across standalone agents and MCP tools:

1. **`app.llm.openrouter.OpenRouterClient`**:
   - Thin, asynchronous wrapper over the OpenAI Python SDK pointing to `https://openrouter.ai/api/v1`.
   - Injects credentials via `AppSettings` (`OPENROUTER_API_KEY`).
   - Translates upstream provider exceptions into typed Outmate domain exceptions (`AuthenticationError`, `LLMQuotaExceededError`, `LLMTimeoutError`, `LLMProviderError`).
   - Strips Markdown formatting fences (```json ... ```) automatically for resilient structured extraction.
   - Logs request telemetry (duration in ms, prompt/completion tokens) without leaking sensitive messages or authorization headers.

2. **`app.services.llm.LLMService`**:
   - Protocol-agnostic service layer consumed by FastAPI routes, CLI, and future research workflows.
   - Provides `generate_response()` for raw completions with optional system prompts.
   - Provides `generate_structured_response()` for Pydantic-validated JSON completions.

3. **Required Environment Variables**:
   - `OPENROUTER_API_KEY`: OpenRouter API key (`sk-or-v1-...`).
   - `OPENROUTER_MODEL`: Model identifier (default: `anthropic/claude-3.5-sonnet` or `openai/gpt-4o-mini`).
   - `OPENROUTER_BASE_URL`: Gateway URL (default: `https://openrouter.ai/api/v1`).
   - `OPENROUTER_TIMEOUT`: Client timeout in seconds (default: `60.0`).
   - `OPENROUTER_MAX_TOKENS`: Optional maximum tokens cap.
   - `OPENROUTER_TEMPERATURE`: Sampling temperature (default: `0.2`).

---

## Running Tests & Quality Checks

```bash
# 1. Run unit tests and mocked integration tests (excluding live network tests)
pytest

# 2. Run the optional live integration test with real OpenRouter API
pytest -m live

# 3. Run Ruff linter and code formatter checks
ruff check app tests
ruff format --check app tests

# 4. Run mypy static type checking
mypy app tests
```

---

## Common Errors & Troubleshooting

| Error | Root Cause | Solution |
|---|---|---|
| `AuthenticationError: Invalid or missing OpenRouter API key` | `OPENROUTER_API_KEY` is empty, expired, or invalid. | Verify `OPENROUTER_API_KEY` in `.env` starts with `sk-or-v1-`. |
| `LLMQuotaExceededError: OpenRouter rate limit or quota exceeded` | Out of credits or rate limit hit on chosen model. | Check balance at [openrouter.ai/credits](https://openrouter.ai/credits) or switch to a lower-cost model. |
| `LLMTimeoutError: OpenRouter request timed out` | Upstream provider latency exceeded `OPENROUTER_TIMEOUT`. | Increase `OPENROUTER_TIMEOUT` in `.env` (e.g., `90.0` or `120.0`). |
| `LLMResponseParsingError: Failed to parse LLM response into schema` | Model did not output valid JSON matching Pydantic schema. | Refine system prompt instructions or reduce `temperature` to `0.0`. |


---

## Documentation Index

- [System Architecture](docs/architecture/system-architecture.md)
- [Data Flow Specification](docs/architecture/data-flow.md)
- [MCP Architecture & Tools](docs/architecture/mcp-architecture.md)
- [Integration Boundaries (OpenRouter vs Nango vs MCP)](docs/architecture/integration-boundaries.md)
- [Local Development Guide](docs/setup/local-development.md)
- [Environment Variables Reference](docs/setup/environment-variables.md)
- [Architecture Decision Records (ADRs)](docs/decisions/)
- [Contributing Guidelines](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)

---

## Roadmap

- [x] **Phase 1: Project Setup & Architectural Foundation**
  - Modular monorepo scaffolding
  - Domain models & schemas
  - Centralized configuration & lazy validation
  - MCP tool registry & contracts
  - OpenRouter client abstraction
  - Nango proxy client abstraction
  - FastAPI health & readiness endpoints
  - Test suites & CI tooling configuration
- [x] **Phase 2: Real Company Research Engine** (Current)
  - Tavily search provider integration with exponential retries
  - Company identity resolution & ambiguity detection
  - Safe source retrieval with strict SSRF & size limits
  - BeautifulSoup HTML content & metadata extraction
  - Evidence-constrained LLM synthesis (zero hallucination)
  - Cross-source verification and confidence scoring
  - REST endpoints (`/company`, `/preview`, `/{id}`, `/{id}/sources`)
- [ ] **Phase 3: Decision-Maker Discovery & Integrations**
  - Public leadership & executive role discovery
  - Decision-maker relevance scoring engine
  - Nango HubSpot CRM export
  - Executive GTM report templating (Markdown & PDF)
  - Claude.ai production connector deployment

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

