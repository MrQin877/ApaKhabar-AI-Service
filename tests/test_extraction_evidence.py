import unittest
from unittest.mock import patch
from app.schemas.information import ExtractionResponse
from app.services.ai_service import AIService, AIServiceError


class EvidenceTests(unittest.TestCase):
    def response(self, source, quote):
        return ExtractionResponse(information=[{
            'type': 'General', 'title': 'Decision', 'summary': 'A decision was issued.',
            'labels': [], 'fields': {}, 'confidence': .8,
            'evidence': [{'source': source, 'quote': quote}],
        }])

    def test_omitted_filename_prefix_resolves_to_exact_page(self):
        text = '[source: filename=decree.pdf, page=1] A decision\n[source: filename=decree.pdf, page=1] was issued.'
        with patch.object(AIService, '_structured_chat', return_value=self.response('decree.pdf, page=1', 'A decision was issued.')):
            result = AIService.extract_information(text)
        self.assertEqual(result['information'][0]['evidence'][0]['source'], 'filename=decree.pdf, page=1')

    def test_wrapper_is_removed_without_changing_location(self):
        text = '[source: filename=decree.pdf, page=1] A decision was issued.'
        with patch.object(AIService, '_structured_chat', return_value=self.response('[source: filename=decree.pdf, page=1]', 'A decision was issued.')):
            self.assertEqual(len(AIService.extract_information(text)['information']), 1)

    def test_wrong_page_other_file_blank_quote_and_spanning_pages_rejected(self):
        text = '[source: filename=decree.pdf, page=1] A decision\n[source: filename=decree.pdf, page=2] was issued.'
        for source, quote in [('decree.pdf, page=2', 'A decision'), ('other.pdf, page=1', 'A decision'),
                              ('decree.pdf, page=1', '   '), ('decree.pdf, page=1', 'A decision was issued.')]:
            with self.subTest(source=source, quote=quote), patch.object(AIService, '_structured_chat', return_value=self.response(source, quote)):
                with self.assertRaises(AIServiceError):
                    AIService.extract_information(text)

    def test_genuine_no_matches_remains_successful_empty_result(self):
        with patch.object(AIService, '_structured_chat', return_value=ExtractionResponse(information=[])):
            self.assertEqual(AIService.extract_information('Unrelated content', 'Another topic')['information'], [])
