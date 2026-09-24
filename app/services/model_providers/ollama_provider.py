from typing import Any

from ollama import Client, ResponseError

from app.core.config import get_settings
from app.services.model_providers.base import GenerationProvider, ModelProviderError


class OllamaProvider(GenerationProvider):
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def model_name(self) -> str:
        return self.settings.ollama_generation_model

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        try:
            response = Client(
                host=self.settings.ollama_base_url,
                timeout=120.0,
            ).chat(
                model=self.model_name,
                messages=messages,
                format=response_schema,
                stream=False,
                think=False,
                options={"temperature": temperature},
            )
            return response.message.content
        except ResponseError as exc:
            raise ModelProviderError(f"Ollama request failed: {exc}") from exc
        except (ConnectionError, OSError) as exc:
            raise ModelProviderError("Ollama is unavailable.") from exc
