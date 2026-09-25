# ApaKhabar AI Service

ApaKhabar is a local-first FastAPI service that converts documents and plain text into labelled, structured information and creates evidence-grounded news drafts. Generation can use Ollama or a directly loaded Gemma 4 model. Document retrieval can use Ollama embeddings or the dedicated multilingual EmbeddingGemma model with ChromaDB-based RAG.

## Features

- PDF, scanned PDF, JPG, JPEG, PNG, DOCX, XLSX, XLSM, CSV, and TXT ingestion
- Page, paragraph, sheet, and row source references
- Schema-validated extraction with labels, evidence, and confidence
- Missing-information and conflict checks before news generation
- English and Bahasa Melayu news generation
- Local embeddings, persistent vector storage, semantic search, and RAG news generation
- Local processing without a paid model API
- Configurable Ollama or Gemma 4 generation provider

## Architecture

```text
Upload or text
    -> validate and normalize
    -> direct extraction OR chunk/embed/index
    -> retrieve relevant evidence when using RAG
    -> completeness check
    -> ask for missing required facts OR generate news
```

RAG is intended for large or multiple documents. Use direct extraction for one small document or a short plain-text submission.

## Requirements

- macOS, Windows, or Linux
- Python 3.11 or newer
- Ollama
- Tesseract OCR with Indonesian and English language data
- At least 8 GB memory; 16 GB is recommended
- Sufficient disk space for local models (approximately 4 GB for the recommended pair)

## 1. Install and prepare Ollama

Install Ollama from <https://ollama.com/download>, start it, and download the models:

```bash
ollama pull qwen3:4b
ollama pull qwen3-embedding:0.6b
ollama list
```

The expected local API address is `http://localhost:11434`.

For scanned PDFs and JPG/JPEG/PNG documents, install Tesseract with Indonesian
and English language data. On macOS with Homebrew:

```bash
brew install tesseract tesseract-lang
```

Verify that `ind` and `eng` appear in `tesseract --list-langs`.

Ollama is required only while either `AI_PROVIDER` or `EMBEDDING_PROVIDER` is
set to `ollama`.

### Optional: use Gemma 4 for generation

Use Python 3.12 for the broadest compatibility with PyTorch and Transformers.
Create the environment and install both dependency groups:

```bash
python3.12 -m venv .venv-gemma
source .venv-gemma/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-gemma.txt
```

Authenticate with Hugging Face if the selected model requires account access:

```bash
pip install huggingface_hub
hf auth login
```

Then configure `.env`:

```env
AI_PROVIDER=gemma
GEMMA_MODEL=google/gemma-4-E4B-it
GEMMA_DEVICE=auto
GEMMA_MAX_NEW_TOKENS=2048
EMBEDDING_PROVIDER=embedding_gemma
EMBEDDING_MODEL=google/embeddinggemma-300m
EMBEDDING_DEVICE=auto
EMBEDDING_DIMENSIONS=768
```

Model weights are downloaded to the Hugging Face cache on first use. They are
not stored in this repository. The first request can therefore take significantly
longer than later requests. Set `AI_PROVIDER=ollama` to switch back without
changing application code.

### Optional: use llama.cpp on Apple Silicon

Install the native runtime:

```bash
brew install llama.cpp
```

Start a Q4-quantized Gemma 4 E2B server. The first run downloads the GGUF
model into the Hugging Face cache:

```bash
llama-server \
  -hf ggml-org/gemma-4-E2B-it-GGUF:Q4_0 \
  --alias apakhabar-gemma \
  --host 127.0.0.1 \
  --port 8080 \
  --ctx-size 8192 \
  --n-gpu-layers 99 \
  --parallel 1 \
  --jinja \
  --reasoning off
```

`--reasoning off` is important for this service: it makes Gemma return the
visible extraction or article result directly instead of spending the response
token budget on a separate reasoning trace.

Configure FastAPI in `.env`:

```env
AI_PROVIDER=llama_cpp
LLAMA_CPP_BASE_URL=http://127.0.0.1:8080/v1
LLAMA_CPP_API_KEY=
LLAMA_CPP_MODEL=apakhabar-gemma
LLAMA_CPP_TIMEOUT_SECONDS=180
LLAMA_CPP_MAX_TOKENS=4096
```

