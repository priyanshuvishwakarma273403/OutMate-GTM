"""Current employment verification service evaluating public evidence for active affiliation."""

import re

from app.domain.models.evidence import EvidenceRecord, EvidenceSourceType
from app.domain.models.person import EmploymentStatus
from app.services.source_normalization import extract_domain_from_url


class EmploymentVerificationService:
    """Verifies whether public evidence supports current employment vs historical affiliation."""

    HISTORICAL_INDICATORS = re.compile(
        r"\b(former|formerly|previously|served as|stepped down|departed|resigned|left\s+"
        r"|prior to|past ceo|past cto|past president|ex-|was the)\b",
        re.IGNORECASE,
    )

    CURRENT_AFFILIATION_INDICATORS = re.compile(
        r"\b(current|currently|serves as|is the|leads|founded|heading|joined as|appointed as)\b",
        re.IGNORECASE,
    )

    def verify_employment(
        self,
        person_name: str,
        company_name: str,
        company_domain: str | None,
        evidence_records: list[EvidenceRecord],
    ) -> tuple[EmploymentStatus, float, str]:
        """Assess whether candidate currently works at the target company based on evidence."""
        if not evidence_records:
            return (
                EmploymentStatus.EMPLOYMENT_NOT_VERIFIED,
                0.0,
                f"No public source evidence discovered linking '{person_name}' to '{company_name}'.",
            )

        clean_target_domain = (
            extract_domain_from_url(f"https://{company_domain}") if company_domain else ""
        )

        has_official_first_party = False
        has_announcement = False
        has_third_party = False
        historical_flags: list[str] = []
        unique_sources: set[str] = set()

        for ev in evidence_records:
            snippet_lower = ev.snippet.lower()
            ev_domain = extract_domain_from_url(ev.source_url)
            if ev_domain:
                unique_sources.add(ev_domain)

            # Check for explicit past affiliation language
            if self.HISTORICAL_INDICATORS.search(snippet_lower):
                historical_flags.append(f"Source {ev.source_url} contains historical phrasing")

            # Check source category
            if clean_target_domain and (
                ev_domain == clean_target_domain
                or ev_domain.endswith(f".{clean_target_domain}")
                or ev.source_type == EvidenceSourceType.OFFICIAL_WEBSITE
            ):
                has_official_first_party = True

            elif ev.source_type in (
                EvidenceSourceType.PRESS_RELEASE,
                EvidenceSourceType.NEWS_ARTICLE,
            ):
                has_announcement = True
            else:
                has_third_party = True

        # Rule 1: Conflicting evidence (some sources indicate current, others indicate departure)
        if historical_flags and has_official_first_party:
            return (
                EmploymentStatus.CONFLICTING_EMPLOYMENT_EVIDENCE,
                0.40,
                "Conflicting public records: official domain mentions individual, but other sources indicate historical affiliation or departure.",
            )

        # Rule 2: Explicit historical employee evidence
        if historical_flags and not has_official_first_party:
            return (
                EmploymentStatus.HISTORICAL_EMPLOYMENT,
                0.85,
                f"Evidence indicates '{person_name}' is a former employee or previously affiliated with '{company_name}'.",
            )

        # Rule 3: Official first-party leadership page evidence
        if has_official_first_party:
            if len(unique_sources) >= 2:
                return (
                    EmploymentStatus.CURRENT_EMPLOYMENT_VERIFIED,
                    0.96,
                    f"Verified current leadership on official '{clean_target_domain}' domain with external corroboration.",
                )
            return (
                EmploymentStatus.CURRENT_EMPLOYMENT_VERIFIED,
                0.92,
                f"Directly verified on official first-party website ('{clean_target_domain}').",
            )

        # Rule 4: Multi-source independent corroboration
        if len(unique_sources) >= 2:
            return (
                EmploymentStatus.CURRENT_EMPLOYMENT_VERIFIED,
                0.85,
                f"Corroborated current employment across {len(unique_sources)} independent public sources.",
            )

        # Rule 5: Single third-party announcement or mention
        if has_announcement or has_third_party:
            single_domain = next(iter(unique_sources)) if unique_sources else "third-party"
            return (
                EmploymentStatus.CURRENT_EMPLOYMENT_PARTIALLY_VERIFIED,
                0.60,
                f"Identified from single third-party publication ({single_domain}); requires official first-party corroboration.",
            )

        return (
            EmploymentStatus.EMPLOYMENT_NOT_VERIFIED,
            0.30,
            "Insufficient public evidence to verify current employment.",
        )
