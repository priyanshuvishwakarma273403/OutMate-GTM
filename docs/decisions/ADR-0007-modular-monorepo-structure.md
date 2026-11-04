# ADR-0007: Modular Monorepo Project Structure

## Status
Accepted

## Context
Outmate GTM combines an API server, an agent orchestrator, a remote MCP server, external integrations, shared domain models, and developer tooling. We evaluated separating these into multi-repository microservices vs a modular single-repository structure.

Creating separate repositories or microservices at this early stage would introduce distributed networking complexity, duplicated schemas, version drift between domain models, and slow developer onboarding without real architectural benefits.

## Decision
We adopted a **Modular Monorepo Structure** organized cleanly under `app/`:

```
outmate-gtm/
    app/
        api/            # HTTP routes, health/readiness probes
        core/           # Config, logging, exceptions
        agent/          # Standalone agent orchestration & prompts (Mode A)
        llm/            # OpenRouter & LLM client abstractions
        mcp/            # MCP server, client, registry, tool contracts (Mode B)
        integrations/   # Nango client, search provider adapters
        services/       # Shared business logic & research services
        domain/models/  # Pure Pydantic domain models
        schemas/        # API DTOs and request/response models
        cli/            # Command-line entry points
    tests/
        unit/           # Fast isolated unit tests
        integration/    # Subsystem and API integration tests
        contract/       # MCP tool schema and contract tests
    docs/               # Architecture, ADRs, and guides
```

## Consequences

### Positive
- **Single Source of Truth**: Shared domain models and services are directly importable across agent, MCP, and API boundaries.
- **Fast Development Velocity**: Single virtual environment, unified test runner (`pytest`), single linter (`ruff`), and static type checker (`mypy`).
- **Clear Architectural Boundaries**: Strict isolation rules prevent lower layers (domain, services) from depending on upper layers (FastAPI, MCP).

### Negative
- Monorepos require discipline to prevent unauthorized circular dependencies; enforced by Ruff and Mypy checks.

