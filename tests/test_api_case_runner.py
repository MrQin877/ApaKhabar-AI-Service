import unittest
from scripts.run_api_cases import payload_for
from app.schemas.news import NewsRequest
from app.api.assistant import ConversationRequest

class ApiCaseRunnerTests(unittest.TestCase):
    def test_answer_key_never_enters_requests(self):
        extraction = {'extraction': {'information': [{'information_id': 'old-id', 'type': 'Event', 'title': 'Activity', 'summary': 'Source fact', 'labels': [], 'fields': {}, 'evidence': [], 'confidence': .8}]}}
        for mode, schema in [('draft', NewsRequest), ('analysis', ConversationRequest)]:
            case = {'mode': mode, 'prompt': 'Summarise this', 'review_checklist': ['SECRET_EXPECTATION']}
            endpoint, payload = payload_for(case, [extraction], 'eval-test')
            schema.model_validate(payload)
            self.assertNotIn('SECRET_EXPECTATION', str(payload))
            self.assertNotIn('old-id', str(payload))

    def test_two_turn_history_is_indexed_not_injected_and_cleaned(self):
        import json
        from unittest.mock import Mock
        from scripts.run_api_cases import ROOT, run_historical
        directory = ROOT / 'evaluations/api_cases'
        case = json.loads((directory/'TC12.json').read_text())
        item = {'type': 'Event', 'title': 'Historical volcano report', 'summary': 'HISTORY_ONLY', 'labels': [], 'fields': {}, 'evidence': [], 'confidence': .9}
        old = {'document': {'document_id': 'old', 'filename': case['files'][0]}, 'extraction': {'information': [item]}}
        new = {'document': {'document_id': 'new', 'filename': case['files'][1]}, 'extraction': {'information': [{**item, 'summary': 'CURRENT_ONLY'}]}}
        session = Mock()
        def response(data):
            result = Mock(); result.json.return_value = data; return result
        session.post.side_effect = [response(old), response({'answer': 'Summary'}), response({'indexed': 1}), response(new), response({'status': 'completed'})]
        report = {'extractions': []}
        run_historical(case, session, 'http://test', directory, report, 10, lambda: None)
        calls = session.post.call_args_list
        self.assertTrue(calls[2].args[0].endswith('/rag/information/index'))
        final = calls[4].kwargs['json']
        self.assertNotIn('HISTORY_ONLY', str(final))
        self.assertIn('CURRENT_ONLY', str(final))
        self.assertEqual(len(final['eligible_information_ids']), 1)
        self.assertEqual(len(report['turns']), 2)
        session.delete.assert_called_once()
