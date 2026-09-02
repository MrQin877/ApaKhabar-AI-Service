from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


OUTPUT = Path("docs/ApaKhabar_AI_Service_User_Developer_Manual.docx")
BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
INK = "0B2545"
MUTED = "5E6B78"
LIGHT_BLUE = "E8EEF5"
LIGHT_GRAY = "F2F4F7"
WHITE = "FFFFFF"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths: list[int]) -> None:
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.first_child_found_in("w:tblW")
    tbl_w.set(qn("w:w"), str(sum(widths)))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = OxmlElement("w:tblInd")
    tbl_ind.set(qn("w:w"), "120")
    tbl_ind.set(qn("w:type"), "dxa")
    tbl_pr.append(tbl_ind)

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        grid_col = OxmlElement("w:gridCol")
        grid_col.set(qn("w:w"), str(width))
        grid.append(grid_col)

    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.first_child_found_in("w:tcW")
            tc_w.set(qn("w:w"), str(width))
            tc_w.set(qn("w:type"), "dxa")
            cell.width = Inches(width / 1440)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell)


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("Page ")
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor.from_string(MUTED)
    fld_char_begin = OxmlElement("w:fldChar")
    fld_char_begin.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char_end = OxmlElement("w:fldChar")
    fld_char_end.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char_begin, instr_text, fld_char_end])


def configure_numbering(document: Document) -> tuple[int, int]:
    numbering = document.part.numbering_part.element

    def create_numbering(abstract_id: int, num_id: int, fmt: str, text: str) -> None:
        abstract = OxmlElement("w:abstractNum")
        abstract.set(qn("w:abstractNumId"), str(abstract_id))
        multi = OxmlElement("w:multiLevelType")
        multi.set(qn("w:val"), "singleLevel")
        abstract.append(multi)
        level = OxmlElement("w:lvl")
        level.set(qn("w:ilvl"), "0")
        start = OxmlElement("w:start")
        start.set(qn("w:val"), "1")
        num_fmt = OxmlElement("w:numFmt")
        num_fmt.set(qn("w:val"), fmt)
        lvl_text = OxmlElement("w:lvlText")
        lvl_text.set(qn("w:val"), text)
        suff = OxmlElement("w:suff")
        suff.set(qn("w:val"), "tab")
        p_pr = OxmlElement("w:pPr")
        tabs = OxmlElement("w:tabs")
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), "num")
        tab.set(qn("w:pos"), "540")
        tabs.append(tab)
        ind = OxmlElement("w:ind")
        ind.set(qn("w:left"), "540")
        ind.set(qn("w:hanging"), "270")
        spacing = OxmlElement("w:spacing")
        spacing.set(qn("w:after"), "80")
        spacing.set(qn("w:line"), "300")
        spacing.set(qn("w:lineRule"), "auto")
        p_pr.extend([tabs, ind, spacing])
        level.extend([start, num_fmt, lvl_text, suff, p_pr])
        abstract.append(level)
        numbering.append(abstract)
        num = OxmlElement("w:num")
        num.set(qn("w:numId"), str(num_id))
        abstract_ref = OxmlElement("w:abstractNumId")
        abstract_ref.set(qn("w:val"), str(abstract_id))
        num.append(abstract_ref)
        numbering.append(num)

    create_numbering(90, 90, "bullet", "•")
    create_numbering(91, 91, "decimal", "%1.")
    return 90, 91


def apply_numbering(paragraph, num_id: int) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    num_pr = OxmlElement("w:numPr")
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), "0")
    num_id_node = OxmlElement("w:numId")
    num_id_node.set(qn("w:val"), str(num_id))
    num_pr.extend([ilvl, num_id_node])
    p_pr.append(num_pr)


def add_numbering_instance(document: Document, num_id: int, abstract_id: int = 91) -> int:
    numbering = document.part.numbering_part.element
    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    abstract_ref = OxmlElement("w:abstractNumId")
    abstract_ref.set(qn("w:val"), str(abstract_id))
    num.append(abstract_ref)
    override = OxmlElement("w:lvlOverride")
    override.set(qn("w:ilvl"), "0")
    start_override = OxmlElement("w:startOverride")
    start_override.set(qn("w:val"), "1")
    override.append(start_override)
    num.append(override)
    numbering.append(num)
    return num_id


def add_bullet(document: Document, text: str, bullet_id: int) -> None:
    paragraph = document.add_paragraph(text)
    apply_numbering(paragraph, bullet_id)


