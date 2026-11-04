"""Unit tests for role taxonomy classification and job-title normalization."""

from app.domain.models.person import Department, RoleCategory, SeniorityLevel
from app.services.role_classification import RoleClassificationService


def test_classify_c_level_executive() -> None:
    """Verify C-level executive titles are normalized and mapped to Executive role category."""
    service = RoleClassificationService()
    role = service.classify_title("Chief Executive Officer")

    assert role.normalized_title == "Chief Executive Officer"
    assert role.seniority == SeniorityLevel.C_LEVEL
    assert role.department == Department.EXECUTIVE
    assert role.role_category == RoleCategory.EXECUTIVE


def test_classify_cto_and_technology_roles() -> None:
    """Verify CTO and VP Engineering are classified under Technology category."""
    service = RoleClassificationService()

    cto_role = service.classify_title("cto")
    assert cto_role.normalized_title == "Chief Technology Officer"
    assert cto_role.seniority == SeniorityLevel.C_LEVEL
    assert cto_role.department == Department.ENGINEERING
    assert cto_role.role_category == RoleCategory.TECHNOLOGY

    vp_role = service.classify_title("VP of Engineering")
    assert vp_role.normalized_title == "VP of Engineering"
    assert vp_role.seniority == SeniorityLevel.VP
    assert vp_role.department == Department.ENGINEERING
    assert vp_role.role_category == RoleCategory.TECHNOLOGY


def test_classify_procurement_and_finance() -> None:
    """Verify Procurement and Finance roles are categorized accurately."""
    service = RoleClassificationService()

    procurement = service.classify_title("Director of Global Sourcing and Procurement")
    assert procurement.seniority == SeniorityLevel.DIRECTOR
    assert procurement.role_category == RoleCategory.PROCUREMENT_FINANCE

    cfo = service.classify_title("Chief Financial Officer")
    assert cfo.seniority == SeniorityLevel.C_LEVEL
    assert cfo.department == Department.FINANCE
    assert cfo.role_category == RoleCategory.PROCUREMENT_FINANCE


def test_classify_security_and_ciso() -> None:
    """Verify CISO and Security roles are classified under Security department."""
    service = RoleClassificationService()
    ciso = service.classify_title("Chief Information Security Officer")
    assert ciso.seniority == SeniorityLevel.C_LEVEL
    assert ciso.department == Department.SECURITY
    assert ciso.role_category == RoleCategory.TECHNOLOGY


def test_classify_preserves_raw_title() -> None:
    """Verify raw title string is preserved exactly as extracted."""
    service = RoleClassificationService()
    raw = "Senior Director, Platform Architecture & Cloud SRE"
    role = service.classify_title(raw)
    assert role.raw_title == raw
    assert role.seniority == SeniorityLevel.DIRECTOR
    assert role.department == Department.ENGINEERING

