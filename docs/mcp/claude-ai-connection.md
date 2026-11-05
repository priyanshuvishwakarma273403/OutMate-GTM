# Connecting Outmate GTM to Claude.ai & Claude Desktop

This guide explains how to connect Outmate GTM's production MCP server to **Claude.ai** (Custom Connectors) and **Claude Desktop**.

---

## 1. Connecting to Claude.ai (Custom Connector)

Claude.ai supports remote MCP servers using the modern **Streamable HTTP** transport.

### Step 1: Start the Outmate GTM Server

Ensure the server is running with Bearer authentication enabled:

```bash
# In your .env file
MCP_TRANSPORT=streamable_http
MCP_HOST=0.0.0.0
MCP_PORT=8000
MCP_ENDPOINT=/mcp
MCP_AUTH_MODE=bearer
MCP_BEARER_TOKEN=outmate_secret_key_claude_2026
```

Start the application:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Step 2: Expose Your Server to the Internet (if testing locally)

Claude.ai requires an internet-accessible HTTPS URL. You can use Cloudflare Tunnel or ngrok:

```bash
# Option A: Cloudflare Tunnel (recommended, no sign-in required)
cloudflared tunnel --url http://localhost:8000

# Option B: ngrok
ngrok http 8000
```

Take note of the assigned HTTPS URL (e.g., `https://outmate-gtm.trycloudflare.com`).

### Step 3: Configure Custom Connector in Claude.ai

1. Open **Claude.ai** in your browser.
2. Go to **Settings** -> **Developer** -> **Connectors** (or **Custom Connectors**).
3. Click **Add Connector**.
4. Configure the connector:
   - **Name**: `Outmate GTM Intelligence`
   - **Type**: `Remote MCP Server`
   - **Server URL**: `https://<your-tunnel-url>/mcp`
   - **Authentication**: `Bearer Token`
   - **Token**: `outmate_secret_key_claude_2026` (must match `MCP_BEARER_TOKEN`)
5. Click **Save** and verify the connection status turns **Connected**.

---

## 2. Connecting to Claude Desktop (stdio Transport)

For local desktop execution with zero network exposure, use the `stdio` transport.

### Configuration (`claude_desktop_config.json`)

On Windows, edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "outmate-gtm": {
      "command": "d:\\Outmate GTM\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "app.mcp.server",
        "--transport",
        "stdio"
      ],
      "env": {
        "OPENROUTER_API_KEY": "sk-or-v1-...",
        "TAVILY_API_KEY": "tvly-...",
        "LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

Restart Claude Desktop. The hammer icon in Claude Desktop will display the 9 Outmate GTM tools.

---

## 3. Example Natural-Language Prompts in Claude

Once connected, ask Claude naturally:

- *"Research the company Vercel and tell me about their business, tech stack, and funding stage."*
- *"Find the key decision makers in engineering and executive leadership at Stripe."*
- *"Verify Guillermo Rauch's current role and employment at Vercel using public sources."*
- *"Show me the public evidence citations used to verify the executives at OpenAI."*

Claude will automatically call:
1. `research_company` to gather corporate intelligence.
2. `find_decision_makers` to discover and rank prospects.
3. `verify_person` to corroborate current employment.
4. `get_decision_maker_sources` to cite authentic public records.

---

## 4. Troubleshooting & Common Issues

### Issue 1: `401 Unauthorized`
- **Cause**: The `Authorization: Bearer <token>` header does not match `MCP_BEARER_TOKEN`.
- **Solution**: Verify the token configured in Claude.ai matches the environment variable exactly. In local development without auth, set `MCP_AUTH_MODE=none`.

### Issue 2: `404 Not Found`
- **Cause**: Incorrect endpoint URL.
- **Solution**: Verify the URL ends with `/mcp` (e.g. `https://my-domain.com/mcp`). Check the readiness probe by navigating to `https://my-domain.com/mcp/health` in your browser.

### Issue 3: Stdio Protocol Deserialization Error
- **Cause**: Logging statements printed to `stdout` instead of `stderr`.
- **Solution**: Outmate GTM enforces strict stdout/stderr separation in `app/mcp/transports/stdio.py`. Ensure third-party libraries do not write unbuffered output to standard output.

### Issue 4: DNS Rebinding Protection Error
- **Cause**: Connecting via an unlisted hostname on localhost.
- **Solution**: The official SDK enables DNS rebinding protection for `127.0.0.1` and `localhost`. If using a custom local domain, configure `ALLOWED_ORIGINS` in your environment.

