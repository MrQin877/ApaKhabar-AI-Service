import unittest
from types import SimpleNamespace

from app.schemas.document import DocumentElement, SourceReference
from app.services.rag_service import RagService, _collection_name


class RagServiceTests(unittest.TestCase):
    def test_index_version_creates_isolated_collection(self):
        legacy = _collection_name(
            "apakhabar_documents", "ollama", "qwen3-embedding:0.6b"
        )
        versioned = _collection_name(
            "apakhabar_documents", "ollama", "qwen3-embedding:0.6b", "v2"
        )

        self.assertNotEqual(versioned, legacy)
        self.assertIn("v2", versioned)

    def test_embedding_gemma_uses_separate_collection(self):
        name = _collection_name(
            "apakhabar_documents",
            "embedding_gemma",
            "google/embeddinggemma-300m",
        )
        self.assertEqual(
            name,
            "apakhabar_documents_google_embeddinggemma_300m",
        )

    def test_ollama_keeps_legacy_collection_name(self):
        self.assertEqual(
            _collection_name("apakhabar_documents", "ollama", "qwen"),
            "apakhabar_documents",
        )

    def test_chunking_keeps_source_markers(self):
        service = RagService.__new__(RagService)
        service.settings = SimpleNamespace(
            rag_chunk_size=1000,
            rag_chunk_overlap=100,
        )
        elements = [
            DocumentElement(
                element_type="paragraph",
                content="Verified announcement",
                source=SourceReference(filename="notice.pdf", page=2),
            )
        ]

        chunks = service._chunk_elements(elements)
        self.assertEqual(len(chunks), 1)
        self.assertIn("filename=notice.pdf, page=2", chunks[0]["source"])
        self.assertIn("[source:", chunks[0]["content"])

    def test_long_documents_create_multiple_chunks(self):
        service = RagService.__new__(RagService)
        service.settings = SimpleNamespace(
            rag_chunk_size=100,
            rag_chunk_overlap=10,
        )
        elements = [
            DocumentElement(
                element_type="paragraph",
                content=f"Paragraph {index} " + ("content " * 10),
                source=SourceReference(filename="notice.txt", paragraph=index),
            )
            for index in range(1, 4)
        ]

        chunks = service._chunk_elements(elements)
        self.assertGreater(len(chunks), 1)


if __name__ == "__main__":
    unittest.main()
