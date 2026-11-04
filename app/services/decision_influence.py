"""Explainable decision-making influence and buying persona assessment service."""

from app.domain.models.person import (
    DecisionInfluenceCategory,
    DecisionMaker,
    DecisionMakerAssessment,
    Department,
    RoleCategory,
    SeniorityLevel,
)


class DecisionInfluenceAssessmentService:
    """Evaluates business influence, budget ownership, and buying roles grounded in public evidence."""

    def assess_influence(
        self,
        candidate: DecisionMaker,
        product_context: str | None = None,
        target_departments: list[Department] | None = None,
    ) -> DecisionMakerAssessment:
        """Calculate explainable purchasing role and decision-making relevance."""
        title_lower = candidate.title.lower()
        dept = candidate.department
        seniority = candidate.seniority
        evidence_ids = [ev.evidence_id for ev in candidate.evidence]

        influence = DecisionInfluenceCategory.UNKNOWN
        reasoning_parts: list[str] = []
        responsibilities: list[str] = []

        # Context relevance
        context_lower = product_context.lower() if product_context else ""

        # 1. Procurement Stakeholder
        if dept == Department.OPERATIONS and any(
            t in title_lower for t in ("procurement", "sourcing", "purchasing", "vendor")
        ):
            influence = DecisionInfluenceCategory.PROCUREMENT_STAKEHOLDER
            reasoning_parts.append(
                "Holds direct responsibility for commercial vendor review, contract negotiations, and purchasing workflows."
            )
            responsibilities.append("Vendor evaluation and procurement contracting")

        # 2. Technical Decision Maker
        elif dept in (Department.ENGINEERING, Department.SECURITY) and seniority in (
            SeniorityLevel.C_LEVEL,
            SeniorityLevel.VP,
            SeniorityLevel.HEAD,
        ):
            influence = DecisionInfluenceCategory.TECHNICAL_DECISION_MAKER
            reasoning_parts.append(
                f"Leads {dept.value} infrastructure and architecture with authority over technical software evaluation."
            )
            responsibilities.append(f"Technical architecture and {dept.value} tooling oversight")

        # 3. Economic Buyer
        elif seniority == SeniorityLevel.C_LEVEL and any(
            t in title_lower for t in ("ceo", "cfo", "chief executive", "chief financial", "president")
        ):
            influence = DecisionInfluenceCategory.ECONOMIC_BUYER
            reasoning_parts.append(
                "Executive with ultimate corporate budget authority; typically acts as economic buyer or executive sponsor."
            )
            responsibilities.append("Corporate budget allocation and executive sign-off")

        # 4. Business Decision Maker
        elif dept in (Department.PRODUCT, Department.OPERATIONS, Department.SALES) and seniority in (
            SeniorityLevel.C_LEVEL,
            SeniorityLevel.VP,
            SeniorityLevel.HEAD,
        ):
            influence = DecisionInfluenceCategory.BUSINESS_DECISION_MAKER
            reasoning_parts.append(
                f"Leads commercial and business initiatives in {dept.value} with purchasing input for departmental tools."
            )
            responsibilities.append(f"{dept.value.title()} strategy and operational management")

        # 5. Technical Evaluator / Champion
        elif dept == Department.ENGINEERING and seniority in (
            SeniorityLevel.DIRECTOR,
            SeniorityLevel.MANAGER,
            SeniorityLevel.INDIVIDUAL_CONTRIBUTOR,
        ):
            if any(t in title_lower for t in ("architect", "staff", "principal", "lead")):
                influence = DecisionInfluenceCategory.INFLUENCER
                reasoning_parts.append(
                    "Senior technical leader whose recommendations strongly influence tooling and developer platform choices."
                )
            else:
                influence = DecisionInfluenceCategory.EVALUATOR
                reasoning_parts.append(
                    "Hands-on engineering practitioner who evaluates technical fit and daily operational integration."
                )
            responsibilities.append("System implementation and technical hands-on evaluation")

        # Alignment with specific product context
        purchasing_relevance = "General organizational leadership role"
        if product_context:
            is_tech_product = any(
                term in context_lower for term in ("dev", "infra", "cloud", "api", "software", "tech")
            )
            if is_tech_product and dept == Department.ENGINEERING:
                purchasing_relevance = (
                    f"High alignment: Product '{product_context}' directly matches candidate's engineering scope."
                )
            elif "security" in context_lower and dept == Department.SECURITY:
                purchasing_relevance = (
                    f"Direct alignment: Security solution matches {candidate.title} remit."
                )
            else:
                purchasing_relevance = (
                    f"Evaluated against product scenario '{product_context}'; relevance depends on organizational purchasing policy."
                )
        else:
            reasoning_parts.append(
                "No target product scenario provided; specific buying authority for custom products remains unverified."
            )

        # Build role category
        role_category = RoleCategory.OTHER
        if seniority == SeniorityLevel.C_LEVEL:
            role_category = RoleCategory.EXECUTIVE
        elif dept in (Department.ENGINEERING, Department.SECURITY):
            role_category = RoleCategory.TECHNOLOGY
        elif dept == Department.FINANCE or "procurement" in title_lower:
            role_category = RoleCategory.PROCUREMENT_FINANCE
        elif dept in (Department.PRODUCT, Department.OPERATIONS, Department.SALES):
            role_category = RoleCategory.PRODUCT_BUSINESS

        full_reasoning = " ".join(reasoning_parts) if reasoning_parts else "Role identified from public titles."

        return DecisionMakerAssessment(
            person_id=candidate.person_id,
            role_category=role_category,
            decision_influence=influence,
            relevant_responsibilities=responsibilities,
            purchasing_relevance=purchasing_relevance,
            reasoning=full_reasoning,
            assessment_status="completed",
            supporting_evidence_ids=evidence_ids,
        )
