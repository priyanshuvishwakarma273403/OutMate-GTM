"""MCP tool handlers for decision-maker discovery, employment verification, and candidate profile retrieval."""

from typing import Any

from app.domain.models.evidence import VerificationStatus
from app.mcp.auth.authorization import require_scope
from app.mcp.auth.tenant_context import validate_tenant_access
from app.mcp.errors import MCPResourceNotFoundError
from app.mcp.schemas.people import (
    FindDecisionMakersInput,
    FindDecisionMakersOutput,
    GetPersonDetailsInput,
    GetPersonDetailsOutput,
    VerifyPersonInput,
    VerifyPersonOutput,
)
from app.mcp.scopes import MCPScopes
from app.schemas.requests import DecisionMakerResearchRequest
from app.services.employment_verification import EmploymentVerificationService
from app.services.people_research import PeopleResearchService
from app.services.report_storage import InMemoryReportRepository, get_report_repository


async def find_decision_makers_tool(
    args: dict[str, Any],
    people_service: PeopleResearchService | None = None,
) -> dict[str, Any]:
    """Execute real evidence-backed decision-maker discovery and purchasing influence assessment."""
    require_scope(MCPScopes.PEOPLE_DISCOVER)
    input_data = FindDecisionMakersInput.model_validate(args)

    service = people_service or PeopleResearchService()
    report = await service.discover_decision_makers(
        DecisionMakerResearchRequest(
            company_name=input_data.company_name,
            company_domain=input_data.company_domain,
            product_context=input_data.product_context,
            target_departments=input_data.target_departments,
            target_roles=input_data.target_roles,
            seniority_levels=input_data.seniority_levels,
            discovery_limit=input_data.discovery_limit,
            research_depth=input_data.research_depth,
        )
    )
    output = FindDecisionMakersOutput(report=report)
    return output.model_dump()


async def verify_person_tool(
    args: dict[str, Any],
    repo: InMemoryReportRepository | None = None,
    employment_service: EmploymentVerificationService | None = None,
) -> dict[str, Any]:
    """Verify a discovered person's identity and employment status against public evidence citations."""
    require_scope(MCPScopes.PEOPLE_VERIFY)
    input_data = VerifyPersonInput.model_validate(args)

    repository = repo or get_report_repository()
    person = repository.get_person(
        research_id=input_data.research_reference,
        person_id=input_data.person_reference,
    )
    if not person:
        raise MCPResourceNotFoundError("Decision maker", input_data.person_reference)

    validate_tenant_access(person.metadata, input_data.person_reference)

    verifier = employment_service or EmploymentVerificationService()
    status, conf, rationale = verifier.verify_employment(
        person_name=person.full_name,
        company_name=person.company_name,
        company_domain=person.company_domain,
        evidence_records=person.evidence,
    )

    verif_status = (
        VerificationStatus.VERIFIED if conf >= 0.8 else VerificationStatus.PARTIALLY_VERIFIED
    )

    output = VerifyPersonOutput(
        person_id=person.person_id,
        full_name=person.full_name,
        company_name=person.company_name,
        employment_status=status.value,
        confidence_score=conf,
        confidence_explanation=rationale,
        verification_status=verif_status.value,
    )
    return output.model_dump()


async def get_person_details_tool(
    args: dict[str, Any],
    repo: InMemoryReportRepository | None = None,
) -> dict[str, Any]:
    """Retrieve full profile, buying influence assessment, and evidence citations for a discovered decision-maker."""
    require_scope(MCPScopes.PEOPLE_READ)
    input_data = GetPersonDetailsInput.model_validate(args)

    repository = repo or get_report_repository()
    person = repository.get_person(
        research_id=input_data.research_reference,
        person_id=input_data.person_reference,
    )
    if not person:
        raise MCPResourceNotFoundError("Decision maker", input_data.person_reference)

    validate_tenant_access(person.metadata, input_data.person_reference)

    output = GetPersonDetailsOutput(person=person)
    return output.model_dump()
