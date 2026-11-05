"""Contract tests verifying input/output schemas of the Outmate GTM MCP tools."""

from app.domain.models import (
    CompanyProfile,
    GTMReport,
    ScoredDecisionMaker,
)
from app.mcp import (
    FindDecisionMakersInput,
    GenerateGTMReportInput,
    GenerateGTMReportOutput,
    GetCompanyProfileInput,
    GetCompanyProfileOutput,
    GetDecisionMakerSourcesInput,
    GetDecisionMakerSourcesOutput,
    GetPersonDetailsInput,
    GetResearchReportInput,
    GetResearchReportOutput,
    GetResearchSourcesInput,
    GetResearchSourcesOutput,
    ResearchCompanyInput,
    SearchCompanyInput,
    SearchCompanyOutput,
    VerifyPersonInput,
    VerifyPersonOutput,
)


def test_search_company_contract() -> None:
    """Verify search_company input and output schema contracts."""
    input_data = SearchCompanyInput(query="Vercel", domain="vercel.com", limit=5)
    assert input_data.query == "Vercel"
    assert input_data.domain == "vercel.com"
    assert input_data.limit == 5

    output = SearchCompanyOutput(query='"Vercel" site:vercel.com', results=[], total_results=0)
    assert output.total_results == 0


def test_research_company_contract() -> None:
    """Verify research_company input schema contract."""
    input_data = ResearchCompanyInput(
        company_name="Vercel", company_domain="vercel.com", research_depth="standard"
    )
    assert input_data.company_name == "Vercel"
    assert input_data.company_domain == "vercel.com"
    assert input_data.research_depth == "standard"


def test_get_company_profile_contract(sample_company: CompanyProfile) -> None:
    """Verify get_company_profile input and output schema contracts."""
    input_data = GetCompanyProfileInput(research_reference="res_123")
    assert input_data.research_reference == "res_123"

    output = GetCompanyProfileOutput(
        research_id="res_123",
        company=sample_company,
        findings=["Corroborated deployment platform."],
        identity_status="resolved",
    )
    assert output.company.name == "Vercel"


def test_find_decision_makers_contract() -> None:
    """Verify find_decision_makers input schema filters and limits."""
    input_data = FindDecisionMakersInput(
        company_name="Vercel",
        target_departments=["engineering"],
        seniority_levels=["c_level", "vp"],
        discovery_limit=5,
    )
    assert input_data.discovery_limit == 5
    assert len(input_data.seniority_levels) == 2


def test_get_person_details_contract() -> None:
    """Verify get_person_details input schema contract."""
    input_data = GetPersonDetailsInput(
        research_reference="res_123",
        person_reference="dm_456",
    )
    assert input_data.research_reference == "res_123"
    assert input_data.person_reference == "dm_456"


def test_verify_person_contract() -> None:
    """Verify verify_person input and output schema contracts."""
    input_data = VerifyPersonInput(
        research_reference="res_123",
        person_reference="dm_456",
    )
    assert input_data.research_reference == "res_123"
    assert input_data.person_reference == "dm_456"

    output_data = VerifyPersonOutput(
        person_id="dm_456",
        full_name="Guillermo Rauch",
        company_name="Vercel",
        employment_status="current_employment_verified",
        confidence_score=0.95,
        confidence_explanation="Grounded in public leadership page.",
        verification_status="verified",
    )
    assert output_data.employment_status == "current_employment_verified"
    assert output_data.confidence_score == 0.95


def test_get_sources_contracts() -> None:
    """Verify source provenance input and output contracts."""
    company_sources_in = GetResearchSourcesInput(research_reference="res_123")
    assert company_sources_in.research_reference == "res_123"
    company_sources_out = GetResearchSourcesOutput(
        research_reference="res_123", total_sources=0, sources=[]
    )
    assert company_sources_out.total_sources == 0

    dm_sources_in = GetDecisionMakerSourcesInput(
        research_reference="res_123", person_reference="dm_456"
    )
    assert dm_sources_in.person_reference == "dm_456"
    dm_sources_out = GetDecisionMakerSourcesOutput(
        research_reference="res_123", person_reference="dm_456", total_sources=0, sources=[]
    )
    assert dm_sources_out.total_sources == 0


def test_get_research_report_contract() -> None:
    """Verify get_research_report input and output contracts."""
    inp = GetResearchReportInput(research_reference="res_123")
    assert inp.research_reference == "res_123"
    out = GetResearchReportOutput(research_id="res_123", report_type="company", data={})
    assert out.report_type == "company"


def test_generate_gtm_report_contract(
    sample_company: CompanyProfile,
    sample_scored_decision_maker: ScoredDecisionMaker,
    sample_gtm_report: GTMReport,
) -> None:
    """Verify generate_gtm_report input and output schema contracts."""
    input_data = GenerateGTMReportInput(
        query="Who are the decision makers in Vercel?",
        company=sample_company.model_dump(),
        decision_makers=[sample_scored_decision_maker.model_dump()],
    )
    assert input_data.company["name"] == "Vercel"
    assert len(input_data.decision_makers) == 1

    output_data = GenerateGTMReportOutput(
        report=sample_gtm_report.model_dump(),
        markdown_content="# Vercel GTM Report\n\nExecutive summary...",
    )
    assert output_data.report["company"]["name"] == "Vercel"
    assert output_data.markdown_content.startswith("# Vercel GTM Report")
