from typing import Literal

from pydantic import BaseModel, Field


AssistantIntent = Literal[
    "conversation",
    "extract_information",
    "search_information",
    "generate_news",
    "revise_news",
]


class AssistantIntentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    has_files: bool = False
    has_selected_information: bool = False
    has_draft: bool = False


class AssistantIntentResponse(BaseModel):
    intent: AssistantIntent
    extraction_mode: Literal["general", "targeted"] | None = None
    normalized_query: str | None = None
    keywords: list[str] = Field(default_factory=list, max_length=20)
    confidence: float = Field(ge=0, le=1)
    guidance: str | None = None
