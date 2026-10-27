import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import app
from app.providers.models import Embeddings, GenerationModel, ModelError
from app.schemas.document import DocumentElement, NormalizedDocument, SourceReference
from app.services.rag_service import RagService


class HostedMigrationTests(unittest.TestCase):
    def test_new_env_names_load_writer_and_evaluator_independently(self):
        with tempfile.TemporaryDirectory() as directory:
            env = Path(directory) / '.env'
            env.write_text('AI_MODEL=writer\nAI_API_KEY=writer-key\nEVALUATOR_MODEL=judge\nEVALUATOR_API_KEY=judge-key\n')
            settings = Settings(_env_file=env)
        self.assertEqual(settings.ai_model, 'writer')
        self.assertEqual(settings.ai_api_key, 'writer-key')
        self.assertEqual(settings.evaluator_model, 'judge')
        self.assertEqual(settings.evaluator_api_key, 'judge-key')
        self.assertEqual(settings.embedding_provider, 'embedding_gemma')

    def test_missing_api_credentials_fail_before_network(self):
        with patch('app.providers.models.requests.post') as post:
            with self.assertRaisesRegex(ModelError, 'API key and model'):
                GenerationModel(Settings(_env_file=None)).text('system', 'input')
        post.assert_not_called()

    def test_removed_embedding_runtime_rejected(self):
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, embedding_provider='ollama')

    def test_approved_embedding_fingerprint_unchanged(self):
        settings = Settings(_env_file=None)
        expected = hashlib.sha256(b'embedding_gemma:google/embeddinggemma-300m:768').hexdigest()[:16]
        self.assertEqual(Embeddings(settings).fingerprint, expected)

    def test_raw_document_index_and_query_use_same_embedding_adapter(self):
        settings = Settings(_env_file=None)
        with patch('app.services.rag_service.get_settings', return_value=settings), patch(
            'app.services.rag_service.Embeddings'
        ) as adapter, patch('app.services.rag_service.chromadb.PersistentClient') as client:
            adapter.return_value.fingerprint = 'test-model'
            adapter.return_value.encode.return_value = [[1., 0.]]
            service = RagService()
        collection = client.return_value.get_or_create_collection.return_value
        self.assertEqual(client.return_value.get_or_create_collection.call_args.kwargs['name'],
                         'apakhabar_documents_test-model')
        document = NormalizedDocument(document_id='test', filename='doc.txt', media_type='text/plain',
            character_count=5, elements=[DocumentElement(element_type='paragraph', content='Facts',
                source=SourceReference(filename='doc.txt', paragraph=1))])
        self.assertEqual(service.index_document(document), 1)
        self.assertEqual(collection.upsert.call_args.kwargs['embeddings'], [[1., 0.]])
        collection.query.return_value = {'ids': [[]], 'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
        self.assertEqual(service.search('Facts'), [])
        adapter.return_value.encode.assert_called_with(['Facts'], query=True)

    def test_health_selects_evaluator_and_requires_no_local_server(self):
        settings = Settings(_env_file=None, evaluator_enabled=True, ai_model='writer', evaluator_model='judge')
        model = Mock(name='judge-adapter')
        model.name = 'judge'
        model.structured.return_value = Mock(ok=True)
        with patch('app.main.get_settings', return_value=settings), patch(
            'app.api.health.get_settings', return_value=settings
        ), patch('app.providers.evaluator.build_evaluator', return_value=model):
            client = TestClient(app)
            result = client.get('/health/models?target=evaluator')
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()['target'], 'evaluator')
            self.assertEqual(result.json()['model'], 'judge')
            self.assertEqual(client.get('/health/ollama').status_code, 404)
