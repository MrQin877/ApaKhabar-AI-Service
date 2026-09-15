import unittest
from unittest.mock import patch

from app.schemas.news import NewsArticle, NewsRequest
from app.services.ai_service import OllamaService


class AIServiceTests(unittest.TestCase):
    def test_news_request_accepts_structured_extraction(self):
        request = NewsRequest.model_validate(
            {
                "information": {
                    "information": [
                        {
                            "type": "Event",
                            "title": "Workshop",
                            "summary": "A workshop was announced.",
                            "labels": ["education"],
                            "fields": {"location": "Punggul"},
                            "evidence": [
                                {"source": "page=1", "quote": "Workshop"}
                            ],
                            "confidence": 0.9,
                        }
                    ]
                },
                "language": "id",
                "tone": "formal",
            }
        )
        self.assertIn('"location": "Punggul"', request.information_text())

    @patch.object(OllamaService, "_structured_chat")
    def test_plain_text_cannot_return_invented_source_metadata(self, chat):
        chat.return_value = NewsArticle(
            headline="Headline",
            subheadline=None,
            lead="Lead",
            body=["Body"],
            summary="Summary",
            labels=["event"],
            language="id",
            sources_used=["page 1"],
            warnings=[],
        )

        result = OllamaService.write_news("A supported fact.", "id", "formal")
        self.assertEqual(result.sources_used, [])

    @patch.object(OllamaService, "_structured_chat")
    def test_normalized_text_may_return_source_metadata(self, chat):
        chat.return_value = NewsArticle(
            headline="Headline",
            subheadline=None,
            lead="Lead",
            body=["Body"],
            summary="Summary",
            labels=["event"],
            language="id",
            sources_used=["page=2"],
            warnings=[],
        )

        result = OllamaService.write_news(
            "[source: page=2] A supported fact.",
            "id",
            "formal",
        )
        self.assertEqual(result.sources_used, ["page=2"])


if __name__ == "__main__":
    unittest.main()
