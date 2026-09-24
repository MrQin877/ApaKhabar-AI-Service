import threading
from typing import Any

from app.core.config import get_settings
from app.services.model_providers.base import GenerationProvider, ModelProviderError


class GemmaProvider(GenerationProvider):
    """Lazy, in-process Gemma 4 provider powered by Hugging Face Transformers."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._processor: Any | None = None
        self._model: Any | None = None
        self._load_lock = threading.Lock()
        self._generation_lock = threading.Lock()

    @property
    def model_name(self) -> str:
        return self.settings.gemma_model

    def _load(self) -> tuple[Any, Any]:
        if self._processor is not None and self._model is not None:
            return self._processor, self._model

        with self._load_lock:
            if self._processor is not None and self._model is not None:
                return self._processor, self._model
            try:
                from huggingface_hub.errors import GatedRepoError
                from transformers import AutoModelForMultimodalLM, AutoProcessor
            except ImportError as exc:
                raise ModelProviderError(
                    "Gemma dependencies are not installed. Run "
                    "'pip install -r requirements-gemma.txt'."
                ) from exc

            try:
                self._processor = AutoProcessor.from_pretrained(self.model_name)
                self._model = AutoModelForMultimodalLM.from_pretrained(
                    self.model_name,
                    dtype="auto",
                    device_map=self.settings.gemma_device,
                )
            except GatedRepoError as exc:
                raise ModelProviderError(
                    "Gemma access has not been approved for the current Hugging "
                    "Face account. Visit "
                    f"https://huggingface.co/{self.model_name}, acknowledge the "
                    "license, then run 'hf auth login' again."
                ) from exc
            except (OSError, ValueError, RuntimeError) as exc:
                raise ModelProviderError(
                    f"Could not load Gemma model '{self.model_name}': {exc}"
                ) from exc

        return self._processor, self._model

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        processor, model = self._load()
        prepared_messages = [dict(message) for message in messages]
        if response_schema:
            prepared_messages[-1] = {
                **prepared_messages[-1],
                "content": (
                    f"{prepared_messages[-1]['content']}\n\n"
                    "Return only one valid JSON object. Do not use Markdown fences. "
                    "The JSON must match this schema:\n"
                    f"{response_schema}"
                ),
            }

        try:
            inputs = processor.apply_chat_template(
                prepared_messages,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
                add_generation_prompt=True,
                enable_thinking=False,
            ).to(model.device)
            input_length = inputs["input_ids"].shape[-1]
            generation_options: dict[str, Any] = {
                "max_new_tokens": self.settings.gemma_max_new_tokens,
                "do_sample": temperature > 0,
            }
            if temperature > 0:
                generation_options.update(
                    temperature=max(temperature, 0.01),
                    top_p=self.settings.gemma_top_p,
                    top_k=self.settings.gemma_top_k,
                )

            # A single in-process model must not execute overlapping generations.
            with self._generation_lock:
                output = model.generate(**inputs, **generation_options)
            decoded = processor.decode(
                output[0][input_length:],
                skip_special_tokens=True,
            )
            return decoded.strip()
        except (OSError, ValueError, RuntimeError) as exc:
            raise ModelProviderError(f"Gemma generation failed: {exc}") from exc
