from fastapi import FastAPI
from app.api.document import router
from app.api.extraction import router as extraction_router
from app.api.health import router as health_router
from app.api.news import router as news_router
from app.api.rag import router as rag_router
from app.api.tools import router as tools_router
from app.api.assistant import router as assistant_router

app = FastAPI(
    title="AI Document Intelligence API",
    version="1.0.0"
)

app.include_router(router)
app.include_router(extraction_router)
app.include_router(health_router)
app.include_router(news_router)
app.include_router(rag_router)
app.include_router(tools_router)
app.include_router(assistant_router)
