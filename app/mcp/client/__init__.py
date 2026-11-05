"""Python client library for consuming Outmate MCP tools."""

from app.mcp.client.client import OutmateMCPClient
from app.mcp.client.errors import (
    MCPClientError,
    MCPConnectionError,
    MCPToolExecutionError,
    MCPTransportError,
)

__all__ = [
    "MCPClientError",
    "MCPConnectionError",
    "MCPToolExecutionError",
    "MCPTransportError",
    "OutmateMCPClient",
]
