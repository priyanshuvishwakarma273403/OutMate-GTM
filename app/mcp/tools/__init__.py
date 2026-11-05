"""Production tool specifications and handlers for Outmate GTM MCP Server."""

from app.mcp.registry import MCPToolRegistry, MCPToolSpecification
from app.mcp.schemas.company import (
    GetCompanyProfileInput,
    GetCompanyProfileOutput,
    ResearchCompanyInput,
    ResearchCompanyOutput,
    SearchCompanyInput,
    SearchCompanyOutput,
)
from app.mcp.schemas.people import (
    FindDecisionMakersInput,
    FindDecisionMakersOutput,
    GetPersonDetailsInput,
    GetPersonDetailsOutput,
    VerifyPersonInput,
    VerifyPersonOutput,
)
from app.mcp.schemas.reports import (
    GetDecisionMakerSourcesInput,
    GetDecisionMakerSourcesOutput,
    GetResearchReportInput,
    GetResearchReportOutput,
    GetResearchSourcesInput,
    GetResearchSourcesOutput,
)
from app.mcp.scopes import MCPScopes
from app.mcp.tools.company_tools import (
    get_company_profile_tool,
    research_company_tool,
    search_company_tool,
)
from app.mcp.tools.decision_maker_tools import (
    find_decision_makers_tool,
    get_person_details_tool,
    verify_person_tool,
)
from app.mcp.tools.report_tools import (
    get_decision_maker_sources_tool,
    get_research_report_tool,
    get_research_sources_tool,
)

# 1. search_company specification
SEARCH_COMPANY_SPEC = MCPToolSpecification(
    name="search_company",
    title="Search Company",
    description="Search public web records for corporate mentions, domains, and general background.",
    input_model=SearchCompanyInput,
    output_model=SearchCompanyOutput,
    required_scope=MCPScopes.COMPANY_SEARCH,
    service_dependency="SearchClient.search",
    expected_errors=["MCPValidationError", "MCPExecutionError"],
)

# 2. research_company specification
RESEARCH_COMPANY_SPEC = MCPToolSpecification(
    name="research_company",
    title="Research Company Intelligence",
    description=(
        "Execute comprehensive company intelligence research including domain resolution, "
        "industry classification, headcount, tech stack, and multi-source evidence corroboration."
    ),
    input_model=ResearchCompanyInput,
    output_model=ResearchCompanyOutput,
    required_scope=MCPScopes.COMPANY_RESEARCH,
    service_dependency="CompanyResearchService.research_company",
    expected_errors=["MCPValidationError", "MCPExecutionError"],
)

# 3. get_company_profile specification
GET_COMPANY_PROFILE_SPEC = MCPToolSpecification(
    name="get_company_profile",
    title="Get Company Profile",
    description="Retrieve a completed company intelligence profile using a valid research reference ID.",
    input_model=GetCompanyProfileInput,
    output_model=GetCompanyProfileOutput,
    required_scope=MCPScopes.COMPANY_READ,
    service_dependency="InMemoryReportRepository.get_report",
    expected_errors=["MCPValidationError", "MCPResourceNotFoundError"],
)

# 4. find_decision_makers specification
FIND_DECISION_MAKERS_SPEC = MCPToolSpecification(
    name="find_decision_makers",
    title="Find Business Decision Makers",
    description=(
        "Discover real business executives and decision-makers for a target company, "
        "verify current employment, classify roles, and assess purchasing influence."
    ),
    input_model=FindDecisionMakersInput,
    output_model=FindDecisionMakersOutput,
    required_scope=MCPScopes.PEOPLE_DISCOVER,
    service_dependency="PeopleResearchService.discover_decision_makers",
    expected_errors=["MCPValidationError", "MCPExecutionError"],
)

# 5. verify_person specification
VERIFY_PERSON_SPEC = MCPToolSpecification(
    name="verify_person",
    title="Verify Discovered Person",
    description="Corroborate a discovered person's active employment and identity against public evidence.",
    input_model=VerifyPersonInput,
    output_model=VerifyPersonOutput,
    required_scope=MCPScopes.PEOPLE_VERIFY,
    service_dependency="EmploymentVerificationService.verify_employment",
    expected_errors=["MCPValidationError", "MCPResourceNotFoundError"],
)

