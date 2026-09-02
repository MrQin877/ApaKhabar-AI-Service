from fastapi import APIRouter, HTTPException, status
from ollama import Client, ResponseError

from app.core.config import get_settings


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def application_health() -> dict[str, str]:
    return {"status": "ok", "service": "ApaKhabar AI Service"}


@router.get("/ollama")
def ollama_health() -> dict[str, object]:
    settings = get_settings()
    client = Client(host=settings.ollama_base_url)

    try:
        response = client.list()
    except (ConnectionError, ResponseError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama is unavailable. Start Ollama and check OLLAMA_BASE_URL.",
        ) from exc

    installed_models = {model.model for model in response.models if model.model}
    required_models = {
        settings.ollama_generation_model,
        settings.ollama_embedding_model,
    }
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
