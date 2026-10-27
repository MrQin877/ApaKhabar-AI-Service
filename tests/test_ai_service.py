import unittest
from unittest.mock import patch

from app.schemas.news import NewsArticle
from app.services.ai_service import AIService


class AIServiceTests(unittest.TestCase):
    @patch.object(AIService, "_structured_chat")
    def test_plain_text_cannot_return_invented_source_metadata(self, chat):
        chat.return_value = NewsArticle(
            headline="Headline",
            subheadline=None,
            lead="Lead",
            body=["Body"],
            summary="Summary",
            labels=["event"],
            language="en",
            sources_used=["page 1"],
            warnings=[],
        )

        result = AIService.write_news("A supported fact.", "en", "formal")
        self.assertEqual(result.sources_used, [])

    @patch.object(AIService, "_structured_chat")
    def test_normalized_text_may_return_source_metadata(self, chat):
        chat.return_value = NewsArticle(
            headline="Headline",
            subheadline=None,
            lead="Lead",
            body=["Body"],
            summary="Summary",
            labels=["event"],
            language="en",
            sources_used=["page=2"],
            warnings=[],
        )

        result = AIService.write_news(
            "[source: page=2] A supported fact.",
            "en",
            "formal",
        )
        self.assertEqual(result.sources_used, ["page=2"])


if __name__ == "__main__":
    unittest.main()