def add_step(document: Document, text: str, number_id: int) -> None:
    paragraph = document.add_paragraph(text)
    apply_numbering(paragraph, number_id)


def add_code(document: Document, code: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.left_indent = Inches(0.18)
    paragraph.paragraph_format.right_indent = Inches(0.18)
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph.paragraph_format.keep_together = True
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), LIGHT_GRAY)
    paragraph._p.get_or_add_pPr().append(shading)
    lines = code.strip("\n").splitlines()
    for index, line in enumerate(lines):
        run = paragraph.add_run(line or " ")
        run.font.name = "Menlo"
        run._element.rPr.rFonts.set(qn("w:ascii"), "Menlo")
        run._element.rPr.rFonts.set(qn("w:hAnsi"), "Menlo")
        run.font.size = Pt(8.5)
        if index < len(lines) - 1:
            run.add_break()


def add_note(document: Document, label: str, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(5)
    paragraph.paragraph_format.space_after = Pt(8)
    paragraph.paragraph_format.left_indent = Inches(0.12)
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), LIGHT_BLUE)
    paragraph._p.get_or_add_pPr().append(shading)
    lead = paragraph.add_run(f"{label}: ")
    lead.bold = True
    lead.font.color.rgb = RGBColor.from_string(DARK_BLUE)
    paragraph.add_run(text)


