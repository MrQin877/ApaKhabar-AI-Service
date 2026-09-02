from typing import Literal

from pydantic import BaseModel, Field, model_validator


NewsLanguage = Literal["en", "ms"]


class MissingInformation(BaseModel):
    field: str
    importance: Literal["required", "recommended"]
    question: str


class CompletenessResult(BaseModel):
    status: Literal["ready", "needs_information", "has_conflicts"]
    missing: list[MissingInformation]
    conflicts: list[str]
    known_facts: list[str]


class NewsRequest(BaseModel):
    information: str = Field(min_length=1)
    language: NewsLanguage = "en"
    tone: str = Field(default="formal", min_length=1, max_length=50)

    @model_validator(mode="after")
    def reject_blank_information(self):
        if not self.information.strip():
            raise ValueError("Information cannot be blank.")
        return self


class NewsArticle(BaseModel):
    headline: str = Field(min_length=1)
    subheadline: str | None
    lead: str = Field(min_length=1)
    body: list[str] = Field(min_length=1)
    summary: str = Field(min_length=1)
    labels: list[str]
    language: NewsLanguage
    sources_used: list[str]
    warnings: list[str]


class NewsGenerationResponse(BaseModel):
    completeness: CompletenessResult
    article: NewsArticle | None
