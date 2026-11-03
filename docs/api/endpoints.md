# Outmate GTM — REST API Endpoints Specification

Outmate GTM provides foundational HTTP endpoints for process monitoring, subsystem readiness, API discovery, and remote MCP connectivity.

---

## 1. Endpoints Overview

| Method | Path | Tag | Description |
|---|---|---|---|
| `GET` | `/health` | Health | Liveness probe indicating if the process is responsive. |
| `GET` | `/ready` | Health | Readiness probe reporting status of configured dependencies without exposing credentials. |
| `GET` | `/docs` | Documentation | Interactive Swagger UI API documentation. |
| `GET` | `/redoc` | Documentation | ReDoc alternative API documentation. |
| `GET` | `/openapi.json`| Documentation | Raw OpenAPI 3.1 schema specification. |
| `GET` | `/mcp/sse` | MCP | Server-Sent Events stream for Claude.ai custom connector. |
| `POST`| `/mcp/messages`| MCP | JSON-RPC message receiver for remote MCP execution. |

---

## 2. Endpoint Details

### `GET /health`
- **Purpose**: Kubernetes/Docker liveness probe.
- **Status Code**: `200 OK`
- **Response Schema** (`HealthResponse`):
  ```json
  {
    "status": "ok",
    "app_name": "Outmate GTM",
    "version": "0.1.0",
    "environment": "development",
    "timestamp": "2026-11-03T14:30:00Z"
  }
  ```

### `GET /ready`
- **Purpose**: Dependency readiness evaluation without secret leakage.
- **Status Code**: `200 OK` (when ready or degraded in dev/test) or `503 Service Unavailable`.
- **Response Schema** (`ReadinessResponse`):
  ```json
  {
    "status": "ready",
    "app_name": "Outmate GTM",
    "version": "0.1.0",
    "timestamp": "2026-11-03T14:30:00Z",
    "dependencies": {
      "openrouter": {
        "name": "openrouter",
        "status": "healthy",
        "details": "Model: anthropic/claude-3.5-sonnet (gateway reachable)"
      },
      "nango": {
        "name": "nango",
        "status": "not_configured",
        "details": "NANGO_SECRET_KEY is not set (CRM proxy features disabled)"
      },
      "search_provider": {
        "name": "search_provider",
        "status": "healthy",
        "details": "Provider engine: exa"
      },
      "mcp_server": {
        "name": "mcp_server",
        "status": "healthy",
        "details": "Transport: sse, Auth: false"
      }
    }
  }
  ```
