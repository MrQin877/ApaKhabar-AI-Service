"""Bounded source-preserving extraction for long normalized documents."""
from app.schemas.information import ExtractionResponse
from app.services.ai_service import AIService

# Maximum data rows kept verbatim per table section; beyond this, only
# a deterministic summary (column headers, row count, samples) is sent.
_TABLE_SUMMARY_THRESHOLD = 20
_TABLE_SAMPLE_ROWS = 5


def _summarize_table_section(header_line, data_lines, table_key):
    """Replace a large table section with a compact summary.

    Returns a single chunk string containing the header row, a pre-computed
    row count, and a few sample data rows.  The model receives an
    authoritative count it must use verbatim instead of attempting to
    enumerate every row.
    """
    count = len(data_lines)
    samples = data_lines[:_TABLE_SAMPLE_ROWS]
    sheet_label = f' (sheet: {table_key[1]})' if table_key[1] else ''
    summary = header_line + '\n'
    source_marker = f"[source: filename={table_key[0]}" + (f", sheet={table_key[1]}" if table_key[1] else "") + ", section=table-summary]"
    summary += f"{source_marker} Total data rows in this table section{sheet_label}: {count}. "
    summary += f"The following {len(samples)} rows are representative samples.\n"
    summary += '\n'.join(samples)
    return summary


def _build_chunks(document):
    """Group document elements into <=10 KB text chunks.

    Large contiguous table sections (> _TABLE_SUMMARY_THRESHOLD data rows)
    are replaced by a compact summary so the model receives an authoritative
    row count and a few samples instead of every individual row.
    """
    from app.schemas.document import NormalizedDocument

    # -- Pass 1: collect elements into lines and detect table runs --
    lines = []  # (table_key | None, rendered_line, element_type)
    table_headers = {}
    for element in document.elements:
        part = NormalizedDocument(
            document_id=document.document_id, filename=document.filename,
            media_type=document.media_type, character_count=len(element.content),
            elements=[element],
        ).as_model_text()
        table = (element.source.filename, element.source.sheet)
        if element.element_type == 'table_row':
            table_headers.setdefault(table, part)
            lines.append((table, part, 'table_row'))
        else:
            # Split long paragraphs so each section stays under ~7 KB.
            marker, content = part.split('] ', 1)
            for start in range(0, len(content), 7000):
                section = marker + '] ' + content[start:start + 7500]
                lines.append((None, section, 'paragraph'))

    # -- Pass 2: identify contiguous table runs that exceed the threshold --
    processed = []  # list of rendered text lines after summarisation
    i = 0
    while i < len(lines):
        table_key, line, etype = lines[i]
        if etype != 'table_row':
            processed.append(line)
            i += 1
            continue
        # Collect the full contiguous run of rows for this table
        run_start = i
        while i < len(lines) and lines[i][0] == table_key and lines[i][2] == 'table_row':
            i += 1
        run = [l[1] for l in lines[run_start:i]]
        header = table_headers.get(table_key, run[0])
        data = [r for r in run if r != header]
        if len(data) > _TABLE_SUMMARY_THRESHOLD:
            processed.append(_summarize_table_section(header, data, table_key))
        else:
            processed.extend(run)

    # -- Pass 3: pack processed lines into <=10 KB chunks --
    chunks, current = [], ''
    for line in processed:
        if current and len(current) + 1 + len(line) > 10000:
            chunks.append(current)
            current = ''
        current += '\n' + line if current else line
    if current:
        chunks.append(current)
    if len(chunks) > 50:
        raise ValueError('Document exceeds 50 extraction chunks; split it into smaller documents')
    return chunks


def extract_document(document, query='', progress=None):
    chunks = _build_chunks(document)
    items, seen = [], set()
    for index, chunk in enumerate(chunks, 1):
        if progress:
            progress('extracting', f'Mengekstrak fakta: bagian {index} dari {len(chunks)}',
                     completed_chunks=index - 1, total_chunks=len(chunks))
        result = ExtractionResponse.model_validate(AIService.extract_information(chunk, query))
        for item in result.information:
            key = (item.type, item.title.casefold(), item.summary.casefold())
            if key not in seen:
                items.append(item)
                seen.add(key)
    if progress:
        progress('completed', 'Ekstraksi selesai; menyimpan hasil untuk ditinjau',
                 completed_chunks=len(chunks), total_chunks=len(chunks), information_count=len(items))
    return ExtractionResponse(information=items)
