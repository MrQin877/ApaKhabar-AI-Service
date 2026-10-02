from app.schemas.news import HistoricalSource
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class PlanStep(BaseModel):
    task: str = Field(min_length=1, max_length=500)
    skill: str


class ExecutionPlan(BaseModel):
    steps: list[PlanStep] = Field(min_length=1, max_length=6)


class ToolAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["search_information", "inspect_source", "web_search", "read_skill", "finish"]
    query: str = Field(default="", max_length=2000)
    source_id: str = ""
    skill: str = ""
    resource: str = ""


class ClaimCheck(BaseModel):
    claim: str
    supported: bool
    source_ids: list[str] = Field(default_factory=list)
    issue: str = ""


class Dimensions(BaseModel):
    accuracy: float = Field(ge=0, le=100)
    completeness: float = Field(ge=0, le=100)
    relevance: float = Field(ge=0, le=100)
    readability: float = Field(ge=0, le=100)
    structure: float = Field(ge=0, le=100)
    language: float = Field(ge=0, le=100)
    safety: float = Field(ge=0, le=100)


class Reflection(BaseModel):
    dimensions: Dimensions
    claim_checks: list[ClaimCheck]
    improvements: list[str]
    warnings: list[str]
    needs_revision: bool
    evidence_gaps: list[str] = Field(default_factory=list, max_length=3, description="Material missing evidence that requires additional research, not wording changes or facts already in the sources.")


class ResumeRequest(BaseModel):
    owner_id: str = Field(min_length=1)
    answers: list[dict[str, str]] = Field(default_factory=list)
    approved_web_source_ids: list[str] = Field(default_factory=list)
    historical_sources: list[HistoricalSource] = Field(default_factory=list, max_length=3)
    # The trusted Laravel caller refreshes eligibility from its database on resume.
    eligible_information_ids: list[str] = Field(default_factory=list)


class RequestUnderstanding(BaseModel):
    content_format: Literal["news_article", "announcement", "event_report", "historical_profile", "data_report", "regulation_summary", "public_awareness"]
    explicit_fact_quotes: list[str] = Field(default_factory=list, max_length=20)
