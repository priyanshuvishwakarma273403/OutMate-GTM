# ADR-0006: Shared Service Layer Architecture

## Status
Accepted

## Context
When supporting multiple entry points (FastAPI REST endpoints, CLI commands, OpenRouter standalone agent loops, and remote MCP servers), there is a significant risk that business logic will bleed into protocol handlers (e.g. writing research logic inside a FastAPI route or an MCP tool callback).

## Decision
We established a strict **Shared Service Layer Architecture** in `app/services/`:
- `CompanyResearchService`
- `PeopleResearchService`
- `VerificationService`
- `ScoringService`
- `ReportGenerationService`

All API endpoints, agent planners, and MCP tool handlers must delegate to these shared services. Services must be protocol-agnostic and accept/return pure domain models.

## Consequences

### Positive
- **Complete Testability**: Services can be unit-tested without mocking HTTP requests, ASGI transports, or MCP JSON-RPC protocol frames.
- **Clean Dependency Injection**: Dependencies (e.g., search clients, LLM clients, settings) are injected via service constructors.
- **Zero Duplication**: Business logic is written once and shared across API, Agent, and MCP interfaces.

### Negative
- Requires defining clean typed interfaces for every service before implementing tool handlers.

