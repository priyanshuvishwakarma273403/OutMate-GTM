# Security & Tenant Isolation — Outmate GTM CRM Layer

**System:** Outmate GTM Platform  
**Scope:** Multi-tenant boundaries, token insulation, and authorization enforcement  

---

## 1. Zero-Token Architecture

Outmate GTM operates under a strict **Zero-Token Storage Policy**:
1. No OAuth `access_token` or `refresh_token` is ever returned to the client, stored in application memory, or written to persistent databases.
2. Nango securely holds and refreshes credentials in its encrypted vault.
3. Outmate servers interact using only authenticated proxy headers (`Connection-Id`, `Provider-Config-Key`, and server `NANGO_SECRET_KEY`).

---

## 2. Multi-Tenant Isolation Model

Tenant isolation prevents cross-tenant data leakage:

### 2.1 Connection Identity Mapping
Every tenant connection in Nango is prefixed with the canonical identifier:
- Organization connection: `org_{organization_id}`
- User personal connection: `usr_{user_id}`

### 2.2 Ownership Verification (`validate_tenant_ownership`)
Whenever an API request or MCP tool call executes:
1. The tenant context is extracted from headers (`X-Organization-Id`, `X-User-Id`) or MCP principal context (`get_current_tenant()`).
2. The `CRMService.validate_tenant_ownership()` method checks the internal connection registry.
3. If an organization attempts to query a connection that belongs to another organization, execution is immediately halted with `AuthorizationError("Cross-tenant access violation")`.

### 2.3 MCP Principal Scoping
MCP tool handlers enforce fine-grained scopes using `require_scope(MCPScopes.CRM_COMPANIES_READ)`. If a token lacks the required scope, execution fails with code `-32003 (MCPAuthorizationError)`.

---

## 3. Audit Logging

Every CRM query is logged to the centralized audit stream:
```text
[CRM-AUDIT] action=search_companies connection_id=org_acme object_type=company status=success
[CRM-AUDIT] action=get_company_crm_context connection_id=org_acme object_type=context status=success
```
Audit logs record the action, connection ID, object type, and status without logging confidential CRM customer details.

