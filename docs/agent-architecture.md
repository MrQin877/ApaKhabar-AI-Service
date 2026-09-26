# Agent architecture

## Ownership

Laravel remains the source of truth for user authorization, source review, document lifecycle, active categories, drafts, and publication. It sends the owner's currently eligible information IDs with every new or resumed run. Python never changes source review or publication status.

`app/workflows/editorial.py` defines the LangGraph state and nodes. `app/services/agent_service.py` owns checkpointing, run leases, event persistence, and request idempotency. `app/providers/models.py` isolates generation and embedding backends. `app/tools/editorial.py` is a finite action dispatcher; there is no arbitrary Python, shell, filesystem, or SQL execution tool. `app/skills/registry.py` implements the Agent Skills directory format.

## Control flow

`plan → research loop → web approval → completeness → clarification → completeness → write → reflect → revise/write or finish`

Research plans describe bounded subtasks. The executor adapts tool choice and query using previous observations. Writing and review are mandatory application stages, so the model cannot plan them away. Direct supported-fact requests skip unnecessary research. Summarization and extraction have focused paths rather than a full editorial research loop.

ReAct uses validated action JSON instead of depending on model-specific native function calling. This provides tool selection/action/observation cycles for local models with inconsistent tool-call formatting. Native ToolNode is not necessary for this dispatcher. Tool errors become observations; malformed actions are repaired at most once and otherwise fail. Maximum tool calls, revisions, graph recursion, node-entry elapsed-time checks, and HTTP timeouts bound execution. An in-flight call can overrun the graph's elapsed-time budget until its provider timeout; this is not a hard real-time cancellation system.

## Skills

Metadata is available for discovery, but skill bodies enter prompts only when activated. Extraction uses document-extraction, research uses evidence-research, generation uses indonesian-news-writing, revision uses draft-revision, and critique uses editorial-review. Format-specific references load on demand. Tool-access rules cannot be overridden by a skill file. Uploaded documents are never scanned as skills. Main skill and loaded resource hashes appear in the run output/events. Changing active skill content requires a fresh run.

## Evidence and approval

Only approved information goes into the dedicated collection. Its identity includes provider, model, and configured embedding dimensions. All searches constrain owner, approval, active status, archive status, and any requested allowlist. An explicitly empty allowlist returns nothing. Raw document search is unavailable in agent mode. The legacy collection is isolated for rollback.

Plain strings and structured information are trusted-backend supplied facts. Prompt assertions are extracted as verbatim quotes, distinguished from writing instructions. They remain user assertions, not independently verified truth. Source existence checks and quote-location matching catch structural errors; semantic factual correctness still needs model and human review.

Web results are pending until the graph is resumed with their source IDs. No pending snippets enter the draft evidence map. Source approval is separate from the single allowed clarification round. Laravel maps approve/reject choices to source IDs and refreshes documentary eligibility. The web adapter only supplies recommendations; no automated browsing or publication occurs.

## Durability

Thread keys are hashed from owner and run ID. Checkpoints contain JSON-compatible state. Events live in a companion SQLite database and can be polled during inference. Laravel proxies progress through an authenticated, ownership-checked route and persists completed event histories and skill/plan metadata.

A request ID is bound to an input hash. A completed or paused retry returns its existing response. Resuming uses the checkpoint instead of replaying the original prompt. Execution leases reject overlapping requests. Failures resume at a checkpoint boundary after a retry with the same request ID; an uncheckpointed call may repeat. Python performs no editorial database mutation in graph nodes.

SQLite is intended for this local deployment. A multi-host deployment needs shared checkpoint storage and a distributed execution lease. Model outputs and evidence in checkpoints are application data; protect and retain these files according to the same policy as conversation records.

## Evaluation and operational checks

Automated acceptance tests cover typed provider responses, bounded schema repair, tool execution, owner and allowlist isolation, extraction quote locations, source approval, revocation on resume, one-round clarification, best-draft reflection, idempotence, and skill resource boundaries. Laravel tests cover request contracts, event persistence, resume, and rejection of pending information. TypeScript checks cover frontend integration.

The fixed Indonesian examples in `evaluation/editorial_cases.json` exercise complete announcements, missing details, conflicting dates, source-text injection, and timeless profiles. `scripts/evaluate_editorial.py` runs them through agent or fixed-pipeline mode and saves outputs, elapsed time, and model calls. Human evaluation should record unsupported claim rate, supported fact coverage, relevance, Indonesian language quality, and appropriate abstention. Compare the modes on the same model/settings. The fixture is an initial regression set, not a statistically sufficient accuracy benchmark.

Local verification during restructuring: unit tests use scripted models, and the installed EmbeddingGemma adapter was exercised locally. Live generation requires the separate llama.cpp server; its absence is not a successful model-compatibility or article-quality evaluation.

## Live progress and latency

Model calls record `stage_started`, `stage_completed` (with duration), or `stage_failed` before/after inference. These are operational steps, not private model reasoning. Sources already supplied in full skip the evidence planning/tool loop unless web discovery is enabled or eligible sources are missing. Reflection stops on a non-improving revision while preserving the best draft and unresolved warnings; improving revisions still obey the configured budget.

The Laravel chat submits `POST /admin/ai-assistant/generate-async` and immediately receives HTTP 202. `GenerateIntelligentNews` runs `NewsGenerationService` on the `generation` queue; the legacy synchronous endpoint delegates to the same service. The authenticated progress endpoint combines queue state with Python's persisted events. A terminal response is returned only after Laravel saves the draft or clarification, then the browser navigates to it. Request IDs prevent duplicate dispatch; a cache lock prevents duplicate execution. Progress survives a page reload in the same browser tab using a user/session-scoped sessionStorage key. Local queue status is retained for 24 hours; shared cache storage is required across multiple hosts.

Document jobs pass an opaque UUID to batch extraction. `/documents/progress/{uuid}` exposes reading/OCR and actual completed/total extraction chunks; Laravel enforces document ownership before proxying it. Progress records contain no document text and expire after 24 hours as new records are written. A successful extraction with zero results completes rather than repeating model calls. Per-file extraction failures are surfaced directly; transport failures retain bounded queue retries.

After updating both repositories, restart FastAPI and run `composer dev` in the Laravel repository (restart an existing dev command). It now starts separate document and generation workers. For a process manager, run both:

```sh
php artisan queue:work --queue=documents,default --tries=5 --timeout=1250
php artisan queue:work --queue=generation --tries=1 --timeout=1250
```

Use an asynchronous Laravel queue, `APAKHABAR_AI_TIMEOUT=1200`, and queue `retry_after=1500` (including environment overrides such as `DB_QUEUE_RETRY_AFTER`). HTTP calls are capped at 1200 seconds, jobs at 1250 seconds, and overlap locks at 1300 seconds. Keep retry_after larger than job timeout to avoid duplicate processing. Clear cached configuration after changing these values, and restart workers. Start the configured model server separately. A queued display means a job is waiting for a worker; disconnected progress means polling could not reach the service, not proof that inference stopped.

Verification: Python tests exercise progress visibility during inference and chunk extraction, redundant-research avoidance, revision stopping and safety flags. Laravel tests exercise immediate queue submission, polling ownership, terminal outcomes, duplicate dispatch/execution, and empty extraction. Real latency still depends on document length, OCR, model speed, and concurrent requests; tests with scripted models are not a speed benchmark.
