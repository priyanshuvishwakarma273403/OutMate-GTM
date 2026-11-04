"""Service for synthesizing and exporting executive GTM research dossiers."""

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.domain.models.company import CompanyProfile
from app.domain.models.report import GTMReport, ScoredDecisionMaker
from app.services.llm import LLMService

logger = get_logger("services.report_generation")


class ReportGenerationService:
    """Synthesizes structured company intelligence and scored decision-makers into executive dossiers."""

    def __init__(
        self,
        llm_service: LLMService | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm_service = llm_service or LLMService(settings=self.settings)

    async def generate_report(
        self,
        query: str,
        company: CompanyProfile,
        decision_makers: list[ScoredDecisionMaker],
        execution_mode: str = "standalone_agent",
    ) -> GTMReport:
        """Synthesize structured GTM dossier combining company intelligence and verified prospects."""
        logger.info(
            "Synthesizing GTM intelligence dossier for '%s' (mode: %s, prospects=%d)",
            company.name,
            execution_mode,
            len(decision_makers),
        )

        # Build executive summary and findings
        dm_summary_lines = []
        for s in decision_makers[:5]:
            dm_summary_lines.append(
                f"- {s.person.full_name}: {s.person.title} ({s.person.department.value}, Tier: {s.score.tier.value})"
            )

        exec_summary = (
            f"GTM intelligence assessment for {company.name} ({company.domain}). "
            f"{company.description or 'Operating in ' + company.industry.value}. "
            f"Identified {len(decision_makers)} key verified prospect(s) across target departments."
        )

        key_findings = [
            f"Primary industry classification: {company.industry.value}.",
            f"Discovered {len(decision_makers)} decision-maker candidate(s) from public records.",
        ]
        if dm_summary_lines:
            key_findings.append(
                "Key verified prospects: "
                + ", ".join(s.person.full_name for s in decision_makers[:3])
                + "."
            )
        if company.headquarters:
            key_findings.append(f"Headquarters verified at: {company.headquarters}.")
        if company.tech_stack:
            key_findings.append(
                f"Identified software/developer stack: {', '.join(company.tech_stack[:4])}."
            )

        # Generate outreach angles based on top candidates
        recommended_outreach_angles = []
        for s in decision_makers[:3]:
            influence = (
                s.person.assessment.decision_influence.value
                if s.person.assessment
                else "key stakeholder"
            )
            recommended_outreach_angles.append(
                f"Engage {s.person.full_name} ({s.person.title}) as {influence} focusing on {s.person.department.value} operational objectives."
            )

        return GTMReport(
            query=query,
            company=company,
            decision_makers=decision_makers,
            executive_summary=exec_summary,
            key_findings=key_findings,
            recommended_outreach_angles=recommended_outreach_angles,
            execution_mode=execution_mode,
            metadata={
                "prospects_count": len(decision_makers),
                "top_candidates": [s.person.full_name for s in decision_makers[:3]],
            },
        )

    def export_markdown(self, report: GTMReport) -> str:
        """Render a GTMReport instance into executive-ready GitHub-flavored markdown."""
        lines = [
            f"# Outmate GTM Intelligence Dossier: {report.company.name}",
            "",
            f"> **Target Domain**: [{report.company.domain}](https://{report.company.domain})  ",
            f"> **Generated**: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            f"> **Execution Mode**: `{report.execution_mode}`  ",
            "",
            "## 1. Executive Summary",
            "",
            report.executive_summary,
            "",
            "## 2. Key Company Intelligence",
            "",
            f"- **Industry**: {report.company.industry.value}",
            f"- **Headquarters**: {report.company.headquarters or 'Unknown / Unverified'}",
            f"- **Estimated Headcount**: {report.company.estimated_headcount or 'Not publicly disclosed'}",
            f"- **Founded Year**: {report.company.founded_year or 'Unknown'}",
            f"- **Funding Stage**: {report.company.funding_stage.value}",
        ]

        if report.company.tech_stack:
            lines.extend(["- **Tech Stack**:", f"  `{', '.join(report.company.tech_stack)}`"])

        lines.extend(["", "## 3. Discovered & Verified Decision Makers", ""])

        if not report.decision_makers:
            lines.append("*No public decision-makers could be corroborated for this company.*")
        else:
            lines.append("| Name | Title | Department | Seniority | Status | Relevance Tier |")
            lines.append("|---|---|---|---|---|---|")
            for s in report.decision_makers:
                lines.append(
                    f"| {s.person.full_name} | {s.person.title} | {s.person.department.value} | "
                    f"{s.person.seniority.value} | `{s.person.employment_status.value}` | **{s.score.tier.value.upper()}** ({s.score.overall_score}) |"
                )

        lines.extend(["", "## 4. Recommended Outreach Hooks", ""])
        for angle in report.recommended_outreach_angles:
            lines.append(f"- {angle}")

        lines.extend(["", "## 5. Strategic Takeaways", ""])
        for finding in report.key_findings:
            lines.append(f"- {finding}")

        lines.extend(
            ["", "---", "*Outmate GTM Intelligence Engine — Real Public Evidence Research*"]
        )
        return "\n".join(lines)
