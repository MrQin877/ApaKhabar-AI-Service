from pathlib import Path
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_user_manual import (
    BLUE,
    DARK_BLUE,
    INK,
    MUTED,
    add_bullet,
    add_code,
    add_heading,
    add_note,
    add_numbering_instance,
    add_page_number,
    add_step,
    add_table,
    configure_numbering,
)


OUTPUT = Path("docs/ApaKhabar_Service_Architecture_and_Development_Guide.docx")


def architecture_flow(document: Document, lines: list[str]) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(8)
    paragraph.paragraph_format.space_after = Pt(10)
    paragraph.paragraph_format.keep_together = True
    for index, line in enumerate(lines):
        run = paragraph.add_run(line)
        run.bold = index % 2 == 0
        run.font.name = "Menlo"
        run._element.rPr.rFonts.set(qn("w:ascii"), "Menlo")
        run._element.rPr.rFonts.set(qn("w:hAnsi"), "Menlo")
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor.from_string(INK if index % 2 == 0 else MUTED)
        if index < len(lines) - 1:
            run.add_break()


def phase(
    document: Document,
    number: int,
    title: str,
    objective: str,
    files: str,
    actions: list[str],
    verification: str,
    numbering_id: int,
) -> None:
    heading = document.add_heading(f"Phase {number}: {title}", level=2)
    heading.paragraph_format.keep_with_next = True
    heading.paragraph_format.page_break_before = number > 0
    add_note(document, "Objective", objective)
    paragraph = document.add_paragraph()
    lead = paragraph.add_run("Main files: ")
    lead.bold = True
    paragraph.add_run(files)
    for action in actions:
        add_step(document, action, numbering_id)
    check = document.add_paragraph()
    check.paragraph_format.space_before = Pt(4)
    run = check.add_run("Verification gate: ")
    run.bold = True
    run.font.color.rgb = RGBColor.from_string(DARK_BLUE)
    check.add_run(verification)


