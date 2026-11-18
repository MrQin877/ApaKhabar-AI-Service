from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ai_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    ai_api_key: str = ""
    ai_model: str = ""
    ai_timeout_seconds: float = Field(default=180, gt=0)
    ai_max_tokens: int = Field(default=4096, gt=0)
    evaluator_enabled: bool = False
    evaluator_base_url: str = "https://api.groq.com/openai/v1"
    evaluator_model: str = ""
    evaluator_api_key: str = ""
    evaluator_timeout_seconds: float = Field(default=180, gt=0)
    evaluator_max_tokens: int = Field(default=4096, gt=0)
    embedding_provider: Literal["embedding_gemma", "openai", "gemini"] = "embedding_gemma"
    embedding_model: str = "google/embeddinggemma-300m"
    embedding_device: str = "auto"
    embedding_dimensions: int = Field(default=768, gt=0)
    embedding_base_url: str = "https://api.openai.com/v1"
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
