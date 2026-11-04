"""Role taxonomy matching and job-title normalization service."""

import re
from typing import NamedTuple

from app.domain.models.person import Department, RoleCategory, SeniorityLevel


class NormalizedRole(NamedTuple):
    """Normalized role classification tuple."""

    raw_title: str
    normalized_title: str
    seniority: SeniorityLevel
    department: Department
    role_category: RoleCategory


class RoleClassificationService:
    """Classifies raw job titles into standardized seniority, departments, and taxonomy categories."""

    # Seniority Regex Patterns
    SENIORITY_PATTERNS = [
        (
            re.compile(
                r"\b(chief executive officer|ceo|chief technology officer|cto|chief operating officer|coo|"
                r"chief financial officer|cfo|chief product officer|cpo|chief information officer|cio|"
                r"chief information security officer|ciso|chief revenue officer|cro|chief marketing officer|cmo|"
                r"chief strategy officer|cso|president|managing director|co-founder|founder)\b",
                re.IGNORECASE,
            ),
            SeniorityLevel.C_LEVEL,
        ),
        (
            re.compile(
                r"\b(executive vice president|senior vice president|vice president|evp|svp|vp)\b",
                re.IGNORECASE,
            ),
            SeniorityLevel.VP,
        ),
        (
            re.compile(r"\b(head of|head)\b", re.IGNORECASE),
            SeniorityLevel.HEAD,
        ),
        (
            re.compile(r"\b(director|sr\.? director|senior director)\b", re.IGNORECASE),
            SeniorityLevel.DIRECTOR,
        ),
        (
            re.compile(r"\b(manager|lead|team lead|engineering lead)\b", re.IGNORECASE),
            SeniorityLevel.MANAGER,
        ),
        (
            re.compile(
                r"\b(staff engineer|principal engineer|architect|senior engineer|software engineer|"
                r"account executive|analyst|developer|specialist)\b",
                re.IGNORECASE,
            ),
            SeniorityLevel.INDIVIDUAL_CONTRIBUTOR,
        ),
    ]

    # Department Regex Patterns
    DEPARTMENT_PATTERNS = [
        (
            re.compile(
                r"\b(engineering|infrastructure|platform|software|technology|architect|devops|sre|systems)\b",
                re.IGNORECASE,
            ),
            Department.ENGINEERING,
            RoleCategory.TECHNOLOGY,
        ),
        (
            re.compile(
                r"\b(security|ciso|infosec|cybersecurity|compliance|risk)\b",
                re.IGNORECASE,
            ),
            Department.SECURITY,
            RoleCategory.TECHNOLOGY,
        ),
        (
            re.compile(
                r"\b(product|product management|cpo|head of product|design|ux)\b",
                re.IGNORECASE,
            ),
            Department.PRODUCT,
            RoleCategory.PRODUCT_BUSINESS,
        ),
        (
            re.compile(
                r"\b(finance|accounting|cfo|treasury|controller|investor relations)\b",
                re.IGNORECASE,
            ),
            Department.FINANCE,
            RoleCategory.PROCUREMENT_FINANCE,
        ),
        (
            re.compile(
                r"\b(procurement|sourcing|purchasing|vendor management)\b",
                re.IGNORECASE,
            ),
            Department.OPERATIONS,
            RoleCategory.PROCUREMENT_FINANCE,
        ),
        (
            re.compile(
                r"\b(sales|revenue|cro|business development|account executive|partnerships)\b",
                re.IGNORECASE,
            ),
            Department.SALES,
            RoleCategory.PRODUCT_BUSINESS,
        ),
        (
            re.compile(
                r"\b(marketing|cmo|growth|brand|communications|pr)\b",
                re.IGNORECASE,
            ),
            Department.MARKETING,
            RoleCategory.PRODUCT_BUSINESS,
        ),
        (
            re.compile(
                r"\b(operations|coo|business operations|strategy)\b",
                re.IGNORECASE,
            ),
            Department.OPERATIONS,
            RoleCategory.PRODUCT_BUSINESS,
        ),
        (
            re.compile(
                r"\b(human resources|people|chro|talent|recruiting|people operations)\b",
                re.IGNORECASE,
            ),
            Department.HUMAN_RESOURCES,
            RoleCategory.OTHER,
        ),
        (
            re.compile(
                r"\b(legal|counsel|general counsel|compliance officer)\b",
                re.IGNORECASE,
            ),
            Department.LEGAL,
            RoleCategory.OTHER,
        ),
        (
            re.compile(
                r"\b(ceo|chief executive officer|president|founder|co-founder)\b",
                re.IGNORECASE,
            ),
            Department.EXECUTIVE,
            RoleCategory.EXECUTIVE,
        ),
    ]

    # Standard Title Normalization Map
    TITLE_NORMALIZATION_MAP = {
        "ceo": "Chief Executive Officer",
        "chief executive officer": "Chief Executive Officer",
        "cto": "Chief Technology Officer",
        "chief technology officer": "Chief Technology Officer",
        "coo": "Chief Operating Officer",
        "chief operating officer": "Chief Operating Officer",
        "cfo": "Chief Financial Officer",
        "chief financial officer": "Chief Financial Officer",
        "cpo": "Chief Product Officer",
        "chief product officer": "Chief Product Officer",
        "ciso": "Chief Information Security Officer",
        "chief information security officer": "Chief Information Security Officer",
        "cro": "Chief Revenue Officer",
        "chief revenue officer": "Chief Revenue Officer",
        "cmo": "Chief Marketing Officer",
        "chief marketing officer": "Chief Marketing Officer",
        "cio": "Chief Information Officer",
        "chief information officer": "Chief Information Officer",
        "founder": "Founder",
        "co-founder": "Co-Founder",
        "president": "President",
        "vp engineering": "VP of Engineering",
        "vp of engineering": "VP of Engineering",
        "vp product": "VP of Product",
        "vp of product": "VP of Product",
        "head of engineering": "Head of Engineering",
        "head of product": "Head of Product",
        "head of infrastructure": "Head of Infrastructure",
        "head of security": "Head of Security",
        "director of engineering": "Director of Engineering",
        "director of product": "Director of Product",
    }

    def classify_title(self, raw_title: str) -> NormalizedRole:
        """Classify a raw title into standardized title, seniority, department, and role category."""
        if not raw_title or not raw_title.strip():
            return NormalizedRole(
                raw_title="",
                normalized_title="Professional",
                seniority=SeniorityLevel.UNKNOWN,
                department=Department.OTHER,
                role_category=RoleCategory.OTHER,
            )

        title_clean = raw_title.strip()
        title_lower = title_clean.lower()

        # 1. Determine Seniority
        seniority = SeniorityLevel.UNKNOWN
        for pattern, level in self.SENIORITY_PATTERNS:
            if pattern.search(title_lower):
                seniority = level
                break

        # 2. Determine Department & Role Category
        department = Department.OTHER
        role_category = RoleCategory.OTHER

        for pattern, dept, cat in self.DEPARTMENT_PATTERNS:
            if pattern.search(title_lower):
                department = dept
                role_category = cat
                break

        # If C-Level but not specifically mapped, treat as Executive
        if seniority == SeniorityLevel.C_LEVEL and department == Department.OTHER:
            department = Department.EXECUTIVE
            role_category = RoleCategory.EXECUTIVE

        # 3. Normalized Title String
        normalized_title = self.TITLE_NORMALIZATION_MAP.get(title_lower)
        if not normalized_title:
            # Title case fallback
            normalized_title = title_clean.title()

        return NormalizedRole(
            raw_title=title_clean,
            normalized_title=normalized_title,
            seniority=seniority,
            department=department,
            role_category=role_category,
        )
