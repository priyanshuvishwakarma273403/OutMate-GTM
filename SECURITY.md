# Security Policy for Outmate GTM

Outmate GTM processes company research and professional executive data. Maintaining confidentiality, data integrity, and responsible data collection is paramount.

---

## 1. Security Principles

### A. Zero Credential Exposure
- All API keys (OpenRouter, Nango, Search Providers) and MCP Bearer tokens reside server-side in environment variables.
- The `app.core.logging.SecretSanitizingFormatter` automatically redacts keys matching sensitive token patterns (`sk-*`, `Bearer *`, `api-key`) before records are written to stdout or logs.
- The `/ready` and `/health` endpoints explicitly report configuration presence without revealing key values.

### B. Dual-Mode Authentication & Remote MCP Protection
- Remote MCP server endpoints exposed over Streamable HTTP/SSE for Claude.ai are protected by `BearerAuthMiddleware`.
- When `MCP_AUTH_ENABLED=true`, unauthenticated requests receive `401 Unauthorized` and mismatched tokens receive `403 Forbidden`.
- Production CORS configurations forbid wildcard (`*`) origins.

### C. Third-Party OAuth Proxy Security (Nango)
- Third-party CRM access tokens (e.g. HubSpot) are never stored in application code or client-side stores.
- Nango functions strictly as an authorized reverse proxy; requests pass through Nango with tenant `Connection-Id` headers.

### D. Responsible Data Collection
- Outmate GTM collects information exclusively from public, indexed records, press releases, public corporate blogs, SEC filings, and conference rosters.
- The platform strictly forbids unauthorized scraping of authenticated LinkedIn member sessions or violating platform terms of service.
- Evidence records retain verifiable canonical URLs, timestamps, and confidence metrics to guarantee transparency and dispute resolution.

---

## 2. Reporting a Vulnerability

If you discover a potential security vulnerability within Outmate GTM, please disclose it responsibly:

1. **Email**: Send vulnerability reports directly to `security@outmate.ai`.
2. **Details to Include**:
   - Description of the vulnerability.
   - Step-by-step reproduction instructions or proof-of-concept.
   - Affected versions or components.
   - Potential impact assessment.
3. **Response Timeline**:
   - Initial acknowledgment within 24 hours.
   - Vulnerability assessment and triage within 72 hours.
   - Release patch timeline coordinated with the reporter.

Please do not disclose security issues publicly until a patch has been published.
