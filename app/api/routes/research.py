"""API endpoints for real company research, query preview, and source provenance."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.logging import get_logger
from app.schemas.requests import CompanyPreviewRequest, CompanyResearchRequest
from app.schemas.responses import (
    CompanyPreviewResponse,
    CompanyResearchReport,
    SourceSummary,
)
from app.services.company_research import CompanyResearchService
from app.services.report_storage import (
    InMemoryReportRepository,
    get_report_repository,
)

logger = get_logger("api.routes.research")

router = APIRouter(prefix="/api/v1/research", tags=["Company Research"])


def get_research_service() -> CompanyResearchService:
    """Dependency provider returning an instantiated CompanyResearchService."""
    return CompanyResearchService()


def get_repository() -> InMemoryReportRepository:
    """Dependency provider returning the report repository."""
    return get_report_repository()


@router.post(
    "/company",
    response_model=CompanyResearchReport,
    status_code=status.HTTP_200_OK,
    summary="Execute real company research",
    description=(
        "Conducts multi-source public research on a target company, validates entity identity, "
        "retrieves accessible webpages with SSRF protection, extracts evidence-backed findings, "
        "and returns a fully traceable research report."
    ),
)
async def research_company_endpoint(
    request: CompanyResearchRequest,
    service: CompanyResearchService = Depends(get_research_service),
) -> CompanyResearchReport:
    """Execute live corporate research pipeline."""
    logger.info("Received company research request for: '%s'", request.company_name)
    return await service.research_company(request)


@router.post(
    "/company/preview",
    response_model=CompanyPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview company research plan and identity resolution",
    description=(
        "Validates input, checks domain resolution, and outlines planned search queries "
        "without claiming research has been completed."
    ),
)
async def preview_company_endpoint(
    request: CompanyPreviewRequest,
    service: CompanyResearchService = Depends(get_research_service),
) -> CompanyPreviewResponse:
    """Evaluate company identity and preview planned queries."""
    logger.info("Received company preview request for: '%s'", request.company_name)
    return await service.preview_research(request)


@router.get(
    "/{research_id}",
    response_model=CompanyResearchReport,
    status_code=status.HTTP_200_OK,
    summary="Retrieve completed company research report",
    description="Fetches an existing research report by research ID.",
)
async def get_research_report_endpoint(
    research_id: str,
    repo: InMemoryReportRepository = Depends(get_repository),
) -> CompanyResearchReport:
    """Retrieve existing research report by ID."""
    report = repo.get(research_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research report with ID '{research_id}' was not found.",
        )
    return report


@router.get(
    "/{research_id}/sources",
    response_model=SourceSummary,
    status_code=status.HTTP_200_OK,
    summary="Retrieve sources for completed research",
    description="Retrieves the detailed source audit trail and provenance for a research result.",
)
async def get_research_sources_endpoint(
    research_id: str,
    repo: InMemoryReportRepository = Depends(get_repository),
) -> SourceSummary:
    """Retrieve source audit trail for a research run."""
    report = repo.get(research_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research report with ID '{research_id}' was not found.",
        )
    return report.source_summary

