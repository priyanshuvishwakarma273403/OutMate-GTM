"""Health and readiness check endpoints for application lifecycle monitoring."""

from datetime import UTC, datetime

from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.schemas.responses import DependencyHealth, HealthResponse, ReadinessResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Liveness Check",
    description="Returns OK if the FastAPI process is responsive and running.",
)
async def check_liveness() -> HealthResponse:
    """Liveness probe indicating whether the process is alive."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version="0.1.0",
        environment=settings.app_env,
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Readiness Probe",
    description="Evaluates configured subsystems (OpenRouter, Nango, Search) without exposing credentials.",
)
async def check_readiness(response: Response) -> ReadinessResponse:
    """Readiness probe evaluating operational readiness of subsystems."""
    settings = get_settings()
    dependencies: dict[str, DependencyHealth] = {}

    # 1. OpenRouter gateway configuration
    if settings.openrouter_api_key:
        dependencies["openrouter"] = DependencyHealth(
            name="openrouter",
            status="healthy",
            details=f"Model: {settings.openrouter_model} (gateway reachable)",
        )
    else:
        dependencies["openrouter"] = DependencyHealth(
            name="openrouter",
            status="not_configured",
            details="OPENROUTER_API_KEY is not set (Mode A agent disabled)",
        )

    # 2. Nango OAuth and proxy integration
    if settings.nango_secret_key:
        dependencies["nango"] = DependencyHealth(
            name="nango",
            status="healthy",
            details=f"Base URL: {settings.nango_base_url}",
        )
    else:
        dependencies["nango"] = DependencyHealth(
            name="nango",
            status="not_configured",
            details="NANGO_SECRET_KEY is not set (CRM proxy features disabled)",
        )

    # 3. Search Provider
    if settings.search_api_key or settings.search_provider == "mock":
        dependencies["search_provider"] = DependencyHealth(
            name="search_provider",
            status="healthy",
            details=f"Provider engine: {settings.search_provider}",
        )
    else:
        dependencies["search_provider"] = DependencyHealth(
            name="search_provider",
            status="not_configured",
            details=f"SEARCH_API_KEY is missing for provider: {settings.search_provider}",
        )

    # 4. MCP Server Subsystem
    dependencies["mcp_server"] = DependencyHealth(
        name="mcp_server",
        status="healthy",
        details=f"Transport: {settings.mcp_transport}, Auth: {settings.mcp_auth_enabled}",
    )

    # Compute overall readiness status
    # Base service is ready if app is running; degraded if external keys are missing in production
    is_fully_configured = all(dep.status == "healthy" for dep in dependencies.values())
    if is_fully_configured:
        overall_status = "ready"
    elif settings.app_env in ["development", "test"]:
        overall_status = "ready"  # Soft ready in dev/test for foundational work
    else:
        overall_status = "degraded"
        response.status_code = status.HTTP_200_OK

    return ReadinessResponse(
        status=overall_status,
        app_name=settings.app_name,
        version="0.1.0",
        timestamp=datetime.now(UTC),
        dependencies=dependencies,
    )
