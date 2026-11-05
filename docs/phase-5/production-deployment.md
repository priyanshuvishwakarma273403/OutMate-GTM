# Production Deployment Guide — Phase 5 CRM Integration

**System:** Outmate GTM Platform  
**Deployment Target:** Containerized Docker / Cloud Virtual Private Cloud  

---

## 1. Environment Configuration Checklist

Before deploying Phase 5 in staging or production, ensure the following environment variables are set in your secrets manager:

| Variable | Recommended Production Value | Description |
| :--- | :--- | :--- |
| `APP_ENV` | `production` | Enables production security constraints |
| `NANGO_SECRET_KEY` | *(Secret Vault)* | Production Nango Secret Key |
| `NANGO_BASE_URL` | `https://api.nango.dev` | Nango API URL (or regional self-hosted endpoint) |
| `NANGO_INTEGRATION_ID_HUBSPOT` | `hubspot` | Matching Nango integration key |
| `HUBSPOT_READ_ONLY` | `true` | Enforces read-only guarantees |
| `INTEGRATION_MAX_RETRIES`| `3` | Maximum retry attempts on transient network failures |
| `OUTMATE_PUBLIC_BASE_URL`| `https://api.outmate.ai` | Publicly reachable API base URL |
| `OUTMATE_FRONTEND_URL` | `https://app.outmate.ai` | Client frontend application URL |
| `ALLOWED_ORIGINS` | `https://app.outmate.ai` | Restrict CORS to authenticated frontend domains |

---

## 2. Docker Deployment

The Outmate Docker container packages the complete Phase 1–5 backend, static assets, and MCP server.

```bash
docker build -t outmate-gtm:phase-5 .
docker run -d \
  -p 8000:8000 \
  --env-file .env.production \
  --name outmate-gtm-service \
  outmate-gtm:phase-5
```

---

## 3. Production Health & Readiness Verification

Once deployed:
1. Verify API readiness:
   ```bash
   curl -f http://localhost:8000/health
   ```
2. Verify MCP Streamable HTTP endpoint:
   ```bash
   curl -f http://localhost:8000/mcp/health
   ```
3. Verify Integrations catalog:
   ```bash
   curl -f http://localhost:8000/api/v1/integrations
   ```
4. Access the web dashboard at `http://localhost:8000/integrations`.

