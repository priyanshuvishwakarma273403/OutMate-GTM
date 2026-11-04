# Outmate GTM — REST API Endpoints Specification

Outmate GTM provides foundational HTTP endpoints for process monitoring, subsystem readiness, API discovery, and remote MCP connectivity.

---

## 1. Endpoints Overview

| Method | Path | Tag | Description |
|---|---|---|---|
| `GET` | `/health` | Health | Liveness probe indicating if the process is responsive. |
| `GET` | `/ready` | Health | Readiness probe reporting status of configured dependencies without exposing credentials. |
| `POST`| `/api/v1/llm/test` | LLM | Live OpenRouter completion test returning model metrics without credential exposure. |
| `POST`| `/api/v1/research/company` | Company Research | Multi-source real company research, evidence collection, and verification report. |
| `POST`| `/api/v1/research/company/preview` | Company Research | Previews identity resolution and generated search query plan without scraping. |
| `GET` | `/api/v1/research/{research_id}` | Company Research | Retrieves existing completed research report by ID. |
| `GET` | `/api/v1/research/{research_id}/sources` | Company Research | Retrieves source audit trail and provenance metadata for a completed research report. |
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

### `POST /api/v1/llm/test`
- **Purpose**: Test OpenRouter live LLM connectivity and token generation without exposing API credentials.
- **Status Code**: `200 OK`
- **Request Schema** (`LLMTestRequest`):
  ```json
  {
    "message": "Explain B2B Go-To-Market strategy in one sentence.",
    "system_prompt": "You are a senior GTM strategist.",
    "temperature": 0.2,
    "max_tokens": 100,
    "model": "openai/gpt-4o-mini"
  }
  ```
- **Response Schema** (`LLMTestResponse`):
  ```json
  {
    "status": "success",
    "model": "openai/gpt-4o-mini",
    "content": "A B2B Go-To-Market strategy is an actionable plan defining how a company targets, acquires, and retains business customers.",
    "usage": {
      "prompt_tokens": 24,
      "completion_tokens": 20,
      "total_tokens": 44
    },
    "duration_ms": 320.5
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: `AuthenticationError` (invalid API key) or `LLMTimeoutError`.
  - `422 Unprocessable Entity`: Input validation error (e.g. empty or missing `message`).

### `POST /api/v1/research/company/preview`
- **Purpose**: Validate company target, resolve domain identity, and preview generated search queries without executing web retrieval.
- **Status Code**: `200 OK`
- **Request Schema** (`CompanyPreviewRequest`):
  ```json
  {
    "company_name": "Vercel",
    "website_domain": "vercel.com"
  }
  ```
- **Response Schema** (`CompanyPreviewResponse`):
  ```json
  {
    "company_name": "Vercel",
    "normalized_name": "Vercel",
    "supplied_domain": "vercel.com",
    "resolved_domain": "vercel.com",
    "official_website": "https://vercel.com",
    "resolution_status": "resolved",
    "confidence": 0.98,
    "planned_search_queries": [
      "\"Vercel\" company overview products services",
      "\"Vercel\" headquarters headcount founded funding",
      "site:vercel.com about OR company OR products"
    ],
    "candidate_domains": ["vercel.com"]
  }
  ```

### `POST /api/v1/research/company`
- **Purpose**: Execute live company research with Tavily web search, SSRF-protected page retrieval, BeautifulSoup extraction, evidence-constrained LLM synthesis, and corroboration verification.
- **Status Code**: `200 OK`
- **Request Schema** (`CompanyResearchRequest`):
  ```json
  {
    "company_name": "Vercel",
    "website_domain": "vercel.com",
    "research_depth": "standard"
  }
  ```
- **Response Schema** (`CompanyResearchReport`):
  ```json
  {
    "research_id": "ec0216c2-3240-42cc-a661-dc972d9fbc85",
    "company": {
      "name": "Vercel",
      "domain": "vercel.com",
      "legal_name": "Vercel Inc.",
      "description": "Frontend cloud platform providing developer tools and global hosting.",
      "industry": "cloud_infrastructure",
      "headquarters": "San Francisco, CA",
      "estimated_headcount": 500,
      "founded_year": 2015,
      "funding_stage": "series_c_plus",
      "tech_stack": ["Next.js", "React", "TypeScript"],
      "evidence": [],
      "last_researched_at": "2026-11-04T04:24:20Z"
    },
    "identity_status": "resolved",
    "findings": [
      "Frontend deployment and cloud developer platform pioneer.",
      "Primary developers and maintainers of Next.js."
    ],
    "evidence": [
      {
        "source_url": "https://vercel.com/about",
        "source_type": "official_website",
        "title": "About Vercel",
        "snippet": "Vercel is the platform for frontend developers...",
        "verification_status": "verified",
        "confidence": 0.96
      }
    ],
    "source_summary": {
      "sources_discovered": 15,
      "sources_retrieved": 6,
      "sources_rejected": 0,
      "sources": []
    },
    "limitations": [
      "Funding stage was not explicitly disclosed in retrieved excerpts."
    ],
    "warnings": [],
    "overall_status": "completed",
    "duration_ms": 18388.5
  }
  ```

### `GET /api/v1/research/{research_id}`
- **Purpose**: Retrieve an existing completed research report by ID.
- **Status Code**: `200 OK` or `404 Not Found`.

### `GET /api/v1/research/{research_id}/sources`
- **Purpose**: Retrieve the audit trail and provenance metadata of discovered and retrieved sources for a completed research report.
- **Status Code**: `200 OK` or `404 Not Found`.

