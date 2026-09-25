"""Approved evidence only. Raw-document collections are never used by agents."""
import json
import hashlib
import chromadb
from app.core.config import get_settings
from app.providers.models import Embeddings


class KnowledgeService:
    def __init__(self, settings=None, embeddings=None, collection=None):
        self.settings = settings or get_settings()
        self.embeddings = embeddings or Embeddings(self.settings)
        self.collection = collection if collection is not None else chromadb.PersistentClient(path=self.settings.chroma_path).get_or_create_collection(
            name=f"approved_information_{self.embeddings.fingerprint}", metadata={"hnsw:space": "cosine"})

    @staticmethod
    def key(owner, information_id):
        return hashlib.sha256(f"{owner}:{information_id}".encode()).hexdigest()

    @staticmethod
    def filters(owner):
        return [{"owner_id": owner}, {"review_status": "approved"}, {"is_active": True}, {"archived": False}]

    def index(self, items):
        texts = [json.dumps(item.model_dump(), ensure_ascii=False) for item in items]
        vectors = self.embeddings.encode(texts)
        self.collection.upsert(ids=[self.key(i.owner_id, i.information_id) for i in items], documents=texts, embeddings=vectors,
            metadatas=[{"owner_id": i.owner_id, "information_id": i.information_id, "document_id": i.document_id,
                        "review_status": i.review_status, "is_active": i.is_active, "archived": i.archived} for i in items])
        return len(items)

    def search(self, query, owner_id, information_ids=None, top_k=5):
        if information_ids == [] or self.collection.count() == 0:
            return []
        filters = self.filters(owner_id)
        if information_ids is not None:
            filters.append({"information_id": {"$in": information_ids}})
        result = self.collection.query(query_embeddings=self.embeddings.encode([query], query=True),
            where={"$and": filters}, n_results=min(top_k, self.collection.count()), include=["documents", "distances"])
        found = []
        for text, distance in zip(result["documents"][0], result["distances"][0]):
            if distance <= self.settings.rag_max_distance:
                item = json.loads(text)
                item.update(source_id=f"information:{item['information_id']}", distance=distance, content=item['title'] + '\n' + item['summary'] + '\n' + json.dumps(item['fields'], ensure_ascii=False))
                found.append(item)
        return found

    def delete(self, owner_id, information_id):
        self.collection.delete(ids=[self.key(owner_id, information_id)])
