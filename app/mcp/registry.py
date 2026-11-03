"""Tool registry and schema dispatcher for Outmate Model Context Protocol (MCP) server."""

from collections.abc import Awaitable, Callable
from typing import Any

from mcp.types import Tool
from pydantic import BaseModel, ValidationError

from app.core.exceptions import (
    MCPExecutionError,
    MCPToolNotFoundError,
    MCPValidationError,
)
from app.core.logging import get_logger

logger = get_logger("mcp.registry")

HandlerType = Callable[[dict[str, Any]], Awaitable[BaseModel]]


class MCPToolSpecification:
    """Detailed architectural specification and contract for an MCP tool."""

    def __init__(
        self,
        name: str,
        description: str,
        input_model: type[BaseModel],
        output_model: type[BaseModel],
        service_dependency: str,
        external_integration_dependency: str | None,
        expected_errors: list[str],
    ) -> None:
        self.name = name
        self.description = description
        self.input_model = input_model
        self.output_model = output_model
        self.service_dependency = service_dependency
        self.external_integration_dependency = external_integration_dependency
        self.expected_errors = expected_errors

    def to_mcp_tool(self) -> Tool:
        """Convert specification into official MCP SDK Tool definition."""
        schema = self.input_model.model_json_schema()
        return Tool(
            name=self.name,
            description=self.description,
            input_schema=schema,
        )


class MCPToolRegistry:
    """Central registry managing MCP tool contracts, validation, and execution routing."""

    def __init__(self) -> None:
        self._tools: dict[str, MCPToolSpecification] = {}
        self._handlers: dict[str, HandlerType] = {}

    def register(
        self,
        specification: MCPToolSpecification,
        handler: HandlerType | None = None,
    ) -> None:
        """Register a tool specification with an optional execution handler."""
        self._tools[specification.name] = specification
        if handler is not None:
            self._handlers[specification.name] = handler
        logger.debug("Registered MCP tool specification: %s", specification.name)

    def get_tool(self, name: str) -> MCPToolSpecification:
        """Retrieve specification for a named tool."""
        if name not in self._tools:
            raise MCPToolNotFoundError(
                f"Tool '{name}' is not registered in the MCP tool registry",
                details={"tool_name": name, "available_tools": list(self._tools.keys())},
            )
        return self._tools[name]

    def list_tools(self) -> list[MCPToolSpecification]:
        """Return all registered tool specifications."""
        return list(self._tools.values())

    def list_sdk_tools(self) -> list[Tool]:
        """Return MCP SDK Tool representations for protocol tool discovery."""
        return [tool.to_mcp_tool() for tool in self._tools.values()]

    async def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Validate input arguments against schema and dispatch to registered tool handler."""
        spec = self.get_tool(name)

        # Validate input schema using Pydantic
        try:
            validated_input = spec.input_model.model_validate(arguments)
        except ValidationError as val_exc:
            logger.warning("Tool %s input validation failed: %s", name, val_exc)
            raise MCPValidationError(
                f"Invalid arguments for tool '{name}'",
                details={"errors": val_exc.errors(), "provided_arguments": arguments},
            ) from val_exc

        # Handler lookup
        handler = self._handlers.get(name)
        if handler is None:
            raise MCPExecutionError(
                f"Tool '{name}' is defined in Phase 1 specification but has no handler registered. "
                "Business execution is scheduled for Phase 2.",
                details={"tool_name": name, "service_dependency": spec.service_dependency},
            )

        try:
            result = await handler(validated_input.model_dump())
            if isinstance(result, BaseModel):
                return result.model_dump(mode="json")
            return dict(result)
        except Exception as exc:
            logger.error("Unhandled error executing tool %s: %s", name, exc)
            raise MCPExecutionError(
                f"Execution failure in tool '{name}': {exc}",
                details={"tool_name": name, "error": str(exc)},
            ) from exc