Keep EmbeddingGemma as the RAG embedding provider. Verify the connection with
`GET /health/model` before testing extraction and news generation.

RAG search uses hybrid reranking: EmbeddingGemma supplies semantic candidates,
while normalized Indonesian keyword coverage recovers exact names, regulation
numbers, dates, and codes. `RAG_SEMANTIC_WEIGHT` and `RAG_KEYWORD_WEIGHT` control
the combined score; only approved information items are eligible for the
information-library search.

### Optional: use vLLM for cloud GPU generation

vLLM runs as a separate model server. Keep FastAPI responsible for extraction,
RAG, orchestration, and quality evaluation; send only generation requests to
vLLM. Standard vLLM deployment requires a supported Linux accelerator. The
included Compose file expects an NVIDIA GPU and keeps the Hugging Face model
cache in a persistent volume.

Accept the Gemma model licence on Hugging Face, then export secrets without
committing them:

```bash
export HF_TOKEN=<hugging-face-token>
export VLLM_API_KEY=<strong-internal-key>
docker compose -f deploy/vllm/docker-compose.yml up -d
```

Configure FastAPI when it runs directly on the same host:

```env
AI_PROVIDER=vllm
VLLM_BASE_URL=http://localhost:8002/v1
VLLM_API_KEY=<same-internal-key>
VLLM_MODEL=google/gemma-4-E2B-it
VLLM_TIMEOUT_SECONDS=180
VLLM_MAX_TOKENS=2048
```

When FastAPI and vLLM share a Compose network, use
`VLLM_BASE_URL=http://vllm:8000/v1`. Confirm connectivity through
`GET /health/model`. Pin the vLLM container version or digest before production
deployment instead of relying on the example's `latest` tag.

## 2. Prepare the Python application

```bash
git clone <repository-url>
cd ApaKhabar-AI-Service
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Review `.env` before starting the server. Do not commit that file.

## 3. Run the service

```bash
uvicorn app.main:app --reload
```

Open:

- API documentation: <http://127.0.0.1:8000/docs>
- Application health: <http://127.0.0.1:8000/health>
- Ollama/model health: <http://127.0.0.1:8000/health/ollama>

## Main workflows

### Upload and extract labelled information

```bash
curl -X POST http://127.0.0.1:8000/documents/extract-information \
  -F "file=@report.pdf"
```

The response includes information type, title, summary, labels, fields, supporting evidence, and model-reported confidence.

### Extract information from plain text

```bash
curl -X POST http://127.0.0.1:8000/extract-information \
  -H "Content-Type: application/json" \
  -d '{"content":"The council announced a health programme in Kuala Lumpur on 15 September 2026."}'
```

### Check whether enough information is available

```bash
curl -X POST http://127.0.0.1:8000/news/check-completeness \
  -H "Content-Type: application/json" \
  -d '{"information":"A community programme will be held next month."}'
```

When required facts are absent, the response contains targeted questions. Collect the user's answers, merge them into the information text, and check again.

### Generate news directly

```bash
curl -X POST http://127.0.0.1:8000/news/generate \
  -H "Content-Type: application/json" \
  -d '{
    "information":"Universiti Example announced on 1 September 2026 that it will organize a free AI workshop for 120 students at Dewan Kuala Lumpur on 15 September 2026.",
    "language":"en",
    "tone":"formal"
  }'
```

Use `"language":"ms"` for Bahasa Melayu. If required information is missing or conflicting, `article` is `null` and the completeness result explains what is needed.

## RAG workflow

### 1. Index a document

```bash
curl -X POST http://127.0.0.1:8000/documents/index \
  -F "file=@background-report.pdf"
```

Save the returned `document_id`. The service extracts source-aware elements, chunks them, creates local embeddings, and stores them in ChromaDB.

### 2. Search indexed documents

```bash
curl -X POST http://127.0.0.1:8000/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query":"What programme was announced and when?",
    "document_ids":["<document-id>"],
    "top_k":5
  }'
```

Omit `document_ids` to search all indexed documents.

### 3. Generate news from retrieved evidence

```bash
curl -X POST http://127.0.0.1:8000/rag/generate-news \
  -H "Content-Type: application/json" \
  -d '{
    "query":"Write news about the announced AI programme",
    "document_ids":["<document-id>"],
    "top_k":5,
    "language":"ms",
    "tone":"formal"
  }'
