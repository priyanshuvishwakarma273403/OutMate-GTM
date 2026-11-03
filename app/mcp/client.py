"""MCP client abstraction enabling Mode A (Standalone Agent) to consume MCP tools."""

from typing import Any

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.llm.base import ToolDefinition
from app.mcp.registry import MCPToolRegistry
from app.mcp.tools import create_gtm_tool_registry

logger = get_logger("mcp.client")


class OutmateMCPClient:
    """Client interface used by the standalone agent to discover and invoke MCP tools.

    Supports both high-performance in-process direct registry execution and
    remote MCP transport.
    """

    def __init__(
        self,
        registry: MCPToolRegistry | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.registry = registry or create_gtm_tool_registry()

    def get_tool_definitions_for_llm(self) -> list[ToolDefinition]:
        """Convert registered MCP tool specifications into OpenAI/OpenRouter function schemas."""
        tool_definitions: list[ToolDefinition] = []
        for tool_spec in self.registry.list_tools():
            tool_definitions.append(
                ToolDefinition(
                    name=tool_spec.name,
                    description=tool_spec.description,
                    parameters=tool_spec.input_model.model_json_schema(),
                )
            )
        return tool_definitions

    async def invoke_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke an MCP tool by name with arguments and return structured results."""
        logger.info("Agent invoking MCP tool '%s'", tool_name)
        return await self.registry.execute(tool_name, arguments)
