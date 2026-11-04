"""Integration tests for Company Research REST endpoints."""

from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient

from app.api.routes.research import get_repository, get_research_service
from app.domain.models.company import CompanyFundingStage, CompanyProfile, IndustryCategory
from app.main import create_app
from app.schemas.responses import (
    CompanyPreviewResponse,
    CompanyResearchReport,
    SourceMetadata,
    SourceSummary,
)
from app.services.company_research import CompanyResearchService
from app.services.report_storage import InMemoryReportRepository


async def test_preview_endpoint_success() -> None:
    """Verify POST /api/v1/research/company/preview returns 200 OK with query plan."""
    app = create_app()

    mock_service = AsyncMock(spec=CompanyResearchService)
    mock_service.preview_research.return_value = CompanyPreviewResponse(
        company_name="Vercel",
        normalized_name="Vercel",
        supplied_domain="vercel.com",
        resolved_domain="vercel.com",
        official_website="https://vercel.com",
        resolution_status="resolved",
        confidence=0.98,
        planned_search_queries=[
            '"Vercel" company overview products services',
            '"Vercel" headquarters headcount founded funding',
        ],
        candidate_domains=["vercel.com"],
    )

    app.dependency_overrides[get_research_service] = lambda: mock_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/research/company/preview",
            json={"company_name": "Vercel", "website_domain": "vercel.com"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] == "Vercel"
    assert data["resolution_status"] == "resolved"
    assert len(data["planned_search_queries"]) == 2


async def test_company_research_endpoint_success() -> None:
    """Verify POST /api/v1/research/company returns 200 OK and valid report."""
    app = create_app()

    mock_profile = CompanyProfile(
        name="Vercel",
        domain="vercel.com",
        legal_name="Vercel Inc.",
        description="Frontend cloud platform.",
        industry=IndustryCategory.CLOUD_INFRASTRUCTURE,
        funding_stage=CompanyFundingStage.SERIES_C_PLUS,
    )
    mock_report = CompanyResearchReport(
        research_id="test-research-uuid-1234",
        company=mock_profile,
        identity_status="resolved",
        findings=["Pioneered frontend deployment with Next.js"],
        evidence=[],
        source_summary=SourceSummary(
            sources_discovered=2,
            sources_retrieved=1,
            sources_rejected=0,
            sources=[
                SourceMetadata(
                    url="https://vercel.com/about",
                    title="About Vercel",
                    source_type="official_website",
                    retrieved=True,
                    status_code=200,
                )
            ],
        ),
        overall_status="completed",
    )

    mock_service = AsyncMock(spec=CompanyResearchService)
    mock_service.research_company.return_value = mock_report

    app.dependency_overrides[get_research_service] = lambda: mock_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/research/company",
            json={"company_name": "Vercel", "website_domain": "vercel.com"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["research_id"] == "test-research-uuid-1234"
    assert data["company"]["name"] == "Vercel"
    assert data["company"]["domain"] == "vercel.com"
    assert data["overall_status"] == "completed"


async def test_get_report_and_sources_by_id() -> None:
    """Verify GET /api/v1/research/{id} and /{id}/sources retrieve stored report."""
    app = create_app()

    test_repo = InMemoryReportRepository()
    mock_report = CompanyResearchReport(
        research_id="stored-uuid-9999",
        company=CompanyProfile(name="Stripe", domain="stripe.com"),
        identity_status="resolved",
        findings=["Payments infrastructure."],
        evidence=[],
        source_summary=SourceSummary(
            sources_discovered=1,
            sources_retrieved=1,
            sources=[
                SourceMetadata(
                    url="https://stripe.com",
                    title="Stripe",
                    source_type="official_website",
                    retrieved=True,
                    status_code=200,
                )
            ],
        ),
        overall_status="completed",
    )
    test_repo.save(mock_report)

    app.dependency_overrides[get_repository] = lambda: test_repo

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Retrieve report
        res_report = await client.get("/api/v1/research/stored-uuid-9999")
        assert res_report.status_code == 200
        assert res_report.json()["research_id"] == "stored-uuid-9999"
        assert res_report.json()["company"]["name"] == "Stripe"

        # Retrieve sources
        res_sources = await client.get("/api/v1/research/stored-uuid-9999/sources")
        assert res_sources.status_code == 200
        sources_data = res_sources.json()
        assert sources_data["sources_retrieved"] == 1
        assert sources_data["sources"][0]["url"] == "https://stripe.com"

        # Missing report 404
        res_missing = await client.get("/api/v1/research/non-existent-uuid")
        assert res_missing.status_code == 404


async def test_validation_error_empty_company_name() -> None:
    """Verify empty company name returns 422 Unprocessable Content."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/research/company", json={"company_name": ""})
        assert response.status_code == 422
