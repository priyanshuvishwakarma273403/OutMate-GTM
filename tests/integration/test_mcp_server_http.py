"""Integration tests for Outmate GTM Streamable HTTP MCP Server."""

from unittest.mock import MagicMock

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.mcp.configuration import MCPAuthMode, MCPConfiguration
from app.mcp.server import OutmateMCPServer
from app.mcp.transports.streamable_http import mcp_health_check


def test_mcp_server_initialization() -> None:
    """Verify OutmateMCPServer initializes with standard prompts, resources, and 9 tools."""
    server = OutmateMCPServer()
    assert server.mcp_app.name in (
        "outmate-mcp-server",
        "outmate-gtm-server",
        "Outmate GTM Intelligence MCP Server",
    )
    assert len(server.registry.list_tools()) in (9, 18)


async def test_mcp_health_check_endpoint() -> None:
    """Verify mcp_health_check returns valid JSON readiness response."""
    mock_request = MagicMock(spec=Request)
    response = await mcp_health_check(mock_request)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    assert b"outmate-gtm-server" in response.body
    assert b"streamable_http" in response.body


def test_mcp_streamable_http_app_creation() -> None:
    """Verify get_streamable_http_app builds a Starlette application with routes."""
    config = MCPConfiguration(auth_mode=MCPAuthMode.NONE, endpoint="/mcp")
    server = OutmateMCPServer(config=config)
    app = server.get_streamable_http_app()

    assert app is not None
    # Verify health routes are present
    route_paths = [r.path for r in app.routes if hasattr(r, "path")]
    assert "/health" in route_paths
    assert "/mcp/health" in route_paths


async def test_mcp_server_with_bearer_auth() -> None:
    """Verify OutmateMCPServer configures token verifier when auth mode is bearer."""
    config = MCPConfiguration(
        auth_mode=MCPAuthMode.BEARER,
        bearer_token="outmate_secret_token_abc123",
        endpoint="/mcp",
    )
    server = OutmateMCPServer(config=config)
    assert server.token_verifier is not None

    token_info = await server.token_verifier.verify_token("outmate_secret_token_abc123")
    assert token_info is not None
    assert token_info.client_id == "claude-personal-connector"

    # Invalid token rejected
    assert await server.token_verifier.verify_token("invalid_token") is None


def test_mcp_server_capabilities_resource() -> None:
    """Verify MCP capability resource is registered."""
    server = OutmateMCPServer()
    assert server.registry.get_tool("search_company") is not None
    assert server.registry.get_tool("find_decision_makers") is not None
    assert server.registry.get_tool("get_research_report") is not None
