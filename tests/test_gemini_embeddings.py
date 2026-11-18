import hashlib
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.core.config import Settings
from app.providers.models import Embeddings, ModelError


class GeminiEmbeddingTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(_env_file=None, embedding_provider='gemini',
            embedding_model='gemini-embedding-001', embedding_api_key='test-key',
            embedding_dimensions=768)

    def test_document_and_query_use_distinct_tasks(self):
        model = Mock()
        model.embed_content.return_value = SimpleNamespace(embeddings=[
            SimpleNamespace(values=[3.0, 4.0] + [0.0] * 766)])
        with patch('google.genai.Client') as client:
            client.return_value.models = model
            adapter = Embeddings(self.settings)
            document = adapter.encode(['approved fact'])
            self.assertEqual(model.embed_content.call_args.kwargs['config'].task_type, 'RETRIEVAL_DOCUMENT')
            query = adapter.encode(['question'], query=True)
            self.assertEqual(model.embed_content.call_args.kwargs['config'].task_type, 'RETRIEVAL_QUERY')
        self.assertEqual(len(document[0]), 768)
        self.assertAlmostEqual(sum(value * value for value in query[0]), 1.0)

    def test_collection_fingerprint_separates_same_dimension_providers(self):
        adapter = Embeddings(self.settings)
        self.assertEqual(adapter.fingerprint,
            hashlib.sha256(b'gemini:gemini-embedding-001:768').hexdigest()[:16])
        local = Embeddings(self.settings.model_copy(update={
            'embedding_provider': 'embedding_gemma',
            'embedding_model': 'google/embeddinggemma-300m',
        }))
        self.assertNotEqual(adapter.fingerprint, local.fingerprint)

    def test_missing_key_fails_before_client_request(self):
        adapter = Embeddings(self.settings.model_copy(update={'embedding_api_key': ''}))
        with patch('google.genai.Client') as client:
            with self.assertRaisesRegex(ModelError, 'EMBEDDING_API_KEY'):
                adapter.encode(['fact'])
        client.assert_not_called()


if __name__ == '__main__':
    unittest.main()
