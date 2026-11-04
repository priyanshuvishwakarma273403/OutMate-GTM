# Outmate GTM — Model Context Protocol (MCP) Architecture

## 1. Overview of MCP in Outmate

The Model Context Protocol (MCP) is an open standard that allows LLM hosts (such as Claude.ai, desktop agents, and developer environments) to securely discover and invoke external tools and context providers.

In Outmate GTM, MCP serves two essential roles:
1. **Mode B Primary Interface**: Exposes Outmate's GTM intelligence capabilities directly to **Claude.ai** as a custom remote connector.
2. **Standardized Tool Protocol for Mode A**: The standalone Python agent interacts with research capabilities via the exact same MCP tool schemas.

---

## 2. Core Architectural Roles

```
┌────────────────────────────────────────────────────────┐
│                        MCP HOST                        │
│             (Claude.ai or Standalone Agent)            │
└───────────────────────────┬────────────────────────────┘
                            │ Discovers & invokes tools
                            ▼
┌────────────────────────────────────────────────────────┐
│                       MCP CLIENT                       │
│           (Claude.ai Client / OutmateMCPClient)        │
└───────────────────────────┬────────────────────────────┘
                            │ Transport (stdio or SSE)
                            ▼
┌────────────────────────────────────────────────────────┐
│                       MCP SERVER                       │
│           (app/mcp/server.py: OutmateMCPServer)        │
└───────────────────────────┬────────────────────────────┘
                            │ Dispatches validated params
                            ▼
┌────────────────────────────────────────────────────────┐
│                   MCP TOOL REGISTRY                    │
│          (app/mcp/registry.py: MCPToolRegistry)        │
└───────────────────────────┬────────────────────────────┘
                            │ Executes business logic
                            ▼
┌────────────────────────────────────────────────────────┐
│                 SHARED SERVICE KERNEL                  │
│       Company, People, Verification, Scoring, Report    │
└────────────────────────────────────────────────────────┘
```

### A. MCP Host
The LLM runtime responsible for initiating the conversation, maintaining chat state, and deciding which tools to call based on user input. In Mode A, this is our `AgentOrchestrator` using OpenRouter; in Mode B, this is Claude.ai.

### B. MCP Client
The component that translates host tool requests into JSON-RPC messages and dispatches them across the selected transport.
- For Mode A: `app.mcp.client.OutmateMCPClient`
- For Mode B: Claude.ai's built-in MCP client

### C. MCP Server
The server listening for client connections, declaring capabilities, handling session negotiation, and routing tool calls.
- Implemented in `app/mcp/server.py` using the official Python MCP SDK (`mcp.server.mcpserver.MCPServer`).

### D. MCP Tool Registry
A decoupled registry (`app/mcp/registry.py`) that manages tool definitions, parameter schemas, validation via Pydantic v2, and invocation dispatch to shared service classes.

---

## 3. Supported Transports

Outmate GTM supports two standard transport layers:

### 1. Streamable HTTP / Server-Sent Events (SSE) (Remote Production)
- **Use Case**: Connecting **Claude.ai** to a remote Outmate deployment.
- **Endpoint**: `/mcp/sse` (initiates SSE stream) and `/mcp/messages` (receives JSON-RPC commands).
- **Security**: Protected by `BearerAuthMiddleware` when `MCP_AUTH_ENABLED=true`. Clients must provide `Authorization: Bearer <MCP_AUTH_TOKEN>`.
- **Implementation**: Starlette SSE application mounted inside FastAPI (`app.mount("/mcp", mcp_server.get_sse_app())`).

### 2. Standard Input/Output (stdio) (Local Development)
- **Use Case**: Local development, command-line testing, and desktop client integrations (e.g. Claude Desktop).
- **Execution**: `outmate run-mcp` or `python -m app.cli.main run-mcp`.
- **Implementation**: `mcp.server.mcpserver.MCPServer.run_stdio_async()`.

---

## 4. Planned GTM Tool Specifications

Outmate GTM plans five specialized GTM research tools:

| Tool Name | Service Dependency | External Integration | Purpose |
|---|---|---|---|
| `search_company` | `CompanyResearchService` | Search Provider | Extract company profile, domain, headcount, tech stack |
| `find_decision_makers` | `PeopleResearchService` | Search Provider | Discover executive prospects filtered by seniority and department |
| `get_person_details` | `PeopleResearchService` | Search Provider | Enrich professional background, contact handles, presence |
| `verify_person` | `VerificationService` | Search Provider | Corroborate current title and affiliation across public sources |
| `generate_gtm_report` | `ReportGenerationService` | In-context / OpenRouter | Synthesize structured research dossier and outreach angles |

### Detailed Tool Contracts

#### 1. `search_company`
- **Input**:
  ```json
  {
    "company_name": "Vercel",
    "domain": "vercel.com"
  }
  ```
- **Output**: `CompanyProfile` object with name, domain, industry, headcount, funding, and evidence.
- **Expected Errors**: `EntityNotFoundError`, `SearchProviderError`, `MCPValidationError`.

#### 2. `find_decision_makers`
- **Input**:
  ```json
  {
    "company_name": "Vercel",
    "company_domain": "vercel.com",
    "target_seniority": ["c_level", "vp"],
    "target_departments": ["engineering", "product"],
    "limit": 10
  }
  ```
- **Output**: `list[DecisionMaker]` with total found count.
- **Expected Errors**: `EntityNotFoundError`, `SearchProviderError`, `MCPValidationError`.

#### 3. `get_person_details`
- **Input**:
  ```json
  {
    "full_name": "Guillermo Rauch",
    "company_name": "Vercel",
    "linkedin_url": "https://linkedin.com/in/rauchg"
  }
  ```
- **Output**: Populated `DecisionMaker` profile with contact coordinates and career notes.
- **Expected Errors**: `EntityNotFoundError`, `SearchProviderError`, `MCPValidationError`.

#### 4. `verify_person`
- **Input**:
  ```json
  {
    "person_name": "Guillermo Rauch",
    "company_name": "Vercel",
    "title": "Chief Executive Officer",
    "linkedin_url": "https://linkedin.com/in/rauchg"
  }
  ```
- **Output**: `DecisionMaker` with updated `verification_status`, `is_verified` boolean, `confidence_score` (0.0 - 1.0), and corroborating evidence records.
- **Expected Errors**: `VerificationError`, `SearchProviderError`, `MCPValidationError`.

#### 5. `generate_gtm_report`
- **Input**:
  ```json
  {
    "query": "Who are the decision makers in Vercel?",
    "company": { ... },
    "decision_makers": [ ... ],
    "include_outreach_angles": true
  }
  ```
- **Output**: Structured `GTMReport` and executive Markdown string.
- **Expected Errors**: `ServiceError`, `MCPValidationError`.

