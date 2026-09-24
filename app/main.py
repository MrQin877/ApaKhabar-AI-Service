import hmac

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api.document import router
from app.api.extraction import router as extraction_router
from app.api.health import router as health_router
from app.api.news import router as news_router
from app.api.rag import router as rag_router
from app.api.tools import router as tools_router
from app.api.assistant import router as assistant_router
from app.core.config import get_settings

app = FastAPI(
    title="AI Document Intelligence API",
    version="1.0.0"
)


@app.middleware("http")
async def authenticate_internal_requests(request: Request, call_next):
    """Protect AI endpoints when a shared service token is configured."""
    settings = get_settings()
    expected = settings.internal_api_token
    is_health_check = request.url.path in {"/health", "/v1/health"}
    if expected and not is_health_check:
        supplied = request.headers.get("X-ApaKhabar-Service-Token", "")
        if not hmac.compare_digest(supplied, expected):
            return JSONResponse(status_code=401, content={"detail": "Invalid service token."})

    return await call_next(request)

app.include_router(router)
app.include_router(extraction_router)
app.include_router(health_router)
app.include_router(news_router)
app.include_router(rag_router)
app.include_router(tools_router)
app.include_router(assistant_router)

# Versioned internal API. Legacy paths remain available during migration.
for versioned_router in (
    router,
    extraction_router,
    health_router,
    news_router,
    rag_router,
    tools_router,
    assistant_router,
):
    app.include_router(versioned_router, prefix="/v1")
