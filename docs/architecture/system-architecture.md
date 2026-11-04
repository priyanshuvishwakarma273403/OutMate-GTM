# Outmate GTM — System Architecture

## 1. Executive Architectural Overview

Outmate GTM is an enterprise-grade AI research engine that automates company intelligence research and discovers verified business decision-makers from natural-language queries.

The platform provides a unified service kernel serving two independent execution modes:
- **Mode A (Standalone Python AI Agent)**: An autonomous CLI and background agent orchestrator communicating with LLMs via OpenRouter using OpenAI-compatible function calling.
- **Mode B (Claude.ai Custom Connector)**: A remotely deployed Model Context Protocol (MCP) server providing Streamable HTTP/SSE endpoints that Claude.ai connects to directly.

---

## 2. High-Level Architecture Diagram

```mermaid
graph TD
    subgraph Clients["Entry Points & Clients"]
        ModeAClient["CLI / API / Standalone Agent User<br/>(Mode A)"]
        ModeBClient["Claude.ai Web / Desktop App<br/>(Mode B: Custom Connector)"]
    end

    subgraph EntryLayers["Protocol & Gateway Layer"]
        Orchestrator["Agent Orchestrator<br/>(app/agent/orchestrator.py)"]
        OpenRouterClient["OpenRouter LLM Gateway<br/>(app/llm/openrouter.py)"]
        MCPServer["Remote MCP Server (SSE / Streamable HTTP)<br/>(app/mcp/server.py)"]
        MCPRegistry["MCP Tool Registry<br/>(app/mcp/registry.py)"]
    end

    subgraph SharedServices["Shared Business Service Kernel"]
        CompanyService["Company Research Service<br/>(app/services/company_research.py)"]
        PeopleService["People Research Service<br/>(app/services/people_research.py)"]
        VerifyService["Verification Service<br/>(app/services/verification.py)"]
        ScoringService["Scoring & Ranking Service<br/>(app/services/scoring.py)"]
        ReportService["Report Generation Service<br/>(app/services/report_generation.py)"]
    end

    subgraph DomainLayer["Pure Domain Layer"]
        DomainModels["Domain Models (Pydantic v2)<br/>CompanyProfile, DecisionMaker,<br/>EvidenceRecord, GTMReport"]
    end

    subgraph Integrations["External Integration Layer"]
        SearchClient["Search Provider Adapter<br/>(Exa / Serper / Tavily)"]
        NangoClient["Nango OAuth & Proxy Client<br/>(HubSpot CRM Integration)"]
    end

    %% Mode A flow
    ModeAClient --> Orchestrator
    Orchestrator <--> OpenRouterClient
    Orchestrator --> MCPRegistry

    %% Mode B flow
    ModeBClient -->|Streamable HTTP / SSE| MCPServer
    MCPServer --> MCPRegistry

    %% Dispatch to Shared Services
    MCPRegistry --> CompanyService
    MCPRegistry --> PeopleService
    MCPRegistry --> VerifyService
    MCPRegistry --> ScoringService
    MCPRegistry --> ReportService

    %% Services use Domain & Integrations
    SharedServices --> DomainModels
    CompanyService --> SearchClient
    PeopleService --> SearchClient
    VerifyService --> SearchClient
    SharedServices -.-> NangoClient
```

---

## 3. Execution Mode A: Standalone Python AI Agent (OpenRouter)

