"""Production Decision-Maker Discovery and Verification Engine."""

import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.domain.models.evidence import (
    EvidenceRecord,
    generate_evidence_id,
)
from app.domain.models.person import (
    ContactCoordinates,
    DecisionMaker,
    Department,
    EmploymentStatus,
    SeniorityLevel,
    generate_person_id,
)
from app.integrations.search.base import BaseSearchClient, SearchQuery, SearchResultItem
from app.integrations.search.factory import get_search_client
from app.schemas.requests import (
    DecisionMakerPreviewRequest,
    DecisionMakerResearchRequest,
)
from app.schemas.responses import (
    DecisionMakerPreviewResponse,
    DecisionMakerReport,
    DiscoverySummary,
)

if TYPE_CHECKING:
    from app.domain.models.report import ScoredDecisionMaker
from app.services.company_identity import (
    CompanyIdentityResolutionService,
    IdentityResolutionStatus,
)
from app.services.content_extraction import ContentExtractionService
from app.services.decision_influence import DecisionInfluenceAssessmentService
from app.services.employment_verification import EmploymentVerificationService
from app.services.llm import LLMService
from app.services.person_identity import PersonIdentityResolutionService
from app.services.report_storage import get_report_repository
from app.services.role_classification import RoleClassificationService
from app.services.scoring import ScoringService
from app.services.source_normalization import (
    classify_source_type,
    deduplicate_urls,
)
from app.services.source_retrieval import SourceRetrievalService

logger = get_logger("services.people_research")


# --- LLM Evidence-Bound Extraction Models ---
class ExtractedPersonCandidate(BaseModel):
    """Candidate person extracted strictly from retrieved text excerpts."""

    full_name: str = Field(..., description="Full name of the real person")
    raw_job_title: str = Field(..., description="Exact job title stated in the text")
    department_hint: str | None = Field(default=None, description="Department mentioned")
    biography_excerpt: str | None = Field(
        default=None, description="Brief background excerpt from text"
    )
    public_profile_url: str | None = Field(
        default=None, description="Public profile or bio URL if mentioned in text"
    )
    supporting_evidence_ids: list[str] = Field(
        default_factory=list, description="IDs of evidence excerpts containing this person"
    )
    is_current_employee_hint: bool = Field(
        default=True, description="True if text suggests current affiliation"
    )
    departure_note: str | None = Field(
        default=None, description="Note if text indicates the person left or is former"
    )


class ExtractedCandidateList(BaseModel):
    """Collection of evidence-grounded candidate people."""

    candidates: list[ExtractedPersonCandidate] = Field(
        default_factory=list, description="List of extracted candidate people"
    )


