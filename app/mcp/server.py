"""Model Context Protocol (MCP) server implementation for Outmate GTM.

Supports both local stdio transport (local development) and streamable HTTP / SSE transport
for remote deployment connecting Claude.ai custom connectors.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.mcpserver import MCPServer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.mcp.registry import MCPToolRegistry
from app.mcp.schemas import (
    FindDecisionMakersInput,
    GetPersonDetailsInput,
    SearchCompanyInput,
    VerifyPersonInput,
)
from app.mcp.tools import create_gtm_tool_registry

logger = get_logger("mcp.server")


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware protecting remote MCP endpoints."""

    def __init__(self, app: Any, auth_token: str | None) -> None:
        super().__init__(app)
        self.auth_token = auth_token

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not self.auth_token:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "message": "Missing Bearer token"},
            )

        token = auth_header.removeprefix("Bearer ").strip()
        if token != self.auth_token:
            return JSONResponse(
                status_code=403,
                content={"error": "Forbidden", "message": "Invalid authentication token"},
            )

        return await call_next(request)


class OutmateMCPServer:
    """Enterprise MCP Server exposing GTM intelligence tools to Claude.ai and AI agents."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        registry: MCPToolRegistry | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.registry = registry or create_gtm_tool_registry()

        # Initialize official Python MCP Server instance
        self.mcp_app = MCPServer(
            name=self.settings.mcp_server_name,
            version="0.1.0",
            instructions=(
                "Outmate GTM Intelligence MCP Server. Provides company research, "
                "decision-maker discovery, public evidence verification, and GTM reporting."
            ),
        )

        self._register_tools()

    def _register_tools(self) -> None:
        """Register the 5 GTM tools onto the MCPServer instance."""

        # 1. search_company
        @self.mcp_app.tool(
            name="search_company",
            description=(
                "Research a target company to extract domain, industry categorization, "
                "headcount, business model, and tech stack using public intelligence."
            ),
        )
        async def search_company(company_name: str, domain: str | None = None) -> dict[str, Any]:
            args = SearchCompanyInput(company_name=company_name, domain=domain).model_dump()
            return await self.registry.execute("search_company", args)

        # 2. find_decision_makers
        @self.mcp_app.tool(
            name="find_decision_makers",
            description=(
                "Discover relevant business executives and decision-makers in a target company, "
                "filtered by seniority tier and department."
            ),
        )
        async def find_decision_makers(
            company_name: str,
            company_domain: str | None = None,
            target_seniority: list[str] | None = None,
            target_departments: list[str] | None = None,
            limit: int = 10,
        ) -> dict[str, Any]:
            args = FindDecisionMakersInput(
                company_name=company_name,
                company_domain=company_domain,
                target_seniority=target_seniority or [],  # type: ignore[arg-type]
                target_departments=target_departments or [],  # type: ignore[arg-type]
                limit=limit,
            ).model_dump()
            return await self.registry.execute("find_decision_makers", args)

        # 3. get_person_details
        @self.mcp_app.tool(
            name="get_person_details",
            description=(
                "Retrieve in-depth professional details, contact coordinates, past roles, "
                "and public presence for a specific named business executive."
            ),
        )
        async def get_person_details(
            full_name: str,
            company_name: str,
            linkedin_url: str | None = None,
        ) -> dict[str, Any]:
            args = GetPersonDetailsInput(
                full_name=full_name,
                company_name=company_name,
                linkedin_url=linkedin_url,
            ).model_dump()
            return await self.registry.execute("get_person_details", args)

        # 4. verify_person
        @self.mcp_app.tool(
            name="verify_person",
            description=(
                "Cross-corroborate a person's current employment claim, job title, and company "
                "affiliation across multiple public evidence sources."
            ),
        )
        async def verify_person(
            person_name: str,
            company_name: str,
            title: str,
            linkedin_url: str | None = None,
        ) -> dict[str, Any]:
            args = VerifyPersonInput(
                person_name=person_name,
                company_name=company_name,
                title=title,
                linkedin_url=linkedin_url,
            ).model_dump()
            return await self.registry.execute("verify_person", args)

        # 5. generate_gtm_report
        @self.mcp_app.tool(
            name="generate_gtm_report",
            description=(
                "Synthesize a structured Go-To-Market research report compiling company intelligence, "
                "ranked decision-makers, relevance rationales, and recommended outreach angles."
            ),
        )
        async def generate_gtm_report(
            query: str,
            company: dict[str, Any],
            decision_makers: list[dict[str, Any]] | None = None,
            include_outreach_angles: bool = True,
        ) -> dict[str, Any]:
            args = {
                "query": query,
                "company": company,
                "decision_makers": decision_makers or [],
                "include_outreach_angles": include_outreach_angles,
            }
            return await self.registry.execute("generate_gtm_report", args)

    def get_sse_app(self) -> Any:
        """Construct the Starlette SSE application, applying Bearer authentication if enabled."""
        app = self.mcp_app.sse_app()
        if self.settings.mcp_auth_enabled and self.settings.mcp_auth_token:
            app.add_middleware(BearerAuthMiddleware, auth_token=self.settings.mcp_auth_token)
        return app

    async def run_stdio(self) -> None:
        """Run MCP server over standard input/output for local execution."""
        logger.info("Starting Outmate MCP server on stdio transport...")
        await self.mcp_app.run_stdio_async()
