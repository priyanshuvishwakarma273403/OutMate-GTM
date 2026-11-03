# Outmate GTM — Environment Variables Reference

All configuration variables are loaded and validated through `app.core.config.AppSettings` using Pydantic v2 Settings.

---

## Configuration Variable Reference

| Variable Name | Category | Execution Mode | Default Value | Description |
|---|---|---|---|---|
| `APP_NAME` | Application | Shared | `"Outmate GTM"` | Display name of the application reported in logs and health probes. |
| `APP_ENV` | Application | Shared | `"development"` | Runtime environment: `development`, `staging`, `production`, `test`. |
| `APP_HOST` | Application | Shared | `"127.0.0.1"` | IP address for binding the web and MCP server. |
| `APP_PORT` | Application | Shared | `8000` | Port for binding the server. |
| `LOG_LEVEL` | Application | Shared | `"INFO"` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `OPENROUTER_API_KEY` | OpenRouter | Mode A | `None` | API key from OpenRouter (https://openrouter.ai/keys). Required for Mode A. |
| `OPENROUTER_BASE_URL` | OpenRouter | Mode A | `"https://openrouter.ai/api/v1"` | Gateway endpoint URL for OpenAI-compatible inference. |
| `OPENROUTER_MODEL` | OpenRouter | Mode A | `"anthropic/claude-3.5-sonnet"` | Default model identifier for the standalone agent. |
| `OPENROUTER_TIMEOUT` | OpenRouter | Mode A | `60.0` | Timeout in seconds for LLM inference calls before raising `LLMTimeoutError`. |
| `OPENROUTER_MAX_RETRIES`| OpenRouter | Mode A | `3` | Number of automatic retries on network or rate limit errors. |
| `NANGO_SECRET_KEY` | Nango | CRM Proxy | `None` | Secret key for Nango API (https://app.nango.dev). Required for CRM proxy calls. |
| `NANGO_BASE_URL` | Nango | CRM Proxy | `"https://api.nango.dev"` | Host URL for Nango API and authorized proxy endpoints. |
| `NANGO_CONNECTION_ID` | Nango | CRM Proxy | `None` | Tenant or user connection identifier in Nango for CRM integrations. |
| `NANGO_INTEGRATION_ID` | Nango | CRM Proxy | `None` | Integration key (e.g. `hubspot`, `salesforce`). |
| `NANGO_TIMEOUT` | Nango | CRM Proxy | `30.0` | HTTP timeout in seconds when calling Nango proxy endpoints. |
| `SEARCH_PROVIDER` | Research | Shared | `"exa"` | Public research engine: `exa`, `serper`, `tavily`, or `mock`. |
| `SEARCH_API_KEY` | Research | Shared | `None` | API key for external search provider. Required if `SEARCH_PROVIDER != "mock"`. |
| `SEARCH_API_BASE_URL` | Research | Shared | `None` | Optional custom base URL if self-hosting a search crawler or proxy. |
| `SEARCH_TIMEOUT` | Research | Shared | `30.0` | Timeout in seconds for external search requests. |
| `MCP_TRANSPORT` | MCP | Mode B | `"sse"` | Transport mode: `sse` (Streamable HTTP for Claude.ai), `stdio`, `http`. |
| `MCP_HOST` | MCP | Mode B | `"127.0.0.1"` | Host address for MCP server. |
| `MCP_PORT` | MCP | Mode B | `8001` | Dedicated port if running standalone MCP runner. |
| `MCP_SERVER_NAME` | MCP | Mode B | `"outmate-mcp-server"` | Name declared during MCP handshake. |
| `MCP_AUTH_ENABLED` | MCP | Mode B | `false` | When `true`, enforces Bearer token authentication on `/mcp` endpoints. |
| `MCP_AUTH_TOKEN` | MCP | Mode B | `None` | Secret Bearer token configured in Claude.ai custom connector setup. |
| `ALLOWED_ORIGINS` | Security | Shared | `"http://localhost:3000,http://127.0.0.1:3000"` | Comma-separated CORS allowed origins. Wildcard forbidden in production. |
| `API_KEY_REQUIRED` | Security | Shared | `false` | When `true`, requires API key for standard REST endpoints. |
| `TESTING` | Testing | Testing | `false` | Set to `true` during automated test runs. |

---

## Lazy Validation Policy

To guarantee fast container cold-starts and seamless local testing:
1. Missing keys for `OPENROUTER_*` do **NOT** fail application boot. They are validated only when `validate_openrouter()` is called as Mode A starts.
2. Missing keys for `NANGO_*` do **NOT** fail application boot. They are validated only when third-party CRM exports are triggered.
3. The `/ready` probe inspects and reports which subsystems are healthy or unconfigured without throwing unhandled exceptions or crashing the server.
