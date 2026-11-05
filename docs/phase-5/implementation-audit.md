# Outmate GTM — Phase 5 Implementation & Architectural Audit

**Date:** November 2026  
**Status:** Approved & Initiated  
**Author:** Principal Software Architect, Senior Python Backend Engineer, AI Systems Engineer

---

## 1. Executive Summary

This document performs an exhaustive audit of the existing Outmate GTM repository following the completion of Phases 1 through 4, and defines the technical plan for **Phase 5: External Application Integration Layer using Nango + Real HubSpot OAuth & Proxy**.

Outmate GTM provides AI-driven Go-To-Market research, company profiling, and decision-maker identification. Phase 5 expands this platform to seamlessly incorporate real CRM intelligence (HubSpot) via Nango as an authorized data source, corroborating public web research with private CRM ground truth while maintaining strict tenant isolation, zero synthetic mock data, and robust prompt-injection defenses.

---

## 2. Audit of Existing Repository Phases (Phases 1–4)

### 2.1 Phase 1: OpenRouter LLM Integration
- **Components:**
  - `app/llm/providers/openrouter.py`: Async client supporting streaming and JSON mode using OpenRouter OpenAI-compatible API.
  - `app/llm/service.py`: Reusable LLM service supporting both unstructured text completion and Pydantic-based structured schema output (`get_structured_response`).
  - `app/agent/orchestrator.py` & `app/agent/planner.py`: Autonomous GTM research plan generation and tool invocation.
- **Audit Assessment:** Clean, resilient, handles timeouts and API failures with structured exceptions. Completely decoupled from external SaaS credentials.

### 2.2 Phase 2: Company Research Engine
- **Components:**
  - `app/integrations/search/`: Extensible search provider abstraction (`SearchProvider`) with real Tavily and Exa implementations.
  - `app/services/company_research.py`: Real-time company discovery, domain resolution, business model extraction, and evidence aggregation.
  - `app/domain/models/company.py`, `evidence.py`, `report.py`: Domain models ensuring evidence traceability and confidence scoring.
- **Audit Assessment:** Every company fact is backed by an `EvidenceRecord`. All claims link to public URLs. No synthetic company records exist.

### 2.3 Phase 3: Decision Maker Discovery & Verification
- **Components:**
  - `app/services/people_research.py`: Public web-based executive and decision-maker discovery.
  - `app/services/employment_verification.py`: Multi-factor corroboration of current employment status, preventing stale or fabricated roles.
  - `app/services/role_classification.py`: Seniority and functional department classification (Executive, VP, Director, Engineering, Sales, Finance, etc.).
  - `app/domain/models/person.py`: Full decision-maker profile with verified source citations.
- **Audit Assessment:** Strict verification rules require at least one corroborated current source before marking employment as verified.

### 2.4 Phase 4: Model Context Protocol (MCP) Infrastructure
- **Components:**
  - `app/mcp/server.py`: FastMCP/Starlette server offering Streamable HTTP transport mounted at `/mcp` and stdio transport.
  - `app/mcp/registry.py`: Centralized tool registry with 9 production GTM tools (`search_company`, `research_company`, `get_company_profile`, `find_decision_makers`, `verify_person`, `get_person_details`, `get_research_sources`, `get_decision_maker_sources`, `get_research_report`).
  - `app/mcp/auth/`: Multi-tier security with static bearer tokens, OIDC JWT verification, tenant isolation (`validate_tenant_access`), and scope authorization (`require_scope`).
  - `app/mcp/client/`: Reusable async Python MCP client (`OutmateMCPClient`) connecting via Streamable HTTP or stdio.
- **Audit Assessment:** 146 unit, contract, and integration tests passing. Full tenant validation and granular scope security in place.

---

## 3. Phase 5 Architectural Boundaries & Objectives

### 3.1 Role of Nango
- **Strictly Limited To:**
  1. Managing OAuth 2.0 connection lifecycle with HubSpot (authorization code exchange, token refresh, revocation).
  2. Issuing ephemeral Connect Session tokens for the frontend Connect UI (`POST /connect/sessions`).
  3. Securely proxying authenticated HTTP requests to HubSpot API (`/proxy/{endpoint}`).
