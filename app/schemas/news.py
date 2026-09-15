from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.information import ExtractionResponse


NewsLanguage = Literal["id"]


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
    information: str | ExtractionResponse
    language: NewsLanguage = "id"
    tone: str = Field(default="formal", min_length=1, max_length=50)

    @model_validator(mode="after")
    def reject_blank_information(self):
        if isinstance(self.information, str) and not self.information.strip():
            raise ValueError("Information cannot be blank.")
        if isinstance(self.information, ExtractionResponse) and not self.information.information:
            raise ValueError("Extracted information cannot be empty.")
        return self

    def information_text(self) -> str:
        """Return either request form as grounded model input."""
        if isinstance(self.information, str):
            return self.information
        return self.information.model_dump_json(indent=2)


class NewsArticle(BaseModel):
    headline: str = Field(min_length=1)
    subheadline: str | None
    lead: str = Field(min_length=1)
    body: list[str] = Field(min_length=1)
    summary: str = Field(min_length=1)
    labels: list[str]
    language: NewsLanguage = "id"
    sources_used: list[str]
    warnings: list[str]


class NewsGenerationResponse(BaseModel):
    completeness: CompletenessResult
    article: NewsArticle | None
