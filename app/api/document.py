from fastapi import APIRouter, UploadFile, File
import os
import shutil

from app.extractors.pdf_extractor import PDFExtractor
from app.services.ai_service import OllamaService

router = APIRouter()

UPLOAD_FOLDER = "app/uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@router.post("/upload")

async def upload_document(file: UploadFile = File(...)):

    file_path = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = PDFExtractor.extract(file_path)

    summary = OllamaService.summarize(result["content"])

    return {
        "pages": result["pages"],
        "summary": summary
    }