- **Strictly Prohibited From:**
  - Storing Outmate application data, research reports, or agent plans.
  - Driving AI reasoning, prompt construction, or LLM calls.
  - Hosting MCP servers or replacing FastAPI routes.

### 3.2 HubSpot CRM Integration Scope
- **Strictly Read-Only:**
  - Supported Objects: Companies (`/crm/v3/objects/companies`), Contacts (`/crm/v3/objects/contacts`), Deals (`/crm/v3/objects/deals`).
  - Supported Associations: Company ↔ Contacts, Company ↔ Deals, Contact ↔ Deals (`/crm/v3/associations`).
  - Read-Only Guarantee: Outmate GTM **NEVER** executes `POST` (create), `PATCH`/`PUT` (update), or `DELETE` requests against HubSpot CRM objects. The adapter actively blocks non-GET/search methods and raises `CRMReadOnlyError`.
  - No synthetic records: If no connection exists or an account is missing, the system returns clear error diagnostics and never invents mock CRM records.

### 3.3 Security, Tenant Isolation, and Token Management
- **Zero Raw Tokens in Memory:** Outmate GTM never requests, reads, stores, or logs raw third-party access tokens or refresh tokens. All interactions pass through Nango's authenticated proxy using `Connection-Id` and `Provider-Config-Key`.
- **Tenant Context Mapping:** Each tenant/organization has an isolated `connection_id` formatted as `org_{organization_id}` or `usr_{user_id}`. Tenant verification ensures a tenant can only query their own CRM connection.
- **Prompt Injection Defense:** CRM records (company notes, contact titles, descriptions) are untrusted external inputs. When passed into LLM contexts or MCP tool responses, they are sanitized (stripping system delimiter spoofing) and isolated within `<crm_data>` delimiters.

---

## 4. Implementation Gap Analysis & Roadmap

| Subsystem | Existing State | Required Phase 5 State | Status |
| :--- | :--- | :--- | :--- |
| **Config** | Basic `nango_secret_key` and URLs in `app/core/config.py` | Full settings for Connect Sessions, timeouts, retries, and read-only flags | Ready to Implement |
| **Nango Client** | Basic stub in `app/integrations/nango/client.py` | Full typed client with Connect Sessions, status checks, connection deletion, and proxy calls | Ready to Implement |
| **CRM Models** | Not present | Normalized `CRMCompany`, `CRMContact`, `CRMDeal`, `CRMAssociation`, `CRMContextSummary` | Ready to Implement |
| **HubSpot Adapter**| Not present | Dedicated read-only adapter with property normalizers and association querying | Ready to Implement |
| **CRM Service** | Not present | High-level service handling tenant resolution, audit logging, and research corroboration | Ready to Implement |
| **Evidence Link** | `EvidenceSourceType` only contains web types | `EvidenceSourceType.HUBSPOT_CRM` added, enabling dual public + CRM evidence tracks | Ready to Implement |
| **MCP Tools** | 9 GTM tools | 9 additional read-only CRM tools added with `crm:*` scopes and tenant checks | Ready to Implement |
| **FastAPI Routes** | LLM, Health, Research, Decision-Makers | `/api/v1/integrations/*` and `/api/v1/crm/*` routes registered | Ready to Implement |
| **Connect UI** | None | Minimal frontend HTML/JS for Nango Connect UI and live connection status | Ready to Implement |
| **Tests & Docs** | Phase 1–4 tests passing | Comprehensive unit, contract, and live integration tests + 14 doc files | Ready to Implement |

---

## 5. Non-Negotiable Engineering Guardrails
1. **No Dummy/Mock Data:** If Nango credentials or a HubSpot connection are absent, status must report disconnected/unconfigured. No fabricated contacts or company profiles.
2. **Read-Only Enforced:** No write operations to CRM under any circumstances.
3. **No Secret Leaks:** `NANGO_SECRET_KEY` must never be sent to the frontend, included in HTTP responses, or written to logs.
4. **Strict Typing & Quality:** 100% clean `ruff`, `mypy`, and `pytest`.

