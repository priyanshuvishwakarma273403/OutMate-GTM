"""Real company research engine coordinating identity resolution, multi-source search, and evidence compilation."""

import time
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.domain.models.company import (
    CompanyFundingStage,
    CompanyProfile,
    IndustryCategory,
)
from app.domain.models.evidence import (
    EvidenceRecord,
    VerificationStatus,
)
from app.integrations.search.base import BaseSearchClient, SearchQuery, SearchResultItem
from app.integrations.search.factory import get_search_client
from app.schemas.requests import CompanyPreviewRequest, CompanyResearchRequest
from app.schemas.responses import (
    CompanyPreviewResponse,
    CompanyResearchReport,
    SourceMetadata,
    SourceSummary,
)
from app.services.company_identity import (
    CompanyIdentityResolutionService,
    IdentityResolutionStatus,
)
from app.services.content_extraction import ContentExtractionService
from app.services.llm import LLMService
from app.services.report_storage import get_report_repository
from app.services.source_normalization import (
    classify_source_type,
    deduplicate_urls,
)
from app.services.source_retrieval import SourceRetrievalService
from app.services.verification import VerificationService

logger = get_logger("services.company_research")


class ExtractedCompanyData(BaseModel):
    """Schema for evidence-constrained LLM synthesis."""

    legal_name: str | None = Field(default=None, description="Official legal corporate name")
    description: str | None = Field(
        default=None, description="Concise description of business and core offering"
    )
    industry: str | None = Field(
        default=None,
        description="High level industry category (e.g. saas_software, cloud_infrastructure)",
    )
    headquarters: str | None = Field(
        default=None, description="City, state, or country of primary office"
    )
    estimated_headcount: int | None = Field(
        default=None, description="Reported total employee count"
    )
    founded_year: int | None = Field(default=None, description="Year company was established")
    funding_stage: str | None = Field(
        default=None, description="Funding stage, e.g. bootstrapped, seed, series_a, public"
    )
    tech_stack: list[str] = Field(
        default_factory=list, description="Explicitly mentioned developer or software tools"
    )
    key_findings: list[str] = Field(
        default_factory=list, description="Factual findings directly corroborated by the text"
    )