def build() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    normal.font.size = Pt(11)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25

    tokens = {
        "Heading 1": (16, BLUE, 18, 10),
        "Heading 2": (13, BLUE, 14, 7),
        "Heading 3": (12, DARK_BLUE, 10, 5),
    }
    for name, (size, color, before, after) in tokens.items():
        style = document.styles[name]
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    bullet_id, base_number_id = configure_numbering(document)
    header = section.header.paragraphs[0]
    header.text = "ApaKhabar AI Service  |  Architecture & Development Guide"
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in header.runs:
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor.from_string(MUTED)
    add_page_number(section.footer.paragraphs[0])

    document.add_paragraph().paragraph_format.space_after = Pt(82)
    kicker = document.add_paragraph()
    kicker.alignment = WD_ALIGN_PARAGRAPH.CENTER
    kicker_run = kicker.add_run("SYSTEM DESIGN + BUILD SEQUENCE")
    kicker_run.bold = True
    kicker_run.font.size = Pt(10)
    kicker_run.font.color.rgb = RGBColor.from_string(BLUE)
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(14)
    title.paragraph_format.space_after = Pt(8)
    title_run = title.add_run("ApaKhabar Service Architecture")
    title_run.bold = True
    title_run.font.size = Pt(28)
    title_run.font.color.rgb = RGBColor.from_string(INK)
    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(28)
    subtitle_run = subtitle.add_run("Concepts and Step-by-Step Development Guide")
    subtitle_run.font.size = Pt(15)
    subtitle_run.font.color.rgb = RGBColor.from_string(DARK_BLUE)
    intro = document.add_paragraph()
    intro.alignment = WD_ALIGN_PARAGRAPH.CENTER
    intro.paragraph_format.left_indent = Inches(0.55)
    intro.paragraph_format.right_indent = Inches(0.55)
    intro.add_run(
        "Explains why the service is structured in layers, how data moves through each path, "
        "and how to reproduce the implementation one verified phase at a time."
    )
    document.add_paragraph().paragraph_format.space_after = Pt(50)
    meta = document.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run("Architecture baseline 1.0  •  September 2026").italic = True
    document.add_page_break()

    add_heading(document, "Contents", 1)
    frontend_number_id = add_numbering_instance(document, 1120)
    for item in [
        "1. Architecture goals and boundaries",
        "2. System components and responsibilities",
        "3. Core data contracts",
        "4. Direct document and text workflows",
        "5. Retrieval-augmented generation workflow",
        "6. Reliability and safety design",
        "7. Step-by-step development plan",
        "8. Endpoint build order and integration",
        "9. Testing and evaluation strategy",
        "10. Evolution toward production",
    ]:
        add_bullet(document, item, bullet_id)
    add_note(
        document,
        "How to use this guide",
        "Read sections 1-6 to understand the design. Follow section 7 in order when rebuilding or explaining the implementation.",
    )
    document.add_page_break()

    add_heading(document, "1. Architecture goals and boundaries", 1)
    document.add_paragraph(
        "The architecture separates document handling, model reasoning, retrieval, and HTTP transport. "
        "This prevents file-format details from leaking into prompts and prevents model-specific code "
        "from spreading across API endpoints."
    )
    add_heading(document, "1.1 Design goals", 2)
    for item in [
        "Hosted API generation and evaluation; cached local EmbeddingGemma supports retrieval.",
        "Traceable: extracted facts retain evidence and source coordinates.",
        "Schema-driven: Pydantic defines stable contracts between model, API, and frontend.",
        "Progressive: short inputs use a direct path; large collections use RAG.",
        "Replaceable: parsers, models, and vector storage can evolve behind service interfaces.",
        "Human-controlled: missing facts stop drafting and publication remains an editorial decision.",
    ]:
        add_bullet(document, item, bullet_id)
    add_heading(document, "1.2 Current boundary", 2)
    add_table(document, ["Inside the service", "Outside the current service"], [
        ["File validation and parsing", "Frontend user interface"],
        ["Information extraction and labels", "Authentication and account management"],
        ["Completeness checks and news drafts", "Automatic publication"],
        ["Embeddings, Chroma indexing, retrieval", "Public production infrastructure"],
    ], [4680, 4680])
    add_note(document, "Reason for the boundary", "The final-year project can evaluate AI quality and provenance independently from a frontend or publishing platform.")

    add_heading(document, "2. System components and responsibilities", 1)
    architecture_flow(document, [
        "CLIENT / SWAGGER / FUTURE FRONTEND",
        "↓ HTTP request",
        "FASTAPI ROUTES",
        "↓ validated request",
        "DOCUMENT  |  AI  |  RAG SERVICES",
        "↓ typed data contracts",
        "HOSTED GENERATION API  |  LOCAL EMBEDDINGS  |  CHROMADB",
    ])
    add_table(document, ["Layer", "Current module", "Responsibility"], [
        ["Transport", "app/api/", "Receive requests, validate inputs, map failures to HTTP responses"],
        ["Configuration", "app/core/config.py", "Load typed environment settings once"],
        ["Contracts", "app/schemas/", "Define normalized documents, extraction, news, and RAG payloads"],
        ["Ingestion", "document_service.py", "Parse bytes and preserve source coordinates"],
        ["Model orchestration", "ai_service.py", "Structured extraction, completeness checks, summaries, writing"],
        ["Retrieval", "rag_service.py", "Chunk, embed, index, filter, retrieve, and delete"],
        ["External runtime", "Hosted API + local EmbeddingGemma + ChromaDB", "Call hosted models and persist local vectors"],
    ], [1400, 2900, 5060])
    add_heading(document, "2.1 Dependency direction", 2)
    document.add_paragraph(
        "API routes depend on services; services depend on schemas and configuration. Schemas do not "
        "depend on APIs or services. This one-way dependency makes individual layers testable and reduces circular imports."
    )

    document.add_page_break()
    add_heading(document, "3. Core data contracts", 1)
    add_heading(document, "3.1 NormalizedDocument", 2)
    document.add_paragraph(
        "Every supported file becomes the same internal representation. A document contains elements; "
        "each element contains content, type, metadata, and a SourceReference."
    )
    add_code(document, "NormalizedDocument\n  document_id\n  filename\n  media_type\n  character_count\n  elements[]\n    element_type\n    content\n    source: page | sheet | row | paragraph")
    add_heading(document, "3.2 ExtractionResponse", 2)
    add_code(document, "ExtractionResponse\n  information[]\n    type\n    title\n    summary\n    labels[]\n    fields{}\n    evidence[]: source + quote\n    confidence: 0..1")
    add_heading(document, "3.3 Completeness and news contracts", 2)
    add_table(document, ["Contract", "Key decision"], [
        ["CompletenessResult", "ready, needs_information, or has_conflicts"],
        ["MissingInformation", "field, importance, and a targeted question"],
        ["NewsArticle", "headline, lead, body, labels, sources, and warnings"],
        ["NewsGenerationResponse", "Always returns completeness; article may be null"],
        ["RetrievedChunk", "Returns content, document identity, source, and distance"],
    ], [3000, 6360])
    add_note(document, "Contract-first principle", "Change schemas before prompts or frontend code. The schema is the shared definition of valid output.")

    add_heading(document, "4. Direct document and text workflows", 1)
    add_heading(document, "4.1 Document extraction", 2)
    architecture_flow(document, [
        "UPLOAD",
        "→ size + extension validation",
        "→ format parser",
        "→ NormalizedDocument with source markers",
        "→ hosted API structured extraction",
        "→ Pydantic validation",
        "→ ExtractionResponse",
    ])
    add_heading(document, "4.2 Direct news generation", 2)
    architecture_flow(document, [
        "USER FACTS OR EXTRACTION OUTPUT",
        "→ completeness and conflict check",
        "→ questions when required facts are missing",
        "→ schema-constrained news generation when ready",
        "→ editable draft + warnings",
    ])
    add_heading(document, "4.3 Why direct mode remains important", 2)
    for item in [
        "It is faster for one small document.",
        "It avoids retrieval errors when all content already fits in the model context.",
        "It provides a simpler baseline for evaluating extraction and generation quality.",
    ]:
        add_bullet(document, item, bullet_id)

    document.add_page_break()
    add_heading(document, "5. Retrieval-augmented generation workflow", 1)
    add_heading(document, "5.1 Indexing path", 2)
    architecture_flow(document, [
        "NORMALIZED DOCUMENT",
        "→ group elements into overlapping source-marked chunks",
        "→ qwen3-embedding:0.6b vectors",
        "→ Chroma upsert: vector + text + scalar metadata",
        "→ return document_id and chunk count",
    ])
    add_heading(document, "5.2 Retrieval path", 2)
    architecture_flow(document, [
        "USER QUERY",
        "→ query embedding",
        "→ cosine search with optional document_id filter",
        "→ reject results beyond RAG_MAX_DISTANCE",
        "→ top relevant RetrievedChunk objects",
    ])
    add_heading(document, "5.3 Grounded-news path", 2)
    architecture_flow(document, [
        "QUERY + OPTIONAL DOCUMENT IDS",
        "→ retrieve relevant chunks",
        "→ assemble source-marked context",
        "→ completeness check",
        "→ news draft only when ready",
        "→ return retrieval and article together",
    ])
    add_heading(document, "5.4 Important RAG decisions", 2)
    add_table(document, ["Decision", "Why it matters"], [
        ["Same embedding model for index and query", "Vectors must share dimensions and semantic space"],
        ["Source markers inside chunk text", "The writer sees provenance with the evidence"],
        ["Metadata document filters", "Prevents unintended cross-document retrieval"],
        ["Distance threshold", "Reduces irrelevant nearest-neighbour results"],
        ["Return retrieved chunks", "Users can audit why an article was generated"],
    ], [3400, 5960])

    document.add_page_break()
    add_heading(document, "6. Reliability and safety design", 1)
    add_table(document, ["Risk", "Current control", "Next production control"], [
        ["Invalid model JSON", "hosted API JSON schema + Pydantic validation", "Evaluation and retry policy"],
        ["Invented facts", "Strict prompts, evidence, source guard", "Claim-level verification"],
        ["Missing facts", "Completeness gate before writing", "Editorial workflow and audit log"],
        ["Irrelevant retrieval", "Top-k, distance threshold, document filter", "Reranker and retrieval evaluation"],
        ["Unsafe files", "Size, extension, parser validation", "MIME inspection and malware scanning"],
        ["Cross-user exposure", "Local single-user scope", "Authentication and tenant partitioning"],
    ], [2350, 3550, 3460])
    add_note(document, "Threat-model reminder", "Text inside an uploaded document is untrusted data. It must never override the application's system rules.")

    document.add_page_break()
    add_heading(document, "7. Step-by-step development plan", 1)
    document.add_paragraph(
        "Each phase should end with a working checkpoint. Do not add the next layer until its verification gate passes."
    )

    phase(document, 0, "Define scope and acceptance criteria",
          "Agree on supported formats, outputs, languages, and non-goals before coding.",
          "Project notes, schemas sketch",
          ["Define the direct extraction use case.", "Define required news facts and supported languages.", "Separate MVP requirements from public-production requirements."],
          "A sample input and expected JSON response exist for every feature.",
          add_numbering_instance(document, 1000))
    phase(document, 1, "Create the FastAPI skeleton",
          "Establish a runnable HTTP service before adding AI.",
          "app/main.py, app/api/health.py",
          ["Create the virtual environment and install FastAPI.", "Create the application and root/health routes.", "Run Uvicorn and open Swagger."],
          "GET /health returns 200 and Swagger loads.",
          add_numbering_instance(document, 1001))

    phase(document, 2, "Configure hosted model APIs",
          "Move runtime settings out of source code and verify required models.",
          ".env.example, app/core/config.py, app/api/health.py",
          ["Configure writer/evaluator API credentials and provision the embedding model cache.", "Create typed settings with safe defaults.", "Add an hosted API/model health endpoint."],
          "GET /health/models probes the writer; target=evaluator probes the judge.",
          add_numbering_instance(document, 1002))
    phase(document, 3, "Design the schemas",
          "Make valid inputs and outputs explicit before prompt engineering.",
          "app/schemas/information.py, document.py, news.py, rag.py",
          ["Define the normalized document and source reference.", "Define extraction items, evidence, labels, and confidence.", "Define completeness, news, and retrieval responses."],
          "Pydantic accepts valid examples and rejects missing required fields.",
          add_numbering_instance(document, 1003))

    phase(document, 4, "Build document normalization",
          "Convert different formats into one source-aware representation.",
          "app/services/document_service.py, app/api/document.py",
          ["Read uploads with a strict size limit.", "Sanitize names and dispatch by supported extension.", "Implement PDF, DOCX, XLSX, CSV, and TXT parsers.", "Attach page, sheet, row, or paragraph coordinates."],
          "All five parser tests pass, including empty and damaged input handling.",
          add_numbering_instance(document, 1004))
    phase(document, 5, "Add structured information extraction",
          "Obtain deterministic JSON-shaped information from local generation.",
          "app/services/ai_service.py, app/api/extraction.py",
          ["Pass the Pydantic JSON schema to hosted API.", "Set temperature to zero for extraction.", "Validate the returned message and map model failures.", "Require evidence and source markers."],
          "A synthetic announcement becomes a valid ExtractionResponse with evidence.",
          add_numbering_instance(document, 1005))

    phase(document, 6, "Add the completeness gate",
          "Ask for missing facts instead of allowing the writer to invent them.",
          "app/schemas/news.py, app/services/ai_service.py, app/api/news.py",
          ["Define required facts: what, who/source, where, and when.", "Return targeted questions and conflicts.", "Test both incomplete and ready inputs."],
          "Incomplete input returns article=null; complete input returns ready.",
          add_numbering_instance(document, 1006))
    phase(document, 7, "Add direct news generation",
          "Generate an editable article only from verified supplied facts.",
          "app/services/ai_service.py, app/api/news.py",
          ["Define the article schema and language field.", "Write strict grounding rules.", "Generate only after completeness is ready.", "Clear source metadata when plain text contains no source markers."],
          "English and Bahasa Melayu responses validate without invented citations.",
          add_numbering_instance(document, 1007))

    phase(document, 8, "Implement chunking and embeddings",
          "Prepare large and multiple documents for semantic retrieval.",
          "app/services/rag_service.py",
          ["Group elements up to the configured chunk size.", "Carry source markers and controlled overlap.", "Embed all chunks with the configured embedding model."],
          "Long input creates multiple source-aware chunks and embedding dimensions are consistent.",
          add_numbering_instance(document, 1008))
    phase(document, 9, "Persist and search with Chroma",
          "Store reusable document knowledge and retrieve it by meaning.",
          "app/services/rag_service.py, app/api/rag.py",
          ["Create a persistent cosine collection.", "Upsert text, vector, document ID, filename, and source.", "Embed queries and apply document filters.", "Filter results by maximum distance."],
          "An indexed synthetic document is found by a semantic query and can be deleted.",
          add_numbering_instance(document, 1009))

    phase(document, 10, "Connect retrieval to news",
          "Generate articles from retrieved evidence rather than whole document collections.",
          "app/api/rag.py",
          ["Retrieve top relevant chunks.", "Return 404 when no relevant context exists.", "Run completeness against retrieved context.", "Return retrieval evidence beside the article."],
          "RAG generation exposes the chunks used and never writes when the context is insufficient.",
          add_numbering_instance(document, 1010))
    phase(document, 11, "Harden errors and boundaries",
          "Make failures understandable without leaking internal details or content.",
          "All API and service modules",
          ["Use 413 for oversized uploads and 422 for invalid content.", "Use 503 for unavailable local AI dependencies.", "Keep uploaded content out of operational error messages.", "Document public-deployment requirements."],
          "Failure-path tests return stable status codes and concise messages.",
          add_numbering_instance(document, 1011))

    phase(document, 12, "Document and evaluate",
          "Make the service reproducible and measurable by another person.",
          "README.md, docs/, tests/",
          ["Provide setup and API examples.", "Build a labelled evaluation dataset.", "Measure extraction, retrieval, grounding, latency, and memory.", "Record limitations and next steps honestly."],
          "A new developer can install, run, test, and use every workflow from the documentation.",
          add_numbering_instance(document, 1012))

    document.add_page_break()
    add_heading(document, "8. Endpoint build order and integration", 1)
    add_table(document, ["Order", "Endpoint", "Depends on"], [
        ["1", "GET /health", "FastAPI only"],
        ["2", "GET /health/models", "Settings + hosted API"],
        ["3", "POST /documents/upload", "Document normalization"],
        ["4", "POST /extract-information", "hosted API + extraction schema"],
        ["5", "POST /documents/extract-information", "Upload + extraction"],
        ["6", "POST /news/check-completeness", "Completeness schema + hosted API"],
        ["7", "POST /news/generate", "Completeness + writer"],
        ["8", "POST /documents/index", "Normalization + embeddings + Chroma"],
        ["9", "POST /rag/search", "Query embedding + Chroma"],
        ["10", "POST /rag/generate-news", "Retrieval + completeness + writer"],
        ["11", "DELETE /rag/documents/{id}", "Chroma metadata deletion"],
    ], [1000, 3950, 4410])
    add_heading(document, "8.1 Frontend sequence", 2)
    for item in [
        "Upload or accept plain text.",
        "Display normalized/extracted facts and evidence for correction.",
        "Call completeness and render missing questions as fields.",
        "Merge explicit user answers and recheck.",
        "Generate, display warnings, and keep the draft editable.",
        "Require a final human approval action outside the AI service.",
    ]:
        add_step(document, item, frontend_number_id)

    add_heading(document, "9. Testing and evaluation strategy", 1)
    add_table(document, ["Test level", "What to verify", "Example"], [
        ["Unit", "One parser or helper", "XLSX row retains sheet and row"],
        ["Schema", "Invalid model/API data is rejected", "Confidence outside 0..1 fails"],
        ["Service", "Prompt orchestration and guards", "Plain text cannot invent a page source"],
        ["API", "Status and response contracts", "Empty upload returns 422"],
        ["Integration", "Real hosted API and Chroma", "Index, search, generate, delete"],
        ["Evaluation", "Quality against labelled samples", "Fact precision and retrieval hit rate"],
    ], [1700, 3900, 3760])
    add_heading(document, "9.1 Recommended project metrics", 2)
    for item in [
        "Extraction precision, recall, and F1 for labelled fields.",
        "Evidence-source accuracy for pages, sheets, and rows.",
        "Retrieval hit rate at k and mean reciprocal rank.",
        "Unsupported-claim rate in generated news.",
        "Completeness-question usefulness rated by users.",
        "Median and p95 latency plus peak memory usage.",
    ]:
        add_bullet(document, item, bullet_id)

    document.add_page_break()
    add_heading(document, "10. Evolution toward production", 1)
    add_table(document, ["Concern", "Current", "Production evolution"], [
        ["Execution", "Synchronous local calls", "Background queue, job status, cancellation"],
        ["Identity", "Single local user", "Authentication, authorization, tenant IDs"],
        ["Storage", "Local Chroma", "Tenant collections, backups, lifecycle policies"],
        ["Files", "Extension and parser validation", "MIME inspection, malware scan, object storage"],
        ["Documents", "Text-layer PDF", "OCR and layout-aware parsing"],
        ["Retrieval", "Dense cosine search", "Hybrid search, reranking, evaluation-driven thresholds"],
        ["Observability", "HTTP errors", "Metrics, traces, structured logs, model/version tracking"],
        ["Governance", "Human review guidance", "Editorial approvals, audit trails, correction workflow"],
    ], [2100, 2850, 4410])
    add_note(document, "Recommended next milestone", "Add a small frontend that shows facts and evidence side by side, collects missing answers, and requires explicit editorial approval.")

    add_heading(document, "Appendix: implementation checkpoints", 1)
    for item in [
        "FastAPI starts and health checks pass.",
        "All supported file types normalize with source coordinates.",
        "Extraction always validates against its schema.",
        "Incomplete information cannot produce an article.",
        "Plain input cannot invent source metadata.",
        "RAG index/search/delete works with a synthetic document.",
        "Retrieved evidence is returned with grounded news.",
        "Automated tests and compile checks pass.",
        "Manuals match the current endpoints and environment settings.",
    ]:
        add_bullet(document, item, bullet_id)

    document.core_properties.title = "ApaKhabar Service Architecture and Development Guide"
    document.core_properties.subject = "Architecture concepts and incremental development sequence"
    document.core_properties.author = "ApaKhabar Project"
    document.core_properties.keywords = "ApaKhabar, architecture, FastAPI, hosted API, RAG, development"
    document.save(OUTPUT)


if __name__ == "__main__":
    build()
