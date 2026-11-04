"""Company identity resolution service to identify canonical corporate domains and detect ambiguity."""

import re
from enum import StrEnum
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.integrations.search.base import BaseSearchClient, SearchQuery, SearchResultItem
from app.services.source_normalization import extract_domain_from_url

logger = get_logger("services.company_identity")


class IdentityResolutionStatus(StrEnum):
    """Status reflecting confidence and clarity of company identity resolution."""

    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class CompanyIdentityResolution(BaseModel):
    """Outcome of corporate entity and official domain resolution."""

    company_name: str = Field(..., description="Target corporate name")
    normalized_name: str = Field(..., description="Cleaned company name without corporate suffixes")
    resolved_domain: str | None = Field(default=None, description="Identified official domain")
    official_website_url: str | None = Field(
        default=None, description="Resolved homepage website URL"
    )
    status: IdentityResolutionStatus = Field(
        default=IdentityResolutionStatus.UNRESOLVED,
        description="Resolution status (resolved, ambiguous, unresolved)",
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence in the resolved identity"
    )
    candidate_domains: list[str] = Field(
        default_factory=list, description="Alternative candidate domains discovered"
    )
    ambiguity_reason: str | None = Field(
        default=None, description="Explanation if identity is ambiguous or unresolved"
    )


