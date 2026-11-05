"""Research planning and query decomposition for the standalone AI agent."""

import re
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from app.agent.prompts import QUERY_DECOMPOSITION_PROMPT_TEMPLATE
from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.domain.models.person import Department, SeniorityLevel
from app.llm.base import BaseLLMClient
from app.services.llm import LLMService

logger = get_logger("agent.planner")


class ResearchPlan(BaseModel):
    """Structured execution plan formulated from a natural-language research query."""

    original_query: str = Field(..., description="Original user prompt")
    target_company: str = Field(..., description="Extracted company name")
    target_domain: str | None = Field(default=None, description="Inferred or extracted domain")
    target_seniority: list[SeniorityLevel] = Field(
        default_factory=list, description="Targeted seniority tiers"
    )
    target_departments: list[Department] = Field(
        default_factory=list, description="Targeted department functions"
    )
    execution_steps: list[str] = Field(
        default_factory=list, description="Sequential tool execution steps planned"
    )


class LLMDecompositionSchema(BaseModel):
    """Schema for LLM structured query extraction."""

    target_company: str = Field(..., description="Name of the company to research")
    target_domain: str | None = Field(
        default=None, description="Domain name if explicitly mentioned"
    )
    seniority_levels: list[str] = Field(
        default_factory=list, description="Extracted seniority levels"
    )
    departments: list[str] = Field(default_factory=list, description="Extracted departments")


class BasePlanner(ABC):
    """Contract for decomposing queries into executable research plans."""

    @abstractmethod
    async def create_plan(self, query: str) -> ResearchPlan:
        """Decompose a natural language query into a structured ResearchPlan."""
        pass


