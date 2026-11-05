# Nango Integration Guide — Outmate GTM

**System:** Outmate GTM Platform  
**Purpose:** Developer and operational reference for Nango API interactions and proxy usage  

---

## 1. Overview of Nango in Outmate GTM

Nango provides continuous third-party API authentication and OAuth token management. In Outmate GTM:
- **Nango Base URL:** `https://api.nango.dev` (or self-hosted equivalent)
- **Authentication:** Server-side HTTP Header `Authorization: Bearer <NANGO_SECRET_KEY>`
- **No Token Storage:** Outmate GTM never stores HubSpot access tokens. Calls are routed through Nango's authenticated proxy.

---

## 2. API Interaction Patterns

### 2.1 Connect Sessions (`POST /connect/sessions`)
Connect Sessions generate ephemeral, short-lived tokens allowing the frontend Connect UI SDK to authenticate an OAuth connection on behalf of a specific tenant.

**Outbound Request:**
```http
POST https://api.nango.dev/connect/sessions HTTP/1.1
Authorization: Bearer <NANGO_SECRET_KEY>
Content-Type: application/json

{
  "connection_id": "org_12345",
  "integration_id": "hubspot",
  "metadata": {
    "organization_id": "org_12345",
    "user_id": "usr_98765"
  }
}
```

**Response Handling:**
```json
{
  "data": {
    "token": "sess_tok_9b2d8f7a...",
    "expires_at": "2026-11-05T13:00:00Z"
  }
}
```

### 2.2 Connection Retrieval (`GET /connection/{connection_id}`)
Verifies that a connection exists and is currently authorized.

**Outbound Request:**
```http
GET https://api.nango.dev/connection/org_12345?provider_config_key=hubspot HTTP/1.1
Authorization: Bearer <NANGO_SECRET_KEY>
```

**Status Mapping:**
- `HTTP 200 OK`: Active and authorized (`status="connected"`).
- `HTTP 401 Unauthorized`: Invalid Nango Secret Key (`NangoAuthError`).
- `HTTP 404 Not Found`: Connection does not exist (`status="not_found"`).
- `HTTP 429 Too Many Requests`: Rate limit exceeded (`NangoRateLimitError`).

### 2.3 Authenticated Proxy Requests (`/proxy/*`)
Outmate GTM queries HubSpot CRM APIs strictly through the Nango proxy endpoint.

**Proxy Request Structure:**
```http
POST https://api.nango.dev/proxy/crm/v3/objects/companies/search HTTP/1.1
Authorization: Bearer <NANGO_SECRET_KEY>
Connection-Id: org_12345
Provider-Config-Key: hubspot
Content-Type: application/json

{
  "filterGroups": [{
    "filters": [{
      "propertyName": "domain",
      "operator": "EQ",
      "value": "stripe.com"
    }]
  }],
  "properties": ["name", "domain", "industry", "annualrevenue"],
  "limit": 10
}
```

**Error Translation & Resilience:**
- `HTTP 401`: Translates to `NangoExpiredConnectionError`. Nango signals that the downstream OAuth refresh token was revoked or expired.
- `HTTP 404`: Translates to `NangoConnectionNotFoundError` or empty list.
- `HTTP 429`: Translates to `NangoRateLimitError`.
- `HTTP 5xx / Network`: Automatically retried up to `INTEGRATION_MAX_RETRIES` (default: 3) with exponential backoff.