class CompanyIdentityResolutionService:
    """Discovers canonical corporate domains and prevents confusion between similarly named entities."""

    # Common generic aggregators and social platforms to skip when resolving official homepage
    AGGREGATOR_DOMAINS = {
        "wikipedia.org",
        "linkedin.com",
        "twitter.com",
        "x.com",
        "facebook.com",
        "instagram.com",
        "youtube.com",
        "crunchbase.com",
        "bloomberg.com",
        "pitchbook.com",
        "zoominfo.com",
        "g2.com",
        "trustradius.com",
        "capterra.com",
        "leadiq.com",
        "github.com",
    }

    LEGAL_SUFFIX_REGEX = re.compile(
        r"\b(inc\.?|llc\.?|corp\.?|corporation|ltd\.?|limited|gmbh|co\.?|s\.a\.?|pvt\.?|holding|holdings)\b",
        re.IGNORECASE,
    )

    def __init__(self, search_client: BaseSearchClient) -> None:
        self.search_client = search_client

    def normalize_company_name(self, raw_name: str) -> str:
        """Strip legal suffixes and extraneous punctuation for robust entity search."""
        if not raw_name:
            return ""
        cleaned = self.LEGAL_SUFFIX_REGEX.sub("", raw_name)
        cleaned = re.sub(r"[,;]+", " ", cleaned)
        return re.sub(r"\s+", " ", cleaned).strip()

    def clean_domain(self, raw_domain: str | None) -> str | None:
        """Normalize user-provided domain string into canonical domain format."""
        if not raw_domain or not raw_domain.strip():
            return None
        domain = raw_domain.strip().lower()
        if not domain.startswith("http://") and not domain.startswith("https://"):
            domain = f"https://{domain}"
        parsed = urlparse(domain)
        netloc = parsed.netloc or parsed.path
        if netloc.startswith("www."):
            netloc = netloc[4:]
        netloc = netloc.split("/")[0].split(":")[0]
        return netloc if "." in netloc else None

    async def resolve_identity(
        self,
        company_name: str,
        user_supplied_domain: str | None = None,
    ) -> CompanyIdentityResolution:
        """Identify official corporate domain and website, flagging ambiguous entities."""
        normalized_name = self.normalize_company_name(company_name)
        clean_user_domain = self.clean_domain(user_supplied_domain)

        logger.info(
            "Resolving company identity for '%s' (normalized: '%s', user_domain: %s)",
            company_name,
            normalized_name,
            clean_user_domain,
        )

        # Case 1: User explicitly provided a valid domain
        if clean_user_domain:
            return CompanyIdentityResolution(
                company_name=company_name,
                normalized_name=normalized_name,
                resolved_domain=clean_user_domain,
                official_website_url=f"https://{clean_user_domain}",
                status=IdentityResolutionStatus.RESOLVED,
                confidence=0.98,
                candidate_domains=[clean_user_domain],
                ambiguity_reason=None,
            )

        # Case 2: Discover domain via real web search query
        query = SearchQuery(
            query=f"{normalized_name} official website company",
            max_results=8,
        )

        results: list[SearchResultItem] = await self.search_client.search(query)
        if not results:
            logger.warning(
                "No search results returned for company identity lookup '%s'", company_name
            )
            return CompanyIdentityResolution(
                company_name=company_name,
                normalized_name=normalized_name,
                status=IdentityResolutionStatus.UNRESOLVED,
                confidence=0.0,
                ambiguity_reason=f"No search results found to corroborate domain for '{company_name}'",
            )

        # Extract non-aggregator candidate domains
        candidates: list[str] = []
        name_token = re.sub(r"[^a-z0-9]", "", normalized_name.lower())

        for item in results:
            domain = extract_domain_from_url(item.url)
            if not domain or domain in self.AGGREGATOR_DOMAINS:
                continue
            if any(domain.endswith(f".{agg}") for agg in self.AGGREGATOR_DOMAINS):
                continue
            if domain not in candidates:
                candidates.append(domain)

        if not candidates:
            logger.warning("Only aggregator or directory links discovered for '%s'", company_name)
            return CompanyIdentityResolution(
                company_name=company_name,
                normalized_name=normalized_name,
                status=IdentityResolutionStatus.UNRESOLVED,
                confidence=0.2,
                ambiguity_reason="Only third-party directories or news sources discovered; official domain unverified.",
            )

        # Check for direct domain match against normalized company name token
        primary_candidate = candidates[0]
        root_token = primary_candidate.split(".")[0]

        # Check if the primary domain name token aligns closely with the company name
        is_token_match = (
            root_token in name_token
            or name_token in root_token
            or name_token.startswith(root_token)
            or root_token.startswith(name_token)
        )

        if is_token_match:
            # Check if there are other strong conflicting candidates (e.g., Apex.com vs ApexHosting.com)
            conflicting_candidates = [
                c
                for c in candidates[1:3]
                if name_token in c.split(".")[0] and c != primary_candidate
            ]

            if conflicting_candidates:
                logger.info(
                    "Detected multiple similarly named candidates for '%s': %s",
                    company_name,
                    [primary_candidate] + conflicting_candidates,
                )
                return CompanyIdentityResolution(
                    company_name=company_name,
                    normalized_name=normalized_name,
                    resolved_domain=primary_candidate,
                    official_website_url=f"https://{primary_candidate}",
                    status=IdentityResolutionStatus.AMBIGUOUS,
                    confidence=0.70,
                    candidate_domains=[primary_candidate] + conflicting_candidates,
                    ambiguity_reason=(
                        f"Multiple distinct corporate domains found for '{company_name}'. "
                        f"Selected '{primary_candidate}' as primary, but alternatives exist: {conflicting_candidates}. "
                        "Specify website_domain to eliminate ambiguity."
                    ),
                )

            return CompanyIdentityResolution(
                company_name=company_name,
                normalized_name=normalized_name,
                resolved_domain=primary_candidate,
                official_website_url=f"https://{primary_candidate}",
                status=IdentityResolutionStatus.RESOLVED,
                confidence=0.92,
                candidate_domains=candidates[:3],
                ambiguity_reason=None,
            )

        # If top candidate doesn't match name token, check second candidate
        for secondary in candidates[1:3]:
            sec_root = secondary.split(".")[0]
            if name_token in sec_root or sec_root in name_token:
                return CompanyIdentityResolution(
                    company_name=company_name,
                    normalized_name=normalized_name,
                    resolved_domain=secondary,
                    official_website_url=f"https://{secondary}",
                    status=IdentityResolutionStatus.AMBIGUOUS,
                    confidence=0.65,
                    candidate_domains=candidates[:3],
                    ambiguity_reason=(
                        f"Top search result was '{primary_candidate}', but '{secondary}' matches name token '{name_token}'. "
                        "Set explicit website_domain for complete resolution."
                    ),
                )

        return CompanyIdentityResolution(
            company_name=company_name,
            normalized_name=normalized_name,
            status=IdentityResolutionStatus.UNRESOLVED,
            confidence=0.3,
            candidate_domains=candidates[:3],
            ambiguity_reason=(
                f"Candidate domains {candidates[:3]} do not match name '{normalized_name}'. "
                "Specify official website_domain to resolve."
            ),
        )
