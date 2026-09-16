from pydantic import BaseModel, Field

from app.schemas.news import NewsGenerationResponse, NewsLanguage


class IndexedDocumentResponse(BaseModel):
    document_id: str
    filename: str
    chunks_indexed: int


class RagSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    document_ids: list[str] = Field(default_factory=list)
    top_k: int | None = Field(default=None, gt=0, le=20)


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    source: str
    content: str
    distance: float | None = None


class RagSearchResponse(BaseModel):
    query: str
    results: list[RetrievedChunk]


class RagNewsRequest(RagSearchRequest):
    language: NewsLanguage = "id"
    tone: str = Field(default="formal", min_length=1, max_length=50)


class RagNewsResponse(BaseModel):
    retrieval: RagSearchResponse
    news: NewsGenerationResponse
