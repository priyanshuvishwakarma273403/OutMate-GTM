"""Architectural specifications for the five planned Outmate GTM MCP tools.

Phase 1 provides complete schema contracts, service mapping, and error declarations.
Tool business handlers are connected to the shared service layer in Phase 2.
"""

from app.mcp.registry import MCPToolRegistry, MCPToolSpecification
from app.mcp.schemas import (
    FindDecisionMakersInput,
    FindDecisionMakersOutput,
    GenerateGTMReportInput,
    GenerateGTMReportOutput,
    GetPersonDetailsInput,
    GetPersonDetailsOutput,
    SearchCompanyInput,
    SearchCompanyOutput,
    VerifyPersonInput,
    VerifyPersonOutput,
)

# 1. search_company specification
SEARCH_COMPANY_SPEC = MCPToolSpecification(
    name="search_company",
    description=(
        "Research a target company to extract domain, industry categorization, "
        "headcount, business model, and tech stack using public intelligence."
    ),
    input_model=SearchCompanyInput,
    output_model=SearchCompanyOutput,
    service_dependency="CompanyResearchService.research_company",
    external_integration_dependency="SearchProvider (Exa / Serper / Tavily)",
    expected_errors=[
        "EntityNotFoundError: Target company could not be resolved from public records",
        "SearchProviderError: External search provider request failed or timed out",
        "MCPValidationError: Provided company_name is missing or invalid",
    ],
)

# 2. find_decision_makers specification
FIND_DECISION_MAKERS_SPEC = MCPToolSpecification(
    name="find_decision_makers",
    description=(
        "Discover relevant business executives and decision-makers in a target company, "
        "filtered by seniority tier (c_level, vp, head, director) and department."
    ),
    input_model=FindDecisionMakersInput,
    output_model=FindDecisionMakersOutput,
    service_dependency="PeopleResearchService.find_decision_makers",
    external_integration_dependency="SearchProvider (Exa / Serper / Tavily)",
    expected_errors=[
        "EntityNotFoundError: Company not found or no public executives discovered",
        "SearchProviderError: Search engine failure during executive discovery query",
        "MCPValidationError: Invalid seniority tier or department filter specified",
    ],
)

# 3. get_person_details specification
GET_PERSON_DETAILS_SPEC = MCPToolSpecification(
    name="get_person_details",
    description=(
        "Retrieve in-depth professional details, contact coordinates, past roles, "
        "and public presence for a specific named business executive."
    ),
    input_model=GetPersonDetailsInput,
    output_model=GetPersonDetailsOutput,
    service_dependency="PeopleResearchService.get_person_details",
    external_integration_dependency="SearchProvider (Exa / Serper / Tavily)",
    expected_errors=[
        "EntityNotFoundError: Named person was not found in affiliation with company",
        "SearchProviderError: Failure querying public profiles and articles",
        "MCPValidationError: Person name or company name is empty",
    ],
)

# 4. verify_person specification
VERIFY_PERSON_SPEC = MCPToolSpecification(
    name="verify_person",
    description=(
        "Cross-corroborate a person's current employment claim, job title, and company "
        "affiliation across multiple public evidence sources."
    ),
    input_model=VerifyPersonInput,
    output_model=VerifyPersonOutput,
    service_dependency="VerificationService.verify_person",
    external_integration_dependency="SearchProvider (Exa / Serper / Tavily)",
    expected_errors=[
        "VerificationError: Public evidence contradicts current employment claim",
        "SearchProviderError: Unable to retrieve corroborating public pages",
        "MCPValidationError: Insufficient parameters provided for verification",
    ],
)

# 5. generate_gtm_report specification
GENERATE_GTM_REPORT_SPEC = MCPToolSpecification(
    name="generate_gtm_report",
    description=(
        "Synthesize a structured Go-To-Market research report compiling company intelligence, "
        "ranked decision-makers, relevance rationales, and recommended outreach angles."
    ),
    input_model=GenerateGTMReportInput,
    output_model=GenerateGTMReportOutput,
    service_dependency="ReportGenerationService.generate_report",
    external_integration_dependency="None (Uses OpenRouter or Claude in-context)",
    expected_errors=[
        "ServiceError: Report synthesis failed due to invalid company or prospect data",
        "MCPValidationError: Missing company profile or decision-maker payload",
    ],
)

ALL_GTM_TOOL_SPECS = [
    SEARCH_COMPANY_SPEC,
    FIND_DECISION_MAKERS_SPEC,
    GET_PERSON_DETAILS_SPEC,
    VERIFY_PERSON_SPEC,
    GENERATE_GTM_REPORT_SPEC,
]


def create_gtm_tool_registry() -> MCPToolRegistry:
    """Instantiate and populate the MCPToolRegistry with all five GTM tool specifications."""
    registry = MCPToolRegistry()
    for spec in ALL_GTM_TOOL_SPECS:
        registry.register(spec)
    return registry
