from collections.abc import Iterable
import re

import chromadb

from app.core.config import get_settings
from app.schemas.document import DocumentElement, NormalizedDocument
from app.schemas.rag import InformationIndexItem, RetrievedChunk, RetrievedInformation
from app.services.ai_service import AIServiceError
from app.services.model_providers import get_embedding_provider
from app.services.model_providers.base import ModelProviderError


def _collection_name(
    base_name: str,
    provider_name: str,
    model_name: str,
    index_version: str = "legacy",
) -> str:
    """Keep legacy Ollama collections while isolating incompatible vector spaces."""
    if index_version.strip().lower() == "legacy":
        if provider_name.strip().lower() == "ollama":
            return base_name
        identity = re.sub(r"[^a-z0-9]+", "_", model_name.lower()).strip("_")
        return f"{base_name}_{identity}"[:63].rstrip("_")

    identity_source = f"{provider_name}_{model_name}_{index_version}"
    identity = re.sub(r"[^a-z0-9]+", "_", identity_source.lower()).strip("_")
    return f"{base_name}_{identity}"[:63].rstrip("_")


class RagService:
    COLLECTION_NAME = "apakhabar_documents"

    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.embedding_provider = get_embedding_provider()
        self.chroma = chromadb.PersistentClient(path=settings.chroma_path)
        collection_name = _collection_name(
            self.COLLECTION_NAME,
            settings.embedding_provider,
            self.embedding_provider.model_name,
            settings.embedding_index_version,
        )
        self.collection = self.chroma.get_or_create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",
                "embedding_provider": settings.embedding_provider,
                "embedding_model": self.embedding_provider.model_name,
                "embedding_index_version": settings.embedding_index_version,
            },
        )

    def index_document(self, document: NormalizedDocument) -> int:
        chunks = self._chunk_elements(document.elements)
        if not chunks:
            return 0

        texts = [chunk["content"] for chunk in chunks]
        try:
            embeddings = self.embedding_provider.embed_documents(
                texts,
                titles=[document.filename] * len(texts),
            )
        except ModelProviderError as exc:
            raise AIServiceError(str(exc)) from exc

        ids = [f"{document.document_id}:{index}" for index in range(len(chunks))]
        metadatas = [
            {
                "document_id": document.document_id,
                "filename": document.filename,
                "source": chunk["source"],
                "chunk_index": index,
                "embedding_index_version": self.settings.embedding_index_version,
            }
            for index, chunk in enumerate(chunks)
        ]
        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(chunks)

    def search(
        self,
        query: str,
        document_ids: list[str] | None = None,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        cleaned_query = query.strip()
        if not cleaned_query:
            raise ValueError("Search query cannot be empty.")

        try:
            query_embedding = self.embedding_provider.embed_query(cleaned_query)
        except ModelProviderError as exc:
            raise AIServiceError(str(exc)) from exc

        where = None
        if document_ids:
            where = (
                {"document_id": document_ids[0]}
                if len(document_ids) == 1
                else {"document_id": {"$in": document_ids}}
            )

        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k or self.settings.rag_top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        retrieved: list[RetrievedChunk] = []
        for chunk_id, content, metadata, distance in zip(
            ids,
            documents,
            metadatas,
            distances,
            strict=False,
        ):
            if distance is not None and distance > self.settings.rag_max_distance:
                continue
            retrieved.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document_id=str(metadata["document_id"]),
                    filename=str(metadata["filename"]),
                    source=str(metadata["source"]),
                    content=content,
                    distance=distance,
                )
            )
        return retrieved

    def delete_document(self, document_id: str) -> None:
        self.collection.delete(where={"document_id": document_id})

    def _chunk_elements(self, elements: Iterable[DocumentElement]) -> list[dict[str, str]]:
        chunk_size = self.settings.rag_chunk_size
        overlap = self.settings.rag_chunk_overlap
        chunks: list[dict[str, str]] = []
        current_parts: list[str] = []
        current_sources: list[str] = []

        def flush() -> None:
            if not current_parts:
                return
            chunks.append(
                {
                    "content": "\n".join(current_parts),
                    "source": "; ".join(dict.fromkeys(current_sources)),
                }
            )

        for element in elements:
            source = self._source_label(element)
            marked_text = f"[source: {source}] {element.content}"
            candidate_size = sum(len(part) for part in current_parts) + len(marked_text)
            if current_parts and candidate_size > chunk_size:
                previous_text = "\n".join(current_parts)
                previous_source = current_sources[-1]
                flush()
                tail = previous_text[-overlap:].strip() if overlap else ""
                current_parts = [tail] if tail else []
                current_sources = [previous_source] if tail else []

            current_parts.append(marked_text)
            current_sources.append(source)

        flush()
        return chunks

    @staticmethod
    def _source_label(element: DocumentElement) -> str:
        source = element.source
        parts = [f"filename={source.filename}"]
        if source.page is not None:
            parts.append(f"page={source.page}")
        if source.sheet is not None:
            parts.append(f"sheet={source.sheet}")
        if source.row is not None:
            parts.append(f"row={source.row}")
        if source.paragraph is not None:
            parts.append(f"paragraph={source.paragraph}")
        return ", ".join(parts)


