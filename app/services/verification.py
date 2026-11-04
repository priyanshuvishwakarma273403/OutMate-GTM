"""Evidence verification, cross-source corroboration, and confidence assessment service."""

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.domain.models.company import CompanyProfile
from app.domain.models.evidence import (
    EvidenceRecord,
    EvidenceSourceType,
    VerificationStatus,
)
from app.domain.models.person import DecisionMaker
from app.integrations.search.base import BaseSearchClient
from app.services.source_normalization import extract_domain_from_url

logger = get_logger("services.verification")


class VerificationService:
    """Evaluates factual evidence, applies corroboration rules, and assigns confidence."""

    def __init__(
        self,
        search_client: BaseSearchClient | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self.search_client = search_client
        self.settings = settings or get_settings()

    def assess_claim_verification(
        self,
        claim: str,
        supporting_evidence: list[EvidenceRecord],
        target_domain: str | None = None,
    ) -> tuple[VerificationStatus, float, str]:
        """Evaluate evidence corroboration and determine verification status and confidence."""
        if not supporting_evidence:
            return (
                VerificationStatus.UNAVAILABLE,
                0.0,
                f"No public source evidence discovered to substantiate claim: '{claim}'",
            )

        unique_domains: set[str] = set()
        has_official_source = False
        clean_target = extract_domain_from_url(f"https://{target_domain}") if target_domain else ""

        for ev in supporting_evidence:
            ev_domain = extract_domain_from_url(ev.source_url)
            if ev_domain:
                unique_domains.add(ev_domain)
            if clean_target and (
                ev_domain == clean_target
                or ev_domain.endswith(f".{clean_target}")
                or ev.source_type == EvidenceSourceType.OFFICIAL_WEBSITE
            ):
                has_official_source = True

        # Rule 1: First-party official website evidence with or without third-party confirmation
        if has_official_source:
            if len(unique_domains) >= 2:
                return (
                    VerificationStatus.VERIFIED,
                    0.96,
                    "Corroborated by official company source and independent public citation.",
                )
            return (
                VerificationStatus.VERIFIED,
                0.90,
                "Directly verified by official first-party company source.",
            )

        # Rule 2: Multi-source independent third-party confirmation
        if len(unique_domains) >= 2:
            return (
                VerificationStatus.VERIFIED,
                0.85,
                f"Corroborated across {len(unique_domains)} independent public sources.",
            )

        # Rule 3: Single third-party source
        if len(unique_domains) == 1:
            domain = next(iter(unique_domains))
            return (
                VerificationStatus.PARTIALLY_VERIFIED,
                0.60,
                f"Sourced from single third-party provider ({domain}); awaiting independent corroboration.",
            )

        return (
            VerificationStatus.NOT_VERIFIED,
            0.30,
            "Insufficient source provenance to confirm claim.",
        )

    def verify_company_evidence(
        self,
        profile: CompanyProfile,
        evidence: list[EvidenceRecord],
    ) -> list[EvidenceRecord]:
        """Corroborate all collected evidence items against the target company domain."""
        verified_records: list[EvidenceRecord] = []
        for ev in evidence:
            claim = ev.claim or ev.snippet[:80]
            status, conf, rationale = self.assess_claim_verification(
                claim=claim,
                supporting_evidence=[ev],
                target_domain=profile.domain,
            )
            ev.verification_status = status
            ev.confidence = conf
            ev.metadata["verification_rationale"] = rationale
            verified_records.append(ev)
        return verified_records

    async def verify_person(
        self,
        person: DecisionMaker,
        company_name: str,
    ) -> DecisionMaker:
        """Contract placeholder for Phase 3 prospect verification."""
        logger.info("Executing verify_person contract for %s at %s", person.full_name, company_name)
        return person
