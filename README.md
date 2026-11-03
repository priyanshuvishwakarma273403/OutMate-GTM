# Outmate GTM

> **AI-Powered Go-To-Market (GTM) Intelligence and Decision-Maker Research Platform**

Outmate GTM is an enterprise-grade AI research engine that automates company intelligence research and identifies high-value business decision-makers from natural-language queries (e.g., *"Who are the decision-makers in the company Vercel?"*).

The platform is architected for dual-execution:
1. **Mode A — Standalone Python AI Agent**: Autonomous research agent powered by OpenRouter (OpenAI-compatible client abstraction) with tool calling and structured evidence compilation.
2. **Mode B — Remote Model Context Protocol (MCP) Server**: Connects directly to **Claude.ai** via custom connector over Streamable HTTP/SSE transport.

Both execution modes share the exact same domain models, service layer, verification logic, scoring algorithms, and report generation engines.

---

## Current Project Status

> **Phase 1: Project Foundation & Architecture** (Active)
>
> This repository contains the complete architectural foundation, interfaces, contracts, configuration management, MCP server definitions, and testing baseline. Actual research search engines, LLM inference endpoints, and external OAuth proxies will be implemented in Phase 2.

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

---

## Running Tests & Quality Checks

```bash
# Run pytest test suite
make test

# Run Ruff linter and formatter checks
make lint
make format

# Run mypy static type analysis
make typecheck
```

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

- [x] **Phase 1: Project Setup & Architectural Foundation** (Current)
  - Modular monorepo scaffolding
  - Domain models & schemas
  - Centralized configuration & lazy validation
  - MCP tool registry & contracts
  - OpenRouter client abstraction
  - Nango proxy client abstraction
  - FastAPI health & readiness endpoints
  - Test suites & CI tooling configuration
- [ ] **Phase 2: Service Layer & Provider Implementations**
  - Search provider integration (Exa / Tavily / Serper)
  - Decision-maker scoring engine
  - Verification & corroboration heuristics
  - OpenRouter prompt engineering & tool loop
  - Remote MCP server HTTP/SSE mounting
- [ ] **Phase 3: Integrations & Reporting**
  - Nango HubSpot CRM export
  - Executive GTM report templating (Markdown & PDF)
  - Claude.ai production connector deployment

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
