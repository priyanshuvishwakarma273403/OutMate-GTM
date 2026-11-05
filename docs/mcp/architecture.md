# Outmate GTM — MCP Infrastructure Architecture

## 1. System Overview

Outmate GTM implements a production-grade **Model Context Protocol (MCP)** infrastructure adhering strictly to the official Python MCP SDK (`mcp>=2.3.0`).

The MCP infrastructure exposes the core B2B research engine through standardized, interoperable tools, resources, and prompts, enabling seamless integration with:
- **Mode A (Standalone Python AI Agent)**: Uses the reusable `OutmateMCPClient` in in-process or network mode.
- **Mode B (Remote Claude.ai / External LLM Clients)**: Connects over modern **Streamable HTTP** (`/mcp`) with optional Bearer or OIDC token authorization.
- **Local Desktop Clients (Claude Desktop / CLI)**: Operates via stdio transport with strict stdout frame isolation and stderr logging.

```
                          ┌──────────────────────────────────────────────┐
                          │         External Consumers & Clients         │
                          │   Claude.ai  │  Claude Desktop  │ Mode A Agent│
                          └───────┬──────────────┬───────────────┬───────┘
                                  │              │               │
                            Streamable HTTP    stdio        In-Process / HTTP
                                  │              │               │
                                  ▼              ▼               ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Outmate MCP Server Layer                        │
│                                                                        │
│   ┌─────────────────────┐   ┌───────────────────┐   ┌──────────────┐   │
│   │ Authentication      │   │ Scope & Tenant    │   │ Capability   │   │
│   │ (Bearer/OIDC RS)    │   │ Enforcement       │   │ Discovery    │   │
│   └─────────────────────┘   └───────────────────┘   └──────────────┘   │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                     Registered Tool Adapters                   │   │
│   │  search_company         │  find_decision_makers │ sources/dossier│   │
│   │  research_company       │  verify_person        │ audit trails   │   │
│   │  get_company_profile    │  get_person_details   │                │   │
│   └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼ Thin Adapters (No Reimplementation)
┌────────────────────────────────────────────────────────────────────────┐
│                       Core Application Services                        │
│                                                                        │
│   CompanyResearchService  │  PeopleResearchService │ ReportStorage     │
│   Tavily/Exa SearchClient │  EmploymentVerifier   │ LLMService (OR)   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Transports

### A. Streamable HTTP Transport (`streamable_http`)
- **Modern MCP Specification**: Built on `MCPServer.streamable_http_app()`, replacing deprecated legacy SSE transports.
- **Endpoint**: Mounted at `/mcp` on the primary FastAPI ASGI server or run independently on dedicated port `8001`.
- **Health Probes**: Integrated `/health` and `/mcp/health` endpoints returning JSON readiness envelopes (`{"status": "ready", ...}`).
- **DNS Rebinding & CORS**: Protected against DNS rebinding attacks on localhost and respects `ALLOWED_ORIGINS` CORS configuration.

### B. Standard I/O Transport (`stdio`)
- **Protocol Isolation**: Strictly reserves file descriptor 1 (`stdout`) for JSON-RPC frame serialization.
- **Diagnostics Isolation**: All runtime logs, trace logs, and debug messages are redirected to file descriptor 2 (`stderr`).
- **Claude Desktop Compatibility**: Configurable in Claude Desktop's `claude_desktop_config.json`.

---

## 3. Security, Authentication & Authorization

### A. Three Authentication Tiers
1. **Unauthenticated Local Development (`MCP_AUTH_MODE=none`)**:
   - Zero friction for local testing and developer workstations.
   - Bypasses token verification while retaining scope audit logs.
2. **Personal Connector Bearer Token (`MCP_AUTH_MODE=bearer`)**:
   - Designed for personal testing in Claude.ai Custom Connectors.
   - Constant-time token verification (`hmac.compare_digest`) via `StaticBearerTokenVerifier`.
   - Never exposes plain tokens in logs or git.
3. **Enterprise OIDC / OAuth 2.1 Resource Server (`MCP_AUTH_MODE=oidc`)**:
   - Full JWT assertion verification conforming to RFC 8707.
   - Validates `iss` (Issuer), `aud` (Audience / Resource Server URI), and `exp` (Expiry).
   - Extracts caller identity, scopes, and tenant metadata directly from claims.

### B. Fine-Grained Scope Matrix
Every MCP tool requires a dedicated permission scope:
- `company:search`: Required for `search_company`
- `company:research`: Required for `research_company`
- `company:read`: Required for `get_company_profile`, `get_research_report`
- `people:discover`: Required for `find_decision_makers`
- `people:verify`: Required for `verify_person`
- `people:read`: Required for `get_person_details`
- `research:sources:read`: Required for `get_research_sources`, `get_decision_maker_sources`

### C. Multi-Tenant Data Isolation
The MCP execution layer enforces cross-tenant guardrails via `validate_tenant_access()`. Requests targeting stored research dossiers or candidate records verify the resource's `tenant_id` against the authenticated caller's active `PrincipalContext`. Mismatched access attempts are rejected immediately with `MCPAuthorizationError`.

---

## 4. Reusable Client (`OutmateMCPClient`)

The reusable Python client provides a unified interface across all three execution environments:
```python
from app.mcp.client import OutmateMCPClient

# 1. In-process direct execution (zero network overhead for Mode A agent)
client = OutmateMCPClient(transport="in_process")

# 2. Remote Streamable HTTP (for distributed microservices or remote testing)
client = OutmateMCPClient(
    transport="streamable_http",
    server_url="https://api.outmate.ai/mcp",
    auth_token="secret_bearer_token",
)

# 3. stdio subprocess (for local CLI automation)
client = OutmateMCPClient(
    transport="stdio",
    stdio_command="python",
    stdio_args=["-m", "app.mcp.server", "--transport", "stdio"],
)

# Dynamic Discovery and Invocation
tools = await client.list_tools()
result = await client.call_tool("search_company", {"query": "Vercel"})
```

