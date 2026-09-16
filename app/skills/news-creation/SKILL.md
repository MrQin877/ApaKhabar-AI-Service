---
name: news-creation
description: Orchestrate grounded Indonesian news creation from moderator-approved documentary evidence and explicitly user-provided facts.
---

# News Creation

Create a publishable draft only from approved sources and user-provided facts.

## Workflow

1. Normalize newly uploaded documents and extract distinct Indonesian information items.
2. Index document chunks for retrieval. Retrieval results are recommendations only.
3. Wait for moderator approval before adding a recommended item to evidence.
4. Check approved evidence for required facts and contradictions.
5. Resolve subject identity, existence, or possible typo ambiguity before asking factual 5W questions. State the unsupported/unclear point explicitly and offer concrete intent choices.
6. When materially important facts are absent, ask at most three short structured questions in Indonesian and wait for answers. Prefer 2-4 supported choices; use free text only when real discrete choices are impossible.
7. Mark answers as `user_provided`; never attribute them to a document.
8. Generate a draft only when completeness status is `ready`.
9. Preserve source identifiers and report limitations in warnings.

## Invariants

- Never use unapproved retrieval results as generation evidence.
- Never interpret an editorial instruction as a fact.
- Never invent a missing name, date, location, amount, quotation, or event.
- Do not ask about low-stakes ambiguity; use a reasonable disclosed assumption.
- Ask one UI-visible question at a time and never repeat an answered question.
- Never ask what happened until the request establishes a real event or an explicit fictional/speculative mode.
- Never publish automatically; return a draft for moderator review.
- Keep documentary evidence distinguishable from user-provided facts.

The executable workflow is `app/agent/news_workflow.py`. Prompt details are in
`prompts/completeness.md` and `prompts/generation.md`.