class CompanyResearchService:
    """Production research engine orchestrating identity resolution, public search, retrieval, and verification."""

    def __init__(
        self,
        search_client: BaseSearchClient | None = None,
        llm_service: LLMService | None = None,
        retrieval_service: SourceRetrievalService | None = None,
        extraction_service: ContentExtractionService | None = None,
        verification_service: VerificationService | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.search_client = search_client or get_search_client(self.settings)
        self.llm_service = llm_service or LLMService(settings=self.settings)
        self.retrieval_service = retrieval_service or SourceRetrievalService()
        self.extraction_service = extraction_service or ContentExtractionService()
        self.verification_service = verification_service or VerificationService(
            search_client=self.search_client, settings=self.settings
        )
        self.identity_service = CompanyIdentityResolutionService(search_client=self.search_client)
        self.repo = get_report_repository()

    def _map_industry(self, industry_str: str | None) -> IndustryCategory:
        """Map text string to IndustryCategory enum safely."""
        if not industry_str:
            return IndustryCategory.OTHER
        clean = industry_str.lower().strip()
        for cat in IndustryCategory:
            if cat.value in clean or clean in cat.value:
                return cat
        return IndustryCategory.OTHER

    def _map_funding(self, funding_str: str | None) -> CompanyFundingStage:
        """Map text string to CompanyFundingStage enum safely."""
        if not funding_str:
            return CompanyFundingStage.UNKNOWN
        clean = funding_str.lower().strip()
        for stage in CompanyFundingStage:
            if stage.value in clean or clean in stage.value:
                return stage
        return CompanyFundingStage.UNKNOWN

    async def preview_research(self, request: CompanyPreviewRequest) -> CompanyPreviewResponse:
        """Evaluate company identity and preview planned search queries without executing full scrape."""
        resolution = await self.identity_service.resolve_identity(
            company_name=request.company_name,
            user_supplied_domain=request.website_domain,
        )

        domain = resolution.resolved_domain or ""
        name = resolution.normalized_name

        queries = [
            f'"{name}" company overview products services',
            f'"{name}" headquarters headcount founded funding',
        ]
        if domain:
            queries.append(f"site:{domain} about OR company OR products")

        return CompanyPreviewResponse(
            company_name=request.company_name,
            normalized_name=name,
            supplied_domain=request.website_domain,
            resolved_domain=resolution.resolved_domain,
            official_website=resolution.official_website_url,
            resolution_status=resolution.status.value,
            confidence=resolution.confidence,
            planned_search_queries=queries,
            candidate_domains=resolution.candidate_domains,
        )

    async def research_company(self, request: CompanyResearchRequest) -> CompanyResearchReport:
        """Execute full real company research workflow and produce evidence-backed report."""
        start_time = time.perf_counter()
        created_at = datetime.now(UTC)
        research_id = str(uuid.uuid4())

        logger.info(
            "Starting company research [id=%s, target='%s', domain=%s]",
            research_id,
            request.company_name,
            request.website_domain,
        )

        limitations: list[str] = []
        warnings: list[str] = []

        # 1. Company Identity Resolution
        resolution = await self.identity_service.resolve_identity(
            company_name=request.company_name,
            user_supplied_domain=request.website_domain,
        )

        if resolution.status == IdentityResolutionStatus.AMBIGUOUS:
            warnings.append(
                resolution.ambiguity_reason or "Multiple plausible corporate identities detected."
            )
        elif resolution.status == IdentityResolutionStatus.UNRESOLVED:
            warnings.append(
                resolution.ambiguity_reason or "Official domain could not be corroborated."
            )
            limitations.append("Research conducted without confirmed first-party corporate domain.")

        target_domain = resolution.resolved_domain or (request.website_domain or "")
        normalized_name = resolution.normalized_name

        # 2. Formulate Targeted Search Queries
        queries = [
            f'"{normalized_name}" company overview products services',
            f'"{normalized_name}" headquarters headcount founded funding',
        ]
        if target_domain:
            queries.append(f"site:{target_domain} about OR company OR products")

        # 3. Retrieve Real Search Results
        all_search_results: list[SearchResultItem] = []
        raw_urls: list[str] = []

        for q_str in queries:
            try:
                items = await self.search_client.search(SearchQuery(query=q_str, max_results=5))
                all_search_results.extend(items)
                raw_urls.extend([item.url for item in items])
            except Exception as exc:
                logger.warning("Search query failed for '%s': %s", q_str, exc)
                warnings.append(f"Search provider warning on query '{q_str}': {exc}")

        # 4. Deduplicate and Prioritize URLs
        deduped_urls = deduplicate_urls(raw_urls)
        max_fetch = 8 if request.research_depth == "deep" else 5
        target_urls = deduped_urls[:max_fetch]

        # 5. Fetch Accessible Source Webpages
        source_metadata_list: list[SourceMetadata] = []
        collected_evidence: list[EvidenceRecord] = []
        extracted_contexts: list[str] = []

        sources_retrieved_count = 0
        sources_rejected_count = 0

        # Prioritize official website homepage if resolved
        if resolution.official_website_url and resolution.official_website_url not in target_urls:
            target_urls.insert(0, resolution.official_website_url)

        for url in target_urls:
            retrieved = await self.retrieval_service.fetch_source(url)
            source_type = classify_source_type(url, target_domain)

            if retrieved.is_accessible and retrieved.raw_html:
                sources_retrieved_count += 1
                extracted = self.extraction_service.extract(retrieved.raw_html, fallback_url=url)

                source_metadata_list.append(
                    SourceMetadata(
                        url=url,
                        title=extracted.title or url,
                        source_type=source_type.value,
                        retrieved=True,
                        status_code=retrieved.status_code,
                    )
                )

                # Extract useful paragraphs as evidence snippets
                if extracted.paragraphs:
                    # Take top relevant content snippets
                    content_chunk = "\n".join(extracted.paragraphs[:6])
                    extracted_contexts.append(
                        f"[SOURCE: {url} | TITLE: {extracted.title}]\n{content_chunk}"
                    )

                    for p in extracted.paragraphs[:3]:
                        if len(p) >= 40:
                            collected_evidence.append(
                                EvidenceRecord(
                                    source_url=url,
                                    source_type=source_type,
                                    title=extracted.title or None,
                                    snippet=p[:400],
                                    publication_date=extracted.published_date,
                                    captured_at=retrieved.retrieved_at,
                                    verification_status=VerificationStatus.UNVERIFIED,
                                    metadata={"char_length": len(p)},
                                )
                            )
            else:
                sources_rejected_count += 1
                source_metadata_list.append(
                    SourceMetadata(
                        url=url,
                        title="",
                        source_type=source_type.value,
                        retrieved=False,
                        status_code=retrieved.status_code,
                    )
                )

        # Fallback to search snippets if webpage retrieval was blocked or limited
        if not collected_evidence:
            logger.info("Using search engine snippets as fallback evidence records")
            for sr in all_search_results[:5]:
                if sr.snippet:
                    sr_source_type = classify_source_type(sr.url, target_domain, sr.title)
                    collected_evidence.append(
                        EvidenceRecord(
                            source_url=sr.url,
                            source_type=sr_source_type,
                            title=sr.title,
                            snippet=sr.snippet,
                            publication_date=sr.published_date,
                            captured_at=datetime.now(UTC),
                            verification_status=VerificationStatus.UNVERIFIED,
                        )
                    )
                    extracted_contexts.append(
                        f"[SOURCE: {sr.url} | TITLE: {sr.title}]\n{sr.snippet}"
                    )

        # 6. Synthesize Factual Findings with LLM (Evidence-Constrained)
        combined_evidence_text = "\n\n---\n\n".join(extracted_contexts[:8])

        system_prompt = (
            "You are an objective, evidence-bound B2B research engine. "
            "Your task is to extract corporate intelligence strictly from the provided text excerpts. "
            "RULES:\n"
            "1. ONLY use facts explicitly stated in the excerpts below.\n"
            "2. If an attribute (such as headcount, founded_year, or funding_stage) is NOT explicitly mentioned, set it to null.\n"
            "3. DO NOT extrapolate, assume, or inject external knowledge.\n"
            "4. Return clean JSON matching the schema."
        )

        user_prompt = (
            f"Target Company: {request.company_name}\n"
            f"Resolved Domain: {target_domain or 'None'}\n\n"
            f"RETRIEVED PUBLIC EVIDENCE EXCERPTS:\n{combined_evidence_text}\n\n"
            "Extract verified company profile fields and factual findings."
        )

        extracted_data: ExtractedCompanyData | None = None
        if combined_evidence_text.strip():
            try:
                llm_result = await self.llm_service.generate_structured_response(
                    prompt=user_prompt,
                    response_model=ExtractedCompanyData,
                    system_prompt=system_prompt,
                    temperature=0.0,
                    max_tokens=600,
                )
                extracted_data = llm_result.parsed
            except Exception as exc:
                logger.warning("LLM structured extraction failed: %s", exc)
                warnings.append(f"LLM synthesis error: {exc}")

        # 7. Build Canonical Company Profile
        description = (
            extracted_data.description
            if extracted_data and extracted_data.description
            else (collected_evidence[0].snippet if collected_evidence else None)
        )
        legal_name = extracted_data.legal_name if extracted_data else None
        headquarters = extracted_data.headquarters if extracted_data else None
        estimated_headcount = extracted_data.estimated_headcount if extracted_data else None
        founded_year = extracted_data.founded_year if extracted_data else None
        tech_stack = extracted_data.tech_stack if extracted_data else []

        industry = self._map_industry(extracted_data.industry if extracted_data else None)
        funding = self._map_funding(extracted_data.funding_stage if extracted_data else None)

        # 8. Record Findings and Document Missing Information
        findings = (
            extracted_data.key_findings if extracted_data and extracted_data.key_findings else []
        )
        if not findings and collected_evidence:
            findings = [ev.snippet[:150] for ev in collected_evidence[:3]]

        if not estimated_headcount:
            limitations.append("Headcount was not verified from public sources.")
        if funding == CompanyFundingStage.UNKNOWN:
            limitations.append("Funding stage was not explicitly disclosed in retrieved excerpts.")
        if not headquarters:
            limitations.append("Corporate headquarters location could not be verified.")

        company_profile = CompanyProfile(
            name=request.company_name,
            domain=target_domain or "unknown.domain",
            legal_name=legal_name,
            description=description,
            industry=industry,
            headquarters=headquarters,
            estimated_headcount=estimated_headcount,
            founded_year=founded_year,
            funding_stage=funding,
            tech_stack=tech_stack,
            evidence=[],
            last_researched_at=created_at,
            raw_metadata={"identity_resolution": resolution.model_dump()},
        )

        # 9. Verify Evidence Records
        verified_evidence = self.verification_service.verify_company_evidence(
            profile=company_profile,
            evidence=collected_evidence,
        )
        company_profile.evidence = verified_evidence

        # 10. Assemble Final Research Report
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        completed_at = datetime.now(UTC)

        overall_status = "completed"
        if not collected_evidence:
            overall_status = "failed"
            warnings.append("No public evidence could be retrieved.")
        elif resolution.status != IdentityResolutionStatus.RESOLVED:
            overall_status = "partially_completed"

        report = CompanyResearchReport(
            research_id=research_id,
            company=company_profile,
            identity_status=resolution.status.value,
            findings=findings,
            evidence=verified_evidence,
            source_summary=SourceSummary(
                sources_discovered=len(deduped_urls),
                sources_retrieved=sources_retrieved_count,
                sources_rejected=sources_rejected_count,
                sources=source_metadata_list,
            ),
            limitations=limitations,
            warnings=warnings,
            overall_status=overall_status,
            created_at=created_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        )

        # Save to repository
        self.repo.save(report)
        logger.info(
            "Company research completed in %.1fms [id=%s, sources_retrieved=%d, findings=%d]",
            duration_ms,
            research_id,
            sources_retrieved_count,
            len(findings),
        )

        return report
