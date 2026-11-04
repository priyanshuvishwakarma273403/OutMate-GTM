"""API endpoints for LLM provider testing and completions."""

from fastapi import APIRouter, Depends, status

from app.core.logging import get_logger
from app.schemas.requests import LLMTestRequest
from app.schemas.responses import LLMTestResponse
from app.services.llm import LLMService

logger = get_logger("api.routes.llm")

router = APIRouter(prefix="/api/v1/llm", tags=["LLM"])


def get_llm_service() -> LLMService:
    """Dependency provider returning an LLMService instance."""
    return LLMService()


@router.post(
    "/test",
    response_model=LLMTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Test OpenRouter LLM completion",
    description=(
        "Sends a test prompt to OpenRouter and returns the live model completion, "
        "model identifier, and usage metrics without exposing internal credentials."
    ),
)
async def test_llm_completion(
    request: LLMTestRequest,
    service: LLMService = Depends(get_llm_service),
) -> LLMTestResponse:
    """Execute live LLM completion request via OpenRouter gateway."""
    logger.info("Received LLM test request (length=%d characters)", len(request.message))

    response = await service.generate_response(
        prompt=request.message,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        model=request.model,
    )

    return LLMTestResponse(
        status="success",
        model=response.model,
        content=response.content or "",
        usage=response.usage,
        duration_ms=response.duration_ms,
    )
