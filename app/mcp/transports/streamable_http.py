"""Streamable HTTP transport builder for remote Claude.ai connectors and HTTP clients."""

from typing import Any

from mcp.server.mcpserver import MCPServer
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.core.logging import get_logger
from app.mcp.configuration import MCPConfiguration

logger = get_logger("mcp.transports.streamable_http")


async def mcp_health_check(request: Any) -> JSONResponse:
    """Readiness probe for MCP HTTP endpoint."""
    return JSONResponse(
        {
            "status": "ready",
            "mcp_server": "outmate-gtm-server",
            "transport": "streamable_http",
            "protocol_version": "2024-11-05",
        }
    )


def create_streamable_http_app(
    mcp_server: MCPServer,
    config: MCPConfiguration,
    allowed_origins: list[str] | None = None,
) -> Starlette:
    """Build and configure the Starlette ASGI app for Streamable HTTP MCP transport."""
    app = mcp_server.streamable_http_app(
        streamable_http_path=config.endpoint,
        host=config.host,
    )

    # Add health probe route on /mcp/health or /ready
    app.routes.append(Route("/mcp/health", mcp_health_check, methods=["GET"]))

    # Configure CORS only if explicitly allowed origins are provided
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )

    logger.info(
        "Streamable HTTP MCP app initialized [endpoint=%s, host=%s:%d, auth=%s]",
        config.endpoint,
        config.host,
        config.port,
        config.auth_mode,
    )
    return app
