import json
from queue import Queue
from threading import Thread

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError

from app.schemas.news import (
    CompletenessResult,
    NewsGenerationResponse,
    NewsLanguage,
    NewsContentType,
    NewsArticle,
    NewsQualityEvaluation,
    NewsRevisionRequest,
    NewsRevisionResponse,
    NewsRequest,
)
from app.services.ai_service import AIServiceError, OllamaService
from app.agent.news_workflow import NewsCreationWorkflow


router = APIRouter(prefix="/news", tags=["news"])


class CompletenessRequest(BaseModel):
    information: str = Field(min_length=1)
    content_type: NewsContentType = "news_article"


class NewsQualityRequest(BaseModel):
    article: NewsArticle
    evidence: str = Field(min_length=1)
    user_request: str | None = Field(default=None, max_length=2000)


def _service_error(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(exc),
    )


@router.post("/check-completeness", response_model=CompletenessResult)
def check_completeness(request: CompletenessRequest) -> CompletenessResult:
    try:
        return OllamaService.check_news_completeness(
            request.information,
            content_type=request.content_type,
        )
    except (AIServiceError, ValueError) as exc:
        raise _service_error(exc) from exc


@router.post("/generate", response_model=NewsGenerationResponse)
def generate_news(request: NewsRequest) -> NewsGenerationResponse:
    try:
        return NewsCreationWorkflow.run(request)
    except (AIServiceError, ValueError, ValidationError) as exc:
        raise _service_error(exc) from exc


@router.post("/evaluate-quality", response_model=NewsQualityEvaluation)
def evaluate_news_quality(request: NewsQualityRequest) -> NewsQualityEvaluation:
    """Evaluate a saved or edited draft against its approved evidence."""
    try:
        return OllamaService.evaluate_news_quality(
            article=request.article,
            evidence=request.evidence,
            user_request=request.user_request,
        )
    except (AIServiceError, ValueError, ValidationError) as exc:
        raise _service_error(exc) from exc


@router.post("/revise", response_model=NewsRevisionResponse)
def revise_news(request: NewsRevisionRequest) -> NewsRevisionResponse:
    try:
        article = OllamaService.revise_news(request)
        try:
            quality = OllamaService.evaluate_news_quality(
                article,
                evidence=request.evidence,
                user_request=request.instruction,
            )
        except (AIServiceError, ValueError):
            quality = None
            article.warnings.append(
                "Evaluasi kualitas otomatis tidak tersedia; tinjauan manual diperlukan."
            )
        return NewsRevisionResponse(article=article, quality=quality)
    except (AIServiceError, ValueError, ValidationError) as exc:
        raise _service_error(exc) from exc


@router.post("/generate-stream")
def generate_news_stream(request: NewsRequest) -> StreamingResponse:
    """Stream stage events and finish with the structured generation response."""

    def stream():
        events: Queue[dict | None] = Queue()

        def progress(stage: str, message: str) -> None:
            events.put({"type": "status", "stage": stage, "message": message})

        def run() -> None:
            try:
                result = NewsCreationWorkflow.run(request, progress=progress)
                events.put({
                    "type": "complete",
                    "data": result.model_dump(mode="json"),
                })
            except (AIServiceError, ValueError, ValidationError) as exc:
                events.put({"type": "error", "message": str(exc)})
            finally:
                events.put(None)

        Thread(target=run, daemon=True).start()
        while True:
            event = events.get()
            if event is None:
                break
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")
