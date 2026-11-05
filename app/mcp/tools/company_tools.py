"""MCP tool handlers for company search, intelligence research, and profile retrieval."""

from typing import Any

from app.integrations.search.base import BaseSearchClient, SearchQuery
from app.integrations.search.factory import get_search_client
from app.mcp.auth.authorization import require_scope
from app.mcp.auth.tenant_context import validate_tenant_access
from app.mcp.errors import MCPResourceNotFoundError
from app.mcp.schemas.company import (
    GetCompanyProfileInput,
    GetCompanyProfileOutput,
    ResearchCompanyInput,
    ResearchCompanyOutput,
    SearchCompanyInput,
    SearchCompanyOutput,
)
from app.mcp.scopes import MCPScopes
from app.schemas.requests import CompanyResearchRequest
from app.services.company_research import CompanyResearchService
from app.services.report_storage import InMemoryReportRepository, get_report_repository


async def search_company_tool(
    args: dict[str, Any],
    search_client: BaseSearchClient | None = None,
) -> dict[str, Any]:
    """Search for company occurrences, public mentions, and domain references."""
    require_scope(MCPScopes.COMPANY_SEARCH)
    input_data = SearchCompanyInput.model_validate(args)

    client = search_client or get_search_client()
    query_str = f'"{input_data.query}"'
    if input_data.domain:
        query_str += f" site:{input_data.domain}"

    results = await client.search(SearchQuery(query=query_str, max_results=input_data.limit))
    output = SearchCompanyOutput(
        query=query_str,
        results=results,
        total_results=len(results),
    )
    return output.model_dump()


async def research_company_tool(
    args: dict[str, Any],
    research_service: CompanyResearchService | None = None,
) -> dict[str, Any]:
    """Execute full real company intelligence research, multi-source corroboration, and dossier synthesis."""
    require_scope(MCPScopes.COMPANY_RESEARCH)
    input_data = ResearchCompanyInput.model_validate(args)

    service = research_service or CompanyResearchService()
    report = await service.research_company(
        CompanyResearchRequest(
            company_name=input_data.company_name,
            website_domain=input_data.company_domain,
            research_depth=input_data.research_depth,
        )
    )
    output = ResearchCompanyOutput(report=report)
    return output.model_dump()


async def get_company_profile_tool(
    args: dict[str, Any],
    repo: InMemoryReportRepository | None = None,
) -> dict[str, Any]:
    """Retrieve an existing company profile from repository by research reference."""
    require_scope(MCPScopes.COMPANY_READ)
    input_data = GetCompanyProfileInput.model_validate(args)

    repository = repo or get_report_repository()
    report = repository.get_report(input_data.research_reference)
    if not report:
        raise MCPResourceNotFoundError("Company research report", input_data.research_reference)

    comp_meta = getattr(report.company, "metadata", getattr(report.company, "raw_metadata", {}))
    validate_tenant_access(comp_meta, input_data.research_reference)

    output = GetCompanyProfileOutput(
        research_id=report.research_id,
        company=report.company,
        findings=report.findings,
        identity_status=report.identity_status,
    )
    return output.model_dump()
