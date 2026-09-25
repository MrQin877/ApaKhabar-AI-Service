import unittest
from types import SimpleNamespace

from app.schemas.document import DocumentElement, SourceReference
from app.services.rag_service import (
    RagService,
    _collection_name,
    _combined_score,
    _keyword_score,
    _match_type,
)


class RagServiceTests(unittest.TestCase):
    def test_keyword_score_prefers_exact_regulation_identifier(self):
        exact = _keyword_score(
            "Peraturan Desa Nomor 12 Tahun 2026",
            "Peraturan Desa Nomor 12 Tahun 2026 mengatur pelayanan publik.",
        )
        unrelated = _keyword_score(
            "Peraturan Desa Nomor 12 Tahun 2026",
            "Kegiatan olahraga masyarakat berlangsung pada hari Minggu.",
        )

        self.assertGreater(exact, unrelated)
        self.assertEqual(exact, 1.0)

    def test_combined_score_rewards_semantic_and_keyword_match(self):
        semantic_only = _combined_score(0.3, 0.0, 0.7, 0.3)
        hybrid = _combined_score(0.3, 0.8, 0.7, 0.3)

        self.assertGreater(hybrid, semantic_only)
        self.assertEqual(_match_type(0.3, 0.8), "hybrid")
        self.assertEqual(_match_type(None, 0.8), "keyword")

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
