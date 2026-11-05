"""Standardized OAuth / MCP permission scopes for Outmate GTM tools."""

from enum import StrEnum


class MCPScopes(StrEnum):
    """Least-privilege permission scopes governing access to Outmate MCP tools."""

    COMPANY_SEARCH = "company:search"
    COMPANY_RESEARCH = "company:research"
    COMPANY_READ = "company:read"
    PEOPLE_DISCOVER = "people:discover"
    PEOPLE_VERIFY = "people:verify"
    PEOPLE_READ = "people:read"
    SOURCES_READ = "research:sources:read"
    REPORTS_READ = "reports:read"


ALL_SCOPES = [scope.value for scope in MCPScopes]
