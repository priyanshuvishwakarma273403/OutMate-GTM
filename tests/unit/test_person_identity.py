"""Unit tests for person identity resolution and candidate deduplication."""

from datetime import UTC, datetime

from app.domain.models.evidence import EvidenceRecord, EvidenceSourceType
from app.domain.models.person import (
    ContactCoordinates,
    DecisionMaker,
    Department,
    EmploymentStatus,
    SeniorityLevel,
)
from app.services.person_identity import PersonIdentityResolutionService


def _create_candidate(
    full_name: str,
    title: str,
    company: str = "Acme Corp",
    department: Department = Department.ENGINEERING,
    seniority: SeniorityLevel = SeniorityLevel.VP,
    source_url: str = "https://example.com/team",
    linkedin_url: str | None = None,
) -> DecisionMaker:
    """Helper to build test DecisionMaker instances."""
    return DecisionMaker(
        full_name=full_name,
        company_name=company,
        title=title,
        department=department,
        seniority=seniority,
        employment_status=EmploymentStatus.CURRENT_EMPLOYMENT_VERIFIED,
        contact_info=ContactCoordinates(linkedin_url=linkedin_url),
        evidence=[
            EvidenceRecord(
                source_url=source_url,
                source_type=EvidenceSourceType.FIRST_PARTY_TEAM_PAGE,
                retrieved_at=datetime.now(UTC),
                content_snippet=f"{full_name} is {title} at {company}",
                confidence=0.9,
            )
        ],
    )


def test_normalize_name_strips_honorifics_and_credentials() -> None:
    """Verify honorifics (Dr., Mr., Prof.) and credentials (Ph.D, MBA, Esq.) are cleanly removed."""
    service = PersonIdentityResolutionService()

    assert service.normalize_name("Dr. Guillermo Rauch, Ph.D.") == "Guillermo Rauch"
    assert service.normalize_name("Prof. John Doe, MBA") == "John Doe"
    assert service.normalize_name("Ms. Jane Smith Esq.") == "Jane Smith"
    assert service.normalize_name("Mr. Robert C. Martin") == "Robert C. Martin"
    assert service.normalize_name("   Sir Richard Branson   ") == "Richard Branson"
    assert service.normalize_name("") == ""


def test_deduplicate_candidates_merges_compatible_roles() -> None:
    """Verify two candidate records of the same person with compatible titles are merged."""
    service = PersonIdentityResolutionService()

    c1 = _create_candidate(
        full_name="Guillermo Rauch",
        title="CEO",
        company="Vercel",
        department=Department.EXECUTIVE,
        seniority=SeniorityLevel.C_LEVEL,
        source_url="https://vercel.com/about",
    )
    c2 = _create_candidate(
        full_name="Dr. Guillermo Rauch",
        title="CEO and Founder",
        company="Vercel",
        department=Department.EXECUTIVE,
        seniority=SeniorityLevel.C_LEVEL,
        source_url="https://github.com/rauchg",
        linkedin_url="https://linkedin.com/in/rauchg",
    )

    deduped = service.deduplicate_candidates([c1, c2])

    assert len(deduped) == 1
    merged = deduped[0]
    assert merged.full_name == "Guillermo Rauch"
    # Keeps longer, more specific title
    assert merged.title == "CEO and Founder"
    # Merges evidence sources
    assert len(merged.evidence) == 2
    assert {e.source_url for e in merged.evidence} == {
        "https://vercel.com/about",
        "https://github.com/rauchg",
    }
    # Merged contact info
    assert merged.contact_info.linkedin_url == "https://linkedin.com/in/rauchg"


def test_deduplicate_candidates_disambiguates_divergent_roles() -> None:
    """Verify distinct individuals with the same name but incompatible roles are flagged as ambiguous and preserved."""
    service = PersonIdentityResolutionService()

    c1 = _create_candidate(
        full_name="Alex Smith",
        title="Staff Software Engineer",
        company="GlobalTech",
        department=Department.ENGINEERING,
        seniority=SeniorityLevel.INDIVIDUAL_CONTRIBUTOR,
        source_url="https://globaltech.com/eng",
    )
    c2 = _create_candidate(
        full_name="Alex Smith",
        title="VP Global Sales",
        company="GlobalTech",
        department=Department.SALES,
        seniority=SeniorityLevel.VP,
        source_url="https://globaltech.com/sales",
    )

    deduped = service.deduplicate_candidates([c1, c2])

    # Both must be kept, not destructively merged
    assert len(deduped) == 2
    assert deduped[0].employment_status == EmploymentStatus.IDENTITY_AMBIGUOUS
    assert deduped[1].employment_status == EmploymentStatus.IDENTITY_AMBIGUOUS
    titles = {d.title for d in deduped}
    assert titles == {"Staff Software Engineer", "VP Global Sales"}
