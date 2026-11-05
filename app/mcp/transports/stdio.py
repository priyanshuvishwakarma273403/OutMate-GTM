"""Stdio transport runner for local MCP development and MCP Inspector testing."""

import logging
import sys

from mcp.server.mcpserver import MCPServer

from app.core.logging import get_logger

logger = get_logger("mcp.transports.stdio")


async def run_stdio_server(mcp_server: MCPServer) -> None:
    """Run MCP server over standard input/output with strict stderr log isolation.

    Ensures that no ordinary log statements, banners, or prints ever leak into stdout,
    which is reserved exclusively for JSON-RPC MCP messages.
    """
    # Ensure all existing log handlers write strictly to sys.stderr
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if hasattr(handler, "stream") and handler.stream != sys.stderr:
            handler.stream = sys.stderr

    logger.info("Initializing Outmate MCP Server over stdio transport...")
    try:
        await mcp_server.run_stdio_async()
    except (KeyboardInterrupt, BrokenPipeError):
        logger.info("Stdio transport closed by client or interrupt.")
    except Exception as exc:
        logger.error("Stdio transport error: %s", exc, exc_info=True)
        raise
