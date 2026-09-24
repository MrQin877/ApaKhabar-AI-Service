import unittest

from app.schemas.assistant import AssistantIntentRequest
from app.services.assistant_service import AssistantIntentService


class AssistantIntentServiceTests(unittest.TestCase):
    def test_routes_general_extraction(self):
        result = AssistantIntentService.classify(AssistantIntentRequest(
            message="I don't know what is inside, extract everything important.",
            has_files=True,
        ))
        self.assertEqual(result.intent, "extract_information")
        self.assertEqual(result.extraction_mode, "general")

    def test_routes_targeted_extraction(self):
        result = AssistantIntentService.classify(AssistantIntentRequest(
            message="Extract information about flood victims and assistance.",
            has_files=True,
        ))
        self.assertEqual(result.intent, "extract_information")
        self.assertEqual(result.extraction_mode, "targeted")

    def test_routes_generation_before_generic_search_words(self):
        result = AssistantIntentService.classify(AssistantIntentRequest(
            message="Generate news about flood assistance.",
        ))
        self.assertEqual(result.intent, "generate_news")

    def test_file_with_greeting_returns_guidance(self):
        result = AssistantIntentService.classify(AssistantIntentRequest(
            message="hi",
            has_files=True,
        ))
        self.assertEqual(result.intent, "conversation")
        self.assertIsNotNone(result.guidance)

    def test_revision_requires_existing_draft(self):
        result = AssistantIntentService.classify(AssistantIntentRequest(
            message="Make the headline shorter.",
            has_draft=True,
        ))
        self.assertEqual(result.intent, "revise_news")

    def test_indonesian_summary_request_is_a_revision(self):
        result = AssistantIntentService.classify(AssistantIntentRequest(
            message="Ringkas draf ini.",
            has_draft=True,
        ))
        self.assertEqual(result.intent, "revise_news")


if __name__ == "__main__":
    unittest.main()
