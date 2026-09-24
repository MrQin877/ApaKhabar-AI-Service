# Unified AI Workspace

## Purpose

The workspace combines document extraction, information retrieval, and news writing in one assistant. Documents remain durable source files; extracted information becomes a moderator-approved library; news drafts retain their generation conversation and every revision.

## Application navigation

- **AI Assistant** (`/admin/ai-assistant`) is an independent, extensible assistant. Document extraction and news generation are its current capabilities; future capabilities can be added without placing the assistant under News.
- **Documents** (`/admin/documents`) is an independent source and extracted-information library.
- **News** (`/admin/news`) contains the news list, manual writing workflow, AI-produced drafts, and category administration.

Selecting **Use in AI Assistant** from Documents opens the independent assistant with that source preselected. Resuming an AI news draft from News restores its assistant session. Legacy `/admin/apakhabar-creator` links redirect to the corresponding new page.

## Runtime flow

1. The assistant classifies the message as conversation, extraction, library search, news generation, or news revision.
2. An extraction request is either `general` (discover all important information) or `targeted` (retrieve document chunks relevant to the user's query first).
3. Files are saved by Laravel's configured filesystem disk and processed by a durable queue job. Restarting the web server does not remove a queued database job.
4. Extracted information starts as `pending`. A moderator reviews its evidence and approves or rejects it.
5. Only approved information is embedded in the information vector collection and can be recommended by RAG.
6. RAG recommendations are displayed for moderator approval; they are never silently added to a publishable draft.
7. The first `generate_news` message creates a news session. Extraction-only conversation is not copied into the news history.
8. A generated or revised article creates a new immutable draft version and quality evaluation. Publication remains a moderator action.

## Database additions

### `intelligence_extraction_requests`

One row records one extraction instruction for one document.

| Column | Type | Purpose |
|---|---|---|
| `id` | bigint PK | Request identity |
| `document_id` | bigint FK | Source document |
| `requested_by` | bigint FK | User who requested extraction |
| `mode` | enum | `general` or `targeted` |
| `original_prompt` | text nullable | Exact user instruction |
| `normalized_query` | text nullable | Query supplied to retrieval/model |
| `keywords` | JSON | Target keywords |
| `model_name` | varchar nullable | Reproducibility metadata |
| `prompt_version` | varchar | Extraction prompt version |
| `status` | enum | pending, processing, completed, failed |
| `error_message` | text nullable | Recoverable processing error |
| `started_at`, `completed_at` | timestamp nullable | Job audit timing |

### Added to `intelligence_information`

| Column | Type | Purpose |
|---|---|---|
| `extraction_request_id` | bigint FK nullable | Extraction that produced the item |
| `review_status` | enum | pending, approved, rejected |
| `quality_score` | decimal nullable | Explainable extraction-quality estimate |
| `quality_breakdown` | JSON nullable | Evidence coverage, completeness, model confidence |
| `information_embedding_status` | enum | pending, ready, failed |
| `reviewed_by`, `reviewed_at` | FK/timestamp nullable | Moderator audit |

The extraction score is not factual ground-truth accuracy. It estimates whether the item is complete and evidence-backed. A labelled evaluation dataset is still required to report scientific accuracy, precision, recall, or F1.

### `intelligent_news_messages`

Stores the history that begins at the first news-generation request.

| Column | Type | Purpose |
|---|---|---|
| `session_id` | bigint FK | Conversation |
| `role` | enum | user, assistant, tool, system |
| `intent` | varchar nullable | generate, revise, clarification, etc. |
| `content` | longtext nullable | Visible message |
| `tool_name` | varchar nullable | Tool audit |
| `payload` | JSON nullable | Selected sources, answers, or structured result |
| `draft_version_id` | bigint FK nullable | Version produced by this message |

### `ai_quality_evaluations`

Stores the seven-dimension score separately from the article so the scoring method can evolve without rewriting old drafts.

| Column | Type | Purpose |
|---|---|---|
| `draft_id` | bigint FK | Evaluated draft |
| `draft_version_id` | bigint FK nullable | Exact evaluated version |
| `evaluation_version` | varchar | Scoring formula version |
| `evaluator_model` | varchar nullable | Evaluator identity |
| `overall_score` | decimal | Weighted quality score |
| `quality_label` | varchar | User-facing band |
| `publish_blocked` | boolean | Blocks unsafe/unsupported publication |
| `dimensions` | JSON | Accuracy, completeness, relevance, readability, structure, language, safety |
| `claim_checks` | JSON | Claim/evidence audit |
| `warnings` | JSON | Problems for moderator review |

### Added to `intelligent_news_draft_versions`

`revision_source` records manual or AI revision, and `revision_instruction` preserves the user's edit request.

## Storage and recovery

Set Laravel's filesystem disk to local storage during development and an S3-compatible disk in production. The database stores only the disk and object path, not the binary document. Run a persistent queue worker (`php artisan queue:work`) under Supervisor, systemd, or the cloud platform's worker service. Database-backed queued jobs survive application restarts; failed jobs can be retried with `php artisan queue:retry all`.

## Deployment order

1. Back up the database.
2. Deploy the Laravel and AI-service changes.
3. Run `php artisan migrate`.
4. Restart the queue worker so it loads the new job constructor.
5. Start FastAPI and verify Ollama plus the embedding model are available.
6. Upload one document, approve one extracted item, search for it, generate a draft, revise it, and verify two versions and their messages exist.
