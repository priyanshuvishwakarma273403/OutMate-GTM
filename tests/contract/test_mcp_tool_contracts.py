"""Contract tests verifying input/output schemas of the five planned MCP GTM tools."""

from app.domain.models import (
    CompanyProfile,
    DecisionMaker,
    Department,
    GTMReport,
    ScoredDecisionMaker,
    SeniorityLevel,
)
from app.mcp import (
    FindDecisionMakersInput,
    FindDecisionMakersOutput,
    GenerateGTMReportInput,
    GenerateGTMReportOutput,
    GetPersonDetailsInput,
    SearchCompanyInput,
    VerifyPersonInput,
    VerifyPersonOutput,
)


def test_search_company_contract() -> None:
    """Verify search_company input and output schema contracts."""
    input_data = SearchCompanyInput(company_name="Vercel", domain="vercel.com")
    assert input_data.company_name == "Vercel"
    assert input_data.domain == "vercel.com"

    json_schema = SearchCompanyInput.model_json_schema()
    assert "company_name" in json_schema["required"]


def test_find_decision_makers_contract() -> None:
    """Verify find_decision_makers input schema filters and output list."""
    input_data = FindDecisionMakersInput(
        company_name="Vercel",
        target_seniority=[SeniorityLevel.C_LEVEL, SeniorityLevel.VP],
        target_departments=[Department.ENGINEERING],
        limit=5,
    )
    assert input_data.limit == 5
    assert len(input_data.target_seniority) == 2

    output_data = FindDecisionMakersOutput(decision_makers=[], total_found=0)
    assert output_data.total_found == 0


def test_get_person_details_contract() -> None:
    """Verify get_person_details input and output schema contracts."""
    input_data = GetPersonDetailsInput(
        full_name="Guillermo Rauch",
        company_name="Vercel",
    )
    assert input_data.full_name == "Guillermo Rauch"
    assert input_data.linkedin_url is None


def test_verify_person_contract(sample_decision_maker: DecisionMaker) -> None:
    """Verify verify_person input and output schema contracts."""
    input_data = VerifyPersonInput(
        person_name="Guillermo Rauch",
        company_name="Vercel",
        title="CEO",
    )
    assert input_data.title == "CEO"

    output_data = VerifyPersonOutput(
        person=sample_decision_maker,
        is_verified=True,
        confidence_score=0.98,
    )
    assert output_data.is_verified is True
    assert output_data.confidence_score == 0.98


def test_generate_gtm_report_contract(
    sample_company: CompanyProfile,
    sample_scored_decision_maker: ScoredDecisionMaker,
    sample_gtm_report: GTMReport,
) -> None:
    """Verify generate_gtm_report input and output schema contracts."""
    input_data = GenerateGTMReportInput(
        query="Who are the decision makers in Vercel?",
        company=sample_company,
        decision_makers=[sample_scored_decision_maker],
    )
    assert input_data.company.name == "Vercel"
    assert len(input_data.decision_makers) == 1

    output_data = GenerateGTMReportOutput(
        report=sample_gtm_report,
        markdown_content="# Vercel GTM Report\n\nExecutive summary...",
    )
    assert output_data.report.company.name == "Vercel"
    assert output_data.markdown_content.startswith("# Vercel GTM Report")
