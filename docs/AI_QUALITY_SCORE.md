# AI Quality Score

ApaKhabar evaluates every successfully generated news draft against the approved
evidence used to create it. The result is an **automated estimate for moderator
support**, not a measured probability that the article is correct.

## Formula

```text
Quality Score =
  (Accuracy     × 30%) +
  (Completeness × 20%) +
  (Relevance    × 15%) +
  (Readability  × 10%) +
  (Structure    × 10%) +
  (Language     × 10%) +
  (Safety       ×  5%)
```

The evaluator model returns component judgements and claim-to-evidence checks.
Python application code calculates the weighted score, label, and blocking rules.
The model cannot provide or override the final arithmetic.

## Meaning of each dimension

| Dimension | Operational meaning |
| --- | --- |
| Accuracy | Estimated factual grounding of article claims in approved evidence |
| Completeness | Coverage of applicable 5W1H details that exist in the evidence |
| Relevance | Alignment with the moderator's request and selected evidence |
| Readability | Clarity, flow, sentence quality, and lack of repetition |
| Structure | Headline, lead, body, news ordering, category, and attribution |
| Language | Natural formal Indonesian and consistent terminology/formatting |
| Safety | Defamation, privacy, hate, graphic/sexual, dangerous, and inflammatory risks |

## Labels

| Score | Label |
| --- | --- |
| 90–100 | excellent |
| 80–89.99 | good |
| 70–79.99 | needs_review |
| 50–69.99 | weak |
| 0–49.99 | not_ready |

Publication is blocked when accuracy or safety is below 70, or when any claim is
classified as unsupported or contradicted. A moderator must still review drafts
that are not automatically blocked.

## API

`POST /news/generate` now returns an optional `quality` object with the article.
If evaluation is temporarily unavailable, the article is retained, `quality` is
`null`, and a manual-review warning is added.

Use `POST /news/evaluate-quality` to evaluate a saved or moderator-edited draft:

```json
{
  "article": {
    "headline": "...",
    "subheadline": null,
    "lead": "...",
    "body": ["..."],
    "summary": "...",
    "labels": ["banjir"],
    "language": "id",
    "sources_used": ["laporan.pdf, page=2"],
    "warnings": [],
    "category": "Bencana"
  },
  "evidence": "[source: laporan.pdf, page=2] ...",
  "user_request": "Fokus pada dampak kepada warga."
}
```

The Laravel application should save the complete quality result against a draft
version, including `evaluation_version` and `evaluator_model`. Re-evaluate after
the moderator edits or regenerates the article.

## Research accuracy remains separate

The quality score must be calibrated against human moderator ratings. Formal
system accuracy is still measured on a held-out labelled dataset using extraction
precision/recall/F1, claim factual consistency, hallucination rate, and editorial
acceptance. The UI should display the supplied disclaimer and must not present a
quality score of 88 as “88% factually accurate.”
