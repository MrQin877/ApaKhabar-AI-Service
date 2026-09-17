from typing import ClassVar, Literal

from pydantic import BaseModel, Field, computed_field, model_validator

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


class QualityDimension(BaseModel):
    score: float = Field(ge=0, le=100)
    explanation: str = Field(min_length=1, max_length=1000)
    issues: list[str] = Field(default_factory=list, max_length=20)


class NewsQualityDimensions(BaseModel):
    accuracy: QualityDimension
    completeness: QualityDimension
    relevance: QualityDimension
    readability: QualityDimension
    structure: QualityDimension
    language: QualityDimension
    safety: QualityDimension


class ClaimCheck(BaseModel):
    claim: str = Field(min_length=1, max_length=2000)
    status: Literal["supported", "partially_supported", "unsupported", "contradicted"]
    source: str | None = Field(default=None, max_length=1000)
    reason: str = Field(min_length=1, max_length=1000)


class NewsQualityAssessment(BaseModel):
    """Raw evaluator output. Weighted arithmetic is deliberately excluded."""

    dimensions: NewsQualityDimensions
    claim_checks: list[ClaimCheck] = Field(default_factory=list, max_length=100)
    warnings: list[str] = Field(default_factory=list, max_length=30)


class NewsQualityEvaluation(NewsQualityAssessment):
    estimated: Literal[True] = True
    evaluation_version: Literal["news-quality-v1"] = "news-quality-v1"
    evaluator_model: str
    publish_blocked: bool

    WEIGHTS: ClassVar[dict[str, float]] = {
        "accuracy": 0.30,
        "completeness": 0.20,
        "relevance": 0.15,
        "readability": 0.10,
        "structure": 0.10,
        "language": 0.10,
        "safety": 0.05,
    }

    @computed_field
    @property
    def quality_score(self) -> float:
        total = sum(
            getattr(self.dimensions, name).score * weight
            for name, weight in self.WEIGHTS.items()
        )
        return round(total, 2)

    @computed_field
    @property
    def weights(self) -> dict[str, float]:
        return self.WEIGHTS.copy()

    @computed_field
    @property
    def weighted_scores(self) -> dict[str, float]:
        return {
            name: round(getattr(self.dimensions, name).score * weight, 2)
            for name, weight in self.WEIGHTS.items()
        }

    @computed_field
    @property
    def quality_label(self) -> Literal[
        "excellent", "good", "needs_review", "weak", "not_ready"
    ]:
        score = self.quality_score
        if score >= 90:
            return "excellent"
        if score >= 80:
            return "good"
        if score >= 70:
            return "needs_review"
        if score >= 50:
            return "weak"
        return "not_ready"

    @computed_field
    @property
    def disclaimer(self) -> str:
        return (
            "This is an automated quality estimate, not a guarantee of factual "
            "accuracy. Moderator review is required."
        )

    @classmethod
    def from_assessment(
        cls,
        assessment: NewsQualityAssessment,
        evaluator_model: str,
    ) -> "NewsQualityEvaluation":
        claim_block = any(
            item.status in {"unsupported", "contradicted"}
            for item in assessment.claim_checks
        )
        dimensions = assessment.dimensions
        if assessment.claim_checks:
            claim_values = {
                "supported": 1.0,
                "partially_supported": 0.5,
                "unsupported": 0.0,
                "contradicted": 0.0,
            }
            grounded_accuracy = round(
                sum(claim_values[item.status] for item in assessment.claim_checks)
                / len(assessment.claim_checks)
                * 100,
                2,
            )
            dimensions = dimensions.model_copy(
                update={
                    "accuracy": dimensions.accuracy.model_copy(
                        update={"score": grounded_accuracy}
                    )
                }
            )
        publish_blocked = (
            dimensions.accuracy.score < 70
            or dimensions.safety.score < 70
            or claim_block
        )
        return cls(
            **assessment.model_dump(exclude={"dimensions"}),
            dimensions=dimensions,
            evaluator_model=evaluator_model,
            publish_blocked=publish_blocked,
        )


class NewsGenerationResponse(BaseModel):
    completeness: CompletenessResult
    article: NewsArticle | None
    tool_call: AskUserChoiceToolCall | None = None
    tool_calls: list[AskUserChoiceToolCall] = Field(default_factory=list, max_length=3)
    web_sources: list[WebSearchResult] = Field(default_factory=list)
    guidance: str | None = None
    quality: NewsQualityEvaluation | None = None
