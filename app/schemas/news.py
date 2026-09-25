from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator
from app.schemas.information import ExtractionResponse

NewsLanguage = Literal["en", "ms", "id"]
ContentFormat = Literal["news_article", "announcement", "event_report", "historical_profile", "data_report", "regulation_summary", "public_awareness"]


class MissingInformation(BaseModel):
    field: str
    importance: Literal["required", "recommended"]
    question: str
    options: list[str] = Field(default_factory=list)
    selection_type: Literal["single", "multi"] = "single"


class CompletenessResult(BaseModel):
    status: Literal["ready", "needs_information", "has_conflicts"]
    missing: list[MissingInformation]
    conflicts: list[str]
    known_facts: list[str]


class NewsArticle(BaseModel):
    headline: str = Field(min_length=1)
    subheadline: str | None = None
    lead: str = Field(min_length=1)
    body: list[str] = Field(min_length=1)
    summary: str = Field(min_length=1)
    labels: list[str]
    language: NewsLanguage
    sources_used: list[str]
    warnings: list[str]
    category: str | None = None


class NewsRequest(BaseModel):
    information: str | ExtractionResponse = ""
    language: NewsLanguage = "id"
    tone: str = Field(default="formal", min_length=1, max_length=50)
    instructions: str = Field(default="", max_length=20000)
    user_facts: list[dict[str, str]] = Field(default_factory=list)
    clarification_completed: bool = False
    available_categories: list[str] = Field(default_factory=list)
    default_category: str | None = None
    content_format: ContentFormat = "news_article"
    current_draft: NewsArticle | None = None
    owner_id: str = Field(default="local", min_length=1, max_length=100)
    session_id: str | None = None
    run_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,100}$")
    eligible_information_ids: list[str] = Field(default_factory=list)
    allow_web: bool = False

    @model_validator(mode="after")
    def reject_blank(self):
        has_information = bool(self.information.strip()) if isinstance(self.information, str) else bool(self.information.information)
        if not has_information and not self.instructions.strip() and not self.user_facts:
            raise ValueError("Supply information, instructions, or explicit user facts")
        if not isinstance(self.information, str):
            supplied_ids = {item.information_id for item in self.information.information if item.information_id}
            if not supplied_ids <= set(self.eligible_information_ids):
                raise ValueError("Provided information IDs must belong to the eligible source allowlist")
        return self


class NewsGenerationResponse(BaseModel):
    completeness: CompletenessResult
    article: NewsArticle | None
    run_id: str | None = None
    status: str = "completed"
    quality: dict[str, Any] | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    skills_used: list[dict[str, str]] = Field(default_factory=list)
    plan: list[dict[str, str]] = Field(default_factory=list)
    web_sources: list[dict[str, Any]] = Field(default_factory=list)
    guidance: str | None = None
    metrics: dict[str, float | int] = Field(default_factory=dict)
