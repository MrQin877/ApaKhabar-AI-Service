import hmac

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.agent import router as agent_router
from app.api.ai import router as ai_router
from app.api.document import router as document_router
from app.api.extraction import router as extraction_router
from app.api.health import router as health_router
from app.api.knowledge import router as knowledge_router
from app.api.news import router as news_router
from app.api.rag import router as rag_router
from app.core.config import get_settings

app = FastAPI(title="ApaKhabar Agentic Editorial API", version="2.0.0")


@app.middleware("http")
async def authenticate_service(request: Request, call_next):
    token = get_settings().apakhabar_ai_service_token
    if token and request.url.path not in {"/", "/health"}:
        supplied = request.headers.get("X-ApaKhabar-Service-Token", "")
        if not hmac.compare_digest(token, supplied):
            return JSONResponse(status_code=401, content={"detail": "Invalid service token"})
    return await call_next(request)


@app.get("/")
def root():
    return {"status": "running", "service": "ApaKhabar AI Service"}


for router in (document_router, ai_router, extraction_router, health_router,
               news_router, rag_router, agent_router, knowledge_router):
    app.include_router(router)
