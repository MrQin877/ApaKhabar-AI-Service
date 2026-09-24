import threading
from typing import Any

from ollama import Client, ResponseError

from app.core.config import get_settings
from app.services.model_providers.base import EmbeddingProvider, ModelProviderError


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = Client(host=self.settings.ollama_base_url, timeout=120.0)

    @property
    def model_name(self) -> str:
        return self.settings.ollama_embedding_model

    def _embed(self, inputs: list[str] | str) -> list[list[float]]:
        try:
            response = self.client.embed(model=self.model_name, input=inputs)
            return [list(vector) for vector in response.embeddings]
        except (ResponseError, ConnectionError, OSError) as exc:
            raise ModelProviderError(f"Embedding request failed: {exc}") from exc

    def embed_documents(
        self,
        texts: list[str],
        *,
        titles: list[str] | None = None,
    ) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, query: str) -> list[float]:
        return self._embed(query)[0]


class EmbeddingGemmaProvider(EmbeddingProvider):
    """Lazy multilingual EmbeddingGemma provider for local RAG."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._model: Any | None = None
        self._load_lock = threading.Lock()
        self._encode_lock = threading.Lock()

    @property
    def model_name(self) -> str:
        return self.settings.embedding_model

    def _resolve_device(self) -> str:
        if self.settings.embedding_device != "auto":
            return self.settings.embedding_device
        try:
            import torch
        except ImportError as exc:
            raise ModelProviderError(
                "EmbeddingGemma dependencies are not installed. Run "
                "'pip install -r requirements-gemma.txt'."
            ) from exc
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _load(self) -> Any:
        if self._model is not None:
            return self._model
        with self._load_lock:
            if self._model is not None:
                return self._model
            try:
                from huggingface_hub.errors import GatedRepoError
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise ModelProviderError(
                    "EmbeddingGemma dependencies are not installed. Run "
                    "'pip install -r requirements-gemma.txt'."
                ) from exc
            try:
                self._model = SentenceTransformer(
                    self.model_name,
                    device=self._resolve_device(),
                    truncate_dim=self.settings.embedding_dimensions,
                )
            except GatedRepoError as exc:
                raise ModelProviderError(
                    "EmbeddingGemma access has not been approved for the current "
                    "Hugging Face account. Visit "
                    f"https://huggingface.co/{self.model_name}, acknowledge the "
                    "license, then run 'hf auth login' again."
                ) from exc
            except (OSError, ValueError, RuntimeError) as exc:
                raise ModelProviderError(
                    f"Could not load embedding model '{self.model_name}': {exc}"
                ) from exc
        return self._model

    def _encode(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        try:
            with self._encode_lock:
                vectors = model.encode(
                    texts,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
            return vectors.tolist()
        except (OSError, ValueError, RuntimeError) as exc:
            raise ModelProviderError(f"Embedding generation failed: {exc}") from exc

    def embed_documents(
        self,
        texts: list[str],
        *,
        titles: list[str] | None = None,
    ) -> list[list[float]]:
        if titles is not None and len(titles) != len(texts):
            raise ValueError("Embedding titles must match the number of texts.")
        titles = titles or ["none"] * len(texts)
        prepared = [
            f"title: {title.strip() or 'none'} | text: {text}"
            for title, text in zip(titles, texts, strict=True)
        ]
        return self._encode(prepared)

    def embed_query(self, query: str) -> list[float]:
        prepared = f"task: search result | query: {query}"
        return self._encode([prepared])[0]
