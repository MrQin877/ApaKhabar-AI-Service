from typing import Any, Literal
from pydantic import BaseModel, Field


class KnowledgeItem(BaseModel):
    information_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    owner_id: str = Field(min_length=1)
    title: str
    summary: str
    labels: list[str] = Field(default_factory=list)
    fields: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, str]] = Field(default_factory=list)
    source: str
    review_status: Literal["approved"]
    is_active: Literal[True]
    archived: Literal[False]


class KnowledgeIndex(BaseModel):
    items: list[KnowledgeItem] = Field(min_length=1, max_length=1000)


class KnowledgeSearch(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    owner_id: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=30)
    information_ids: list[str]
