## Setup & Configuration

### Prerequisites
- Python 3.10+
- `llama.cpp` server (or Ollama) running locally for generation.
- (Optional) `Tesseract OCR` for extracting text from images/PDFs.

### Installation
1. Clone the repository and navigate to the root directory.
2. Create and activate a Python virtual environment:
   ```sh
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   pip install -r requirements-embedding.txt
   ```

### Configuration (.env)
Copy `.env.example` to `.env` and adjust the variables.
```sh
cp .env.example .env
```
Key configurations include:
- **`AI_PROVIDER`**: Set to `llama_cpp` (default) or `ollama`.
- **`LLAMA_CPP_BASE_URL`**: URL to your local LLM (e.g., `http://127.0.0.1:8080/v1`).
- **`EMBEDDING_PROVIDER`**: Default is `embedding_gemma`. Requires local HF model caching.
- **`APAKHABAR_AI_SERVICE_TOKEN`**: Must match the token in your Laravel `.env` file to authorize API calls.

### Databases (Agent SQLite & ChromaDB)
The service automatically initializes its databases upon startup based on the `.env` paths:
- **Agent Checkpoints (SQLite)**: Automatically created at `./data/agent/checkpoints.sqlite`.
- **Vector Search (ChromaDB)**: Automatically created at `./data/chroma`. No separate ChromaDB server installation is required (runs in embedded mode).

Ensure the `data/` directory is writable.

### Running the Server
Start the FastAPI service using Uvicorn:
```sh
uvicorn app.main:app --host 127.0.0.1 --port 8001
```
The API documentation will be available at `http://127.0.0.1:8001/docs`.

---
# ApaKhabar AI Service

A local-first editorial service built with FastAPI, LangGraph, Pydantic, and Chroma. It combines **Plan-and-Execute**, **ReAct**, **Reflection**, and **Agent Skills** to turn approved evidence into Indonesian drafts. Laravel owns users, files, source approval, conversations, draft versions, categories, and publication. Python owns extraction, retrieval, model execution, and durable graph checkpoints.

## Setup

Use Python 3.12 or newer. Use `.venv` for the local environment, including the embedding model dependencies.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-embedding.txt  # only for local EmbeddingGemma
cp .env.example .env                     # only for a new installation
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Keep an existing `.env`; the implementation reads the existing `AI_PROVIDER`, `LLAMA_CPP_*`, and `EMBEDDING_*` settings. Start your llama.cpp server separately with the configured model alias and URL. The service does not download or start generation models. Local EmbeddingGemma loads an already cached model through Sentence Transformers with `local_files_only=True`; provision the model separately. Alternatively use an embedding HTTP server or Ollama.

For image and scanned-PDF OCR, install Tesseract and its language data. Set `OCR_LANGUAGE=ind+eng` for Indonesian/English documents if both language packs are installed. Without OCR support, image-only inputs fail with an explicit error. DOCX, XLSX/XLSM, CSV, TXT, and text PDFs do not require OCR. Legacy binary DOC/XLS formats are not supported.

Configure the **same nonempty** `APAKHABAR_AI_SERVICE_TOKEN` in Laravel and Python for a shared deployment. Laravel supplies `X-ApaKhabar-Service-Token`; never expose this token to the browser. Owner IDs and approval assertions are accepted only from this trusted backend. An empty token is for isolated local development. Python is not a public end-user authentication service.

Laravel settings:

```dotenv
APAKHABAR_AI_URL=http://127.0.0.1:8001
APAKHABAR_AI_TIMEOUT=1200
APAKHABAR_AI_WEB_DISCOVERY=false
```

The web frontend uses Laravel's authenticated progress proxy. Run a concurrent PHP server/worker setup for live polling; a single PHP development worker may queue polling behind generation. Generation is synchronous per request; it can take several model calls. Laravel's document queue continues to handle uploads.

## Editorial workflow

1. Validate the request and identify explicit user facts and requested format.
2. Plan up to three research tasks when approved-library retrieval or optional web discovery is available.
3. Execute research through a bounded ReAct loop: choose a typed action, execute an allowlisted tool, inspect observations, and adapt or finish.
4. Pause for moderator approval of web recommendations. Rejected web results are never drafting evidence.
5. Check completeness and conflicts. Pause for at most one clarification round.
6. Write or revise a draft using approved evidence and explicit user facts.
7. Reflect against the evidence and revise at most twice. Retain the best reviewed candidate.
8. Return the draft, sources, findings, weighted quality score, actual events, skill hashes, and execution metrics. Laravel saves a draft version; publication remains a human action.

No sufficient facts after clarification produces `insufficient_evidence`, not an invented article. Scores are model estimates, not measured accuracy. Source IDs, category membership, tool schemas, access scope, and loop bounds also have deterministic checks.

## Agent Skills

Five bundled skills live under `skills/`:

- `document-extraction`
- `evidence-research`
- `indonesian-news-writing`
- `editorial-review`
- `draft-revision`

Each has standard YAML `name` and `description` frontmatter in `SKILL.md`, plus optional Markdown references. The registry exposes metadata for discovery, activates instructions at the relevant workflow stage, and reads references on demand. SHA-256 hashes identify the exact content used. Files must remain within the configured skill root; arbitrary script execution is not supported. Only maintained application skills belong here, never uploaded documents.

