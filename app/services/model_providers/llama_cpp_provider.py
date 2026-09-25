from app.core.config import get_settings
from app.services.model_providers.openai_compatible_provider import (
    OpenAICompatibleProvider,
)


class LlamaCppProvider(OpenAICompatibleProvider):
    """Generation provider for llama.cpp's OpenAI-compatible llama-server."""

    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            provider_name="llama.cpp",
            base_url=settings.llama_cpp_base_url,
            api_key=settings.llama_cpp_api_key,
            model_name=settings.llama_cpp_model,
            timeout_seconds=settings.llama_cpp_timeout_seconds,
            max_tokens=settings.llama_cpp_max_tokens,
        )
