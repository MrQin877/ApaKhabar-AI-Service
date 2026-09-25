import json
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.schemas.document import DocumentExtractionResponse, NormalizedDocument
from app.services.ai_service import AIServiceError
from app.services.document_service import DocumentService
from app.services.extraction_service import extract_document
from app.schemas.rag import IndexedDocumentResponse
from app.services.rag_service import RagService


router = APIRouter(prefix="/documents", tags=["documents"])


async def _normalize_upload(file: UploadFile) -> NormalizedDocument:
    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    await file.close()

    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_mb} MB limit.",
        )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The uploaded file is empty.",
        )

    try:
        return await run_in_threadpool(
            DocumentService.normalize,
            data=data,
            filename=file.filename or "unnamed",
            media_type=file.content_type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.post("/upload", response_model=NormalizedDocument)
async def upload_document(file: UploadFile = File(...)) -> NormalizedDocument:
    return await _normalize_upload(file)


@router.post("/extract-information", response_model=DocumentExtractionResponse)
async def extract_uploaded_document(
    file: UploadFile = File(...),
) -> DocumentExtractionResponse:
    document = await _normalize_upload(file)
    try:
        extraction = await run_in_threadpool(extract_document, document)
    except (AIServiceError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return DocumentExtractionResponse(
        document=document,
        extraction=extraction,
    )


@router.post("/index", response_model=IndexedDocumentResponse)
async def index_uploaded_document(
    file: UploadFile = File(...),
) -> IndexedDocumentResponse:
    document = await _normalize_upload(file)
    try:
        chunks_indexed = await run_in_threadpool(lambda: RagService().index_document(document))
    except (AIServiceError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return IndexedDocumentResponse(
        document_id=document.document_id,
        filename=document.filename,
        chunks_indexed=chunks_indexed,
    )


@router.post('/batch-extract')
async def batch_extract(
    files: list[UploadFile] = File(...),
    extraction_mode: Literal['general', 'targeted'] = Form('general'),
    extraction_query: str = Form(''),
    keywords_json: str = Form('[]'),
):
    try:
        keywords = json.loads(keywords_json)
        if not isinstance(keywords, list) or any(not isinstance(k, str) for k in keywords):
            raise ValueError()
        if extraction_mode == 'targeted' and not extraction_query.strip() and not keywords:
            raise ValueError()
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, 'Targeted extraction requires a query or a JSON string list of keywords') from exc
    if len(files) > 20:
        raise HTTPException(422, 'At most 20 files per batch')
    results = []
    for file in files:
        try:
            document = await _normalize_upload(file)
            query = ' '.join([extraction_query, *keywords]) if extraction_mode == 'targeted' else ''
            extraction = await run_in_threadpool(extract_document, document, query)
            # Pending extractions never enter the approved evidence index.
            results.append({'status': 'ready', 'document': document.model_dump(), 'extraction': extraction.model_dump(), 'chunks_indexed': 0})
        except (HTTPException, AIServiceError, ValueError) as exc:
            results.append({'status': 'failed', 'filename': file.filename, 'error': str(getattr(exc, 'detail', exc))})
    return {'results': results}
