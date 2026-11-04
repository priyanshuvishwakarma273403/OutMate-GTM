"""Unit tests for explainable decision-making influence and persona assessment."""

from app.domain.models.evidence import EvidenceRecord, EvidenceSourceType
from app.domain.models.person import (
    ContactCoordinates,
    DecisionInfluenceCategory,
    DecisionMaker,
    Department,
    EmploymentStatus,
    RoleCategory,
    SeniorityLevel,
)
from app.services.decision_influence import DecisionInfluenceAssessmentService


def _build_candidate(
    full_name: str,
    title: str,
    dept: Department,
    seniority: SeniorityLevel,
    company: str = "CloudScale",
) -> DecisionMaker:
    return DecisionMaker(
        full_name=full_name,
        company_name=company,
        title=title,
        department=dept,
        seniority=seniority,
        employment_status=EmploymentStatus.CURRENT_EMPLOYMENT_VERIFIED,
        contact_info=ContactCoordinates(),
        evidence=[
            EvidenceRecord(
                source_url=f"https://{company.lower()}.com/team",
                source_type=EvidenceSourceType.OFFICIAL_WEBSITE,
                snippet=f"{full_name} is {title} at {company}",
                confidence=0.9,
            )
        ],
    )


def test_assess_economic_buyer_c_level() -> None:
    """Verify CEO/CFO are assessed as Economic Buyers with budget allocation responsibility."""
    service = DecisionInfluenceAssessmentService()
    ceo = _build_candidate("Jane Boss", "Chief Executive Officer", Department.EXECUTIVE, SeniorityLevel.C_LEVEL)

    assessment = service.assess_influence(ceo)

    assert assessment.decision_influence == DecisionInfluenceCategory.ECONOMIC_BUYER
    assert assessment.role_category == RoleCategory.EXECUTIVE
    assert "budget" in assessment.reasoning.lower()
    assert len(assessment.supporting_evidence_ids) == 1
    assert assessment.supporting_evidence_ids[0] == ceo.evidence[0].evidence_id


def test_assess_technical_decision_maker() -> None:
    """Verify VP Engineering and Head of Security are categorized as Technical Decision Makers."""
    service = DecisionInfluenceAssessmentService()
    vp_eng = _build_candidate("Bob Tech", "VP of Engineering", Department.ENGINEERING, SeniorityLevel.VP)

    assessment = service.assess_influence(vp_eng)

    assert assessment.decision_influence == DecisionInfluenceCategory.TECHNICAL_DECISION_MAKER
    assert assessment.role_category == RoleCategory.TECHNOLOGY
    assert "engineering" in assessment.reasoning.lower()


def test_assess_procurement_stakeholder() -> None:
    """Verify sourcing and procurement roles are identified as Procurement Stakeholders."""
    service = DecisionInfluenceAssessmentService()
    proc = _build_candidate(
        "Sarah Sourcing",
        "Director of Global Procurement",
        Department.OPERATIONS,
        SeniorityLevel.DIRECTOR,
    )

    assessment = service.assess_influence(proc)

    assert assessment.decision_influence == DecisionInfluenceCategory.PROCUREMENT_STAKEHOLDER
    assert assessment.role_category == RoleCategory.PROCUREMENT_FINANCE
    assert "procurement" in assessment.reasoning.lower()


def test_assess_product_context_alignment() -> None:
    """Verify purchasing relevance reflects high alignment when candidate matches product context."""
    service = DecisionInfluenceAssessmentService()
    vp_eng = _build_candidate("Bob Tech", "VP of Engineering", Department.ENGINEERING, SeniorityLevel.VP)

    # 1. With aligned developer tool context
    assessment_aligned = service.assess_influence(
        vp_eng,
        product_context="Developer infrastructure and CI/CD cloud pipeline",
    )
    assert "High alignment" in assessment_aligned.purchasing_relevance

    # 2. Without product context
    assessment_neutral = service.assess_influence(vp_eng, product_context=None)
    assert "No target product scenario provided" in assessment_neutral.reasoning


def test_assess_evaluator_and_influencer() -> None:
    """Verify IC engineers are categorized as Evaluators or Influencers depending on title."""
    service = DecisionInfluenceAssessmentService()

    staff_eng = _build_candidate(
        "Alice Architect",
        "Staff Software Architect",
        Department.ENGINEERING,
        SeniorityLevel.INDIVIDUAL_CONTRIBUTOR,
    )
    assessment_staff = service.assess_influence(staff_eng)
    assert assessment_staff.decision_influence == DecisionInfluenceCategory.INFLUENCER

    dev = _build_candidate(
        "Charlie Dev",
        "Software Engineer",
        Department.ENGINEERING,
        SeniorityLevel.INDIVIDUAL_CONTRIBUTOR,
    )
    assessment_dev = service.assess_influence(dev)
    assert assessment_dev.decision_influence == DecisionInfluenceCategory.EVALUATOR
