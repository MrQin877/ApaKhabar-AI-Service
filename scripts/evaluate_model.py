#!/usr/bin/env python3
"""Run extraction evaluation or summarize human news ratings."""

import argparse
import json
import sys
from pathlib import Path

# Allow the documented `python scripts/evaluate_model.py ...` invocation.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.ai_service import OllamaService
from evaluation.metrics import (
    expected_facts,
    extraction_facts,
    read_jsonl,
    score_extraction,
    score_news_rating,
)


def evaluate_extraction(dataset: Path, output: Path | None) -> dict:
    cases = read_jsonl(dataset)
    expected_total = expected_facts([])
    actual_total = expected_facts([])
    details = []
    for case in cases:
        actual_response = OllamaService.extract_information(case["input"])
        expected = expected_facts(case["expected_facts"])
        actual = extraction_facts(actual_response)
        expected_total.update(expected)
        actual_total.update(actual)
        details.append({
            "id": case["id"],
            "metrics": score_extraction(expected, actual).as_dict(),
            "actual": actual_response,
        })

    report = {
        "evaluation": "data-to-information",
        "cases": len(cases),
        "aggregate": score_extraction(expected_total, actual_total).as_dict(),
        "details": details,
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def evaluate_news(dataset: Path, output: Path | None) -> dict:
    ratings = read_jsonl(dataset)
    details = [{"id": row["id"], **score_news_rating(row)} for row in ratings]
    passed = sum(item["passed"] for item in details)
    report = {
        "evaluation": "information-to-news",
        "articles": len(details),
        "passed_articles": passed,
        "acceptance_rate": round(passed / len(details), 4) if details else 0.0,
        "target_acceptance_rate": 0.80,
        "passed": bool(details) and passed / len(details) >= 0.80,
        "details": details,
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("extraction", "news"):
        command = subparsers.add_parser(name)
        command.add_argument("--dataset", type=Path, required=True)
        command.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = (
        evaluate_extraction(args.dataset, args.output)
        if args.command == "extraction"
        else evaluate_news(args.dataset, args.output)
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