```

The response contains both retrieved chunks and the news result so users can inspect the evidence.

### 4. Remove an indexed document

```bash
curl -X DELETE http://127.0.0.1:8000/rag/documents/<document-id>
```

## API summary

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check the application |
| GET | `/health/ollama` | Check Ollama and configured models |
| GET | `/health/model` | Check the configured remote vLLM model server |
| POST | `/documents/extract-information` | Upload and extract labelled information |
| POST | `/documents/index` | Add a document to the RAG index |
| POST | `/extract-information` | Extract information from plain text |
| POST | `/news/check-completeness` | Find missing or conflicting news facts |
| POST | `/news/generate` | Generate news from supplied information |
| POST | `/news/evaluate-quality` | Score a saved or edited draft against approved evidence |
| POST | `/rag/search` | Search indexed evidence |
| POST | `/rag/generate-news` | Retrieve evidence and generate news |
| DELETE | `/rag/documents/{document_id}` | Remove a document from the index |

## Configuration

| Variable | Default | Description |
|---|---:|---|
| `AI_PROVIDER` | `ollama` | Generation provider: `ollama`, `gemma`, `llama_cpp`, or `vllm` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama API |
| `OLLAMA_GENERATION_MODEL` | `qwen3:4b` | Extraction and writing model |
| `OLLAMA_EMBEDDING_MODEL` | `qwen3-embedding:0.6b` | RAG embedding model |
| `GEMMA_MODEL` | `google/gemma-4-E4B-it` | Hugging Face Gemma generation model |
| `GEMMA_DEVICE` | `auto` | Transformers device map |
| `GEMMA_MAX_NEW_TOKENS` | `2048` | Maximum generated tokens per response |
| `GEMMA_TOP_P` | `0.95` | Gemma sampling probability threshold |
| `GEMMA_TOP_K` | `64` | Gemma sampling candidate limit |
| `VLLM_BASE_URL` | `http://localhost:8002/v1` | Self-hosted vLLM OpenAI-compatible API |
| `VLLM_API_KEY` | empty | Private API key configured on the vLLM server |
| `VLLM_MODEL` | `google/gemma-4-E2B-it` | Model name exposed by vLLM |
| `VLLM_TIMEOUT_SECONDS` | `180` | Maximum generation request duration |
| `VLLM_MAX_TOKENS` | `2048` | Maximum output tokens requested from vLLM |
| `LLAMA_CPP_BASE_URL` | `http://localhost:8080/v1` | Local llama-server OpenAI-compatible API |
| `LLAMA_CPP_API_KEY` | empty | Optional llama-server API key |
| `LLAMA_CPP_MODEL` | `apakhabar-gemma` | Model alias exposed by llama-server |
| `LLAMA_CPP_TIMEOUT_SECONDS` | `180` | Maximum llama.cpp generation duration |
| `LLAMA_CPP_MAX_TOKENS` | `2048` | Maximum output tokens requested from llama.cpp |
| `EMBEDDING_PROVIDER` | `ollama` | RAG provider: `ollama` or `embedding_gemma` |
| `EMBEDDING_MODEL` | `google/embeddinggemma-300m` | Local EmbeddingGemma checkpoint |
| `EMBEDDING_DEVICE` | `auto` | Chooses CUDA, Apple MPS, or CPU automatically |
| `EMBEDDING_DIMENSIONS` | `768` | EmbeddingGemma vector dimensions |
| `EMBEDDING_INDEX_VERSION` | `legacy` | Vector index generation; change deliberately and re-index when embeddings or chunking change |
| `INTERNAL_API_TOKEN` | empty | Optional shared secret required in `X-ApaKhabar-Service-Token` for internal calls |
| `API_VERSION` | `v1` | Reported internal API contract version |
| `CHROMA_PATH` | `./data/chroma` | Persistent vector database directory |
| `MAX_UPLOAD_MB` | `20` | Maximum accepted upload size |
| `OCR_LANGUAGES` | `ind+eng` | Tesseract languages used for scans and images |
| `RAG_CHUNK_SIZE` | `1000` | Approximate characters in each chunk |
| `RAG_CHUNK_OVERLAP` | `150` | Repeated characters between chunks |
| `RAG_TOP_K` | `5` | Default retrieval result count |
| `RAG_MAX_DISTANCE` | `0.75` | Maximum cosine distance accepted as relevant |
| `RAG_SEMANTIC_WEIGHT` | `0.7` | Semantic contribution to hybrid retrieval |
| `RAG_KEYWORD_WEIGHT` | `0.3` | Exact-keyword contribution to hybrid retrieval |
| `RAG_CANDIDATE_MULTIPLIER` | `4` | Candidate pool size before reranking |