Skills supply procedures; Python code enforces source approval, ownership, limits, and available operations. To change behavior, edit the relevant skill and restart the service. Start a new run after changing a skill used by a paused run; version mismatches fail rather than silently mixing instructions.

## API

All non-health endpoints require the service header when configured. Swagger is at `/docs` (also protected when a token is configured).

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Lightweight process health |
| `GET /health/models` | Explicit structured-generation capability probe (one model call, with at most one schema repair) |
| `GET /agent/skills` | Skill metadata and hashes |
| `POST /news/generate` | Laravel-compatible agent generation |
| `POST /agent/runs` | Start an editorial run |
| `GET /agent/runs/{run_id}?owner_id=...` | Run state and persisted progress events |
| `POST /agent/runs/{run_id}/resume` | Resume clarification or web-source approval |
| `POST /documents/upload` | Normalize a document |
| `POST /documents/extract-information` | Extract a single document |
| `POST /documents/batch-extract` | Multipart `files`, `extraction_mode`, `extraction_query`, `keywords_json` |
| `POST /extract-information` | Extract plain text |
| `POST /summarize` | Direct summary without agent overhead |
| `POST /rag/information/index` | Index explicitly approved, active, non-archived records |
| `POST /rag/information/search` | Owner- and eligibility-filtered approved knowledge search |
| `DELETE /rag/information/{id}?owner_id=...` | Remove approved knowledge |

Generation accepts either a string of supplied facts or Laravel's `information: {information: [...]}` object. Additional fields include `owner_id`, `session_id`, `run_id`, `eligible_information_ids`, `instructions`, `user_facts`, `language`, `tone`, `content_format`, `current_draft`, `available_categories`, `default_category`, `clarification_completed`, and `allow_web`.

```json
{
  "run_id": "example-001",
  "owner_id": "7",
  "information": "Desa Makmur mengumumkan lokakarya komputer untuk 30 peserta di balai desa pada 20 Oktober 2026.",
  "instructions": "Buat pengumuman singkat.",
  "language": "id",
  "available_categories": ["Pendidikan", "Lainnya"],
  "default_category": "Lainnya"
}
```

For library research, pass the currently eligible `eligible_information_ids` determined by Laravel. An empty list means **no library access**, never all records. Provided structured information with stable IDs is also checked against that allowlist. The search API requires `information_ids` refreshed from Laravel; `[]` returns no matches. The information index API requires `review_status: "approved"`, `is_active: true`, `archived: false`, plus `owner_id` and record identifiers. Index writes are idempotent per owner and information ID. Pending extracted candidates are not indexed.

A paused result has `status: awaiting_answers` or `awaiting_approval`. Resume with:

```json
{
  "owner_id": "7",
  "answers": [{"field": "location", "value": "Balai desa"}],
  "approved_web_source_ids": [],
  "eligible_information_ids": ["42"]
}
```

The trusted caller must refresh eligible IDs on every resume. Revoked documentary sources are removed from the checkpoint's evidence before execution continues. A retry with the same run ID and original input returns the saved result; a different input returns 409. Completed results are historical snapshots, not a current authorization decision. Laravel must validate current editorial eligibility before publishing.

## Persistence and migration

SQLite checkpoints and run/event records are stored below `data/agent/`. Back up the checkpoint file and companion `.runs` database together. Per-run execution leases prevent simultaneous duplicate calls; after a crashed process, recovery can begin after the lease expires. Successfully completed node results are reused, but a model call interrupted before its checkpoint may repeat. The AI graph does not write Laravel drafts or publish, so replay cannot duplicate those side effects inside Python.

Approved knowledge uses a separate Chroma collection keyed by embedding provider/model/dimensions. Existing raw-document vectors are never silently considered approved. Reindex approved Laravel information into the new collection with `php artisan ai:reindex-approved` from the Laravel project (optionally `--owner=7`); do not delete the old collection to migrate. The AI server and embedding provider must be available. Changing embedding configuration requires reindexing.

`AGENT_ENABLED=false` restores the legacy fixed `/news/generate` path for debugging. Legacy `/rag/search` and `/rag/generate-news` are disabled (410) in agent mode because they query raw documents. Use approved-information endpoints instead. `/documents/index` remains an isolated legacy raw-document indexing endpoint, not an approval operation. `/health/ollama` remains available only as an Ollama-specific diagnostic.

## Optional web discovery

Configure `WEB_SEARCH_URL` for a trusted search adapter accepting `POST {"query": "...", "limit": 5}` and returning `{"results": [{"title": "...", "url": "https://...", "snippet": "..."}]}`. `WEB_SEARCH_API_KEY`, when set, is sent as a bearer token. Set Laravel's `APAKHABAR_AI_WEB_DISCOVERY=true` to enable requests. No provider is configured by default. Web snippets require explicit moderator approval and remain limited evidence; the adapter should provide useful, attributable excerpts.

## Verification

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
python scripts/evaluate_editorial.py --mode agent --output /tmp/agent-evaluation.json
python scripts/evaluate_editorial.py --mode legacy --output /tmp/legacy-evaluation.json
```

Unit/integration tests use scripted generation and small test vectors, and require no model server. The evaluation commands require the configured local models and produce reviewable outputs and latency/call metrics. They do not establish 95% accuracy. Human reviewers must assess factual support against the fixture evidence.

See [the architecture and evaluation notes](docs/agent-architecture.md) for implementation boundaries and acceptance cases.
