from fastapi import APIRouter
from pydantic import BaseModel

from app.services.ai_service import OllamaService

router = APIRouter()


class DocumentRequest(BaseModel):
    content: str


@router.post("/summarize")
def summarize_document(req: DocumentRequest):

    summary = OllamaService.summarize(req.content)

    return {
        "summary": summary
    }