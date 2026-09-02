from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    ollama_generation_model: str = "qwen3:4b"
    ollama_embedding_model: str = "qwen3-embedding:0.6b"

    chroma_path: str = "./data/chroma"
    upload_path: str = "./data/uploads"

    max_upload_mb: int = Field(default=20, gt=0)
    rag_chunk_size: int = Field(default=1000, gt=0)
    rag_chunk_overlap: int = Field(default=150, ge=0)
    rag_top_k: int = Field(default=5, gt=0)
    rag_max_distance: float = Field(default=0.75, ge=0, le=2)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
