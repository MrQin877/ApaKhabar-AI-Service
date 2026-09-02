from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.schemas.document import DocumentExtractionResponse, NormalizedDocument
from app.schemas.information import ExtractionResponse
from app.services.ai_service import AIServiceError, OllamaService
from app.services.document_service import DocumentService
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


@router.post("/upload", response_model=NormalizedDocument)
async def upload_document(file: UploadFile = File(...)) -> NormalizedDocument:
    return await _normalize_upload(file)


@router.post("/extract-information", response_model=DocumentExtractionResponse)
async def extract_uploaded_document(
    file: UploadFile = File(...),
) -> DocumentExtractionResponse:
    document = await _normalize_upload(file)
    try:
        extraction = ExtractionResponse.model_validate(
            OllamaService.extract_information(document.as_model_text())
        )
    except AIServiceError as exc:
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
