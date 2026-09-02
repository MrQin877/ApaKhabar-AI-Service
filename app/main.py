from fastapi import FastAPI
from app.api.document import router
from app.api.ai import router as ai_router
from app.api.extraction import router as extraction_router

app = FastAPI(
    title="AI Document Intelligence API",
    version="1.0.0"
)

@app.get("/")
def root():
    return {
        "status": "running",
        "service": "AI Document Intelligence"
    }

app.include_router(router)
app.include_router(ai_router)
app.include_router(extraction_router)