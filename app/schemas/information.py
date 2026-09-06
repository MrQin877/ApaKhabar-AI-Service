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
