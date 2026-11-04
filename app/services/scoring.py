"""Decision-maker relevance scoring and persona ranking service."""

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.domain.models.person import DecisionMaker, Department, EmploymentStatus, SeniorityLevel
from app.domain.models.report import RelevanceScore, RelevanceTier, ScoredDecisionMaker

logger = get_logger("services.scoring")


class ScoringService:
    """Calculates multi-dimensional relevance scores for decision-makers against GTM criteria."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or get_settings()

    def _calc_seniority_fit(
        self,
        seniority: SeniorityLevel,
        target_seniority: list[SeniorityLevel] | None = None,
    ) -> float:
        """Calculate alignment with targeted seniority tiers."""
        if target_seniority:
            if seniority in target_seniority:
                return 1.0
            # Adjacent tier credit
            if seniority in (SeniorityLevel.C_LEVEL, SeniorityLevel.VP, SeniorityLevel.HEAD):
                return 0.75
            return 0.3

        # Default general hierarchy weighting
        weights = {
            SeniorityLevel.C_LEVEL: 1.0,
            SeniorityLevel.VP: 0.90,
            SeniorityLevel.HEAD: 0.85,
            SeniorityLevel.DIRECTOR: 0.75,
            SeniorityLevel.MANAGER: 0.55,
            SeniorityLevel.INDIVIDUAL_CONTRIBUTOR: 0.35,
            SeniorityLevel.UNKNOWN: 0.25,
        }
        return weights.get(seniority, 0.4)

    def _calc_department_fit(
        self,
        department: Department,
        query_context: str,
        target_departments: list[Department] | None = None,
    ) -> float:
        """Calculate alignment with targeted functional departments or query scenario."""
        if target_departments:
            return 1.0 if department in target_departments else 0.35

        context_lower = query_context.lower()
        if not context_lower or context_lower == "general":
            # Core commercial/executive departments score well by default
            if department in (Department.EXECUTIVE, Department.ENGINEERING, Department.PRODUCT):
                return 0.90
            return 0.70

        dept_keywords = {
            Department.ENGINEERING: ("eng", "developer", "infra", "cloud", "software", "tech"),
            Department.SECURITY: ("security", "ciso", "compliance", "cyber"),
            Department.PRODUCT: ("product", "design", "ux"),
            Department.FINANCE: ("finance", "accounting", "cfo", "budget"),
            Department.SALES: ("sales", "revenue", "cro"),
            Department.MARKETING: ("marketing", "growth", "brand"),
        }

        keywords = dept_keywords.get(department, ())
        if any(kw in context_lower for kw in keywords):
            return 1.0
        if department == Department.EXECUTIVE:
            return 0.85  # Executives retain relevance across scenarios
        return 0.40

    def _calc_evidence_confidence(self, candidate: DecisionMaker) -> float:
        """Calculate evidence credibility score factoring in employment verification status."""
        base_confidence = candidate.confidence_score if candidate.confidence_score > 0 else 0.5

        if candidate.employment_status == EmploymentStatus.CURRENT_EMPLOYMENT_VERIFIED:
            return min(1.0, base_confidence * 1.1)
        if candidate.employment_status == EmploymentStatus.CURRENT_EMPLOYMENT_PARTIALLY_VERIFIED:
            return base_confidence * 0.8
        if candidate.employment_status == EmploymentStatus.HISTORICAL_EMPLOYMENT:
            return 0.15  # Former employees heavily penalized on current purchasing relevance
        if candidate.employment_status == EmploymentStatus.CONFLICTING_EMPLOYMENT_EVIDENCE:
            return 0.35
        return 0.25

    async def score_decision_maker(
        self,
        person: DecisionMaker,
        query_context: str = "",
        target_seniority: list[SeniorityLevel] | None = None,
        target_departments: list[Department] | None = None,
    ) -> RelevanceScore:
        """Calculate multi-dimensional relevance score (0-100) and explainable rationale."""
        seniority_fit = self._calc_seniority_fit(person.seniority, target_seniority)
        department_fit = self._calc_department_fit(person.department, query_context, target_departments)
        evidence_confidence = self._calc_evidence_confidence(person)

        # 35% Seniority, 35% Department, 30% Evidence confidence
        raw_score = (seniority_fit * 35.0) + (department_fit * 35.0) + (evidence_confidence * 30.0)
        overall_score = round(raw_score, 1)

        # Assign Relevance Tier
        if overall_score >= 75.0 and person.employment_status != EmploymentStatus.HISTORICAL_EMPLOYMENT:
            tier = RelevanceTier.HIGH
        elif overall_score >= 50.0 and person.employment_status != EmploymentStatus.HISTORICAL_EMPLOYMENT:
            tier = RelevanceTier.MEDIUM
        elif overall_score >= 25.0:
            tier = RelevanceTier.LOW
        else:
            tier = RelevanceTier.IRRELEVANT

        rationale = (
            f"Seniority fit: {seniority_fit:.2f} ({person.seniority.value}), "
            f"Department fit: {department_fit:.2f} ({person.department.value}), "
            f"Evidence confidence: {evidence_confidence:.2f} (Status: {person.employment_status.value})."
        )

        return RelevanceScore(
            overall_score=overall_score,
            tier=tier,
            seniority_fit=round(seniority_fit, 2),
            department_fit=round(department_fit, 2),
            evidence_confidence=round(evidence_confidence, 2),
            rationale=rationale,
        )

    async def rank_decision_makers(
        self,
        people: list[DecisionMaker],
        query_context: str = "",
        target_seniority: list[SeniorityLevel] | None = None,
        target_departments: list[Department] | None = None,
    ) -> list[ScoredDecisionMaker]:
        """Score each candidate and return sorted in descending order of buying relevance."""
        scored_candidates: list[ScoredDecisionMaker] = []
        for person in people:
            score = await self.score_decision_maker(
                person=person,
                query_context=query_context,
                target_seniority=target_seniority,
                target_departments=target_departments,
            )
            scored_candidates.append(ScoredDecisionMaker(person=person, score=score))

        # Sort descending by overall_score
        scored_candidates.sort(key=lambda s: s.score.overall_score, reverse=True)
        return scored_candidates
