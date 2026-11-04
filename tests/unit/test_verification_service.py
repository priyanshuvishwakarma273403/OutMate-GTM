"""Unit tests for evidence verification and corroboration service."""

from app.domain.models.evidence import (
    EvidenceRecord,
    EvidenceSourceType,
    VerificationStatus,
)
from app.services.verification import VerificationService


def test_assess_claim_with_official_first_party_source() -> None:
    """Verify official first-party evidence receives VERIFIED status with high confidence."""
    service = VerificationService()
    evidence = [
        EvidenceRecord(
            source_url="https://vercel.com/about",
            source_type=EvidenceSourceType.OFFICIAL_WEBSITE,
            title="About Vercel",
            snippet="Guillermo Rauch founded Vercel in 2015.",
        )
    ]

    status, confidence, rationale = service.assess_claim_verification(
        claim="Guillermo Rauch founded Vercel in 2015.",
        supporting_evidence=evidence,
        target_domain="vercel.com",
    )

    assert status == VerificationStatus.VERIFIED
    assert confidence >= 0.90
    assert "official first-party" in rationale.lower()


def test_assess_claim_with_multiple_independent_sources() -> None:
    """Verify 2+ independent third-party sources achieve VERIFIED status."""
    service = VerificationService()
    evidence = [
        EvidenceRecord(
            source_url="https://techcrunch.com/article-1",
            source_type=EvidenceSourceType.NEWS_ARTICLE,
            title="TechCrunch article",
            snippet="Vercel raised Series D.",
        ),
        EvidenceRecord(
            source_url="https://forbes.com/article-2",
            source_type=EvidenceSourceType.NEWS_ARTICLE,
            title="Forbes article",
            snippet="Vercel closed new funding round.",
        ),
    ]

    status, confidence, rationale = service.assess_claim_verification(
        claim="Vercel raised Series D funding.",
        supporting_evidence=evidence,
        target_domain="vercel.com",
    )

    assert status == VerificationStatus.VERIFIED
    assert confidence >= 0.85
    assert "2 independent public sources" in rationale


def test_assess_claim_single_third_party_source() -> None:
    """Verify single third-party source receives PARTIALLY_VERIFIED status."""
    service = VerificationService()
    evidence = [
        EvidenceRecord(
            source_url="https://randomblog.com/post",
            source_type=EvidenceSourceType.OTHER,
            title="Blog Post",
            snippet="Vercel has 500 employees.",
        )
    ]

    status, confidence, rationale = service.assess_claim_verification(
        claim="Vercel has 500 employees.",
        supporting_evidence=evidence,
        target_domain="vercel.com",
    )

    assert status == VerificationStatus.PARTIALLY_VERIFIED
    assert confidence <= 0.65
    assert "single third-party" in rationale.lower()


def test_assess_claim_with_zero_evidence() -> None:
    """Verify empty evidence list returns UNAVAILABLE status with 0.0 confidence."""
    service = VerificationService()
    status, confidence, rationale = service.assess_claim_verification(
        claim="Undisclosed confidential metric",
        supporting_evidence=[],
        target_domain="vercel.com",
    )

    assert status == VerificationStatus.UNAVAILABLE
    assert confidence == 0.0
    assert "no public source evidence" in rationale.lower()
