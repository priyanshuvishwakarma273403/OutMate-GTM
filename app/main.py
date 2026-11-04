"""Main FastAPI application factory and entry point for Outmate GTM."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.health import router as health_router
from app.api.routes.llm import router as llm_router
from app.core.config import get_settings
from app.core.exceptions import OutmateError
from app.core.logging import get_logger, setup_logging
from app.mcp.server import OutmateMCPServer

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle context manager handling startup and shutdown tasks."""
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info(
        "Starting %s [env=%s, host=%s:%d]",
        settings.app_name,
        settings.app_env,
        settings.app_host,
        settings.app_port,
    )
    # Yield control during application uptime
    yield

    logger.info("Shutting down %s...", settings.app_name)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "AI-powered Go-To-Market (GTM) intelligence and decision-maker research platform. "
            "Supports standalone AI agent execution via OpenRouter and Claude.ai MCP integration."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS middleware
    # In production, wildcard origin is explicitly forbidden
    cors_origins = settings.allowed_origins
    if settings.app_env == "production" and "*" in cors_origins:
        logger.warning("Wildcard CORS detected in production; restricting to localhost.")
        cors_origins = ["http://localhost:3000"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Global Exception Handlers
    @app.exception_handler(OutmateError)
    async def outmate_error_handler(request: Request, exc: OutmateError) -> JSONResponse:
        logger.error("Outmate domain error: %s (%s)", exc.message, exc.__class__.__name__)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "error_type": exc.__class__.__name__,
                    "message": exc.message,
                    "details": exc.details,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning("Request schema validation failed on %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "error_type": "ValidationError",
                    "message": "Input validation failed",
                    "details": {"errors": exc.errors()},
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.critical(
            "Unhandled server exception on %s: %s", request.url.path, exc, exc_info=True
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "error_type": "InternalServerError",
                    "message": "An unexpected error occurred while processing the request.",
                    "details": {},
                },
            },
        )

    # Register API routes
    app.include_router(health_router)
    app.include_router(llm_router)

    # Mount Streamable MCP Server Starlette App for Remote Claude.ai integration
    mcp_server = OutmateMCPServer(settings=settings)
    app.mount("/mcp", mcp_server.get_sse_app())

    return app


app = create_app()
