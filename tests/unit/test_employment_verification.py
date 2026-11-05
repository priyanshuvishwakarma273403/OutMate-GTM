"""Unit tests for current employment verification service."""

from app.domain.models.evidence import EvidenceRecord, EvidenceSourceType
from app.domain.models.person import EmploymentStatus
from app.services.employment_verification import EmploymentVerificationService


def test_verify_current_employment_official_website() -> None:
    """Verify first-party official website evidence achieves CURRENT_EMPLOYMENT_VERIFIED."""
    service = EmploymentVerificationService()
    evidence = [
        EvidenceRecord(
            source_url="https://vercel.com/about",
            source_type=EvidenceSourceType.OFFICIAL_WEBSITE,
            title="About Vercel Leadership",
            snippet="Guillermo Rauch is the CEO and founder of Vercel.",
        )
    ]

    status, confidence, rationale = service.verify_employment(
        person_name="Guillermo Rauch",
        company_name="Vercel",
        company_domain="vercel.com",
        evidence_records=evidence,
    )

    assert status == EmploymentStatus.CURRENT_EMPLOYMENT_VERIFIED
    assert confidence >= 0.90
    assert "official" in rationale.lower()


def test_verify_historical_employment_phrasing() -> None:
    """Verify former employee phrasing is accurately identified as HISTORICAL_EMPLOYMENT."""
    service = EmploymentVerificationService()
    evidence = [
        EvidenceRecord(
            source_url="https://techcrunch.com/article",
            source_type=EvidenceSourceType.NEWS_ARTICLE,
            title="Executive Transition",
            snippet="Jane Doe, former VP of Product at Acme Corp, has stepped down.",
        )
    ]

    status, confidence, rationale = service.verify_employment(
        person_name="Jane Doe",
        company_name="Acme Corp",
        company_domain="acme.com",
        evidence_records=evidence,
    )

    assert status == EmploymentStatus.HISTORICAL_EMPLOYMENT
    assert confidence >= 0.80
    assert "former employee" in rationale.lower()


def test_verify_conflicting_employment_evidence() -> None:
    """Verify conflicting evidence flags CONFLICTING_EMPLOYMENT_EVIDENCE status."""
    service = EmploymentVerificationService()
    evidence = [
        EvidenceRecord(
            source_url="https://acme.com/team",
            source_type=EvidenceSourceType.OFFICIAL_WEBSITE,
            snippet="John Smith serves as Chief Operating Officer.",
        ),
        EvidenceRecord(
            source_url="https://news.com/departure",
            source_type=EvidenceSourceType.NEWS_ARTICLE,
            snippet="John Smith departed Acme Corp earlier this year.",
        ),
    ]

    status, confidence, rationale = service.verify_employment(
        person_name="John Smith",
        company_name="Acme Corp",
        company_domain="acme.com",
        evidence_records=evidence,
    )

    assert status == EmploymentStatus.CONFLICTING_EMPLOYMENT_EVIDENCE
    assert "conflicting" in rationale.lower()


def test_verify_single_third_party_mention() -> None:
    """Verify single third-party source achieves CURRENT_EMPLOYMENT_PARTIALLY_VERIFIED."""
    service = EmploymentVerificationService()
    evidence = [
        EvidenceRecord(
            source_url="https://blog.dev/post",
            source_type=EvidenceSourceType.OTHER,
            snippet="Alex is an engineering manager at Vercel.",
        )
    ]

    status, confidence, rationale = service.verify_employment(
        person_name="Alex",
        company_name="Vercel",
        company_domain="vercel.com",
        evidence_records=evidence,
    )

    assert status == EmploymentStatus.CURRENT_EMPLOYMENT_PARTIALLY_VERIFIED
    assert confidence <= 0.65


def test_verify_empty_evidence() -> None:
    """Verify zero evidence yields EMPLOYMENT_NOT_VERIFIED."""
    service = EmploymentVerificationService()
    status, confidence, _ = service.verify_employment(
        person_name="Unknown",
        company_name="Vercel",
        company_domain="vercel.com",
        evidence_records=[],
    )

    assert status == EmploymentStatus.EMPLOYMENT_NOT_VERIFIED
    assert confidence == 0.0
