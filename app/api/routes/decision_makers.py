"""API endpoints for real decision-maker discovery, verification, and role assessment."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.logging import get_logger
from app.domain.models.evidence import EvidenceRecord
from app.domain.models.person import DecisionMaker
from app.schemas.requests import (
    DecisionMakerPreviewRequest,
    DecisionMakerResearchRequest,
)
from app.schemas.responses import (
    DecisionMakerPreviewResponse,
    DecisionMakerReport,
)
from app.services.people_research import PeopleResearchService
from app.services.report_storage import (
    InMemoryReportRepository,
    get_report_repository,
)

logger = get_logger("api.routes.decision_makers")

router = APIRouter(prefix="/api/v1/research/decision-makers", tags=["Decision Makers"])


def get_people_service() -> PeopleResearchService:
    """Dependency provider returning instantiated PeopleResearchService."""
    return PeopleResearchService()


def get_repository() -> InMemoryReportRepository:
    """Dependency provider returning the report repository."""
    return get_report_repository()


@router.post(
    "",
    response_model=DecisionMakerReport,
    status_code=status.HTTP_200_OK,
    summary="Discover and verify business decision-makers",
    description=(
        "Executes evidence-backed decision-maker discovery for a target company, "
        "verifies current employment, classifies organizational role and seniority, "
        "and assesses purchasing influence grounded in public citations."
    ),
)
async def discover_decision_makers_endpoint(
    request: DecisionMakerResearchRequest,
    service: PeopleResearchService = Depends(get_people_service),
) -> DecisionMakerReport:
    """Execute live decision-maker discovery pipeline."""
    logger.info("Received decision-maker discovery request for: '%s'", request.company_name)
    return await service.discover_decision_makers(request)


@router.post(
    "/preview",
    response_model=DecisionMakerPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview decision-maker discovery plan",
    description=(
        "Evaluates company domain and outlines planned search queries and target personas "
        "without claiming any candidates have been discovered."
    ),
)
async def preview_decision_makers_endpoint(
    request: DecisionMakerPreviewRequest,
    service: PeopleResearchService = Depends(get_people_service),
) -> DecisionMakerPreviewResponse:
    """Preview discovery search strategy."""
    logger.info("Received decision-maker preview request for: '%s'", request.company_name)
    return await service.preview_discovery(request)


@router.get(
    "/{research_id}",
    response_model=DecisionMakerReport,
    status_code=status.HTTP_200_OK,
    summary="Retrieve completed decision-maker report",
    description="Fetches an existing decision-maker discovery report by research ID.",
)
async def get_decision_maker_report_endpoint(
    research_id: str,
    repo: InMemoryReportRepository = Depends(get_repository),
) -> DecisionMakerReport:
    """Retrieve existing decision-maker report by ID."""
    report = repo.get_decision_maker_report(research_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision-maker research report with ID '{research_id}' was not found.",
        )
    return report


@router.get(
    "/{research_id}/people/{person_id}",
    response_model=DecisionMaker,
    status_code=status.HTTP_200_OK,
    summary="Retrieve candidate details and evidence",
    description="Fetches an individual decision-maker's verified profile and supporting evidence.",
)
async def get_person_details_endpoint(
    research_id: str,
    person_id: str,
    repo: InMemoryReportRepository = Depends(get_repository),
) -> DecisionMaker:
    """Retrieve verified person details within a research report."""
    person = repo.get_person(research_id=research_id, person_id=person_id)
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Person '{person_id}' was not found in research report '{research_id}'.",
        )
    return person


@router.get(
    "/{research_id}/sources",
    response_model=list[EvidenceRecord],
    status_code=status.HTTP_200_OK,
    summary="Retrieve decision-maker source evidence",
    description="Retrieves the public evidence citations backing a decision-maker research report.",
)
async def get_decision_maker_sources_endpoint(
    research_id: str,
    repo: InMemoryReportRepository = Depends(get_repository),
) -> list[EvidenceRecord]:
    """Retrieve supporting evidence records for a decision-maker research run."""
    report = repo.get_decision_maker_report(research_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision-maker research report with ID '{research_id}' was not found.",
        )
    return report.evidence

