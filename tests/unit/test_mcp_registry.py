"""Unit tests for MCP tool registry, schema validation, and tool contracts."""

import pytest
from pydantic import BaseModel, Field

from app.core.exceptions import (
    MCPExecutionError,
    MCPToolNotFoundError,
    MCPValidationError,
)
from app.mcp import (
    MCPToolRegistry,
    MCPToolSpecification,
    create_gtm_tool_registry,
)


def test_gtm_registry_contains_all_five_tools() -> None:
    """Verify default registry is populated with exactly the 5 specified GTM tools."""
    registry = create_gtm_tool_registry()
    tools = registry.list_tools()
    tool_names = [t.name for t in tools]

    assert len(tools) == 5
    assert "search_company" in tool_names
    assert "find_decision_makers" in tool_names
    assert "get_person_details" in tool_names
    assert "verify_person" in tool_names
    assert "generate_gtm_report" in tool_names


def test_tool_specification_metadata() -> None:
    """Verify tool specification holds dependencies and error declarations."""
    registry = create_gtm_tool_registry()
    tool = registry.get_tool("search_company")

    assert tool.name == "search_company"
    assert "CompanyResearchService" in tool.service_dependency
    assert "SearchProvider" in (tool.external_integration_dependency or "")
    assert len(tool.expected_errors) >= 2


def test_sdk_tool_conversion() -> None:
    """Verify tool specifications convert to official MCP SDK Tool objects."""
    registry = create_gtm_tool_registry()
    sdk_tools = registry.list_sdk_tools()

    assert len(sdk_tools) == 5
    first_tool = sdk_tools[0]
    assert hasattr(first_tool, "name")
    assert hasattr(first_tool, "input_schema")
    assert "properties" in first_tool.input_schema


async def test_tool_execution_input_validation() -> None:
    """Verify MCPValidationError is raised when required arguments are missing."""
    registry = create_gtm_tool_registry()

    # search_company requires company_name
    with pytest.raises(MCPValidationError):
        await registry.execute("search_company", {})


async def test_unknown_tool_invocation() -> None:
    """Verify MCPToolNotFoundError is raised when invoking an unregistered tool."""
    registry = create_gtm_tool_registry()

    with pytest.raises(MCPToolNotFoundError, match="is not registered"):
        await registry.execute("non_existent_tool", {})


async def test_phase_1_tool_handler_not_implemented() -> None:
    """Verify executing a Phase 1 tool specification without registered handler raises MCPExecutionError."""
    registry = create_gtm_tool_registry()

    with pytest.raises(MCPExecutionError, match="Phase 1 specification but has no handler"):
        await registry.execute("search_company", {"company_name": "Vercel"})


async def test_custom_handler_execution() -> None:
    """Verify custom handler can be registered and successfully executed."""
    registry = MCPToolRegistry()

    class EchoInput(BaseModel):
        message: str = Field(...)

    class EchoOutput(BaseModel):
        echoed: str = Field(...)

    spec = MCPToolSpecification(
        name="echo",
        description="Echo input",
        input_model=EchoInput,
        output_model=EchoOutput,
        service_dependency="None",
        external_integration_dependency=None,
        expected_errors=[],
    )

    async def echo_handler(args: dict) -> EchoOutput:
        return EchoOutput(echoed=args["message"])

    registry.register(spec, echo_handler)

    result = await registry.execute("echo", {"message": "hello outmate"})
    assert result == {"echoed": "hello outmate"}
