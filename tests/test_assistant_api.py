import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.api.assistant import ConversationResponse
from app.providers.models import ModelError
from app.core.config import Settings


class AssistantApiTests(unittest.TestCase):
    def setUp(self):
        self.settings = patch('app.main.get_settings', return_value=Settings(_env_file=None))
        self.settings.start()
        self.addCleanup(self.settings.stop)
        self.client = TestClient(app)

    def test_laravel_contract_registered(self):
        response = ConversationResponse(intent='question', answer='Ada 60 peserta.', source_ids=[7])
        with patch('app.api.assistant.GenerationModel.structured', return_value=response) as model:
            result = self.client.post('/assistant/respond', json={
                'message': 'Berapa peserta?', 'history': [{'role': 'assistant', 'content': None}],
                'information': [{'id': 7, 'title': 'Acara', 'summary': '60 peserta', 'fields': [], 'evidence': [], 'review_status': 'approved'}]})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['source_ids'], [7])
        self.assertIn('60 peserta', model.call_args.args[2])

    def test_unknown_sources_rejected(self):
        with patch('app.api.assistant.GenerationModel.structured', return_value=ConversationResponse(
                intent='question', answer='Jawaban', source_ids=[999])):
            self.assertEqual(self.client.post('/assistant/respond', json={'message': 'Apa?'}).status_code, 502)

    def test_provider_failure_and_blank_input(self):
        with patch('app.api.assistant.GenerationModel.structured', side_effect=ModelError('offline')):
            self.assertEqual(self.client.post('/assistant/respond', json={'message': 'Halo'}).status_code, 503)
            self.assertEqual(self.client.post('/assistant/respond', json={'message': '  '}).status_code, 422)
