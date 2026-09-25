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
from app.services.rag_service import RagService
from evaluation.metrics import (
    expected_facts,
    extraction_facts,
    read_jsonl,
    score_extraction,
    score_news_rating,
    score_retrieval,
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


def evaluate_retrieval(dataset: Path, output: Path | None) -> dict:
    cases = read_jsonl(dataset)
    details = []
    rag = RagService()
    for case in cases:
        top_k = int(case.get("top_k", 5))
        results = rag.search(case["query"], top_k=top_k)
        ranked_ids = [result.document_id for result in results]
        metrics = score_retrieval(set(case["relevant_document_ids"]), ranked_ids)
        details.append({
            "id": case["id"],
            "query": case["query"],
            "top_k": top_k,
            "metrics": metrics,
            "results": [result.model_dump() for result in results],
        })

    count = len(details)
    hit_rate = sum(item["metrics"]["hit"] for item in details) / count if count else 0
    mean_recall = (
        sum(item["metrics"]["recall"] for item in details) / count if count else 0
    )
    mrr = (
        sum(item["metrics"]["reciprocal_rank"] for item in details) / count
        if count
        else 0
    )
    report = {
        "evaluation": "rag-retrieval",
        "cases": count,
        "aggregate": {
            "hit_rate_at_k": round(hit_rate, 4),
            "mean_recall_at_k": round(mean_recall, 4),
            "mrr": round(mrr, 4),
            "target_mean_recall_at_k": 0.90,
            "passed": bool(count) and mean_recall >= 0.90,
        },
        "details": details,
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("extraction", "news", "retrieval"):
        command = subparsers.add_parser(name)
        command.add_argument("--dataset", type=Path, required=True)
        command.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.dataset.is_file():
        parser.error(
            f"dataset file not found: {args.dataset}. "
            "Copy and edit a template from evaluation/data first."
        )
    if args.command == "extraction":
        report = evaluate_extraction(args.dataset, args.output)
    elif args.command == "news":
        report = evaluate_news(args.dataset, args.output)
    else:
        report = evaluate_retrieval(args.dataset, args.output)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
