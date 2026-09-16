from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class AskUserChoice(BaseModel):
    lead_in: str = Field(min_length=1, max_length=300)
    question: str = Field(min_length=1, max_length=300)
    options: list[str] = Field(min_length=2, max_length=50)
    select_type: Literal["single", "multi"] = "single"
    field: str = Field(min_length=1, max_length=100)


class AskUserChoiceToolCall(BaseModel):
    name: Literal["ask_user_choice"] = "ask_user_choice"
    arguments: AskUserChoice


class WebSearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=600)
    count: int = Field(default=5, ge=1, le=10)
    freshness: Literal["pd", "pw", "pm", "py"] | None = None
    country: str = Field(default="MY", min_length=2, max_length=2)
    search_language: str = Field(default="id", min_length=2, max_length=5)


class WebSearchResult(BaseModel):
    title: str
    url: HttpUrl
    snippet: str
    published_at: str | None = None
    source: str = "Brave Search"
