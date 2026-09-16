from fastapi import APIRouter, HTTPException, status

from app.schemas.tools import AskUserChoice, WebSearchInput, WebSearchResult
from app.services.web_search_service import WebSearchError, WebSearchService


router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/definitions")
def tool_definitions() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": (
                    "Search the current web for factual claims about real people, "
                    "events, companies, products, or recent news. Do not call for "
                    "explicitly fictional, hypothetical, satire, or parody requests."
                ),
                "parameters": WebSearchInput.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "ask_user_choice",
                "description": (
                    "Ask exactly one material clarifying question as tappable choices. "
                    "Use only when proceeding would materially change accuracy, tone, "
                    "or format."
                ),
                "parameters": AskUserChoice.model_json_schema(),
            },
        },
    ]


@router.post("/web-search", response_model=list[WebSearchResult])
def web_search(payload: WebSearchInput) -> list[WebSearchResult]:
    try:
        return WebSearchService.search(payload)
    except WebSearchError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
