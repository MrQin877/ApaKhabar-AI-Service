import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


def normalize_value(value: Any) -> str:
    """Normalize a value for reproducible, conservative exact matching."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return f"{value:g}"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    text = str(value).casefold().strip()
    return re.sub(r"\s+", " ", text)


def _leaf_facts(value: Any, field: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _leaf_facts(child, str(key).casefold())
    elif isinstance(value, list):
        for child in value:
            yield from _leaf_facts(child, field)
    elif value is not None:
        yield field.casefold(), normalize_value(value)


def extraction_facts(response: dict[str, Any]) -> Counter[tuple[str, str]]:
    """Convert an extraction response into field/value pairs for scoring."""
    facts: Counter[tuple[str, str]] = Counter()
    for item in response.get("information", []):
        # Title and summary are free-form text and need a separate human/semantic
        # rubric; exact matching them would unfairly reject valid paraphrases.
        for key in ("type",):
            if item.get(key) is not None:
                facts[(key, normalize_value(item[key]))] += 1
        for label in item.get("labels", []):
            facts[("label", normalize_value(label))] += 1
        for fact in _leaf_facts(item.get("fields", {})):
            facts[fact] += 1
    return facts


def expected_facts(records: list[dict[str, Any]]) -> Counter[tuple[str, str]]:
    facts: Counter[tuple[str, str]] = Counter()
    for record in records:
        facts[(record["field"].casefold(), normalize_value(record["value"]))] += 1
    return facts


@dataclass(frozen=True)
class ExtractionScore:
    true_positive: int
    false_positive: int
    false_negative: int

    @property
    def precision(self) -> float:
        denominator = self.true_positive + self.false_positive
        return self.true_positive / denominator if denominator else 0.0

    @property
    def recall(self) -> float:
        denominator = self.true_positive + self.false_negative
        return self.true_positive / denominator if denominator else 0.0

    @property
    def f1(self) -> float:
        denominator = self.precision + self.recall
        return 2 * self.precision * self.recall / denominator if denominator else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "true_positive": self.true_positive,
            "false_positive": self.false_positive,
            "false_negative": self.false_negative,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "target_f1": 0.95,
            "passed": self.f1 >= 0.95,
        }


def score_extraction(expected: Counter, actual: Counter) -> ExtractionScore:
    true_positive = sum((expected & actual).values())
    return ExtractionScore(
        true_positive=true_positive,
        false_positive=sum(actual.values()) - true_positive,
        false_negative=sum(expected.values()) - true_positive,
    )


NEWS_WEIGHTS = {
    "factual_grounding": 40,
    "fact_coverage": 25,
    "structure": 15,
    "language_style": 10,
    "source_attribution": 10,
}


def score_news_rating(rating: dict[str, Any]) -> dict[str, Any]:
    weighted_score = 0.0
    for criterion, weight in NEWS_WEIGHTS.items():
        value = float(rating[criterion])
        if not 0 <= value <= 5:
            raise ValueError(f"{criterion} must be between 0 and 5")
        weighted_score += (value / 5) * weight
    critical = bool(rating.get("critical_hallucination", False))
    return {
        "score": round(weighted_score, 2),
        "critical_hallucination": critical,
        "passed": weighted_score >= 80 and not critical,
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on {path}:{line_number}") from exc
    return records