def add_table(document: Document, headers: list[str], rows: list[list[str]], widths: list[int]):
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for index, header in enumerate(headers):
        cell = table.rows[0].cells[index]
        cell.text = header
        set_cell_shading(cell, LIGHT_BLUE)
        for run in cell.paragraphs[0].runs:
            run.bold = True
            run.font.color.rgb = RGBColor.from_string(INK)
    set_repeat_table_header(table.rows[0])
    for values in rows:
        cells = table.add_row().cells
        for index, value in enumerate(values):
            cells[index].text = value
            for run in cells[index].paragraphs[0].runs:
                run.font.size = Pt(10.25)
    set_table_geometry(table, widths)
    for row in table.rows:
        tr_pr = row._tr.get_or_add_trPr()
        cant_split = OxmlElement("w:cantSplit")
        tr_pr.append(cant_split)
    document.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def add_heading(document: Document, text: str, level: int) -> None:
    paragraph = document.add_heading(text, level=level)
    paragraph.paragraph_format.keep_with_next = True


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

    styles = document.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25

    heading_tokens = {
        "Heading 1": (16, BLUE, 18, 10),
        "Heading 2": (13, BLUE, 14, 7),
        "Heading 3": (12, DARK_BLUE, 10, 5),
    }
    for style_name, (size, color, before, after) in heading_tokens.items():
        style = styles[style_name]
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    bullet_id, number_id = configure_numbering(document)

    header = section.header.paragraphs[0]
    header.text = "ApaKhabar AI Service  |  User & Developer Manual"
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in header.runs:
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor.from_string(MUTED)
    add_page_number(section.footer.paragraphs[0])

    # Editorial cover pattern.
    document.add_paragraph().paragraph_format.space_after = Pt(80)
    kicker = document.add_paragraph()
    kicker.alignment = WD_ALIGN_PARAGRAPH.CENTER
    kicker_run = kicker.add_run("LOCAL-FIRST DOCUMENT INTELLIGENCE")
    kicker_run.bold = True
    kicker_run.font.size = Pt(10)
    kicker_run.font.color.rgb = RGBColor.from_string(BLUE)
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(14)
    title.paragraph_format.space_after = Pt(8)
    title_run = title.add_run("ApaKhabar AI Service")
    title_run.bold = True
    title_run.font.size = Pt(30)
    title_run.font.color.rgb = RGBColor.from_string(INK)
    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(28)
    subtitle_run = subtitle.add_run("User, Setup & Developer Manual")
    subtitle_run.font.size = Pt(16)
    subtitle_run.font.color.rgb = RGBColor.from_string(DARK_BLUE)
    summary = document.add_paragraph()
    summary.alignment = WD_ALIGN_PARAGRAPH.CENTER
    summary.paragraph_format.left_indent = Inches(0.55)
    summary.paragraph_format.right_indent = Inches(0.55)
    summary.add_run(
        "A practical guide to installing, operating, integrating, testing, and extending "
        "the document extraction, news-writing, and retrieval-augmented generation service."
    )
    document.add_paragraph().paragraph_format.space_after = Pt(55)
    metadata = document.add_paragraph()
    metadata.alignment = WD_ALIGN_PARAGRAPH.CENTER
    metadata.add_run("Version 1.0  •  September 2026  •  Local Ollama Edition").italic = True
    document.add_page_break()

    add_heading(document, "Contents", 1)
    contents = [
        "1. Service overview", "2. Installation and first run", "3. User workflows",
        "4. RAG workflow", "5. API reference", "6. Configuration",
        "7. Developer guide", "8. Testing and evaluation", "9. Security and operations",
        "10. Troubleshooting", "Appendix A. Quick commands", "Appendix B. Current limitations",
    ]
    for item in contents:
        add_bullet(document, item, bullet_id)
    add_note(document, "Audience", "End users, evaluators, frontend developers, backend developers, and project maintainers.")
    document.add_page_break()

    add_heading(document, "1. Service overview", 1)
    document.add_paragraph(
        "ApaKhabar converts supported documents or plain text into labelled, structured information, "
        "checks whether the facts are sufficient for news writing, and produces editable news drafts. "
        "All model inference and embeddings run locally through Ollama."
    )
    add_heading(document, "1.1 What the service does", 2)
    for item in [
        "Reads PDF, DOCX, XLSX, CSV, and TXT files.",
        "Preserves page, paragraph, sheet, and row references.",
        "Extracts titles, summaries, labels, fields, evidence, and a review confidence signal.",
        "Asks targeted questions when required news facts are absent.",
        "Generates English or Bahasa Melayu news drafts.",
        "Indexes and retrieves evidence from multiple or large documents using RAG.",
    ]:
        add_bullet(document, item, bullet_id)
    add_heading(document, "1.2 Processing paths", 2)
    add_table(document, ["Path", "Use when", "Flow"], [
        ["Direct", "One short document or plain text", "Normalize → extract → check → write"],
        ["RAG", "Large or multiple documents", "Normalize → chunk → embed → retrieve → check → write"],
    ], [1400, 3000, 4960])
    add_note(document, "Editorial rule", "A generated article is a draft. A human must verify names, dates, amounts, quotations, and evidence before publication.")

    add_heading(document, "2. Installation and first run", 1)
    add_heading(document, "2.1 Prerequisites", 2)
    for item in ["Python 3.11 or newer", "Ollama", "8 GB memory minimum; 16 GB recommended", "Approximately 4 GB free storage for the recommended models"]:
        add_bullet(document, item, bullet_id)
    add_heading(document, "2.2 Install models", 2)
    add_code(document, "ollama pull qwen3:4b\nollama pull qwen3-embedding:0.6b\nollama list")
    add_heading(document, "2.3 Create the Python environment", 2)
    for step in [
        "Clone or copy the repository and open a terminal in its root directory.",
        "Create and activate a virtual environment.",
        "Install dependencies and create the local environment file.",
        "Start FastAPI and verify both health endpoints.",
    ]:
        add_step(document, step, number_id)
    add_code(document, "python3 -m venv .venv\nsource .venv/bin/activate\npython -m pip install --upgrade pip\npip install -r requirements.txt\ncp .env.example .env\nuvicorn app.main:app --reload")
    add_note(document, "Windows", "Use .venv\\Scripts\\Activate.ps1 in PowerShell instead of the source command.")
    add_heading(document, "2.4 Verify installation", 2)
    add_code(document, "curl http://127.0.0.1:8000/health\ncurl http://127.0.0.1:8000/health/ollama")
    document.add_paragraph("Interactive API documentation is available at http://127.0.0.1:8000/docs.")

    add_heading(document, "3. User workflows", 1)
    add_heading(document, "3.1 Convert an uploaded document", 2)
    add_code(document, 'curl -X POST http://127.0.0.1:8000/documents/extract-information \\\n  -F "file=@report.pdf"')
    document.add_paragraph("Review the returned information items. Each item includes:")
    for item in [
        "type and labels for classification", "title and concise summary", "type-specific factual fields",
        "evidence quote and source location", "confidence from 0 to 1 as a review-priority signal",
    ]:
        add_bullet(document, item, bullet_id)
    add_note(document, "Confidence", "Confidence is generated by the model and is not a calibrated probability. Evidence should remain the main basis for verification.")
    add_heading(document, "3.2 Check missing information", 2)
    add_code(document, 'curl -X POST http://127.0.0.1:8000/news/check-completeness \\\n  -H "Content-Type: application/json" \\\n  -d \'{"information":"A community event will be held next month."}\'')
    document.add_paragraph("Ask the displayed questions, append the user's answers to the information, and repeat the check.")
    add_heading(document, "3.3 Generate a news draft", 2)
    add_code(document, 'curl -X POST http://127.0.0.1:8000/news/generate \\\n  -H "Content-Type: application/json" \\\n  -d \'{"information":"<verified facts>","language":"en","tone":"formal"}\'')
    for item in ["Use en for English or ms for Bahasa Melayu.", "If required facts are missing, article is null.", "Show warnings and sources beside the editable draft."]:
        add_bullet(document, item, bullet_id)

    add_heading(document, "4. RAG workflow", 1)
    document.add_paragraph("RAG retrieves the most relevant indexed passages before information checking and news writing.")
    add_heading(document, "4.1 Index", 2)
    add_code(document, 'curl -X POST http://127.0.0.1:8000/documents/index \\\n  -F "file=@background-report.pdf"')
    document.add_paragraph("Save the returned document_id. Documents are stored as embeddings and source-marked text chunks in the configured Chroma directory.")
    add_heading(document, "4.2 Search", 2)
    add_code(document, 'curl -X POST http://127.0.0.1:8000/rag/search \\\n  -H "Content-Type: application/json" \\\n  -d \'{"query":"What was announced?","document_ids":["<id>"],"top_k":5}\'')
    add_heading(document, "4.3 Generate grounded news", 2)
    add_code(document, 'curl -X POST http://127.0.0.1:8000/rag/generate-news \\\n  -H "Content-Type: application/json" \\\n  -d \'{"query":"Write news about the programme","document_ids":["<id>"],"language":"ms","tone":"formal"}\'')
    document.add_page_break()
    add_heading(document, "4.4 Delete indexed data", 2)
    add_code(document, "curl -X DELETE http://127.0.0.1:8000/rag/documents/<document-id>")

    add_heading(document, "5. API reference", 1)
    api_rows = [
        ["GET", "/health", "Application health"], ["GET", "/health/ollama", "Ollama and model health"],
        ["POST", "/documents/upload", "Normalize a file"], ["POST", "/documents/extract-information", "Extract labelled information"],
        ["POST", "/documents/index", "Index a file for RAG"], ["POST", "/extract-information", "Extract plain text"],
        ["POST", "/summarize", "Summarize plain text"], ["POST", "/news/check-completeness", "Find missing/conflicting facts"],
        ["POST", "/news/generate", "Generate from supplied facts"], ["POST", "/rag/search", "Retrieve indexed evidence"],
        ["POST", "/rag/generate-news", "Retrieve and write"], ["DELETE", "/rag/documents/{id}", "Delete indexed document"],
    ]
    add_table(document, ["Method", "Endpoint", "Purpose"], api_rows, [1050, 3600, 4710])

    document.add_page_break()
    add_heading(document, "6. Configuration", 1)
    config_rows = [
        ["OLLAMA_BASE_URL", "http://localhost:11434", "Ollama API address"],
        ["OLLAMA_GENERATION_MODEL", "qwen3:4b", "Extraction and writing model"],
        ["OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:0.6b", "Embedding model"],
        ["CHROMA_PATH", "./data/chroma", "Vector data directory"],
        ["MAX_UPLOAD_MB", "20", "Upload limit"], ["RAG_CHUNK_SIZE", "1000", "Approximate chunk characters"],
        ["RAG_CHUNK_OVERLAP", "150", "Chunk overlap"], ["RAG_TOP_K", "5", "Default retrieval count"],
        ["RAG_MAX_DISTANCE", "0.75", "Maximum accepted cosine distance"],
    ]
    add_table(document, ["Variable", "Default", "Purpose"], config_rows, [3000, 2600, 3760])
    add_note(document, "Embedding migration", "Changing the embedding model requires a new collection or full re-index because vector dimensions and spaces may differ.")

    document.add_page_break()
    add_heading(document, "7. Developer guide", 1)
    add_heading(document, "7.1 Code map", 2)
    add_table(document, ["Module", "Responsibility"], [
        ["app/services/document_service.py", "Parsing, validation, normalization, source coordinates"],
        ["app/services/ai_service.py", "Structured extraction, completeness, summaries, news writing"],
        ["app/services/rag_service.py", "Chunking, embeddings, Chroma indexing, retrieval"],
        ["app/schemas/", "Pydantic request and response contracts"],
        ["app/api/", "FastAPI transport and error mapping"],
        ["tests/", "Parser, service, API, and RAG checks"],
    ], [3900, 5460])
    add_heading(document, "7.2 Add a document format", 2)
    extension_number_id = add_numbering_instance(document, 92)
    for step in [
        "Add a parser that accepts bytes and returns DocumentElement objects.",
        "Preserve meaningful source coordinates such as page, row, or section.",
        "Register the extension in DocumentService.SUPPORTED_EXTENSIONS.",
        "Add valid, damaged, and empty-file tests.",
        "Verify upload and extraction through Swagger.",
    ]:
        add_step(document, step, extension_number_id)
    add_heading(document, "7.3 Change prompts or schemas", 2)
    document.add_paragraph("Update the Pydantic schema first, then the matching system prompt. Keep temperature at zero for extraction and validation. Run tests and a small labelled evaluation set after every change.")
    add_heading(document, "7.4 Frontend integration", 2)
    for item in [
        "Show upload progress and accepted file types before submission.",
        "Render evidence beside each extracted fact.",
        "Display missing questions as a form and merge answers explicitly.",
        "Keep the generated article editable and require approval before publishing.",
        "Configure CORS only for trusted frontend origins.",
    ]:
        add_bullet(document, item, bullet_id)

    add_heading(document, "8. Testing and evaluation", 1)
    add_code(document, "source .venv/bin/activate\npython -m unittest discover -s tests -v\npython -m compileall -q app tests")
    document.add_paragraph("For project evaluation, prepare manually labelled documents and measure:")
    for item in [
        "field precision and recall", "label accuracy", "source-reference correctness", "missing-question usefulness",
        "retrieval hit rate at top-k", "unsupported-fact rate in generated articles", "latency and memory use",
    ]:
        add_bullet(document, item, bullet_id)

    add_heading(document, "9. Security and operations", 1)
    for item in [
        "Treat document content as untrusted data and never as system instructions.",
        "Add authentication, authorization, tenant filters, and rate limiting before public use.",
        "Scan uploads and enforce retention/deletion policies.",
        "Use HTTPS and a reverse proxy outside local development.",
        "Do not expose Chroma data across users without tenant isolation.",
        "Log operational errors without storing sensitive document content.",
        "Require editorial review and maintain provenance for published claims.",
    ]:
        add_bullet(document, item, bullet_id)
    add_note(document, "Deployment status", "The current build is intended for local development, demonstrations, and controlled evaluation—not direct public production exposure.")

    document.add_page_break()
    add_heading(document, "10. Troubleshooting", 1)
    troubleshooting = [
        ["Ollama returns 503", "Start Ollama; compare ollama list with .env model names."],
        ["Slow response", "Use qwen3:4b, shorten input, reduce top-k, close memory-heavy apps."],
        ["No RAG result", "Confirm indexing; refine the query; cautiously tune maximum distance."],
        ["Scanned PDF is empty", "The file has no text layer; add OCR for image-only PDFs."],
        ["Frontend blocked", "Configure CORS for the exact trusted frontend origin."],
        ["Wrong vector dimension", "Embedding model changed; rebuild the collection and re-index."],
    ]
    add_table(document, ["Problem", "Action"], troubleshooting, [2800, 6560])

    add_heading(document, "Appendix A. Quick commands", 1)
    add_code(document, "ollama list\nsource .venv/bin/activate\nuvicorn app.main:app --reload\npython -m unittest discover -s tests -v")
    add_heading(document, "Appendix B. Current limitations", 1)
    for item in [
        "No OCR for image-only PDFs", "No user authentication or tenant isolation", "Synchronous model jobs can block under concurrent load",
        "No background queue or progress events", "Confidence is model-reported", "No automatic publication integration",
    ]:
        add_bullet(document, item, bullet_id)

    document.core_properties.title = "ApaKhabar AI Service User & Developer Manual"
    document.core_properties.subject = "Installation, API usage, RAG, development, and operations"
    document.core_properties.author = "ApaKhabar Project"
    document.core_properties.keywords = "ApaKhabar, Ollama, FastAPI, RAG, ChromaDB, news"
    document.save(OUTPUT)


if __name__ == "__main__":
    build()
