from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ai_provider: Literal["ollama", "llama_cpp"] = "ollama"
    llama_cpp_base_url: str = "http://127.0.0.1:8080/v1"
    llama_cpp_api_key: str = ""
    llama_cpp_model: str = "apakhabar-gemma"
    llama_cpp_timeout_seconds: float = Field(default=180, gt=0)
    llama_cpp_max_tokens: int = Field(default=4096, gt=0)
    embedding_provider: Literal["ollama", "embedding_gemma", "openai"] = "ollama"
    embedding_model: str = "google/embeddinggemma-300m"
    embedding_device: str = "auto"
    embedding_dimensions: int = Field(default=768, gt=0)
    embedding_base_url: str = "http://127.0.0.1:8081/v1"
    embedding_api_key: str = ""
    apakhabar_ai_service_token: str = ""
    agent_enabled: bool = True
    agent_db_path: str = "./data/agent/checkpoints.sqlite"
    agent_skills_path: str = str(Path(__file__).resolve().parents[2] / "skills")
    agent_max_tool_calls: int = Field(default=5, ge=1, le=20)
    agent_max_revisions: int = Field(default=2, ge=0, le=3)
    agent_max_seconds: int = Field(default=900, ge=10)
    agent_quality_target: float = Field(default=80, ge=0, le=100)
    web_search_url: str = ""
    web_search_api_key: str = ""
    ocr_language: str = "eng"
    ocr_max_pages: int = Field(default=100, ge=1)
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
