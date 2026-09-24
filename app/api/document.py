from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.schemas.document import (
    BatchDocumentExtractionItem,
    BatchDocumentExtractionResponse,
    DocumentExtractionResponse,
    NormalizedDocument,
)
from app.schemas.information import ExtractionContext, ExtractionResponse
from app.services.ai_service import AIServiceError, OllamaService
from app.services.document_service import DocumentService
from app.schemas.rag import IndexedDocumentResponse
from app.services.rag_service import RagService


router = APIRouter(prefix="/documents", tags=["documents"])
MAX_BATCH_FILES = 5


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
        return DocumentService.normalize(
            data=data,
            filename=file.filename or "unnamed",
            media_type=file.content_type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.post("/extract-information", response_model=DocumentExtractionResponse)
async def extract_uploaded_document(
    file: UploadFile = File(...),
    extraction_mode: str = Form(default="general"),
    extraction_query: str | None = Form(default=None),
    keywords: list[str] = Form(default=[]),
    keywords_json: str | None = Form(default=None),
) -> DocumentExtractionResponse:
    document = await _normalize_upload(file)
    try:
        if keywords_json:
            import json

            keywords = json.loads(keywords_json)
        context = ExtractionContext(
            mode=extraction_mode,
            query=extraction_query,
            keywords=keywords,
        )
        extraction = ExtractionResponse.model_validate(
            OllamaService.extract_information(document.as_model_text(), context)
        )
    except (AIServiceError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return DocumentExtractionResponse(
        document=document,
        extraction=extraction,
    )


@router.post("/batch-extract", response_model=BatchDocumentExtractionResponse)
async def batch_extract_uploaded_documents(
    files: list[UploadFile] = File(...),
    extraction_mode: str = Form(default="general"),
    extraction_query: str | None = Form(default=None),
    keywords: list[str] = Form(default=[]),
    keywords_json: str | None = Form(default=None),
) -> BatchDocumentExtractionResponse:
    if not 1 <= len(files) <= MAX_BATCH_FILES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Upload between 1 and {MAX_BATCH_FILES} files per request.",
        )

    try:
        if keywords_json:
            import json

            keywords = json.loads(keywords_json)
        context = ExtractionContext(
            mode=extraction_mode,
            query=extraction_query,
            keywords=keywords,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    results: list[BatchDocumentExtractionItem] = []
    for file in files:
        filename = file.filename or "unnamed"
        try:
            document = await _normalize_upload(file)
            rag = RagService()
            chunks_indexed = rag.index_document(document)
            extraction_text = document.as_model_text()
            if context.mode == "targeted":
                retrieved = rag.search(
                    context.effective_query() or "",
                    document_ids=[document.document_id],
                    top_k=max(8, get_settings().rag_top_k),
                )
                if not retrieved:
                    raise ValueError("No document sections matched the extraction request.")
                extraction_text = "\n\n".join(
                    f"[source: {chunk.source}] {chunk.content}" for chunk in retrieved
                )
            extraction = ExtractionResponse.model_validate(
                OllamaService.extract_information(extraction_text, context)
            )
            results.append(
                BatchDocumentExtractionItem(
                    filename=filename,
                    status="ready",
                    document=document,
                    extraction=extraction,
                    chunks_indexed=chunks_indexed,
                )
            )
        except HTTPException as exc:
            results.append(
                BatchDocumentExtractionItem(
                    filename=filename,
                    status="failed",
                    error=str(exc.detail),
                )
            )
        except (AIServiceError, ValueError) as exc:
            results.append(
                BatchDocumentExtractionItem(
                    filename=filename,
                    status="failed",
                    error=str(exc),
                )
            )

    return BatchDocumentExtractionResponse(results=results)


@router.post("/index", response_model=IndexedDocumentResponse)
async def index_uploaded_document(
    file: UploadFile = File(...),
) -> IndexedDocumentResponse:
    document = await _normalize_upload(file)
    try:
        chunks_indexed = RagService().index_document(document)
    except AIServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return IndexedDocumentResponse(
        document_id=document.document_id,
        filename=document.filename,
        chunks_indexed=chunks_indexed,
    )
