"""CLI commands for launching Outmate GTM servers and standalone research agent."""

import argparse
import asyncio
import sys

import uvicorn

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.mcp.server import OutmateMCPServer

logger = get_logger("cli")


def run_api_server(host: str | None = None, port: int | None = None, reload: bool = False) -> None:
    """Launch the FastAPI application including mounted MCP SSE server."""
    settings = get_settings()
    target_host = host or settings.app_host
    target_port = port or settings.app_port

    logger.info("Starting Outmate GTM API server on %s:%d...", target_host, target_port)
    uvicorn.run(
        "app.main:app",
        host=target_host,
        port=target_port,
        reload=reload,
        log_level=settings.log_level.lower(),
    )


def run_mcp_stdio_server() -> None:
    """Launch the Outmate MCP server over stdio for local tool integration."""
    settings = get_settings()
    server = OutmateMCPServer(settings=settings)
    logger.info("Starting Outmate MCP server over stdio transport...")
    asyncio.run(server.run_stdio())


def main() -> None:
    """CLI argument parsing and command dispatch."""
    parser = argparse.ArgumentParser(
        prog="outmate",
        description="Outmate GTM — AI-powered Go-To-Market Intelligence Platform",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Server runner
    server_parser = subparsers.add_parser("run-server", help="Launch FastAPI and MCP SSE servers")
    server_parser.add_argument("--host", type=str, default=None, help="Host address to bind")
    server_parser.add_argument("--port", type=int, default=None, help="Port to bind")
    server_parser.add_argument("--reload", action="store_true", help="Enable code hot-reloading")

    # Local MCP stdio runner
    subparsers.add_parser(
        "run-mcp", help="Run MCP server on stdio transport for local desktop/agent use"
    )

    args = parser.parse_args()
    settings = get_settings()
    setup_logging(settings.log_level)

    if args.command == "run-server":
        run_api_server(host=args.host, port=args.port, reload=args.reload)
    elif args.command == "run-mcp":
        run_mcp_stdio_server()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
