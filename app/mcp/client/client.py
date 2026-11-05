"""Reusable official-SDK-based Python MCP client supporting stdio and Streamable HTTP transports."""

import json
from contextlib import AsyncExitStack
from typing import Any, Literal

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import Tool

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.llm.base import ToolDefinition
from app.mcp.client.errors import (
    MCPClientError,
    MCPConnectionError,
    MCPToolExecutionError,
    MCPTransportError,
)
from app.mcp.registry import MCPToolRegistry
from app.mcp.tools import create_gtm_tool_registry

logger = get_logger("mcp.client")


class OutmateMCPClient:
    """Official MCP client for Standalone Agent Mode A and testing integrations."""

    def __init__(
        self,
        transport: Literal["in_process", "stdio", "streamable_http"] = "in_process",
        server_url: str | None = None,
        auth_token: str | None = None,
        stdio_command: str = "python",
        stdio_args: list[str] | None = None,
        stdio_env: dict[str, str] | None = None,
        registry: MCPToolRegistry | None = None,
        settings: AppSettings | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.transport_type = transport
        self.server_url = server_url or "http://127.0.0.1:8000/mcp"
        self.auth_token = auth_token
        self.stdio_command = stdio_command
        self.stdio_args = stdio_args or ["-m", "app.mcp.server"]
        self.stdio_env = stdio_env
        self.settings = settings or get_settings()
        self.timeout = timeout

        # In-process direct execution registry fallback
        self._registry = registry or create_gtm_tool_registry()

        # Session & ExitStack for managing remote or stdio streams
        self._exit_stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._server_info: dict[str, Any] = {}
        self._connected = False

    async def connect(self) -> None:
        """Establish connection and perform protocol initialization."""
        if self._connected:
            return

        if self.transport_type == "in_process":
            self._connected = True
            self._server_info = {"name": "outmate-in-process-registry", "version": "0.1.0"}
            logger.info("OutmateMCPClient connected via in-process tool registry")
            return

        self._exit_stack = AsyncExitStack()

        try:
            if self.transport_type == "stdio":
                logger.info("Connecting OutmateMCPClient via stdio subprocess (%s)...", self.stdio_command)
                server_params = StdioServerParameters(
                    command=self.stdio_command,
                    args=self.stdio_args,
                    env=self.stdio_env,
                )
                read_stream, write_stream = await self._exit_stack.enter_async_context(
                    stdio_client(server_params)
                )

            elif self.transport_type == "streamable_http":
                logger.info("Connecting OutmateMCPClient via Streamable HTTP (%s)...", self.server_url)
                headers = {}
                if self.auth_token:
                    headers["Authorization"] = f"Bearer {self.auth_token}"

                http_client = httpx.AsyncClient(headers=headers, timeout=self.timeout)
                await self._exit_stack.enter_async_context(http_client)

                read_stream, write_stream = await self._exit_stack.enter_async_context(
                    streamable_http_client(self.server_url, http_client=http_client)  # type: ignore[arg-type]
                )
            else:
                raise MCPConnectionError(f"Unsupported transport type '{self.transport_type}'")

            session = ClientSession(read_stream, write_stream)
            self._session = await self._exit_stack.enter_async_context(session)

            init_result = await self._session.initialize()
            self._server_info = {
                "name": init_result.server_info.name if hasattr(init_result, "server_info") else "mcp-server",
                "version": init_result.server_info.version if hasattr(init_result, "server_info") else "0.1.0",
                "protocol_version": getattr(init_result, "protocol_version", "2024-11-05"),
            }
            self._connected = True
            logger.info("MCP client connected to %s (%s)", self._server_info.get("name"), self.transport_type)

        except Exception as exc:
            logger.error("Failed to connect MCP client over %s: %s", self.transport_type, exc)
            if self._exit_stack:
                await self._exit_stack.aclose()
                self._exit_stack = None
            raise MCPConnectionError(f"Connection to MCP server failed: {exc}") from exc

    async def list_tools(self) -> list[Tool]:
        """Discover tools dynamically from the connected server."""
        if not self._connected:
            await self.connect()

        if self.transport_type == "in_process":
            return self._registry.list_sdk_tools()

        if not self._session:
            raise MCPTransportError("Client session is not active")

        try:
            result = await self._session.list_tools()
            return result.tools
        except Exception as exc:
            logger.error("Failed to list tools from MCP server: %s", exc)
            raise MCPTransportError(f"Failed to discover tools: {exc}") from exc

    def get_tool_definitions_for_llm(self) -> list[ToolDefinition]:
        """Convert registered MCP tool specifications into OpenAI/OpenRouter function schemas."""
        tool_definitions: list[ToolDefinition] = []
        for tool_spec in self._registry.list_tools():
            tool_definitions.append(
                ToolDefinition(
                    name=tool_spec.name,
                    description=tool_spec.description,
                    parameters=tool_spec.input_model.model_json_schema(),
                )
            )
        return tool_definitions

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool on the MCP server and return validated structured results."""
        if not self._connected:
            await self.connect()

        if self.transport_type == "in_process":
            logger.info("Invoking tool '%s' via in-process registry", tool_name)
            return await self._registry.execute(tool_name, arguments)

        if not self._session:
            raise MCPTransportError("Client session is not active")

        logger.info("Invoking remote MCP tool '%s' with arguments: %s", tool_name, list(arguments.keys()))
        try:
            result = await self._session.call_tool(tool_name, arguments)
            if result.is_error:
                error_msg = "Tool reported failure"
                if result.content and hasattr(result.content[0], "text"):
                    error_msg = result.content[0].text
                raise MCPToolExecutionError(tool_name, error_msg)

            # Prefer structured content when provided by server
            if hasattr(result, "structured_content") and result.structured_content:
                if isinstance(result.structured_content, dict):
                    return result.structured_content
                return dict(result.structured_content)

            # Parse content blocks
            if result.content:
                for block in result.content:
                    if hasattr(block, "text") and block.text:
                        text = block.text.strip()
                        if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
                            try:
                                return json.loads(text)
                            except Exception:
                                pass
                        return {"text": text}

            return {}

        except MCPToolExecutionError:
            raise
        except Exception as exc:
            logger.error("Error executing tool '%s': %s", tool_name, exc)
            raise MCPToolExecutionError(tool_name, str(exc)) from exc

    async def get_server_info(self) -> dict[str, Any]:
        """Return server identification and protocol capabilities."""
        if not self._connected:
            await self.connect()
        return self._server_info

    async def health_check(self) -> bool:
        """Verify server responsiveness."""
        try:
            if not self._connected:
                await self.connect()
            tools = await self.list_tools()
            return len(tools) > 0
        except Exception as exc:
            logger.warning("MCP client health check failed: %s", exc)
            return False

    async def close(self) -> None:
        """Gracefully terminate client session and release network resources."""
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception as exc:
                logger.debug("Error during client exit stack teardown: %s", exc)
            finally:
                self._exit_stack = None
                self._session = None
        self._connected = False
        logger.info("OutmateMCPClient connection closed")

    async def __aenter__(self) -> "OutmateMCPClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
