# Outmate GTM — Production Deployment Guide

## 1. Containerization Architecture

Outmate GTM is containerized using a multi-stage, non-root Docker build designed for security and minimal attack surface.

### Dockerfile Highlights
- **Base Image**: `python:3.12-slim` (minimal base with security updates).
- **Package Manager**: Astral `uv` for ultra-fast, deterministic wheel installations.
- **Unprivileged Runtime User**: Runs as `appuser` (`UID=1001`, `GID=1001`). No root privileges.
- **Port**: Exposes port `8000` (FastAPI + Streamable HTTP `/mcp`).
- **Health Check Probe**: Periodic curl query against `/health` every 30 seconds.

---

## 2. Docker Compose Deployment

To deploy using Docker Compose:

```bash
# 1. Ensure .env file has required API keys
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY and TAVILY_API_KEY

# 2. Build and launch container in detached mode
docker compose up -d --build

# 3. Verify container logs
docker compose logs -f outmate-gtm

# 4. Check application health
curl -f http://127.0.0.1:8000/health
curl -f http://127.0.0.1:8000/mcp/health
```

---

## 3. Production Environment Checklist

| Variable | Description | Recommended Production Value |
|---|---|---|
| `APP_ENV` | Application environment | `production` |
| `APP_HOST` | FastAPI bind address | `0.0.0.0` |
| `APP_PORT` | FastAPI bind port | `8000` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `OPENROUTER_API_KEY` | OpenRouter gateway credential | Real API Key |
| `OPENROUTER_MODEL` | Default model for synthesis | `openai/gpt-4o-mini` |
| `TAVILY_API_KEY` | Real web search provider credential | Real API Key |
| `MCP_TRANSPORT` | MCP server transport | `streamable_http` |
| `MCP_ENDPOINT` | MCP path prefix | `/mcp` |
| `MCP_AUTH_MODE` | MCP authentication | `bearer` (or `oidc`) |
| `MCP_BEARER_TOKEN` | Bearer token for Claude.ai connector | Strong random token (32+ chars) |
| `ALLOWED_ORIGINS` | CORS whitelist | Comma-separated trusted origins |

---

## 4. Kubernetes / Cloud Run Deployment

### Google Cloud Run
```bash
# Build image with Google Cloud Build
gcloud builds submit --tag gcr.io/PROJECT_ID/outmate-gtm:v1

# Deploy to Cloud Run
gcloud run deploy outmate-gtm \
  --image gcr.io/PROJECT_ID/outmate-gtm:v1 \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --set-env-vars "APP_ENV=production,MCP_AUTH_MODE=bearer" \
  --set-secrets "OPENROUTER_API_KEY=openrouter-key:latest,TAVILY_API_KEY=tavily-key:latest,MCP_BEARER_TOKEN=mcp-bearer-token:latest"
```

The Streamable HTTP MCP server is then directly reachable by Claude.ai at:
`https://outmate-gtm-<project-id>.run.app/mcp`

