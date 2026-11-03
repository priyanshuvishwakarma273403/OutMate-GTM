"""Pytest configuration and global fixtures for Outmate GTM."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import AppSettings
from app.domain.models import (
    CompanyFundingStage,
    CompanyProfile,
    ContactCoordinates,
    DecisionMaker,
    Department,
    EvidenceRecord,
    EvidenceSourceType,
    GTMReport,
    IndustryCategory,
    RelevanceScore,
    RelevanceTier,
    ScoredDecisionMaker,
    SeniorityLevel,
    VerificationStatus,
)
from app.main import create_app


@pytest.fixture
def test_settings() -> AppSettings:
    """Provide isolated application settings for testing."""
    return AppSettings(
        APP_NAME="Outmate GTM Test",
        APP_ENV="test",
        LOG_LEVEL="DEBUG",
        TESTING=True,
    )


@pytest.fixture
def sample_evidence() -> EvidenceRecord:
    """Fixture providing a valid EvidenceRecord instance."""
    return EvidenceRecord(
        source_url="https://vercel.com/about",
        source_type=EvidenceSourceType.OFFICIAL_WEBSITE,
        title="About Vercel Leadership",
        snippet="Guillermo Rauch is the CEO and founder of Vercel.",
        confidence=0.95,
        verification_status=VerificationStatus.VERIFIED,
    )


@pytest.fixture
def sample_company(sample_evidence: EvidenceRecord) -> CompanyProfile:
    """Fixture providing a valid CompanyProfile instance."""
    return CompanyProfile(
        name="Vercel",
        domain="vercel.com",
        legal_name="Vercel Inc.",
        description="Frontend cloud platform providing developer tools and global hosting.",
        industry=IndustryCategory.CLOUD_INFRASTRUCTURE,
        headquarters="San Francisco, CA, USA",
        estimated_headcount=500,
        founded_year=2015,
        funding_stage=CompanyFundingStage.SERIES_C_PLUS,
        tech_stack=["Next.js", "React", "Rust", "TypeScript"],
        evidence=[sample_evidence],
    )


@pytest.fixture
def sample_decision_maker(sample_evidence: EvidenceRecord) -> DecisionMaker:
    """Fixture providing a valid DecisionMaker instance."""
    return DecisionMaker(
        full_name="Guillermo Rauch",
        company_name="Vercel",
        company_domain="vercel.com",
        title="Chief Executive Officer",
        seniority=SeniorityLevel.C_LEVEL,
        department=Department.EXECUTIVE,
        location="San Francisco, CA",
        contact_info=ContactCoordinates(
            email="guillermo@vercel.com",
            twitter_handle="@rauchg",
            linkedin_url="https://linkedin.com/in/rauchg",
            github_username="rauchg",
        ),
        verification_status=VerificationStatus.VERIFIED,
        evidence=[sample_evidence],
    )


@pytest.fixture
def sample_scored_decision_maker(sample_decision_maker: DecisionMaker) -> ScoredDecisionMaker:
    """Fixture providing a valid ScoredDecisionMaker instance."""
    score = RelevanceScore(
        overall_score=95.0,
        tier=RelevanceTier.HIGH,
        seniority_fit=1.0,
        department_fit=0.9,
        evidence_confidence=0.95,
        rationale="Chief Executive Officer is the ultimate commercial and organizational decision maker.",
    )
    return ScoredDecisionMaker(person=sample_decision_maker, score=score)


@pytest.fixture
def sample_gtm_report(
    sample_company: CompanyProfile,
    sample_scored_decision_maker: ScoredDecisionMaker,
) -> GTMReport:
    """Fixture providing a valid GTMReport instance."""
    return GTMReport(
        query="Who are the decision makers in the company Vercel?",
        company=sample_company,
        decision_makers=[sample_scored_decision_maker],
        executive_summary="Vercel is a high-growth developer cloud company led by Guillermo Rauch.",
        key_findings=["Primary decision maker identified: Guillermo Rauch (CEO)."],
        recommended_outreach_angles=["Focus on developer productivity and enterprise cloud scale."],
        execution_mode="standalone_agent",
    )


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client fixture configured against the FastAPI ASGI app."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
