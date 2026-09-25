from app.core.config import get_settings
from app.services.model_providers.openai_compatible_provider import (
    OpenAICompatibleProvider,
)


class VllmProvider(OpenAICompatibleProvider):
    """Generation provider for a self-hosted vLLM server."""

    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            provider_name="vLLM",
            base_url=settings.vllm_base_url,
            api_key=settings.vllm_api_key,
            model_name=settings.vllm_model,
            timeout_seconds=settings.vllm_timeout_seconds,
            max_tokens=settings.vllm_max_tokens,
        )