# 6. get_person_details specification
GET_PERSON_DETAILS_SPEC = MCPToolSpecification(
    name="get_person_details",
    title="Get Person Details",
    description="Retrieve in-depth profile, buying influence assessment, and evidence citations for a decision-maker.",
    input_model=GetPersonDetailsInput,
    output_model=GetPersonDetailsOutput,
    required_scope=MCPScopes.PEOPLE_READ,
    service_dependency="InMemoryReportRepository.get_person",
    expected_errors=["MCPValidationError", "MCPResourceNotFoundError"],
)

# 7. get_research_sources specification
GET_RESEARCH_SOURCES_SPEC = MCPToolSpecification(
    name="get_research_sources",
    title="Get Company Research Sources",
    description="Retrieve the public evidence records backing a completed company research dossier.",
    input_model=GetResearchSourcesInput,
    output_model=GetResearchSourcesOutput,
    required_scope=MCPScopes.SOURCES_READ,
    service_dependency="InMemoryReportRepository.get_report",
    expected_errors=["MCPValidationError", "MCPResourceNotFoundError"],
)

# 8. get_decision_maker_sources specification
GET_DECISION_MAKER_SOURCES_SPEC = MCPToolSpecification(
    name="get_decision_maker_sources",
    title="Get Decision Maker Evidence Sources",
    description="Retrieve public evidence citations backing discovered decision-makers or a specific person.",
    input_model=GetDecisionMakerSourcesInput,
    output_model=GetDecisionMakerSourcesOutput,
    required_scope=MCPScopes.SOURCES_READ,
    service_dependency="InMemoryReportRepository.get_decision_maker_report",
    expected_errors=["MCPValidationError", "MCPResourceNotFoundError"],
)

# 9. get_research_report specification
GET_RESEARCH_REPORT_SPEC = MCPToolSpecification(
    name="get_research_report",
    title="Get Research Report",
    description="Retrieve a full completed company or decision-maker research report by ID.",
    input_model=GetResearchReportInput,
    output_model=GetResearchReportOutput,
    required_scope=MCPScopes.COMPANY_READ,
    service_dependency="InMemoryReportRepository",
    expected_errors=["MCPValidationError", "MCPResourceNotFoundError"],
)

ALL_GTM_TOOL_SPECS = [
    SEARCH_COMPANY_SPEC,
    RESEARCH_COMPANY_SPEC,
    GET_COMPANY_PROFILE_SPEC,
    FIND_DECISION_MAKERS_SPEC,
    VERIFY_PERSON_SPEC,
    GET_PERSON_DETAILS_SPEC,
    GET_RESEARCH_SOURCES_SPEC,
    GET_DECISION_MAKER_SOURCES_SPEC,
    GET_RESEARCH_REPORT_SPEC,
]


def create_gtm_tool_registry() -> MCPToolRegistry:
    """Instantiate and populate the MCPToolRegistry with all 9 production tool specifications and handlers."""
    registry = MCPToolRegistry()

    registry.register(SEARCH_COMPANY_SPEC, search_company_tool)
    registry.register(RESEARCH_COMPANY_SPEC, research_company_tool)
    registry.register(GET_COMPANY_PROFILE_SPEC, get_company_profile_tool)
    registry.register(FIND_DECISION_MAKERS_SPEC, find_decision_makers_tool)
    registry.register(VERIFY_PERSON_SPEC, verify_person_tool)
    registry.register(GET_PERSON_DETAILS_SPEC, get_person_details_tool)
    registry.register(GET_RESEARCH_SOURCES_SPEC, get_research_sources_tool)
    registry.register(GET_DECISION_MAKER_SOURCES_SPEC, get_decision_maker_sources_tool)
    registry.register(GET_RESEARCH_REPORT_SPEC, get_research_report_tool)

    return registry
