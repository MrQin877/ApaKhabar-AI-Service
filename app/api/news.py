from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, ValidationError

from app.schemas.news import (
    CompletenessResult,
    NewsGenerationResponse,
    NewsLanguage,
    NewsRequest,
)
from app.services.ai_service import AIServiceError, OllamaService


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
        return OllamaService.check_news_completeness(request.information)
    except (AIServiceError, ValueError) as exc:
        raise _service_error(exc) from exc


@router.post("/generate", response_model=NewsGenerationResponse)
def generate_news(request: NewsRequest) -> NewsGenerationResponse:
    try:
        information_text = request.information_text()
        completeness = OllamaService.check_news_completeness(information_text)
        if completeness.status != "ready":
            return NewsGenerationResponse(
                completeness=completeness,
                article=None,
            )

        article = OllamaService.write_news(
            text=information_text,
            language=request.language,
            tone=request.tone,
        )
        return NewsGenerationResponse(
            completeness=completeness,
            article=article,
        )
    except (AIServiceError, ValueError, ValidationError) as exc:
        raise _service_error(exc) from exc