In Mode A, Outmate operates autonomously without Claude.ai:
1. User provides a query via CLI or API (e.g. *"Who are the decision makers in Vercel?"*).
2. The `ResearchPlanner` analyzes the query and extracts targeting constraints.
3. The `AgentOrchestrator` invokes `OpenRouterClient` (using model configured in `OPENROUTER_MODEL`, e.g. `anthropic/claude-3.5-sonnet` or `openai/gpt-4o`).
4. The model returns tool calls corresponding to registered GTM tools (`search_company`, `find_decision_makers`, `get_person_details`, `verify_person`, `generate_gtm_report`).
5. Tool calls execute against shared services, returning structured JSON back into the agent conversation loop.
6. The agent terminates by generating a complete `GTMReport`.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Agent as Agent Orchestrator
    participant LLM as OpenRouter Gateway
    participant Registry as MCP Tool Registry
    participant Services as Shared Services Layer
    participant Search as Search Provider

    User->>Agent: "Who are the decision makers in Vercel?"
    Agent->>LLM: Prompt + Registered GTM Tool Definitions
    LLM-->>Agent: ToolCall(search_company, {company_name: "Vercel"})
    Agent->>Registry: Execute "search_company"
    Registry->>Services: CompanyResearchService.research_company("Vercel")
    Services->>Search: Public web query
    Search-->>Services: Search results
    Services-->>Registry: CompanyProfile
    Registry-->>Agent: Result JSON
    Agent->>LLM: Tool Result + Conversation History
    LLM-->>Agent: ToolCall(find_decision_makers, {company_name: "Vercel", target_seniority: ["c_level", "vp"]})
    Agent->>Registry: Execute "find_decision_makers"
    Registry->>Services: PeopleResearchService.find_decision_makers(...)
    Services-->>Registry: list[DecisionMaker]
    Registry-->>Agent: Result JSON
    Agent->>LLM: Compile Executive Dossier
    LLM-->>Agent: Structured GTM Report
    Agent-->>User: GTMReport (Dossier + Outreach Angles)
```

---

## 4. Execution Mode B: Claude.ai Custom Connector (Remote MCP Server)

In Mode B, Claude.ai acts as the host and orchestration engine:
1. Outmate GTM is deployed to an HTTPS host (e.g., `https://api.outmate.ai/mcp/sse`).
2. The user connects Claude.ai to this URL using Claude's Custom Connector settings.
3. Claude.ai connects via Server-Sent Events (SSE) and receives the list of available tools (`list_tools`).
4. When the user asks Claude.ai a question in chat, Claude chooses when to call Outmate's GTM tools via POST requests to the MCP endpoint.
5. `OutmateMCPServer` validates the input schema, checks Bearer authorization (if configured), and executes the exact same shared service kernel.
6. Structured tool results are rendered directly inside Claude.ai's conversational interface.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Claude as Claude.ai
    participant MCPServer as Outmate MCP Server (SSE)
    participant Registry as MCP Tool Registry
    participant Services as Shared Services Layer

    Note over Claude,MCPServer: Connection established via SSE Transport (/mcp/sse)
    Claude->>MCPServer: list_tools Request
    MCPServer-->>Claude: Tools: search_company, find_decision_makers, get_person_details, verify_person, generate_gtm_report

    User->>Claude: "Find decision makers at Datadog in security"
    Claude->>MCPServer: POST /mcp/messages (call_tool: find_decision_makers)
    MCPServer->>Registry: Execute "find_decision_makers"
    Registry->>Services: PeopleResearchService.find_decision_makers(...)
    Services-->>Registry: list[DecisionMaker]
    Registry-->>MCPServer: Formatted MCP Tool Result
    MCPServer-->>Claude: JSON Tool Result
    Claude-->>User: Natural language synthesis with interactive tables & citations
```

---

## 5. Architectural Invariants

1. **Service Reuse**: Every business function (company lookup, executive identification, verification, relevance ranking, report formatting) is implemented once in `app/services/` and consumed by both modes.
2. **Protocol Independence**: The services layer has zero dependency on FastAPI, Starlette, OpenAI SDK, or MCP SDK types.
3. **Strict Nango Boundaries**: Nango manages third-party OAuth tokens and executes authorized proxies (e.g. HubSpot CRM). It never manages LLM execution or internal agent states.
4. **Data Integrity**: All discovered entities must link back to public `EvidenceRecord` instances with confidence metrics.

