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


class InformationIndexItem(BaseModel):
    information_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    labels: list[str] = Field(default_factory=list)
    fields: dict = Field(default_factory=dict)
    source: str = Field(min_length=1)
    owner_id: str = Field(min_length=1)

    def searchable_text(self) -> str:
        import json

        return "\n".join([
            f"Title: {self.title}",
            f"Summary: {self.summary}",
            f"Labels: {', '.join(self.labels)}",
            f"Fields: {json.dumps(self.fields, ensure_ascii=False)}",
        ])


class InformationIndexRequest(BaseModel):
    items: list[InformationIndexItem] = Field(min_length=1, max_length=100)


class IndexedInformationResponse(BaseModel):
    indexed: int


class InformationSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    owner_id: str = Field(min_length=1)
    top_k: int = Field(default=8, gt=0, le=20)


class RetrievedInformation(BaseModel):
    information_id: str
    document_id: str
    title: str
    content: str
    source: str
    distance: float | None = None


class InformationSearchResponse(BaseModel):
    query: str
    results: list[RetrievedInformation]
