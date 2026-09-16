from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.information import ExtractionResponse
from app.schemas.tools import AskUserChoiceToolCall, WebSearchResult


NewsLanguage = Literal["id"]


class MissingInformation(BaseModel):
    field: str
    importance: Literal["required", "recommended"]
    kind: Literal[
        "unverified_subject",
        "possible_typo",
        "format_choice",
        "missing_fact",
        "conflict",
    ] = "missing_fact"
    question: str
    reason: str | None = None
    options: list[str] = Field(default_factory=list, max_length=50)
    selection_type: Literal["single", "multi", "ranked", "text"] = "text"


class UserProvidedFact(BaseModel):
    field: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=2000)


class CompletenessResult(BaseModel):
    status: Literal["ready", "needs_information", "has_conflicts"]
    missing: list[MissingInformation] = Field(max_length=3)
    conflicts: list[str]
    known_facts: list[str]


class NewsRequest(BaseModel):
    information: str | ExtractionResponse
    language: NewsLanguage = "id"
    tone: str = Field(default="formal", min_length=1, max_length=50)
    instructions: str | None = Field(default=None, max_length=2000)
    user_facts: list[UserProvidedFact] = Field(default_factory=list, max_length=30)
    clarification_completed: bool = False
    available_categories: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def reject_blank_information(self):
        if isinstance(self.information, str) and not self.information.strip():
            raise ValueError("Information cannot be blank.")
        if (
            isinstance(self.information, ExtractionResponse)
            and not self.information.information
            and not self.user_facts
            and not (self.instructions and self.instructions.strip())
        ):
            raise ValueError("Extracted information cannot be empty.")
        return self

    def information_text(self) -> str:
        """Return either request form as grounded model input."""
        if isinstance(self.information, str):
            evidence = self.information
        else:
            evidence = self.information.model_dump_json(indent=2)
            if not self.information.information:
                evidence = "NO APPROVED FACTUAL EVIDENCE HAS BEEN PROVIDED."
        if not self.user_facts:
            return evidence
        facts = "\n".join(
            f"[user_provided: {fact.field}] {fact.value}" for fact in self.user_facts
        )
        return f"{evidence}\n\nEXPLICIT USER-PROVIDED FACTS:\n{facts}"


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
    category: str | None = None


class NewsGenerationResponse(BaseModel):
    completeness: CompletenessResult
    article: NewsArticle | None
    tool_call: AskUserChoiceToolCall | None = None
    tool_calls: list[AskUserChoiceToolCall] = Field(default_factory=list, max_length=3)
    web_sources: list[WebSearchResult] = Field(default_factory=list)
    guidance: str | None = None
