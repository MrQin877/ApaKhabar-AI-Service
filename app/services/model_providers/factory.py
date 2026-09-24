from functools import lru_cache

from app.core.config import get_settings
from app.services.model_providers.base import EmbeddingProvider, GenerationProvider


@lru_cache
def get_generation_provider() -> GenerationProvider:
    settings = get_settings()
    provider = settings.ai_provider.strip().lower()

    if provider == "ollama":
        from app.services.model_providers.ollama_provider import OllamaProvider

        return OllamaProvider()
    if provider == "gemma":
        from app.services.model_providers.gemma_provider import GemmaProvider

        return GemmaProvider()

    raise ValueError(
        f"Unsupported AI_PROVIDER '{settings.ai_provider}'. Use 'ollama' or 'gemma'."
    )


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    provider = settings.embedding_provider.strip().lower()

    if provider == "ollama":
        from app.services.model_providers.embedding_providers import (
            OllamaEmbeddingProvider,
        )

        return OllamaEmbeddingProvider()
    if provider in {"embedding_gemma", "embeddinggemma", "gemma"}:
        from app.services.model_providers.embedding_providers import (
            EmbeddingGemmaProvider,
        )

        return EmbeddingGemmaProvider()

    raise ValueError(
        "Unsupported EMBEDDING_PROVIDER "
        f"'{settings.embedding_provider}'. Use 'ollama' or 'embedding_gemma'."
    )
