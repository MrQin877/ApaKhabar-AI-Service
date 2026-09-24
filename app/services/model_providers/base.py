from abc import ABC, abstractmethod
from typing import Any


class ModelProviderError(RuntimeError):
    """Raised when a configured generation provider cannot return a response."""


class GenerationProvider(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        raise NotImplementedError


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def embed_documents(
        self,
        texts: list[str],
        *,
        titles: list[str] | None = None,
    ) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, query: str) -> list[float]:
        raise NotImplementedError