class PeopleResearchService:
    """Production decision-maker discovery engine coordinating multi-source search, retrieval, and verification."""

    def __init__(
        self,
        search_client: BaseSearchClient | None = None,
        llm_service: LLMService | None = None,
        retrieval_service: SourceRetrievalService | None = None,
        extraction_service: ContentExtractionService | None = None,
        employment_service: EmploymentVerificationService | None = None,
        identity_service: PersonIdentityResolutionService | None = None,
        role_service: RoleClassificationService | None = None,
        influence_service: DecisionInfluenceAssessmentService | None = None,
        scoring_service: ScoringService | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.search_client = search_client or get_search_client(self.settings)
        self.llm_service = llm_service or LLMService(settings=self.settings)
        self.retrieval_service = retrieval_service or SourceRetrievalService()
        self.extraction_service = extraction_service or ContentExtractionService()
        self.employment_service = employment_service or EmploymentVerificationService()
        self.identity_service = identity_service or PersonIdentityResolutionService()
        self.role_service = role_service or RoleClassificationService()
        self.influence_service = influence_service or DecisionInfluenceAssessmentService()
        self.scoring_service = scoring_service or ScoringService(settings=self.settings)
        self.company_identity_service = CompanyIdentityResolutionService(
            search_client=self.search_client
        )
        self.repo = get_report_repository()

    async def preview_discovery(
        self,
        request: DecisionMakerPreviewRequest,
    ) -> DecisionMakerPreviewResponse:
        """Preview search query plan and targeted roles without executing web retrieval."""
        company_name = request.company_name
        domain = request.company_domain

        if not domain:
            resolution = await self.company_identity_service.resolve_identity(company_name)
            domain = resolution.resolved_domain

        queries = [
            f'"{company_name}" ("CEO" OR "CTO" OR "Founder" OR "Chief Executive") leadership',
            f'"{company_name}" ("VP Engineering" OR "Head of Product" OR "VP" OR "Director")',
        ]
        if domain:
            queries.insert(0, f"site:{domain} leadership OR team OR executives OR founders")

        if request.target_departments:
            depts_str = " OR ".join(f'"{d}"' for d in request.target_departments)
            queries.append(f'"{company_name}" ({depts_str}) (Head OR Director OR VP)')

        role_targets = [
            "Chief Executive Officer",
            "Chief Technology Officer",
            "VP of Engineering",
            "Head of Product",
        ]
        if request.target_departments:
            for d in request.target_departments:
                role_targets.append(f"Head of {d.title()}")

        return DecisionMakerPreviewResponse(
            company_name=company_name,
            company_domain=domain,
            target_departments=request.target_departments,
            planned_search_queries=queries,
            estimated_role_targets=role_targets,
        )

    async def discover_decision_makers(
        self,
        request: DecisionMakerResearchRequest,
    ) -> DecisionMakerReport:
        """Execute full real decision-maker discovery, employment verification, and relevance scoring."""
        start_time = time.perf_counter()
        created_at = datetime.now(UTC)
        research_id = str(uuid.uuid4())

        logger.info(
            "Initiating decision-maker discovery [id=%s, company='%s', domain=%s]",
            research_id,
            request.company_name,
            request.company_domain,
        )

        limitations: list[str] = []
        warnings: list[str] = []
        excluded_candidates_summary: list[str] = []

        # 1. Company Identity & Domain Resolution
        company_domain = request.company_domain
        company_name = request.company_name

        if not company_domain:
            resolution = await self.company_identity_service.resolve_identity(company_name)
            company_domain = resolution.resolved_domain
            company_name = resolution.normalized_name
            if resolution.status == IdentityResolutionStatus.AMBIGUOUS:
                warnings.append(resolution.ambiguity_reason or "Company identity has ambiguous domain candidates.")
            elif resolution.status == IdentityResolutionStatus.UNRESOLVED:
                warnings.append("Company official domain unverified; discovery relying on public references.")
                limitations.append("Research conducted without verified first-party domain.")

        target_domain = company_domain or ""

        # 2. Formulate Targeted Search Queries
        queries = [
            f'"{company_name}" ("CEO" OR "CTO" OR "Chief Technology Officer" OR "Founder" OR "Chief Executive") leadership',
            f'"{company_name}" ("VP Engineering" OR "Head of Product" OR "VP" OR "Director" OR "Chief Product Officer")',
            f'"{company_name}" ("appointed as" OR "joined as" OR "promoted to" OR "Head of")',
        ]
        if target_domain:
            queries.insert(0, f"site:{target_domain} leadership OR team OR executives OR founders")

        if request.target_departments:
            dept_terms = " OR ".join(f'"{d}"' for d in request.target_departments)
            queries.append(f'"{company_name}" ({dept_terms}) (Head OR Director OR VP)')

        # 3. Dispatch Search Queries
        raw_urls: list[str] = []
        search_snippets_map: dict[str, SearchResultItem] = {}

        for q_str in queries:
            try:
                results = await self.search_client.search(
                    SearchQuery(query=q_str, max_results=5)
                )
                for item in results:
                    raw_urls.append(item.url)
                    if item.url not in search_snippets_map:
                        search_snippets_map[item.url] = item
            except Exception as exc:
                logger.warning("Search query failed for '%s': %s", q_str, exc)
                warnings.append(f"Search provider warning on query '{q_str}': {exc}")

        # 4. Deduplicate and Prioritize URLs
        deduped_urls = deduplicate_urls(raw_urls)
        max_fetch = 8 if request.research_depth == "deep" else 5
        target_urls = deduped_urls[:max_fetch]

        # Prioritize official website pages
        if target_domain:
            official_url = f"https://{target_domain}"
            if official_url not in target_urls:
                target_urls.insert(0, official_url)

        # 5. Fetch Accessible Webpages & Compile Evidence
        evidence_store: dict[str, EvidenceRecord] = {}
        source_excerpts_for_llm: list[str] = []
        sources_retrieved_count = 0

        for url in target_urls:
            retrieved = await self.retrieval_service.fetch_source(url)
            source_type = classify_source_type(url, target_domain)

            if retrieved.is_accessible and retrieved.raw_html:
                sources_retrieved_count += 1
                extracted = self.extraction_service.extract(retrieved.raw_html, fallback_url=url)

                # Collect informative paragraphs mentioning potential roles or leadership
                leadership_keywords = (
                    "founder", "ceo", "cto", "chief", "vp", "vice president", "head",
                    "director", "lead", "leadership", "executive", "joined", "appointed",
                    "president", "officer", "team", "author", "engineer"
                )

                candidate_paragraphs = [
                    p for p in extracted.paragraphs
                    if any(kw in p.lower() for kw in leadership_keywords)
                ]

                # Fallback to general paragraphs if none matched keywords
                selected_paragraphs = candidate_paragraphs[:5] if candidate_paragraphs else extracted.paragraphs[:3]

                for p in selected_paragraphs:
                    ev_id = generate_evidence_id()
                    ev_record = EvidenceRecord(
                        evidence_id=ev_id,
                        source_url=url,
                        source_type=source_type,
                        title=extracted.title or None,
                        snippet=p[:400],
                        captured_at=retrieved.retrieved_at,
                        publication_date=extracted.published_date,
                    )
                    evidence_store[ev_id] = ev_record
                    source_excerpts_for_llm.append(
                        f"[EVIDENCE_ID: {ev_id} | SOURCE: {url} | TITLE: {extracted.title}]\n{p}"
                    )
            else:
                # Use search result snippet as fallback evidence
                sr_item = search_snippets_map.get(url)
                if sr_item and sr_item.snippet:
                    ev_id = generate_evidence_id()
                    ev_record = EvidenceRecord(
                        evidence_id=ev_id,
                        source_url=url,
                        source_type=source_type,
                        title=sr_item.title,
                        snippet=sr_item.snippet,
                        captured_at=datetime.now(UTC),
                        publication_date=sr_item.published_date,
                    )
                    evidence_store[ev_id] = ev_record
                    source_excerpts_for_llm.append(
                        f"[EVIDENCE_ID: {ev_id} | SOURCE: {url} | TITLE: {sr_item.title}]\n{sr_item.snippet}"
                    )

        # 6. Evidence-Bound Candidate Extraction via LLM
        combined_text = "\n\n---\n\n".join(source_excerpts_for_llm[:12])
        extracted_candidates: list[ExtractedPersonCandidate] = []

        if combined_text.strip():
            system_prompt = (
                "You are an objective B2B executive researcher. "
                "Your task is to identify real people and their job titles strictly from the provided text excerpts. "
                "CRITICAL RULES:\n"
                "1. ONLY extract people who are explicitly named in the text with a corporate title or role.\n"
                "2. NEVER invent names, people, job titles, or contact info.\n"
                "3. In 'supporting_evidence_ids', list ONLY the exact EVIDENCE_ID (e.g. 'ev_abc123') where that person appears.\n"
                "4. If text says someone left, resigned, or is 'former', set 'is_current_employee_hint': false and explain in 'departure_note'.\n"
                "5. If no people are mentioned in the text, return an empty list."
            )
            user_prompt = (
                f"Target Company: {company_name} (Domain: {target_domain})\n\n"
                f"RETRIEVED PUBLIC SOURCE EXCERPTS:\n{combined_text}\n\n"
                "Extract all named executives, leaders, and decision-maker candidates."
            )

            try:
                llm_response = await self.llm_service.generate_structured_response(
                    prompt=user_prompt,
                    response_model=ExtractedCandidateList,
                    system_prompt=system_prompt,
                    temperature=0.0,
                    max_tokens=1000,
                )
                extracted_candidates = llm_response.parsed.candidates
            except Exception as exc:
                logger.warning("LLM candidate extraction failed: %s", exc)
                warnings.append(f"LLM candidate extraction error: {exc}")

        # 7. Grounding Verification & Schema Conversion
        candidate_entities: list[DecisionMaker] = []
        raw_discovered_count = len(extracted_candidates)

        for candidate in extracted_candidates:
            # Reject empty names or hallucinated strings matching company name
            clean_name = self.identity_service.normalize_name(candidate.full_name)
            if not clean_name or len(clean_name.split()) < 2:
                continue
            if clean_name.lower() in company_name.lower():
                continue

            # Validate evidence IDs: Must exist in our actual retrieved evidence_store!
            valid_evidence: list[EvidenceRecord] = []
            for ev_id in candidate.supporting_evidence_ids:
                if ev_id in evidence_store:
                    valid_evidence.append(evidence_store[ev_id])

            # Reject candidate if NO actual evidence backs their extraction
            if not valid_evidence:
                logger.warning(
                    "Rejected candidate '%s': evidence IDs %s not found in retrieved store",
                    candidate.full_name,
                    candidate.supporting_evidence_ids,
                )
                continue

            # Classify role taxonomy
            norm_role = self.role_service.classify_title(candidate.raw_job_title)

            # Build initial DecisionMaker entity
            dm = DecisionMaker(
                person_id=generate_person_id(),
                full_name=clean_name,
                company_name=company_name,
                company_domain=target_domain,
                title=candidate.raw_job_title,
                normalized_title=norm_role.normalized_title,
                seniority=norm_role.seniority,
                department=norm_role.department,
                biography=candidate.biography_excerpt,
                biography_url=candidate.public_profile_url,
                contact_info=ContactCoordinates(
                    linkedin_url=candidate.public_profile_url
                ),
                evidence=valid_evidence,
            )
            candidate_entities.append(dm)

        # 8. Deduplication & Disambiguation
        deduped_candidates = self.identity_service.deduplicate_candidates(candidate_entities)
        duplicate_count = len(candidate_entities) - len(deduped_candidates)

        # 9. Current Employment Verification & Decision Influence Assessment
        verified_candidates: list[DecisionMaker] = []
        excluded_count = 0

        for candidate in deduped_candidates:
            emp_status, conf_score, rationale = self.employment_service.verify_employment(
                person_name=candidate.full_name,
                company_name=company_name,
                company_domain=target_domain,
                evidence_records=candidate.evidence,
            )

            candidate.employment_status = emp_status
            candidate.confidence_score = conf_score
            candidate.confidence_explanation = rationale

            # Assess decision-making influence
            assessment = self.influence_service.assess_influence(
                candidate=candidate,
                product_context=request.product_context,
            )
            candidate.assessment = assessment

            # Filter historical employees if requested
            if (
                emp_status == EmploymentStatus.HISTORICAL_EMPLOYMENT
                and not request.include_former_employees
            ):
                excluded_count += 1
                excluded_candidates_summary.append(
                    f"{candidate.full_name} ({candidate.title}): Excluded as historical employee ({rationale})"
                )
                continue

            verified_candidates.append(candidate)

        # 10. Relevance Scoring & Ranking
        target_seniority_enums: list[SeniorityLevel] | None = None
        if request.seniority_levels:
            target_seniority_enums = [
                SeniorityLevel(s.lower()) for s in request.seniority_levels if s.lower() in SeniorityLevel._value2member_map_
            ]

        target_dept_enums: list[Department] | None = None
        if request.target_departments:
            target_dept_enums = [
                Department(d.lower()) for d in request.target_departments if d.lower() in Department._value2member_map_
            ]

        scored_candidates: list[ScoredDecisionMaker] = await self.scoring_service.rank_decision_makers(
            people=verified_candidates,
            query_context=request.product_context or "",
            target_seniority=target_seniority_enums,
            target_departments=target_dept_enums,
        )

        # Apply discovery limit
        top_scored = scored_candidates[: request.discovery_limit]
        final_people = [s.person for s in top_scored]

        # 11. Compile Limitations and Audit Summary
        if not final_people:
            limitations.append(
                "No decision-makers could be verified from accessible public sources. Company may have restricted leadership directories."
            )
        if request.target_departments:
            found_depts = {p.department.value for p in final_people}
            missing = [d for d in request.target_departments if d.lower() not in found_depts]
            if missing:
                limitations.append(
                    f"No public decision-makers discovered for requested department(s): {missing}."
                )

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        completed_at = datetime.now(UTC)

        overall_status = "completed"
        if not final_people:
            overall_status = "partially_completed" if raw_discovered_count > 0 else "failed"

        all_used_evidence = [ev for dm in final_people for ev in dm.evidence]
        # Deduplicate evidence by evidence_id
        unique_evidence_map = {ev.evidence_id: ev for ev in all_used_evidence}

        report = DecisionMakerReport(
            research_id=research_id,
            company_name=company_name,
            company_domain=target_domain,
            people=final_people,
            scored_people=top_scored,
            evidence=list(unique_evidence_map.values()),
            discovery_summary=DiscoverySummary(
                search_queries_executed=queries,
                sources_retrieved=sources_retrieved_count,
                candidates_discovered=raw_discovered_count,
                candidates_verified=len(final_people),
                candidates_excluded=excluded_count,
                duplicate_candidates_merged=duplicate_count,
            ),
            limitations=limitations,
            excluded_candidates_summary=excluded_candidates_summary,
            warnings=warnings,
            overall_status=overall_status,
            created_at=created_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        )

        # Persist in repository
        self.repo.save_decision_maker_report(report)
        logger.info(
            "Decision maker discovery completed in %.1fms [id=%s, candidates_verified=%d]",
            duration_ms,
            research_id,
            len(final_people),
        )

        return report

    async def find_decision_makers(
        self,
        company_name: str,
        company_domain: str | None = None,
        target_seniority: list[SeniorityLevel] | None = None,
        target_departments: list[Department] | None = None,
        limit: int = 10,
    ) -> list[DecisionMaker]:
        """Contract implementation fulfilling BasePeopleResearchService."""
        dept_strings = [d.value for d in target_departments] if target_departments else []
        sen_strings = [s.value for s in target_seniority] if target_seniority else []

        report = await self.discover_decision_makers(
            DecisionMakerResearchRequest(
                company_name=company_name,
                company_domain=company_domain,
                target_departments=dept_strings,
                seniority_levels=sen_strings,
                discovery_limit=limit,
            )
        )
        return report.people

    async def get_person_details(
        self,
        full_name: str,
        company_name: str,
        linkedin_url: str | None = None,
    ) -> DecisionMaker:
        """Retrieve detailed background, contact coordinates, and evidence for a specific person."""
        logger.info("Executing get_person_details for '%s' at '%s'", full_name, company_name)
        # Search specifically for the individual
        query = f'"{full_name}" "{company_name}" (title OR role OR bio OR leadership)'
        results = await self.search_client.search(SearchQuery(query=query, max_results=3))

        evidence_list: list[EvidenceRecord] = []
        for r in results:
            ev = EvidenceRecord(
                source_url=r.url,
                title=r.title,
                snippet=r.snippet,
                captured_at=datetime.now(UTC),
                publication_date=r.published_date,
            )
            evidence_list.append(ev)

        # Classify from snippet
        snippet_text = " ".join(r.snippet for r in results)
        norm_role = self.role_service.classify_title(snippet_text[:80])

        dm = DecisionMaker(
            person_id=generate_person_id(),
            full_name=full_name,
            company_name=company_name,
            title=norm_role.raw_title or "Executive",
            normalized_title=norm_role.normalized_title,
            seniority=norm_role.seniority,
            department=norm_role.department,
            contact_info=ContactCoordinates(linkedin_url=linkedin_url),
            evidence=evidence_list,
        )

        emp_status, conf, rationale = self.employment_service.verify_employment(
            person_name=full_name,
            company_name=company_name,
            company_domain=None,
            evidence_records=evidence_list,
        )
        dm.employment_status = emp_status
        dm.confidence_score = conf
        dm.confidence_explanation = rationale
        dm.assessment = self.influence_service.assess_influence(dm)

        return dm
