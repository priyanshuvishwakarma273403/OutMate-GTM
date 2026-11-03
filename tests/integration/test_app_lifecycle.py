"""Integration tests for application lifecycle, exception middleware, and CORS policies."""

from httpx import AsyncClient

from app.main import create_app


def test_app_factory() -> None:
    """Verify application factory constructs FastAPI instance with mounted routes."""
    app = create_app()
    assert app.title == "Outmate GTM"

    openapi_paths = list(app.openapi().get("paths", {}).keys())
    assert "/health" in openapi_paths
    assert "/ready" in openapi_paths


async def test_cors_headers_present(async_client: AsyncClient) -> None:
    """Verify CORS middleware adds Access-Control-Allow-Origin header for allowed origins."""
    response = await async_client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


async def test_404_handling(async_client: AsyncClient) -> None:
    """Verify 404 responses for undefined endpoints."""
    response = await async_client.get("/non-existent-path-12345")
    assert response.status_code == 404
