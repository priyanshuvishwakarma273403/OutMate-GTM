# Troubleshooting & Diagnostic Guide — Phase 5 CRM Integration

**System:** Outmate GTM Platform  
**Target:** Nango & HubSpot CRM Connectivity  

---

## 1. Common Issues & Resolutions

### 1.1 "Invalid Nango secret key provided (HTTP 401)"
- **Cause:** The `NANGO_SECRET_KEY` in `.env` is missing, miscopied, or revoked in the Nango Dashboard.
- **Resolution:**
  1. Open [app.nango.dev](https://app.nango.dev) → Settings → API Keys.
  2. Copy the Secret Key and update `.env`:
     ```env
     NANGO_SECRET_KEY=nango_sec_xxxxxxxxxxxx
     ```
  3. Restart the Outmate server.

### 1.2 "Connection does not exist in Nango (HTTP 404)"
- **Cause:** The requested tenant `connection_id` has not completed the OAuth flow or was deleted.
- **Resolution:**
  1. Navigate to `http://localhost:8000/integrations`.
  2. Click **Connect with HubSpot** and complete the authorization prompt.
  3. Upon redirect/close, the connection status will transition to **Connected**.

### 1.3 "OAuth connection for hubspot expired or revoked (HTTP 401 via proxy)"
- **Cause:** The user revoked Outmate's access in their HubSpot portal, or HubSpot invalidated the refresh token.
- **Resolution:**
  1. Navigate to `/integrations`.
  2. Click **Reconnect** to re-authorize and refresh credentials via Nango.

### 1.4 "Cross-tenant access violation"
- **Cause:** A request with tenant header `X-Organization-Id: tenant_b` attempted to access data associated with `org_tenant_a`.
- **Resolution:** Ensure client application passes the correct matching organization context headers.

### 1.5 "Nango Connect SDK could not be loaded"
- **Cause:** The browser or network environment blocked loading `https://assets.nango.dev/connect-ui/index.js`.
- **Resolution:** Verify internet access, check ad-blockers, or configure local CDN proxy.