class ResearchPlanner(BasePlanner):
    """Planner analyzing queries and formulating structured GTM execution plans."""

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm_client = llm_client
        self.llm_service = LLMService(client=llm_client, settings=self.settings)

    async def create_plan(self, query: str) -> ResearchPlan:
        """Decompose a natural language query into a structured ResearchPlan."""
        logger.info("Formulating research plan for query: '%s'", query)

        # 1. Attempt LLM structured decomposition if OpenRouter is configured
        if self.settings.openrouter_api_key:
            try:
                prompt = QUERY_DECOMPOSITION_PROMPT_TEMPLATE.format(query=query)
                res = await self.llm_service.generate_structured_response(
                    prompt=prompt,
                    response_model=LLMDecompositionSchema,
                    temperature=0.1,
                )
                extracted = res.parsed
                company = extracted.target_company.strip().strip("\"'")
                if company and company.lower() != "unknown":
                    seniority = self._map_seniority(extracted.seniority_levels)
                    departments = self._map_departments(extracted.departments)
                    return ResearchPlan(
                        original_query=query,
                        target_company=company,
                        target_domain=extracted.target_domain,
                        target_seniority=seniority,
                        target_departments=departments,
                        execution_steps=["research_company", "find_decision_makers"],
                    )
            except Exception as exc:
                logger.warning("LLM query decomposition failed, falling back to heuristic: %s", exc)

        # 2. Heuristic rule-based fallback
        company, domain = self._extract_company_heuristic(query)
        seniority = self._extract_seniority_heuristic(query)
        departments = self._extract_department_heuristic(query)

        return ResearchPlan(
            original_query=query,
            target_company=company,
            target_domain=domain,
            target_seniority=seniority,
            target_departments=departments,
            execution_steps=["research_company", "find_decision_makers"],
        )

    def _extract_company_heuristic(self, query: str) -> tuple[str, str | None]:
        """Heuristically extract company name and optional domain from query string."""
        clean = query.strip()

        # Check for explicit domain (e.g. vercel.com)
        domain_match = re.search(
            r"\b([a-zA-Z0-9-]+\.(?:com|io|ai|co|org|net|dev|app))\b", clean, re.IGNORECASE
        )
        domain = domain_match.group(1).lower() if domain_match else None

        # Common patterns:
        # "decision makers in/at (the company) X"
        # "research (the company) X"
        patterns = [
            r"(?:decision\s*makers?|executives?|leaders?|prospects?|people|team)\s*(?:at|in|for|of)\s*(?:the\s*company\s*)?([A-Za-z0-9\.\-\s]+?)(?:\?|\.|\,|;|$)",
            r"(?:research|analyze|look\s*up|investigate|profile)\s*(?:the\s*company\s*)?([A-Za-z0-9\.\-\s]+?)(?:\?|\.|\,|;|$)",
            r"(?:in|at)\s*(?:the\s*company\s*)?([A-Za-z0-9\.\-\s]+?)(?:\?|\.|\,|;|$)",
        ]
        for pat in patterns:
            m = re.search(pat, clean, re.IGNORECASE)
            if m:
                extracted = m.group(1).strip()
                # Clean up words like "and find..."
                extracted = re.split(
                    r"\s+(?:and|with|to|for|who)\s+", extracted, flags=re.IGNORECASE
                )[0]
                if extracted and len(extracted) > 1:
                    return extracted, domain

        # If query has a domain, use the domain stem
        if domain:
            stem = domain.split(".")[0].capitalize()
            return stem, domain

        # Fallback: strip common non-entity lead phrases
        stripped = re.sub(
            r"^(?:who\s*are\s*the\s*decision\s*makers\s*in|who\s*is\s*at|find\s*people\s*at|research|analyze)\s*",
            "",
            clean,
            flags=re.IGNORECASE,
        ).strip("?. ")
        return stripped if stripped else clean, domain

    def _map_seniority(self, values: list[str]) -> list[SeniorityLevel]:
        """Map string seniority labels to SeniorityLevel enums."""
        result = []
        for v in values:
            v_clean = v.lower().strip()
            for s in SeniorityLevel:
                if s.value in v_clean or v_clean in s.value:
                    result.append(s)
                    break
        return list(dict.fromkeys(result))

    def _map_departments(self, values: list[str]) -> list[Department]:
        """Map string department labels to Department enums."""
        result = []
        for v in values:
            v_clean = v.lower().strip()
            for d in Department:
                if d.value in v_clean or v_clean in d.value:
                    result.append(d)
                    break
        return list(dict.fromkeys(result))

    def _extract_seniority_heuristic(self, query: str) -> list[SeniorityLevel]:
        """Heuristically identify requested seniority tiers."""
        q = query.lower()
        levels = []
        if any(
            term in q
            for term in [
                "ceo",
                "cto",
                "cfo",
                "cro",
                "cpo",
                "cio",
                "ciso",
                "c-level",
                "chief",
                "founder",
            ]
        ):
            levels.append(SeniorityLevel.C_LEVEL)
        if any(term in q for term in ["vp", "vice president", "svp", "evp"]):
            levels.append(SeniorityLevel.VP)
        if "head of" in q or "head" in q:
            levels.append(SeniorityLevel.HEAD)
        if "director" in q:
            levels.append(SeniorityLevel.DIRECTOR)
        if "manager" in q:
            levels.append(SeniorityLevel.MANAGER)
        return levels

    def _extract_department_heuristic(self, query: str) -> list[Department]:
        """Heuristically identify requested department functions."""
        q = query.lower()
        deps = []
        if any(
            term in q for term in ["engineering", "tech", "technology", "developer", "software"]
        ):
            deps.append(Department.ENGINEERING)
        if any(term in q for term in ["product", "product management"]):
            deps.append(Department.PRODUCT)
        if any(term in q for term in ["sales", "revenue", "commercial"]):
            deps.append(Department.SALES)
        if any(term in q for term in ["marketing", "growth"]):
            deps.append(Department.MARKETING)
        if any(term in q for term in ["security", "infosec", "cyber"]):
            deps.append(Department.SECURITY)
        if any(term in q for term in ["finance", "financial"]):
            deps.append(Department.FINANCE)
        return deps
