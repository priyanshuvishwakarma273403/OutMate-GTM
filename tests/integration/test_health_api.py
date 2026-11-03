"""Integration tests for FastAPI health and readiness API endpoints."""

from httpx import AsyncClient


async def test_health_liveness_endpoint(async_client: AsyncClient) -> None:
    """Verify GET /health returns 200 OK and expected liveness payload."""
    response = await async_client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "app_name" in data
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data


async def test_health_readiness_endpoint(async_client: AsyncClient) -> None:
    """Verify GET /ready returns 200 OK and reports dependency health without secret leakage."""
    response = await async_client.get("/ready")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ["ready", "degraded"]
    assert "dependencies" in data

    dependencies = data["dependencies"]
    assert "openrouter" in dependencies
    assert "nango" in dependencies
    assert "search_provider" in dependencies
    assert "mcp_server" in dependencies

    # Verify no secret patterns are leaked in response body
    raw_text = response.text
    assert "sk-" not in raw_text
    assert "Bearer" not in raw_text


async def test_openapi_schema_endpoint(async_client: AsyncClient) -> None:
    """Verify OpenAPI specification is accessible and valid JSON."""
    response = await async_client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert schema["info"]["title"] == "Outmate GTM"
    assert "/health" in schema["paths"]
    assert "/ready" in schema["paths"]
