# Outmate GTM — Company Research Engine Architecture (Phase 2)

> **Document Version**: 2.0  
> **Status**: Production-Ready  
> **Target Audience**: Backend Engineers, AI Architects, Security Reviewers  

---

## 1. Executive Summary

The **Outmate GTM Company Research Engine** is a real-time, public-evidence research pipeline designed to investigate target companies, discover canonical corporate domains, retrieve accessible web content, extract verified business attributes, and corroborate claims across multi-source evidence trails without hallucination or fabricated data.

### Core Tenets
1. **Zero Hallucination Policy**: The LLM is never treated as a source of truth. It is strictly constrained to extract facts present in retrieved excerpts. If an attribute is missing from public sources, it remains `null` or `UNKNOWN`.
2. **SSRF Defense-in-Depth**: Outbound web requests undergo strict pre-flight DNS inspection, blocking private IP ranges, loopbacks, link-local addresses, cloud metadata endpoints (`169.254.169.254`), and non-HTTP protocols.
3. **Traceable Evidence Provenance**: Every factual finding is linked to an `EvidenceRecord` containing the original URL, source classification, publication date, retrieval date, verification status, and confidence score.
4. **Protocol Independence**: The research pipeline lives entirely within reusable application services (`CompanyResearchService`, `VerificationService`, `SourceRetrievalService`, `ContentExtractionService`) consumable identically by FastAPI routes, Standalone Python agents, and future MCP tools.

---

## 2. Research Pipeline Data Flow

```
                      ┌────────────────────────────┐
                      │  User / Client Request     │
                      │  (company_name, [domain])  │
                      └─────────────┬──────────────┘
                                    │
                                    ▼
                      ┌────────────────────────────┐
                      │ Company Identity Service   │
                      │ - Suffix stripping         │
                      │ - Canonical domain lookup  │
                      │ - Ambiguity detection      │
                      └─────────────┬──────────────┘
                                    │
                                    ▼
                      ┌────────────────────────────┐
                      │ Query Generation & Search  │
                      │ - Targeted search queries  │
                      │ - Tavily Search API        │
                      │ - URL deduplication        │
                      └─────────────┬──────────────┘
                                    │
                                    ▼
                      ┌────────────────────────────┐
                      │ Source Retrieval Engine    │
                      │ - Strict SSRF validation   │
                      │ - Max 2MB streaming cap    │
                      │ - Content-Type validation  │
                      └─────────────┬──────────────┘
                                    │
                                    ▼
                      ┌────────────────────────────┐
                      │ HTML Content Extraction    │
                      │ - Boilerplate stripping    │
                      │ - Paragraph & meta parsing │
                      │ - Date extraction          │
                      └─────────────┬──────────────┘
                                    │
                                    ▼
                      ┌────────────────────────────┐
                      │ LLM Synthesis (OpenRouter) │
                      │ - Evidence-constrained     │
                      │ - Structured Pydantic schema│
                      │ - Zero assumption rules    │
                      └─────────────┬──────────────┘
                                    │
                                    ▼
                      ┌────────────────────────────┐
                      │ Evidence Verification      │
                      │ - First-party corroboration│
                      │ - Multi-source scoring     │
                      │ - Status: VERIFIED, etc.   │
                      └─────────────┬──────────────┘
                                    │
                                    ▼
                      ┌────────────────────────────┐
                      │ Final Company Research     │
                      │ Report + Audit Trail       │
                      └────────────────────────────┘
```

---

## 3. Search Provider Integration

- **Configured Engine**: **Tavily Search API** (`https://api.tavily.com/search`).
- **Authentication**: API key supplied via `TAVILY_API_KEY` or `SEARCH_API_KEY` in `AppSettings`.
- **Query Strategy**:
  1. `"<name>" company overview products services`
  2. `"<name>" headquarters headcount founded funding`
  3. `site:<domain> about OR company OR products` (when domain resolved)
- **Retry & Resilience**: Up to 3 automatic retries with exponential backoff on HTTP 429 (rate limit) and HTTP 5xx (transient gateway errors).
- **Security**: Search credentials are kept server-side and never echoed in API payloads or telemetry.

---

