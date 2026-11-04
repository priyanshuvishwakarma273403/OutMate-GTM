"""Unit tests for multi-dimensional decision-maker relevance scoring and ranking."""

import pytest

from app.domain.models.evidence import EvidenceRecord, EvidenceSourceType
from app.domain.models.person import (
    ContactCoordinates,
    DecisionMaker,
    Department,
    EmploymentStatus,
    SeniorityLevel,
)
from app.domain.models.report import RelevanceTier
from app.services.scoring import ScoringService


def _create_person(
    full_name: str,
    title: str,
    department: Department,
    seniority: SeniorityLevel,
    employment_status: EmploymentStatus = EmploymentStatus.CURRENT_EMPLOYMENT_VERIFIED,
    confidence_score: float = 0.9,
) -> DecisionMaker:
    return DecisionMaker(
        full_name=full_name,
        company_name="Acme",
        title=title,
        department=department,
        seniority=seniority,
        employment_status=employment_status,
        confidence_score=confidence_score,
        contact_info=ContactCoordinates(),
        evidence=[
            EvidenceRecord(
                source_url="https://example.com/team",
                source_type=EvidenceSourceType.OFFICIAL_WEBSITE,
                snippet=f"{full_name} is {title}",
                confidence=confidence_score,
            )
        ],
    )


@pytest.mark.asyncio
async def test_score_high_seniority_target_department() -> None:
    """Verify C-level / VP in targeted department with verified employment achieves High tier."""
    scoring = ScoringService()
    vp_eng = _create_person("Alice VP", "VP of Engineering", Department.ENGINEERING, SeniorityLevel.VP)

    score = await scoring.score_decision_maker(
        person=vp_eng,
        query_context="cloud infrastructure",
        target_departments=[Department.ENGINEERING],
        target_seniority=[SeniorityLevel.VP],
    )

    assert score.overall_score >= 80.0
    assert score.tier == RelevanceTier.HIGH
    assert score.seniority_fit == 1.0
    assert score.department_fit == 1.0
    assert score.evidence_confidence >= 0.9


@pytest.mark.asyncio
async def test_historical_employee_is_penalized() -> None:
    """Verify former employees are heavily penalized and never assigned High or Medium tier."""
    scoring = ScoringService()
    former_cto = _create_person(
        "Bob Ex-CTO",
        "Former CTO",
        Department.ENGINEERING,
        SeniorityLevel.C_LEVEL,
        employment_status=EmploymentStatus.HISTORICAL_EMPLOYMENT,
    )

    score = await scoring.score_decision_maker(
        person=former_cto,
        query_context="infrastructure",
    )

    assert score.evidence_confidence == 0.15
    assert score.tier in (RelevanceTier.LOW, RelevanceTier.IRRELEVANT)


@pytest.mark.asyncio
async def test_rank_decision_makers_sorting_order() -> None:
    """Verify rank_decision_makers orders candidates strictly descending by overall score."""
    scoring = ScoringService()

    vp = _create_person("Alice VP", "VP of Engineering", Department.ENGINEERING, SeniorityLevel.VP)
    staff = _create_person("Charlie IC", "Software Engineer", Department.ENGINEERING, SeniorityLevel.INDIVIDUAL_CONTRIBUTOR)
    former = _create_person("Dan Ex", "Former VP", Department.ENGINEERING, SeniorityLevel.VP, employment_status=EmploymentStatus.HISTORICAL_EMPLOYMENT)

    ranked = await scoring.rank_decision_makers(
        people=[staff, former, vp],
        query_context="engineering leadership",
        target_departments=[Department.ENGINEERING],
    )

    assert len(ranked) == 3
    assert ranked[0].person.full_name == "Alice VP"
    assert ranked[0].score.overall_score >= ranked[1].score.overall_score
    assert ranked[1].score.overall_score >= ranked[2].score.overall_score
