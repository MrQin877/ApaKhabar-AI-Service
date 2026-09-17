# ApaKhabar AI Service Architecture

The companion diagram is available at
[`AI_SERVICE_ARCHITECTURE.svg`](./AI_SERVICE_ARCHITECTURE.svg).

## Main request paths

### 1. Document ingestion and information extraction

1. A moderator uploads up to five PDF, DOCX, XLSX, XLSM, CSV, TXT, JPG,
   JPEG, or PNG files through the ApaKhabar web application.
2. Laravel forwards the files to the FastAPI document endpoints.
3. `DocumentService` validates and normalizes the files. Text PDFs and office
   files use their native parsers; scanned PDFs and images use Tesseract OCR.
4. The normalized, source-aware text is sent through `OllamaService` to the
   configured Qwen generation model.
5. The model returns distinct Indonesian information items. Pydantic validates
   the structured result before it is returned to Laravel.
6. In the host application, the original document, extracted information, and
   review status are stored for later selection and reuse.

### 2. RAG indexing and retrieval

1. Normalized document elements are split into overlapping chunks.
2. Ollama creates vectors using `qwen3-embedding:0.6b`.
3. ChromaDB stores vectors, chunk text, document identifiers, filenames, and
   source metadata.
4. A search query is embedded with the same model and compared with stored
   vectors using cosine distance.
5. Relevant chunks are returned as recommendations. They do not become
   publishable evidence until the moderator approves them.

### 3. Grounded news generation

1. The moderator supplies a prompt and may select saved documents or extracted
   information, upload new files, or provide explicit facts.
2. The news workflow may search Brave Search or the Google News RSS fallback
   when current real-world facts are needed.
3. Web sources and RAG recommendations require moderator approval before use.
4. The completeness step checks important ambiguity, missing facts, and
   conflicts. When necessary, it returns the structured `ask_user_choice` tool
   for the frontend to render as buttons.
5. After one clarification round, the workflow must generate rather than enter
   another question loop. Remaining low-risk uncertainty is handled using a
   disclosed conservative assumption.
6. Qwen writes a Bahasa Indonesia draft using only approved evidence and
   user-provided facts. Pydantic validates the article schema.
7. The draft, category, citations, warnings, evidence links, and session state
   return to Laravel for moderator review. The AI service does not publish it.

## Runtime components

| Component | Current purpose |
| --- | --- |
| FastAPI | REST and NDJSON streaming API |
| News creation workflow | Search, approval, completeness, clarification, and generation orchestration |
| Runtime skill prompts | Version-controlled rules for completeness and grounded generation |
| Qwen `qwen3:4b` | Structured extraction, completeness checks, and news drafting |
| Qwen Embedding `qwen3-embedding:0.6b` | Document and query embeddings |
| Ollama | Local model runtime and API |
| ChromaDB | Persistent local vector index for RAG |
| Tesseract | OCR for images and scanned PDF pages |
| Brave Search / Google News RSS | Current web-source discovery |
| Pydantic | Request and response schema validation |

## Important storage boundary

The FastAPI service currently keeps the RAG vector index in ChromaDB. Uploaded
file bytes are processed in memory and are not a durable original-document
archive inside this service. Durable local or cloud object storage, document
records, extracted information records, draft versions, and moderator approval
state belong to the Laravel application layer.

