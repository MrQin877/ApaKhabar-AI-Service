from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, ValidationError

from app.schemas.news import (
    CompletenessResult,
    NewsGenerationResponse,
    NewsRequest,
)
from app.services.ai_service import AIServiceError, AIService
from app.core.config import get_settings
from app.api.agent import execute
from app.services.agent_service import AgentService


router = APIRouter(prefix="/news", tags=["news"])


class CompletenessRequest(BaseModel):
    information: str = Field(min_length=1)


def _service_error(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(exc),
    )


@router.post("/check-completeness", response_model=CompletenessResult)
def check_completeness(request: CompletenessRequest) -> CompletenessResult:
    try:
        return AIService.check_news_completeness(request.information)
    except (AIServiceError, ValueError) as exc:
        raise _service_error(exc) from exc


@router.post("/generate", response_model=NewsGenerationResponse)
def generate_news(request: NewsRequest) -> NewsGenerationResponse:
    if get_settings().agent_enabled:
        return execute(lambda: AgentService().run(request))
    information = request.information if isinstance(request.information, str) else request.information.model_dump_json()
    try:
        completeness = AIService.check_news_completeness(information)
        if completeness.status != "ready":
            return NewsGenerationResponse(
                completeness=completeness,
                article=None,
            )

        article = AIService.write_news(
            text=information,
            language=request.language,
            tone=request.tone,
        )
        return NewsGenerationResponse(
            completeness=completeness,
            article=article,
        )
    except (AIServiceError, ValueError, ValidationError) as exc:
        raise _service_error(exc) from exc