## 4. SSRF & Ingestion Security Controls

To protect internal infrastructure, containers, and VPC resources:

1. **Scheme Whitelist**: Strictly `http` and `https`. Schemes such as `file://`, `ftp://`, `gopher://`, `data://` are immediately rejected.
2. **DNS Pre-Flight Inspection**: Hostnames are resolved via TCP `getaddrinfo` before connection:
   - `127.0.0.0/8` (Loopback)
   - `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` (RFC 1918 Private networks)
   - `169.254.0.0/16` (Link-local & Cloud Metadata `169.254.169.254`)
   - `::1`, `fc00::/7`, `fe80::/10` (IPv6 loopback, unique local, link-local)
   - IPv4-mapped IPv6 representations (`::ffff:127.0.0.1`)
   - RFC 6052 NAT64 prefixes (`64:ff9b::/96`) are unwrapped to verify that the embedded IPv4 target is a public internet address.
3. **Internal Hostname Blocking**: `localhost`, `*.local`, `*.internal`, `*.localhost` are blocked prior to DNS resolution.
4. **Streaming Response Size Cap**: Maximum body limit of **2 Megabytes** enforced during streaming (`aiter_bytes()`). Exceeding payloads are terminated immediately to prevent memory starvation attacks.
5. **Content-Type Filter**: Only `text/html`, `application/xhtml+xml`, and `text/plain` are processed. Executables, archives, and binary documents are rejected.
6. **Redirect Re-Evaluation**: Redirects (up to 3) re-run the complete SSRF check on every new `Location` target before following.

---

## 5. Evidence Verification & Confidence Scoring

Every claim and profile attribute is evaluated by `VerificationService`:

| Verification Status | Definition | Typical Confidence | Corroboration Rule |
|---|---|---|---|
| `VERIFIED` | Corroborated with high certainty | `0.85` - `0.98` | Backed by official first-party website OR at least 2 independent third-party sources. |
| `PARTIALLY_VERIFIED` | Supported by single source | `0.50` - `0.65` | Sourced from a single third-party publication; pending multi-source confirmation. |
| `NOT_VERIFIED` | Insufficient evidence | `0.10` - `0.40` | Weak or contradictory provenance. |
| `CONFLICTING` | Opposing factual statements | `0.20` - `0.50` | Divergent headcounts or founding dates across sources; flagged for manual review. |
| `UNAVAILABLE` | Not found in public records | `0.00` | Attribute not disclosed publicly. |

---

## 6. Future Model Context Protocol (MCP) Tool Contracts

The research service architecture is decoupled from HTTP transports to support direct invocation by the future MCP server:

### 1. `search_company`
- **Inputs**: `query: str`, `max_results: int`
- **Output**: `list[SearchResultItem]` (url, title, snippet, score)
- **Service Dependency**: `app.integrations.search.factory.get_search_client()`

### 2. `research_company`
- **Inputs**: `company_name: str`, `website_domain: str | None`, `research_depth: str`
- **Output**: `CompanyResearchReport` (full verified dossier)
- **Service Dependency**: `app.services.company_research.CompanyResearchService.research_company()`

### 3. `get_company_profile`
- **Inputs**: `research_id: str`
- **Output**: `CompanyProfile` (clean corporate profile)
- **Service Dependency**: `app.services.report_storage.InMemoryReportRepository.get()`

### 4. `get_research_sources`
- **Inputs**: `research_id: str`
- **Output**: `SourceSummary` (audit trail and discovered URLs)
- **Service Dependency**: `app.services.report_storage.InMemoryReportRepository.get().source_summary`

---

## 7. Operational Limitations & Production Notes

1. **JavaScript-Heavy SPAs**: Simple client-rendered single-page applications without server-side rendering or OpenGraph meta tags may yield limited HTML paragraphs. In such cases, the engine automatically falls back to search provider snippets.
2. **Session Persistence**: In-memory repository preserves completed reports for the duration of the server process. Production clustered deployments should back this with persistent storage (e.g., PostgreSQL or Redis) in future phases.
3. **Paywalls & CAPTCHAs**: The engine respects website access controls and does not attempt to bypass paywalls or anti-bot protections.
