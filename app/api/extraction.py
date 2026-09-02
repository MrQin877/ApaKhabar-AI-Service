from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ai_service import OllamaService

router = APIRouter()


class DocumentRequest(BaseModel):
    content: str


@router.post("/extract-information")
def extract_information(req: DocumentRequest):

    result = OllamaService.extract_information(req.content)

    return result