EmbeddingGemma uses separate Chroma collections so it cannot accidentally query
existing Qwen vectors. After switching, upload/re-index the documents and approved
information again. The legacy Ollama collections remain available if you switch
back; remove them only after confirming the new index works.

## Internal API contract

Laravel should call the versioned `/v1` routes. Legacy unversioned routes remain
available temporarily so existing local integrations continue to work. Set the
same strong value as `INTERNAL_API_TOKEN` in this service and
`APAKHABAR_AI_SERVICE_TOKEN` in Laravel before deployment. When no token is set,
authentication is disabled for local development.

`EMBEDDING_INDEX_VERSION=legacy` preserves existing Chroma collection names. When
changing an embedding model, dimensions, or chunking strategy, set a new value
such as `v2`, restart the service, and re-index approved information. This avoids
mixing incompatible vectors and keeps the old index available for rollback.

## Development

Run automated tests:

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
```

Compile-check the application:

```bash
python -m compileall -q app tests
```

Measure the project objectives with the labelled evaluation workflow in
[`docs/MODEL_EVALUATION_AND_TUNING.md`](docs/MODEL_EVALUATION_AND_TUNING.md). It
calculates field-level extraction F1, retrieval Hit@K/Recall@K/MRR, and the
human-reviewed news acceptance rate; model-reported `confidence` is not used as
accuracy.

Run retrieval evaluation after replacing the example document IDs with IDs from
the indexed Chroma collection:

```bash
python scripts/evaluate_model.py retrieval \
  --dataset evaluation/data/retrieval_test.jsonl \
  --output evaluation/results/retrieval.json
```

Core modules:

- `app/services/document_service.py`: file parsing and normalization
- `app/services/ai_service.py`: provider-neutral structured extraction, completeness, and writing
- `app/services/model_providers/`: Ollama and Gemma generation adapters
- `app/services/rag_service.py`: chunking, embedding, indexing, and retrieval
- `app/schemas/`: request and response contracts
- `app/api/`: FastAPI routes

When adding a new file format, add its parser to `DocumentService`, preserve meaningful source coordinates, add its extension to `SUPPORTED_EXTENSIONS`, and create a test fixture.

## Operational and safety notes

- Treat uploaded document content as untrusted data, not model instructions.
- Do not publish drafts automatically; require human editorial approval.
- Model confidence is a review signal, not a calibrated probability.
- Verify names, dates, amounts, and quotations against returned evidence.
- Chroma data is local and persistent; implement user/tenant isolation before multi-user deployment.
- Shared-token authentication is available for Laravel-to-FastAPI calls. Add rate limiting, malware scanning, secret rotation, tenant isolation, and a retention policy before exposing the service publicly.
- Use a reverse proxy and HTTPS for any non-local deployment.

## Troubleshooting

### Ollama health returns 503

Start Ollama, run `ollama list`, and confirm that model names match `.env` exactly.

### Model responses are slow

Use `qwen3:4b`, close memory-heavy applications, reduce input size, or reduce `RAG_TOP_K`.

### No relevant RAG results

Confirm the document was indexed, search with a more specific query, or cautiously increase `RAG_MAX_DISTANCE`. High distance values can admit irrelevant text.

### Scanned PDF returns no text

The current PDF parser reads text layers. Add an OCR pipeline for image-only PDFs before production use.

### Swagger works but another frontend cannot connect

Configure FastAPI CORS for the exact trusted frontend origins. Avoid unrestricted origins in production.

## Current scope

This version is suitable for local development, demonstrations, and controlled evaluation. Public production deployment still requires authentication, tenant isolation, background jobs, stronger file inspection/OCR, monitoring, and editorial governance.
