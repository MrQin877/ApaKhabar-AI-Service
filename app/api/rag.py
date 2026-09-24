from fastapi import APIRouter, HTTPException, Response, status

from app.schemas.news import NewsGenerationResponse
from app.schemas.rag import (
    IndexedInformationResponse,
    InformationIndexRequest,
    InformationSearchRequest,
    InformationSearchResponse,
    RagNewsRequest,
    RagNewsResponse,
    RagSearchRequest,
    RagSearchResponse,
)
from app.services.ai_service import AIServiceError, OllamaService
from app.services.rag_service import InformationRagService, RagService


router = APIRouter(prefix="/rag", tags=["rag"])


def _unavailable(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(exc),
    )


@router.post("/search", response_model=RagSearchResponse)
def search_documents(request: RagSearchRequest) -> RagSearchResponse:
    try:
        results = RagService().search(
            query=request.query,
            document_ids=request.document_ids,
            top_k=request.top_k,
        )
    except (AIServiceError, ValueError) as exc:
        raise _unavailable(exc) from exc
    return RagSearchResponse(query=request.query, results=results)


@router.post("/information/index", response_model=IndexedInformationResponse)
def index_information(request: InformationIndexRequest) -> IndexedInformationResponse:
    try:
        indexed = InformationRagService().index(request.items)
    except (AIServiceError, ValueError) as exc:
        raise _unavailable(exc) from exc
    return IndexedInformationResponse(indexed=indexed)


@router.post("/information/search", response_model=InformationSearchResponse)
def search_information(request: InformationSearchRequest) -> InformationSearchResponse:
    try:
        results = InformationRagService().search(
            request.query,
            owner_id=request.owner_id,
            top_k=request.top_k,
        )
    except (AIServiceError, ValueError) as exc:
        raise _unavailable(exc) from exc
    return InformationSearchResponse(query=request.query, results=results)


@router.delete("/information/{information_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_information(information_id: str) -> Response:
    InformationRagService().delete(information_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/generate-news", response_model=RagNewsResponse)
def generate_grounded_news(request: RagNewsRequest) -> RagNewsResponse:
    try:
        chunks = RagService().search(
            query=request.query,
            document_ids=request.document_ids,
            top_k=request.top_k,
        )
        retrieval = RagSearchResponse(query=request.query, results=chunks)
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No sufficiently relevant information was found.",
            )

        context = "\n\n".join(
            f"[source: {chunk.source}]\n{chunk.content}" for chunk in chunks
        )
        completeness = OllamaService.check_news_completeness(context)
        if completeness.status != "ready":
            return RagNewsResponse(
                retrieval=retrieval,
                news=NewsGenerationResponse(
                    completeness=completeness,
                    article=None,
                ),
            )

        article = OllamaService.write_news(
            text=context,
            language=request.language,
            tone=request.tone,
        )
        return RagNewsResponse(
            retrieval=retrieval,
            news=NewsGenerationResponse(
                completeness=completeness,
                article=article,
            ),
        )
    except HTTPException:
        raise
    except (AIServiceError, ValueError) as exc:
        raise _unavailable(exc) from exc


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_indexed_document(document_id: str) -> Response:
    RagService().delete_document(document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
