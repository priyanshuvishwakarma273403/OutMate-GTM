"""Centralized Pydantic schemas for Outmate MCP tools."""

from app.mcp.schemas.common import MCPToolResult
from app.mcp.schemas.company import (
    GetCompanyProfileInput,
    GetCompanyProfileOutput,
    ResearchCompanyInput,
    ResearchCompanyOutput,
    SearchCompanyInput,
    SearchCompanyOutput,
)
from app.mcp.schemas.crm import (
    GetCompanyCRMContextInput,
    GetCRMCompanyInput,
    GetCRMContactInput,
    GetCRMDealInput,
    GetIntegrationStatusInput,
    ListIntegrationsInput,
    SearchCRMCompaniesInput,
    SearchCRMContactsInput,
    SearchCRMDealsInput,
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
    GenerateGTMReportInput,
    GenerateGTMReportOutput,
    GetDecisionMakerSourcesInput,
    GetDecisionMakerSourcesOutput,
    GetResearchReportInput,
    GetResearchReportOutput,
    GetResearchSourcesInput,
    GetResearchSourcesOutput,
)

__all__ = [
    "FindDecisionMakersInput",
    "FindDecisionMakersOutput",
    "GenerateGTMReportInput",
    "GenerateGTMReportOutput",
    "GetCompanyCRMContextInput",
    "GetCompanyProfileInput",
    "GetCompanyProfileOutput",
    "GetCRMCompanyInput",
    "GetCRMContactInput",
    "GetCRMDealInput",
    "GetDecisionMakerSourcesInput",
    "GetDecisionMakerSourcesOutput",
    "GetIntegrationStatusInput",
    "GetPersonDetailsInput",
    "GetPersonDetailsOutput",
    "GetResearchReportInput",
    "GetResearchReportOutput",
    "GetResearchSourcesInput",
    "GetResearchSourcesOutput",
    "ListIntegrationsInput",
    "MCPToolResult",
    "ResearchCompanyInput",
    "ResearchCompanyOutput",
    "SearchCompanyInput",
    "SearchCompanyOutput",
    "SearchCRMCompaniesInput",
    "SearchCRMContactsInput",
    "SearchCRMDealsInput",
    "VerifyPersonInput",
    "VerifyPersonOutput",
]
