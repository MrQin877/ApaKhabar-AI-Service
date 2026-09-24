from fastapi import APIRouter, HTTPException, status
from ollama import Client, ResponseError

from app.core.config import get_settings


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def application_health() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "ApaKhabar AI Service",
        "generation_provider": settings.ai_provider,
        "embedding_provider": settings.embedding_provider,
        "api_version": settings.api_version,
        "service_authentication": bool(settings.internal_api_token),
        "embedding_index_version": settings.embedding_index_version,
    }


@router.get("/ollama")
def ollama_health() -> dict[str, object]:
    settings = get_settings()
    required_models: set[str] = set()
    if settings.ai_provider.strip().lower() == "ollama":
        required_models.add(settings.ollama_generation_model)
    if settings.embedding_provider.strip().lower() == "ollama":
        required_models.add(settings.ollama_embedding_model)
    if not required_models:
        return {
            "status": "not_required",
            "message": "Neither generation nor embeddings currently use Ollama.",
        }

    client = Client(host=settings.ollama_base_url)

    try:
        response = client.list()
    except (ConnectionError, ResponseError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama is unavailable. Start Ollama and check OLLAMA_BASE_URL.",
        ) from exc

    installed_models = {model.model for model in response.models if model.model}
    missing_models = sorted(required_models - installed_models)

    if missing_models:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Ollama is running, but required models are missing.",
                "missing_models": missing_models,
            },
        )

    return {
        "status": "ok",
        "generation_model": settings.ollama_generation_model,
        "embedding_model": settings.ollama_embedding_model,
    }
