"""Bounded source-preserving extraction for long normalized documents."""
from app.schemas.information import ExtractionResponse
from app.services.ai_service import AIService


def extract_document(document, query=''):
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
    for chunk in chunks:
        result = ExtractionResponse.model_validate(AIService.extract_information(chunk, query))
        for item in result.information:
            key = (item.type, item.title.casefold(), item.summary.casefold())
            if key not in seen:
                items.append(item)
                seen.add(key)
    return ExtractionResponse(information=items)
