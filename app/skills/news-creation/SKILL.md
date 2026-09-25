---
name: news-creation
description: Orchestrate grounded Indonesian news creation from moderator-approved documentary evidence and explicitly user-provided facts.
---

# News Creation

Create a publishable draft only from approved sources and user-provided facts.

## Workflow

1. Classify the request as extraction, retrieval, generation, or revision.
2. Inspect the prompt, conversation state, selected documents, and approved information before choosing a tool.
3. Normalize newly uploaded documents and extract distinct Indonesian information items.
4. Index document chunks for retrieval. Treat retrieval results as recommendations only.
5. Wait for moderator approval before adding a recommended item to evidence.
6. Check approved evidence for required facts, source support, contradictions, and freshness.
7. Resolve subject identity, existence, or possible typo ambiguity before asking factual 5W questions. State the unsupported point explicitly and offer concrete intent choices.
8. If materially important facts are absent, ask one clarification round containing at most three short structured questions. Prefer 2-4 supported choices; use free text only when discrete choices are impossible.
9. After that one answer round, use reasonable disclosed defaults and continue. Never open another clarification round for the same request.
10. Mark answers as `user_provided`; never attribute them to a document.
11. Generate or revise the draft, then validate citations, language, structure, and quality before returning it.
12. Preserve source identifiers and report limitations in warnings.

## Observable Work Log

Emit short user-visible activity summaries for completed or active operations, such as request classification, source inspection, retrieval, evidence comparison, drafting, and quality validation. Include tool names and useful counts when available. Do not reveal private chain-of-thought, hidden deliberation, raw prompts, or secrets. Stream draft text separately from the work log.

## Invariants

- Never use unapproved retrieval results as generation evidence.
- Never interpret an editorial instruction as a fact.
- Never invent a missing name, date, location, amount, quotation, or event.
- Do not ask about low-stakes ambiguity; use a reasonable disclosed assumption.
- Use at most one clarification round per request and never repeat an answered question.
- Never ask what happened until the request establishes a real event or an explicit fictional/speculative mode.
- Never publish automatically; return a draft for moderator review.
- Keep documentary evidence distinguishable from user-provided facts.

The executable workflow is `app/agent/news_workflow.py`. Prompt details are in
`prompts/completeness.md` and `prompts/generation.md`.
