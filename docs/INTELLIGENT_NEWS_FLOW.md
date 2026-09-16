# Intelligent News Creator: Implemented Flow and Storage

## Purpose

The workflow turns a source document into one or more Indonesian information
items. A moderator then selects related items, optionally supplies an editorial
instruction, and generates a grounded Indonesian news draft. Editorial
instructions control focus and style but are never treated as factual evidence.

## Processing flow

1. The Laravel application receives up to five files and stores each original on
   its configured private filesystem disk (`local` or `s3`).
2. It sends the files to `POST /documents/batch-extract` in this service.
3. `DocumentService` reads PDF, scanned PDF, JPG, JPEG, PNG, DOCX, XLSX, XLSM,
   CSV, or TXT. Scans and images use Tesseract OCR.
4. Source-aware text is sent to the configured Ollama generation model.
5. The model returns one item per distinct newsworthy topic, decision,
   announcement, event, project, or issue. Titles, summaries, labels, and text
   field values are requested in Bahasa Indonesia.
6. Pydantic validates the extraction before it is returned.
7. Successful documents are embedded in Chroma and Laravel stores every
   extracted item separately so moderators can search and
   combine information from one or many documents.
8. The moderator selects the relevant items and calls the Laravel generation
   endpoint, which passes structured evidence to `POST /news/generate`.
9. The `news-creation` runtime skill checks completeness and conflicts. It
   either returns targeted Indonesian questions or writes a structured draft.
   Questions, answers, approved sources, and explicit user facts are persisted
   in an intelligent news session so the conversation can resume.
10. Laravel stores the draft and links it to the exact information records used.

## Database tables in the web application

### `intelligence_documents`

Stores file identity, private storage path, uploader, checksum, MIME type,
processing status, AI document identifier, character count, and processing
errors. `storage_disk` makes the same record portable between local storage and
private S3 storage; `embedding_status` records retrieval readiness. Its purpose
is upload management, duplicate detection, retry support,
and processing audit history. Original file content is not duplicated in the
information table.

### `intelligence_information`

Stores each extracted information item separately. One document can own many
items. It contains the Indonesian title and explanatory paragraph, type, labels,
flexible facts, evidence, model confidence, searchable text, and moderation
state. Its purpose is moderator review, information search, selection, and reuse
across different news drafts. Confidence is a review signal, not measured
accuracy.

### `intelligent_news_drafts`

Stores the structured article, editorial instruction, labels, warnings, sources,
creator, and draft/published/archived state. Its purpose is to preserve AI output
for editorial revision without prematurely inserting unreviewed content into the
public `news` table.

### `intelligent_news_draft_sources`

Links a draft to every information item used to generate it. Its purpose is
traceability: moderators can identify which documents and evidence support each
draft, and evaluation can detect unsupported claims.

### `intelligent_news_sessions`

Stores the active prompt, approved document and information IDs, explicit
user-provided facts, targeted questions, conflicts, workflow state, and final
draft link. Its purpose is a resumable ask-answer-check-generate workflow. User
answers are never relabelled as document evidence.

## Direct extraction versus RAG

Direct extraction creates reusable information records. RAG recommends related
indexed documents in the creator, but recommendations remain outside the
evidence set until the moderator presses **Approve source**. Generation receives
only approved documents, approved information items, newly extracted items, and
explicit user-provided facts.

## Operational limitations

- Tesseract and its Indonesian trained data must be installed on the AI host.
- OCR quality must be evaluated separately from model extraction quality.
- Each request accepts at most five files and currently processes synchronously;
  production deployment should move extraction to a queue for large collections
  such as the initial 80 documents.
- Files must remain private and require retention/deletion rules.
- Human editorial review remains mandatory before copying a draft to `news`.
