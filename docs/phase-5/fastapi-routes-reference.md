# FastAPI Routes Reference — Integrations & CRM APIs

**Base Prefix:** `/api/v1`  
**Tags:** `Integrations & OAuth`, `CRM Data (Read-Only)`  

---

## 1. Integrations Management Endpoints

### 1.1 `POST /api/v1/integrations/hubspot/connect-session`
Initiates a Nango Connect Session for HubSpot.
- **Request Body:**
  ```json
  {
    "user_id": "usr_123",
    "organization_id": "org_456"
  }
  ```
- **Response (HTTP 200):**
  ```json
  {
    "success": true,
    "data": {
      "token": "sess_tok_abc123",
      "connection_id": "org_456",
      "integration_id": "hubspot",
      "expires_at": "2026-11-05T13:00:00Z"
    }
  }
  ```

### 1.2 `GET /api/v1/integrations`
Lists supported integrations, connection health, and tenant connections.
- **Query Params:** `organization_id` (optional).
- **Response (HTTP 200):**
  ```json
  {
    "success": true,
    "data": {
      "integrations": [
        {
          "id": "hubspot",
          "name": "HubSpot CRM",
          "read_only": true,
          "connected": true,
          "active_connections_count": 1
        }
      ],
      "connections": [...]
    }
  }
  ```

### 1.3 `POST /api/v1/integrations/hubspot/verify`
Triggers server-side verification with Nango.
- **Request Body:** `{"connection_id": "org_456"}`
- **Response (HTTP 200):** `{"success": true, "data": {"connected": true, ...}}`

### 1.4 `POST /api/v1/integrations/hubspot/disconnect`
Revokes connection in Nango and local registry.
- **Request Body:** `{"connection_id": "org_456"}`
- **Response (HTTP 200):** `{"success": true, "message": "HubSpot integration connection revoked successfully"}`

---

## 2. CRM Data Query Endpoints (Read-Only)

All CRM query endpoints accept tenant headers:
- `X-Organization-Id`
- `X-User-Id`
- `X-Connection-Id`

### 2.1 `GET /api/v1/crm/companies`
- **Query Params:** `query`, `domain`, `limit` (default: 10).
- **Response (HTTP 200):** `{"success": true, "data": [...], "total": 1}`

### 2.2 `GET /api/v1/crm/companies/{company_id}`
- **Response (HTTP 200):** Returns single `CRMCompany` object or HTTP 404.

### 2.3 `GET /api/v1/crm/contacts`
- **Query Params:** `query`, `email`, `company_id`, `limit` (default: 20).
- **Response (HTTP 200):** `{"success": true, "data": [...], "total": 1}`

### 2.4 `GET /api/v1/crm/contacts/{contact_id}`
- **Response (HTTP 200):** Returns single `CRMContact` object or HTTP 404.

### 2.5 `GET /api/v1/crm/deals`
- **Query Params:** `company_id`, `limit` (default: 20).
- **Response (HTTP 200):** `{"success": true, "data": [...], "total": 1}`

### 2.6 `GET /api/v1/crm/companies/{company_id}/context`
- **Response (HTTP 200):** Returns aggregated `CRMContextSummary` (company + contacts + deals).

---

## 3. UI Route

### `GET /integrations`
Serves the management HTML page (`app/static/integrations.html`) displaying live connection status and the Nango Connect UI SDK.

