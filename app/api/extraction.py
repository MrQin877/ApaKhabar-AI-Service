from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.services.ai_service import AIServiceError, OllamaService

router = APIRouter()


class DocumentRequest(BaseModel):
    content: str


@router.post("/extract-information")
def extract_information(req: DocumentRequest):
    try:
        return OllamaService.extract_information(req.content)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except AIServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
