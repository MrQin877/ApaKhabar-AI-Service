# ApaKhabar AI Service

ApaKhabar is a local-first FastAPI service that converts documents and plain text into labelled, structured information and creates evidence-grounded news drafts. It uses free local models through Ollama and can optionally retrieve information from multiple or large documents through ChromaDB-based RAG.

## Features

- PDF, scanned PDF, JPG, JPEG, PNG, DOCX, XLSX, XLSM, CSV, and TXT ingestion
- Page, paragraph, sheet, and row source references
- Schema-validated extraction with labels, evidence, and confidence
- Missing-information and conflict checks before news generation
- English and Bahasa Melayu news generation
- Local embeddings, persistent vector storage, semantic search, and RAG news generation
- Local processing without a paid model API

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
| POST | `/documents/extract-information` | Upload and extract labelled information |
| POST | `/documents/index` | Add a document to the RAG index |
| POST | `/extract-information` | Extract information from plain text |
| POST | `/news/check-completeness` | Find missing or conflicting news facts |
| POST | `/news/generate` | Generate news from supplied information |
| POST | `/rag/search` | Search indexed evidence |
| POST | `/rag/generate-news` | Retrieve evidence and generate news |
| DELETE | `/rag/documents/{document_id}` | Remove a document from the index |

## Configuration

| Variable | Default | Description |
|---|---:|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama API |
| `OLLAMA_GENERATION_MODEL` | `qwen3:4b` | Extraction and writing model |
| `OLLAMA_EMBEDDING_MODEL` | `qwen3-embedding:0.6b` | RAG embedding model |
| `CHROMA_PATH` | `./data/chroma` | Persistent vector database directory |
| `MAX_UPLOAD_MB` | `20` | Maximum accepted upload size |
| `OCR_LANGUAGES` | `ind+eng` | Tesseract languages used for scans and images |
| `RAG_CHUNK_SIZE` | `1000` | Approximate characters in each chunk |
| `RAG_CHUNK_OVERLAP` | `150` | Repeated characters between chunks |
| `RAG_TOP_K` | `5` | Default retrieval result count |
| `RAG_MAX_DISTANCE` | `0.75` | Maximum cosine distance accepted as relevant |

If the embedding model changes, delete or migrate the existing Chroma collection and re-index documents because embedding dimensions and vector spaces may differ.

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
calculates field-level extraction F1 and the human-reviewed news acceptance rate;
model-reported `confidence` is not used as accuracy.

Core modules:

- `app/services/document_service.py`: file parsing and normalization
- `app/services/ai_service.py`: Ollama structured extraction, completeness, and writing
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
- Add authentication, authorization, rate limiting, malware scanning, and a retention policy before exposing the API publicly.
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
