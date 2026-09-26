"""Bounded source-preserving extraction for long normalized documents."""
from app.schemas.information import ExtractionResponse
from app.services.ai_service import AIService


def extract_document(document, query='', progress=None):
    from app.schemas.document import NormalizedDocument
    chunks, current = [], ''
    for element in document.elements:
        part = NormalizedDocument(document_id=document.document_id, filename=document.filename,
            media_type=document.media_type, character_count=len(element.content), elements=[element]).as_model_text()
        marker, content = part.split('] ', 1)
        for start in range(0, len(content), 7000):
            section = marker + '] ' + content[start:start + 7500]
            if current and len(current) + len(section) > 10000:
                chunks.append(current)
                current = ''
            current += '\n' + section
    if current:
        chunks.append(current)
    if len(chunks) > 50:
        raise ValueError('Document exceeds 50 extraction chunks; split it into smaller documents')
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
