import unittest
from unittest.mock import Mock, patch

from app.core.config import Settings
from app.providers.models import GenerationModel, ModelError


class OpenAIProviderTests(unittest.TestCase):
    @patch('app.providers.models.time.sleep')
    def test_internal_error_recovers_without_exposing_provider_message(self, sleep):
        failure = Mock(ok=False, status_code=500, text='PRIVATE')
        success = Mock(ok=True)
        success.json.return_value = {'choices': [{'message': {'content': 'OK'}}]}
        with patch('app.providers.models.requests.post', side_effect=[failure, success]) as post:
            self.assertEqual(self.model().text('system', 'test'), 'OK')
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(1)

    @patch('app.providers.models.time.sleep')
    def test_persistent_internal_error_stops_after_three_requests(self, sleep):
        failure = Mock(ok=False, status_code=500, text='PRIVATE')
        failure.json.return_value = {'error': {'status': 'INTERNAL', 'message': 'PRIVATE'}}
        with patch('app.providers.models.requests.post', return_value=failure) as post:
            with self.assertRaises(ModelError) as raised:
                self.model().text('system', 'test')
        self.assertEqual(post.call_count, 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [1, 2])
        self.assertIn('HTTP 500', str(raised.exception))
        self.assertNotIn('PRIVATE', str(raised.exception))

    def test_hosted_gemma_uses_json_mode_and_validates_extraction(self):
        from app.services.ai_service import ExtractionChunkResponse
        model = GenerationModel(Settings(_env_file=None,
            ai_base_url='https://generativelanguage.googleapis.com/v1beta/openai',
            ai_model='gemma-4-26b-a4b-it', ai_api_key='test-key'))
        response = Mock(ok=True)
        response.json.side_effect = [
            {'choices': [{'message': {'content': '{"information": "invalid"}'}}]},
            {'choices': [{'message': {'content': '{"information": []}'}}]},
        ]
        with patch('app.providers.models.requests.post', return_value=response) as post:
            result = model.structured(ExtractionChunkResponse, 'Extract facts.', 'No facts.')
        self.assertEqual(result.information, [])
        self.assertEqual(post.call_count, 2)
        for call in post.call_args_list:
            payload = call.kwargs['json']
            self.assertEqual(payload['response_format'], {'type': 'json_object'})
            self.assertIn('"$defs"', payload['messages'][0]['content'])
            self.assertEqual(payload['messages'][1]['content'], 'No facts.')

    def test_local_gemma_keeps_native_schema(self):
        response = Mock(ok=True)
        response.json.return_value = {'choices': [{'message': {'content': '{}'}}]}
        model = GenerationModel(Settings(_env_file=None, ai_base_url='http://localhost:8080/v1',
            ai_model='gemma-4-26b-a4b-it', ai_api_key='local'))
        with patch('app.providers.models.requests.post', return_value=response) as post:
            model._chat([{'role': 'system', 'content': 'Test'}], {'type': 'object'}, 0)
        self.assertEqual(post.call_args.kwargs['json']['response_format']['type'], 'json_schema')

    def model(self, endpoint='https://api.openai.com/v1'):
        return GenerationModel(Settings(_env_file=None, 
            ai_base_url=endpoint, ai_model='gpt-5.4-mini', ai_api_key='test-key'))

    def test_openai_reasoning_request_uses_completion_budget_without_temperature(self):
        response = Mock(ok=True)
        response.json.return_value = {'choices': [{'message': {'content': 'OK'}}]}
        with patch('app.providers.models.requests.post', return_value=response) as post:
            self.assertEqual(self.model().text('system', 'test'), 'OK')
        payload = post.call_args.kwargs['json']
        self.assertEqual(payload['max_completion_tokens'], 4096)
        self.assertNotIn('max_tokens', payload)
        self.assertNotIn('temperature', payload)

    def test_other_providers_keep_existing_parameters(self):
        response = Mock(ok=True)
        response.json.return_value = {'choices': [{'message': {'content': 'OK'}}]}
        with patch('app.providers.models.requests.post', return_value=response) as post:
            self.model('https://api.groq.com/openai/v1').text('system', 'test')
        self.assertIn('max_tokens', post.call_args.kwargs['json'])
        self.assertIn('temperature', post.call_args.kwargs['json'])

    def test_quota_error_is_actionable_without_leaking_provider_message(self):
        response = Mock(ok=False, status_code=429, text='quota exceeded')
        response.json.return_value = {'error': {'code': 'insufficient_quota',
            'type': 'insufficient_quota', 'param': None, 'message': 'PRIVATE_SOURCE_VALUE'}}
        with patch('app.providers.models.requests.post', return_value=response):
            with self.assertRaises(ModelError) as raised:
                self.model().text('system', 'test')
        self.assertIn('HTTP 429', str(raised.exception))
        self.assertIn('insufficient_quota', str(raised.exception))
        self.assertNotIn('PRIVATE_SOURCE_VALUE', str(raised.exception))

    def test_non_json_error_retains_http_status(self):
        response = Mock(ok=False, status_code=502, text='gateway unavailable')
        response.json.side_effect = ValueError()
        with patch('app.providers.models.requests.post', return_value=response):
            with self.assertRaisesRegex(ModelError, 'HTTP 502'):
                self.model().text('system', 'test')

    def test_timeout_identifies_endpoint_model_and_limit(self):
        import requests
        with patch('app.providers.models.requests.post', side_effect=requests.ReadTimeout('PRIVATE')):
            with self.assertRaises(ModelError) as raised:
                self.model().text('system', 'test')
        message = str(raised.exception)
        self.assertIn('api.openai.com', message)
        self.assertIn('gpt-5.4-mini', message)
        self.assertIn('180s', message)
        self.assertNotIn('PRIVATE', message)

    def test_exhausted_credit_has_billing_guidance(self):
        response = Mock(ok=False, status_code=429, text='quota')
        response.json.return_value = {'error': {'code': 'credit_balance_exhausted', 'type': 'insufficient_quota'}}
        with patch('app.providers.models.requests.post', return_value=response):
            with self.assertRaisesRegex(ModelError, 'billing balance'):
                self.model().text('system', 'test')

    @patch('app.providers.models.time.sleep')
    def test_temporary_failure_recovers_with_bounded_retry(self, sleep):
        unavailable = Mock(ok=False, status_code=503)
        success = Mock(ok=True)
        success.json.return_value = {'choices': [{'message': {'content': 'OK'}}]}
        with patch('app.providers.models.requests.post', side_effect=[unavailable, success]) as post:
            self.assertEqual(self.model().text('system', 'test'), 'OK')
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(1)

    @patch('app.providers.models.time.sleep')
    def test_google_list_error_and_retry_limit(self, sleep):
        response = Mock(ok=False, status_code=503, text='unavailable')
        response.json.return_value = [{'error': {'code': 503, 'status': 'UNAVAILABLE', 'message': 'PRIVATE'}}]
        with patch('app.providers.models.requests.post', return_value=response) as post:
            with self.assertRaises(ModelError) as raised:
                self.model().text('system', 'test')
        self.assertEqual(post.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertIn('UNAVAILABLE', str(raised.exception))
        self.assertNotIn('PRIVATE', str(raised.exception))

    def test_quota_and_auth_errors_are_not_retried(self):
        for status in (400, 401, 403, 404, 429):
            with self.subTest(status=status):
                response = Mock(ok=False, status_code=status, text='error')
                response.json.return_value = {'error': {'code': 'rejected'}}
                with patch('app.providers.models.requests.post', return_value=response) as post:
                    with self.assertRaises(ModelError):
                        self.model().text('system', 'test')
                post.assert_called_once()

    @patch('app.providers.models.time.monotonic', side_effect=[0, 0, 180])
    @patch('app.providers.models.time.sleep')
    def test_retry_stops_when_time_budget_is_exhausted(self, sleep, monotonic):
        response = Mock(ok=False, status_code=503, text='unavailable')
        response.json.return_value = {'error': {'status': 'UNAVAILABLE'}}
        with patch('app.providers.models.requests.post', return_value=response) as post:
            with self.assertRaisesRegex(ModelError, 'HTTP 503'):
                self.model().text('system', 'test')
        post.assert_called_once()
        sleep.assert_not_called()
