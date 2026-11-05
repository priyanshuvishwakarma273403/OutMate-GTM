"""MCP tool handlers for evidence source audit trails and completed research dossiers."""

from typing import Any

from app.mcp.auth.authorization import require_scope
from app.mcp.auth.tenant_context import validate_tenant_access
from app.mcp.errors import MCPResourceNotFoundError
from app.mcp.schemas.reports import (
    GetDecisionMakerSourcesInput,
    GetDecisionMakerSourcesOutput,
    GetResearchReportInput,
    GetResearchReportOutput,
    GetResearchSourcesInput,
    GetResearchSourcesOutput,
)
from app.mcp.scopes import MCPScopes
from app.services.report_storage import InMemoryReportRepository, get_report_repository


async def get_research_sources_tool(
    args: dict[str, Any],
    repo: InMemoryReportRepository | None = None,
) -> dict[str, Any]:
    """Retrieve public source evidence citations backing a completed company research run."""
    require_scope(MCPScopes.SOURCES_READ)
    input_data = GetResearchSourcesInput.model_validate(args)

    repository = repo or get_report_repository()
    report = repository.get_report(input_data.research_reference)
    if not report:
        raise MCPResourceNotFoundError("Company research report", input_data.research_reference)

    comp_meta = getattr(report.company, "metadata", getattr(report.company, "raw_metadata", {}))
    validate_tenant_access(comp_meta, input_data.research_reference)

    output = GetResearchSourcesOutput(
        research_reference=input_data.research_reference,
        total_sources=len(report.evidence),
        sources=report.evidence,
    )
    return output.model_dump()


async def get_decision_maker_sources_tool(
    args: dict[str, Any],
    repo: InMemoryReportRepository | None = None,
) -> dict[str, Any]:
    """Retrieve public evidence citations backing discovered decision-makers or a specific person."""
    require_scope(MCPScopes.SOURCES_READ)
    input_data = GetDecisionMakerSourcesInput.model_validate(args)

    repository = repo or get_report_repository()
    report = repository.get_decision_maker_report(input_data.research_reference)
    if not report:
        raise MCPResourceNotFoundError("Decision maker report", input_data.research_reference)

    if input_data.person_reference:
        person = repository.get_person(
            research_id=input_data.research_reference,
            person_id=input_data.person_reference,
        )
        if not person:
            raise MCPResourceNotFoundError("Decision maker", input_data.person_reference)
        validate_tenant_access(person.metadata, input_data.person_reference)
        sources = person.evidence
    else:
        sources = report.evidence

    output = GetDecisionMakerSourcesOutput(
        research_reference=input_data.research_reference,
        person_reference=input_data.person_reference,
        total_sources=len(sources),
        sources=sources,
    )
    return output.model_dump()


async def get_research_report_tool(
    args: dict[str, Any],
    repo: InMemoryReportRepository | None = None,
) -> dict[str, Any]:
    """Retrieve a completed company or decision-maker research report by ID."""
    require_scope(MCPScopes.COMPANY_READ)
    input_data = GetResearchReportInput.model_validate(args)

    repository = repo or get_report_repository()

    # Check company research reports first
    company_report = repository.get_report(input_data.research_reference)
    if company_report:
        comp_meta = getattr(
            company_report.company, "metadata", getattr(company_report.company, "raw_metadata", {})
        )
        validate_tenant_access(comp_meta, input_data.research_reference)
        return GetResearchReportOutput(
            research_id=company_report.research_id,
            report_type="company",
            data=company_report.model_dump(),
        ).model_dump()

    # Check decision-maker research reports second
    dm_report = repository.get_decision_maker_report(input_data.research_reference)
    if dm_report:
        return GetResearchReportOutput(
            research_id=dm_report.research_id,
            report_type="decision_maker",
            data=dm_report.model_dump(),
        ).model_dump()

    raise MCPResourceNotFoundError("Research report", input_data.research_reference)
