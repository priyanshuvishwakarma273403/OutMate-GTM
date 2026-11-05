"""Unit tests for the reusable Python OutmateMCPClient."""

import pytest

from app.domain.models import CompanyProfile
from app.domain.models.evidence import EvidenceRecord, EvidenceSourceType
from app.mcp.client import (
    MCPToolNotFoundError,
    OutmateMCPClient,
)
from app.mcp.errors import MCPValidationError
from app.mcp.schemas.common import MCPToolResult
from app.schemas.responses import CompanyResearchReport
from app.services.report_storage import get_report_repository


@pytest.fixture
def in_process_client() -> OutmateMCPClient:
    """Fixture providing an in-process MCP client with real GTM tool registry."""
    return OutmateMCPClient(transport_mode="in_process")


async def test_client_get_server_info(in_process_client: OutmateMCPClient) -> None:
    """Verify get_server_info returns server metadata and capabilities."""
    info = await in_process_client.get_server_info()
    assert "outmate" in info["name"]
    assert "tools" in info["capabilities"]
    assert "resources" in info["capabilities"]
    assert "prompts" in info["capabilities"]


async def test_client_list_tools(in_process_client: OutmateMCPClient) -> None:
    """Verify list_tools discovers all 9 production tools."""
    tools = await in_process_client.list_tools()
    assert len(tools) in (9, 18)
    tool_names = [t.name for t in tools]
    assert "search_company" in tool_names
    assert "research_company" in tool_names
    assert "get_company_profile" in tool_names
    assert "find_decision_makers" in tool_names
    assert "verify_person" in tool_names
    assert "get_person_details" in tool_names
    assert "get_research_sources" in tool_names
    assert "get_decision_maker_sources" in tool_names
    assert "get_research_report" in tool_names


async def test_client_call_tool_not_found(in_process_client: OutmateMCPClient) -> None:
    """Verify calling an unregistered tool raises MCPToolNotFoundError."""
    with pytest.raises(MCPToolNotFoundError, match="is not registered"):
        await in_process_client.call_tool("non_existent_tool", {})


async def test_client_call_tool_validation_error(in_process_client: OutmateMCPClient) -> None:
    """Verify calling a tool with missing required arguments raises validation error."""
    with pytest.raises(MCPValidationError):
        # search_company requires 'query'
        await in_process_client.call_tool("search_company", {})


async def test_client_call_tool_success(in_process_client: OutmateMCPClient) -> None:
    """Verify successful tool execution via client."""
    # Seed repository with a test report
    repo = get_report_repository()
    report = CompanyResearchReport(
        research_id="client_test_ref_123",
        company=CompanyProfile(name="Stripe", domain="stripe.com"),
        identity_status="resolved",
        findings=["Financial infrastructure platform."],
        evidence=[
            EvidenceRecord(
                source_url="https://stripe.com",
                source_type=EvidenceSourceType.OFFICIAL_WEBSITE,
                title="Stripe Homepage",
                snippet="Financial infrastructure for the internet.",
            )
        ],
    )
    repo.save_report(report)

    # Call get_company_profile
    res = await in_process_client.call_tool(
        "get_company_profile",
        {"research_reference": "client_test_ref_123"},
    )
    assert isinstance(res, MCPToolResult)
    assert res.is_error is False
    assert res.data["research_id"] == "client_test_ref_123"
    assert res.data["company"]["name"] == "Stripe"


async def test_client_health_check(in_process_client: OutmateMCPClient) -> None:
    """Verify health_check method on in-process client."""
    is_healthy = await in_process_client.health_check()
    assert is_healthy is True
