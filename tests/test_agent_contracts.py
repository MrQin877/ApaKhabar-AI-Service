import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError
import chromadb
from app.main import app
from app.core.config import Settings
from app.providers.models import GenerationModel, ModelError
from app.schemas.knowledge import KnowledgeItem
from app.services.knowledge_service import KnowledgeService
from app.services.ai_service import OllamaService
from app.schemas.information import ExtractionResponse


class Probe(BaseModel):
    ok: bool


class ContractTests(unittest.TestCase):
    def test_schema_repair_is_bounded(self):
        model = GenerationModel(Settings(_env_file=None))
        with patch.object(model, '_chat', side_effect=['not json', '{"ok":true}']) as chat:
            self.assertTrue(model.structured(Probe, 'System', 'Input').ok)
            self.assertEqual(chat.call_count, 2)
        with patch.object(model, '_chat', return_value='not json') as chat:
            with self.assertRaises(ModelError):
                model.structured(Probe, 'System', 'Input')
            self.assertEqual(chat.call_count, 2)

    @patch('app.providers.models.requests.post')
    def test_llama_adapter_sends_json_schema(self, post):
        post.return_value.json.return_value = {'choices': [{'message': {'content': '{"ok":true}'}}]}
        model = GenerationModel(Settings(_env_file=None, ai_provider='llama_cpp'))
        self.assertTrue(model.structured(Probe, 'System', 'Input').ok)
        self.assertEqual(post.call_args.kwargs['json']['response_format']['json_schema']['schema'], Probe.model_json_schema())

    def test_auth_and_index_contract_reject_unapproved(self):
        settings = Settings(_env_file=None, apakhabar_ai_service_token='test-secret')
        with patch('app.main.get_settings', return_value=settings):
            client = TestClient(app)
            self.assertEqual(client.get('/agent/skills').status_code, 401)
            response = client.post('/rag/information/index', headers={'X-ApaKhabar-Service-Token': 'test-secret'}, json={'items': [{
                'information_id': '1', 'document_id': '1', 'owner_id': '1', 'title': 'X', 'summary': 'X', 'source': 'X',
                'review_status': 'pending', 'is_active': True, 'archived': False}]})
            self.assertEqual(response.status_code, 422)

    def test_knowledge_filters_owner_and_allowlist(self):
        embeddings = Mock(fingerprint='test')
        embeddings.encode.side_effect = lambda texts, **kwargs: [[1., 0., 0.] for _ in texts]
        collection = chromadb.EphemeralClient().get_or_create_collection('agent_contract_test', metadata={'hnsw:space': 'cosine'})
        service = KnowledgeService(Settings(_env_file=None), embeddings=embeddings, collection=collection)
        for owner, id in [('one', '1'), ('two', '2')]:
            service.index([KnowledgeItem(information_id=id, document_id=id, owner_id=owner, title='Event', summary='Facts', source='doc', review_status='approved', is_active=True, archived=False)])
        self.assertEqual([r['information_id'] for r in service.search('Event', 'one')], ['1'])
        self.assertEqual(service.search('Event', 'one', []), [])
        self.assertEqual(service.search('Event', 'one', ['2']), [])
        service.delete('two', '1')
        self.assertEqual(len(service.search('Event', 'one')), 1)
        service.delete('one', '1')
        self.assertEqual(service.search('Event', 'one'), [])

    def test_batch_extraction_does_not_index_pending_information(self):
        with patch('app.api.document.extract_document', return_value=ExtractionResponse(information=[])) as extract, patch('app.api.document.RagService') as rag:
            response = TestClient(app).post('/documents/batch-extract', files=[('files', ('test.txt', b'Workshop in the village.', 'text/plain'))],
                data={'extraction_mode': 'targeted', 'extraction_query': 'workshop', 'keywords_json': '["village"]'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['results'][0]['status'], 'ready')
            self.assertEqual(response.json()['results'][0]['chunks_indexed'], 0)
            self.assertEqual(extract.call_args.args[1], 'workshop village')
            rag.assert_not_called()

    def test_provided_information_id_requires_eligibility(self):
        from app.schemas.news import NewsRequest
        with self.assertRaises(ValidationError):
            NewsRequest(information={'information': [{'information_id':'42', 'type':'General', 'title':'A', 'summary':'B', 'labels':[], 'fields':{}, 'evidence':[], 'confidence': .8}]})

    @patch.object(OllamaService, '_structured_chat')
    def test_extraction_rejects_invented_quote_location(self, chat):
        chat.return_value = ExtractionResponse(information=[{'type': 'General', 'title': 'Title', 'summary': 'Summary', 'labels': [], 'fields': {}, 'confidence': .9,
            'evidence': [{'source': 'page=2', 'quote': 'Real text'}]}])
        with self.assertRaises(ModelError):
            OllamaService.extract_information('[source: page=1] Real text')


if __name__ == '__main__':
    unittest.main()
