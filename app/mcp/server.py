"""Production-grade Model Context Protocol (MCP) server for Outmate GTM.

Exposes real company research, decision-maker discovery, public source verification,
and report retrieval to Claude.ai and AI agents via local stdio and remote Streamable HTTP transports.
"""

import sys
from typing import Any

from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from starlette.applications import Starlette

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.mcp.auth.verifier import OIDCTokenVerifier, StaticBearerTokenVerifier
from app.mcp.configuration import MCPConfiguration
from app.mcp.registry import MCPToolRegistry
from app.mcp.tools import create_gtm_tool_registry
from app.mcp.transports.stdio import run_stdio_server
from app.mcp.transports.streamable_http import create_streamable_http_app

logger = get_logger("mcp.server")


class OutmateMCPServer:
    """Enterprise MCP Server providing real B2B Go-To-Market research and intelligence tools."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        config: MCPConfiguration | None = None,
        registry: MCPToolRegistry | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.config = config or MCPConfiguration(
            server_name=self.settings.mcp_server_name,
            transport=self.settings.mcp_transport if self.settings.mcp_transport in ("stdio", "streamable_http") else "streamable_http",
            host=self.settings.mcp_host,
            port=self.settings.mcp_port,
            bearer_token=self.settings.mcp_auth_token,
            auth_mode="bearer" if (self.settings.mcp_auth_enabled and self.settings.mcp_auth_token) else "none",
        )
        self.registry = registry or create_gtm_tool_registry()

        # Build official AuthSettings and TokenVerifier if protected mode is active
        auth_settings: AuthSettings | None = None
        token_verifier: Any = None

        if self.config.auth_mode == "bearer" and self.config.get_token_hash():
            res_url = self.config.resource_server_url or f"http://{self.config.host}:{self.config.port}{self.config.endpoint}"
            iss_url = self.config.oauth_issuer_url or f"http://{self.config.host}:{self.config.port}"
            auth_settings = AuthSettings(
                issuer_url=iss_url,
                resource_server_url=res_url,
                validate_token_resource=True,
                required_scopes=self.config.required_scopes,
            )
            token_verifier = StaticBearerTokenVerifier(self.config)
            logger.info("MCP server configured with personal static bearer token verification")

        elif self.config.auth_mode == "oidc" and self.config.oauth_issuer_url:
            res_url = self.config.resource_server_url or f"http://{self.config.host}:{self.config.port}{self.config.endpoint}"
            auth_settings = AuthSettings(
                issuer_url=self.config.oauth_issuer_url,
                resource_server_url=res_url,
                validate_token_resource=True,
                required_scopes=self.config.required_scopes,
            )
            token_verifier = OIDCTokenVerifier(self.config)
            logger.info("MCP server configured with OIDC JWT resource server verification")

        # Initialize official Python MCP Server instance
        self.mcp_app = MCPServer(
            name=self.config.server_name,
            version=self.config.server_version,
            instructions=(
                "Outmate GTM Intelligence Server. Provides verifiable company research, "
                "decision-maker discovery, public evidence citations, and GTM dossiers. "
                "All returned data is grounded in actual public sources."
            ),
            auth=auth_settings,
            token_verifier=token_verifier,
        )

        self._register_tools()
        self._register_resources()
        self._register_prompts()

    def _register_tools(self) -> None:
        """Register all 9 GTM tools onto the official MCPServer instance."""

        # 1. search_company
        @self.mcp_app.tool(
            name="search_company",
            description="Search public web records for corporate mentions, domains, and general background.",
        )
        async def search_company(
            query: str,
            domain: str | None = None,
            limit: int = 5,
        ) -> dict[str, Any]:
            args = {"query": query, "domain": domain, "limit": limit}
            return await self.registry.execute("search_company", args)

        # 2. research_company
        @self.mcp_app.tool(
            name="research_company",
            description=(
                "Execute comprehensive company intelligence research including domain resolution, "
                "industry classification, headcount, tech stack, and multi-source evidence corroboration."
            ),
        )
        async def research_company(
            company_name: str,
            company_domain: str | None = None,
            research_depth: str = "standard",
            requested_fields: list[str] | None = None,
        ) -> dict[str, Any]:
            args = {
                "company_name": company_name,
                "company_domain": company_domain,
                "research_depth": research_depth,
                "requested_fields": requested_fields,
            }
            return await self.registry.execute("research_company", args)

        # 3. get_company_profile
        @self.mcp_app.tool(
            name="get_company_profile",
            description="Retrieve a completed company intelligence profile using a valid research reference ID.",
        )
        async def get_company_profile(research_reference: str) -> dict[str, Any]:
            args = {"research_reference": research_reference}
            return await self.registry.execute("get_company_profile", args)

        # 4. find_decision_makers
        @self.mcp_app.tool(
            name="find_decision_makers",
            description=(
                "Discover real business executives and decision-makers for a target company, "
                "verify current employment, classify roles, and assess purchasing influence."
            ),
        )
        async def find_decision_makers(
            company_name: str,
            company_domain: str | None = None,
            product_context: str | None = None,
            target_departments: list[str] | None = None,
            target_roles: list[str] | None = None,
            seniority_levels: list[str] | None = None,
            discovery_limit: int = 10,
            research_depth: str = "standard",
        ) -> dict[str, Any]:
            args = {
                "company_name": company_name,
                "company_domain": company_domain,
                "product_context": product_context,
                "target_departments": target_departments or [],
                "target_roles": target_roles or [],
                "seniority_levels": seniority_levels or [],
                "discovery_limit": discovery_limit,
                "research_depth": research_depth,
            }
            return await self.registry.execute("find_decision_makers", args)

        # 5. verify_person
        @self.mcp_app.tool(
            name="verify_person",
            description="Corroborate a discovered person's active employment and identity against public evidence.",
        )
        async def verify_person(
            research_reference: str,
            person_reference: str,
        ) -> dict[str, Any]:
            args = {
                "research_reference": research_reference,
                "person_reference": person_reference,
            }
            return await self.registry.execute("verify_person", args)

        # 6. get_person_details
        @self.mcp_app.tool(
            name="get_person_details",
            description="Retrieve in-depth profile, buying influence assessment, and evidence citations for a decision-maker.",
        )
        async def get_person_details(
            research_reference: str,
            person_reference: str,
        ) -> dict[str, Any]:
            args = {
                "research_reference": research_reference,
                "person_reference": person_reference,
            }
            return await self.registry.execute("get_person_details", args)

        # 7. get_research_sources
        @self.mcp_app.tool(
            name="get_research_sources",
            description="Retrieve the public evidence records backing a completed company research dossier.",
        )
        async def get_research_sources(research_reference: str) -> dict[str, Any]:
            args = {"research_reference": research_reference}
            return await self.registry.execute("get_research_sources", args)

        # 8. get_decision_maker_sources
        @self.mcp_app.tool(
            name="get_decision_maker_sources",
            description="Retrieve public evidence citations backing discovered decision-makers or a specific person.",
        )
        async def get_decision_maker_sources(
            research_reference: str,
            person_reference: str | None = None,
        ) -> dict[str, Any]:
            args = {
                "research_reference": research_reference,
                "person_reference": person_reference,
            }
            return await self.registry.execute("get_decision_maker_sources", args)

        # 9. get_research_report
        @self.mcp_app.tool(
            name="get_research_report",
            description="Retrieve a full completed company or decision-maker research report by ID.",
        )
        async def get_research_report(research_reference: str) -> dict[str, Any]:
            args = {"research_reference": research_reference}
            return await self.registry.execute("get_research_report", args)

    def _register_resources(self) -> None:
        """Register read-only MCP capabilities resource."""

        @self.mcp_app.resource(
            "gtm://capabilities",
            name="Outmate GTM Capabilities",
            description="Overview of Outmate GTM research capabilities, tools, and schemas",
        )
        async def get_capabilities() -> str:
            return (
                "Outmate GTM Intelligence Platform:\n"
                "- Tools Available: 9 production tools covering company intelligence, executive discovery, "
                "employment verification, and evidence provenance.\n"
                "- Guarantee: 100% public source grounding with zero AI hallucinations or fake people."
            )

    def _register_prompts(self) -> None:
        """Register reusable research workflows as standard MCP prompts."""

        @self.mcp_app.prompt(
            name="research_company_prompt",
            description="Workflow prompt for researching a target company's business model and tech stack",
        )
        async def research_company_prompt(company_name: str, domain: str | None = None) -> str:
            return (
                f"Please conduct an in-depth Go-To-Market research assessment of '{company_name}' "
                f"(Domain: {domain or 'auto-resolve'}). Use `research_company` to gather verified public evidence."
            )

        @self.mcp_app.prompt(
            name="find_decision_makers_prompt",
            description="Workflow prompt for discovering real verified executives and buying decision-makers",
        )
        async def find_decision_makers_prompt(company_name: str, departments: str | None = None) -> str:
            return (
                f"Please identify active key decision-makers at '{company_name}' "
                f"focusing on {departments or 'Executive and Engineering'} leadership. "
                "Use `find_decision_makers` and verify their current employment."
            )

    def get_streamable_http_app(self, allowed_origins: list[str] | None = None) -> Starlette:
        """Construct the Starlette ASGI application for Streamable HTTP remote transport."""
        return create_streamable_http_app(
            mcp_server=self.mcp_app,
            config=self.config,
            allowed_origins=allowed_origins or self.settings.allowed_origins if isinstance(self.settings.allowed_origins, list) else None,
        )

    # Alias for backward compatibility
    get_sse_app = get_streamable_http_app

    async def run_stdio(self) -> None:
        """Run MCP server over standard input/output for local execution and MCP Inspector."""
        await run_stdio_server(self.mcp_app)

    async def run(self) -> None:
        """Entrypoint honoring configured transport."""
        if self.config.transport == "stdio":
            await self.run_stdio()
        else:
            import uvicorn
            app = self.get_streamable_http_app()
            uv_config = uvicorn.Config(
                app,
                host=self.config.host,
                port=self.config.port,
                log_level=self.config.log_level.lower(),
            )
            server = uvicorn.Server(uv_config)
            logger.info("Starting Outmate MCP server on %s:%d via uvicorn...", self.config.host, self.config.port)
            await server.serve()


if __name__ == "__main__":
    import asyncio
    import os

    settings = get_settings()
    server = OutmateMCPServer(settings=settings)
    asyncio.run(server.run())
