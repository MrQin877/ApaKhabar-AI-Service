from typing import Any, Literal

from pydantic import BaseModel, Field


InformationType = Literal[
    "Meeting",
    "Finance",
    "Event",
    "Health",
    "Announcement",
    "Project",
    "Emergency",
    "Education",
    "General",
]


class Evidence(BaseModel):
    source: str = Field(min_length=1)
    quote: str = Field(min_length=1)


class InformationItem(BaseModel):
    type: InformationType
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    labels: list[str]
    fields: dict[str, Any]
    evidence: list[Evidence]
    confidence: float = Field(ge=0, le=1)


class ExtractionResponse(BaseModel):
    information: list[InformationItem]


class ExtractionContext(BaseModel):
    mode: Literal["general", "targeted"] = "general"
    query: str | None = Field(default=None, max_length=2000)
    keywords: list[str] = Field(default_factory=list, max_length=20)

    def effective_query(self) -> str | None:
        query = " ".join((self.query or "").split())
        keywords = [" ".join(value.split()) for value in self.keywords if value.strip()]
        combined = " ".join(part for part in [query, " ".join(keywords)] if part)
        return combined or None
