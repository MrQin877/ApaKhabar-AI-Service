from fastapi import APIRouter, HTTPException, status
from ollama import Client, ResponseError
import requests

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


@router.get("/model")
def generation_model_health() -> dict[str, object]:
    """Check an external generation server without loading an in-process model."""
    settings = get_settings()
    provider = settings.ai_provider.strip().lower()
    if provider not in {"vllm", "openai_compatible", "llama_cpp", "llamacpp"}:
        return {
            "status": "not_remote",
            "provider": provider,
            "message": "The configured generation provider runs in process or via Ollama.",
        }

    is_llama_cpp = provider in {"llama_cpp", "llamacpp"}
    base_url = (
        settings.llama_cpp_base_url if is_llama_cpp else settings.vllm_base_url
    )
    api_key = settings.llama_cpp_api_key if is_llama_cpp else settings.vllm_api_key
    model_name = settings.llama_cpp_model if is_llama_cpp else settings.vllm_model
    timeout = (
        settings.llama_cpp_timeout_seconds
        if is_llama_cpp
        else settings.vllm_timeout_seconds
    )

    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = requests.get(
            f"{base_url.rstrip('/')}/models",
            headers=headers,
            timeout=min(timeout, 15),
        )
        response.raise_for_status()
        body = response.json()
        models = [item.get("id") for item in body.get("data", []) if item.get("id")]
    except (requests.RequestException, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The configured model server is unavailable.",
        ) from exc

    if model_name not in models:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "The model server is running, but the configured model is unavailable.",
                "configured_model": model_name,
                "available_models": models,
            },
        )

    return {
        "status": "ok",
        "provider": "llama_cpp" if is_llama_cpp else "vllm",
        "generation_model": model_name,
    }
