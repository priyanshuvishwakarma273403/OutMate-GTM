"""Unit tests for domain models, validation constraints, and serialization."""

import pytest
from pydantic import ValidationError

from app.domain.models import (
    CompanyFundingStage,
    CompanyProfile,
    DecisionMaker,
    Department,
    EvidenceRecord,
    EvidenceSourceType,
    GTMReport,
    IndustryCategory,
    RelevanceScore,
    RelevanceTier,
    SeniorityLevel,
    VerificationStatus,
)


def test_evidence_record_validation() -> None:
    """Verify EvidenceRecord constraints on confidence and types."""
    record = EvidenceRecord(
        source_url="https://news.ycombinator.com",
        source_type=EvidenceSourceType.NEWS_ARTICLE,
        snippet="Vercel announced a new release.",
        confidence=0.85,
    )
    assert record.confidence == 0.85
    assert record.verification_status == VerificationStatus.UNVERIFIED

    # Test confidence out of bounds
    with pytest.raises(ValidationError):
        EvidenceRecord(
            source_url="https://test.com",
            snippet="Test",
            confidence=1.5,  # Exceeds 1.0 limit
        )


def test_company_profile_instantiation(sample_company: CompanyProfile) -> None:
    """Verify CompanyProfile domain model attributes and nested evidence."""
    assert sample_company.name == "Vercel"
    assert sample_company.domain == "vercel.com"
    assert sample_company.industry == IndustryCategory.CLOUD_INFRASTRUCTURE
    assert sample_company.funding_stage == CompanyFundingStage.SERIES_C_PLUS
    assert len(sample_company.evidence) == 1
    assert sample_company.estimated_headcount == 500


def test_decision_maker_model(sample_decision_maker: DecisionMaker) -> None:
    """Verify DecisionMaker model fields, contact coordinates, and verification state."""
    assert sample_decision_maker.full_name == "Guillermo Rauch"
    assert sample_decision_maker.seniority == SeniorityLevel.C_LEVEL
    assert sample_decision_maker.department == Department.EXECUTIVE
    assert sample_decision_maker.contact_info.email == "guillermo@vercel.com"
    assert sample_decision_maker.verification_status == VerificationStatus.VERIFIED


def test_relevance_score_boundaries() -> None:
    """Verify RelevanceScore enforces 0-100 score bounds and 0-1 sub-scores."""
    valid_score = RelevanceScore(
        overall_score=88.5,
        tier=RelevanceTier.HIGH,
        seniority_fit=0.9,
        department_fit=0.85,
        evidence_confidence=0.9,
        rationale="Strong VP engineering fit.",
    )
    assert valid_score.overall_score == 88.5

    with pytest.raises(ValidationError):
        RelevanceScore(
            overall_score=105.0,  # Invalid: > 100
            tier=RelevanceTier.HIGH,
            rationale="Invalid score",
        )


def test_gtm_report_serialization(sample_gtm_report: GTMReport) -> None:
    """Verify GTMReport serialization to JSON and deserialization integrity."""
    json_str = sample_gtm_report.model_dump_json()
    assert "Vercel" in json_str
    assert "Guillermo Rauch" in json_str

    deserialized = GTMReport.model_validate_json(json_str)
    assert deserialized.company.name == sample_gtm_report.company.name
    assert len(deserialized.decision_makers) == 1
    assert deserialized.decision_makers[0].person.full_name == "Guillermo Rauch"