class InformationRagService:
    COLLECTION_NAME = "apakhabar_information_items"

    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.embedding_provider = get_embedding_provider()
        self.chroma = chromadb.PersistentClient(path=settings.chroma_path)
        collection_name = _collection_name(
            self.COLLECTION_NAME,
            settings.embedding_provider,
            self.embedding_provider.model_name,
            settings.embedding_index_version,
        )
        self.collection = self.chroma.get_or_create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",
                "embedding_provider": settings.embedding_provider,
                "embedding_model": self.embedding_provider.model_name,
                "embedding_index_version": settings.embedding_index_version,
            },
        )

    def index(self, items: list[InformationIndexItem]) -> int:
        texts = [item.searchable_text() for item in items]
        try:
            embeddings = self.embedding_provider.embed_documents(
                texts,
                titles=[item.title for item in items],
            )
        except ModelProviderError as exc:
            raise AIServiceError(str(exc)) from exc

        self.collection.upsert(
            ids=[item.information_id for item in items],
            documents=texts,
            embeddings=embeddings,
            metadatas=[{
                "information_id": item.information_id,
                "document_id": item.document_id,
                "title": item.title,
                "source": item.source,
                "owner_id": item.owner_id,
                "status": "approved",
                "embedding_index_version": self.settings.embedding_index_version,
            } for item in items],
        )
        return len(items)

    def search(self, query: str, owner_id: str, top_k: int = 8) -> list[RetrievedInformation]:
        cleaned = query.strip()
        if not cleaned:
            raise ValueError("Search query cannot be empty.")
        try:
            query_embedding = self.embedding_provider.embed_query(cleaned)
        except ModelProviderError as exc:
            raise AIServiceError(str(exc)) from exc

        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"$and": [{"owner_id": owner_id}, {"status": "approved"}]},
            include=["documents", "metadatas", "distances"],
        )
        retrieved: list[RetrievedInformation] = []
        for content, metadata, distance in zip(
            result.get("documents", [[]])[0],
            result.get("metadatas", [[]])[0],
            result.get("distances", [[]])[0],
            strict=False,
        ):
            if distance is not None and distance > self.settings.rag_max_distance:
                continue
            retrieved.append(RetrievedInformation(
                information_id=str(metadata["information_id"]),
                document_id=str(metadata["document_id"]),
                title=str(metadata["title"]),
                content=content,
                source=str(metadata["source"]),
                distance=distance,
            ))
        return retrieved

    def delete(self, information_id: str) -> None:
        self.collection.delete(ids=[information_id])
