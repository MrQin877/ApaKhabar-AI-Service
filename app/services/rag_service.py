from collections.abc import Iterable

import chromadb
from app.providers.models import Embeddings

from app.core.config import get_settings
from app.schemas.document import DocumentElement, NormalizedDocument
from app.schemas.rag import RetrievedChunk


class RagService:
    COLLECTION_NAME = "apakhabar_documents"

    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.embeddings = Embeddings(settings)
        self.chroma = chromadb.PersistentClient(path=settings.chroma_path)
        self.collection = self.chroma.get_or_create_collection(
            name=f"{self.COLLECTION_NAME}_{self.embeddings.fingerprint}",
            metadata={"hnsw:space": "cosine"},
        )

    def index_document(self, document: NormalizedDocument) -> int:
        chunks = self._chunk_elements(document.elements)
        if not chunks:
            return 0

        texts = [chunk["content"] for chunk in chunks]
        vectors = self.embeddings.encode(texts)

        ids = [f"{document.document_id}:{index}" for index in range(len(chunks))]
        metadatas = [
            {
                "document_id": document.document_id,
                "filename": document.filename,
                "source": chunk["source"],
                "chunk_index": index,
            }
            for index, chunk in enumerate(chunks)
        ]
        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=vectors,
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

        vectors = self.embeddings.encode([cleaned_query], query=True)

        where = None
        if document_ids:
            where = (
                {"document_id": document_ids[0]}
                if len(document_ids) == 1
                else {"document_id": {"$in": document_ids}}
            )

        result = self.collection.query(
            query_embeddings=vectors,
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
