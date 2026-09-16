import unittest
from unittest.mock import patch

from app.schemas.news import MissingInformation, NewsArticle, NewsRequest
from app.services.ai_service import OllamaService
from app.agent.news_workflow import NewsCreationWorkflow, load_skill_prompt
from app.schemas.news import CompletenessResult
from app.schemas.tools import WebSearchResult
from app.services.web_search_service import WebSearchService


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

    def test_user_provided_facts_are_marked_separately(self):
        request = NewsRequest.model_validate({
            "information": "[source: page=1] Program diumumkan.",
            "user_facts": [{"field": "event_date", "value": "20 September 2026"}],
        })
        self.assertIn("[user_provided: event_date]", request.information_text())

    def test_user_fact_can_supply_information_without_document_item(self):
        request = NewsRequest.model_validate({
            "information": {"information": []},
            "user_facts": [{"field": "announcement", "value": "Jalan ditutup sementara."}],
        })
        self.assertIn("Jalan ditutup sementara", request.information_text())

    def test_text_only_request_can_enter_question_workflow(self):
        request = NewsRequest.model_validate({
            "information": {"information": []},
            "instructions": "Buat berita tentang kegiatan desa.",
        })
        self.assertIn("NO APPROVED FACTUAL EVIDENCE", request.information_text())

    @patch.object(WebSearchService, "search", return_value=[])
    def test_topic_only_request_returns_guidance_without_question(self, _search):
        request = NewsRequest.model_validate({
            "information": {"information": []},
            "instructions": "Ekonomi",
            "user_facts": [{"field": "category", "value": "Ekonomi"}],
            "clarification_completed": True,
        })

        result = NewsCreationWorkflow.run(request)

        self.assertIsNone(result.article)
        self.assertIsNotNone(result.guidance)
        self.assertEqual(result.tool_calls, [])

    def test_runtime_skill_prompt_is_loadable(self):
        self.assertIn("approved", load_skill_prompt("generation"))

    def test_completeness_prompt_resolves_subject_before_five_w_questions(self):
        prompt = load_skill_prompt("completeness")
        self.assertIn("subject_intent", prompt)
        self.assertIn("do not ask what", prompt.lower())
        self.assertIn("iPhone Duo", prompt)

    def test_unverified_subject_question_supports_concrete_options(self):
        question = MissingInformation.model_validate({
            "field": "subject_intent",
            "importance": "required",
            "kind": "unverified_subject",
            "reason": "No approved source confirms this product name.",
            "question": "How should this topic be treated?",
            "selection_type": "single",
            "options": [
                "Speculation or rumor",
                "Fiction",
                "Satire or parody",
                "A different name was intended",
            ],
        })
        self.assertEqual(question.kind, "unverified_subject")
        self.assertEqual(len(question.options), 4)

    def test_web_search_policy_skips_explicit_fiction(self):
        self.assertFalse(
            WebSearchService.should_search("Tulis cerita fiksi tentang Mars", False)
        )
        self.assertTrue(
            WebSearchService.should_search("Berita terbaru tentang Apple", False)
        )

    def test_broad_topic_is_expanded_for_news_discovery(self):
        payload = WebSearchService.discovery_input("Ekonomi")
        self.assertEqual(payload.query, "Ekonomi berita terbaru")
        self.assertEqual(payload.freshness, "pw")

    @patch.object(WebSearchService, "search")
    def test_web_sources_require_moderator_approval(self, search):
        search.return_value = [
            WebSearchResult(
                title="Example source",
                url="https://example.com/news",
                snippet="A current factual summary.",
            )
        ]
        request = NewsRequest.model_validate({
            "information": {"information": []},
            "instructions": "Berita terbaru tentang Example Company",
        })
        result = NewsCreationWorkflow.run(request)
        self.assertIsNone(result.article)
        self.assertEqual(result.tool_call.name, "ask_user_choice")
        self.assertEqual(
            result.tool_call.arguments.field,
            "web_source_approval",
        )

    @patch.object(OllamaService, "check_news_completeness")
    def test_workflow_stops_and_returns_questions_when_incomplete(self, check):
        check.return_value = CompletenessResult(
            status="needs_information",
            missing=[{
                "field": "location",
                "importance": "required",
                "question": "Di mana kegiatan berlangsung?",
                "reason": "Lokasi diperlukan.",
            }],
            conflicts=[],
            known_facts=["Kegiatan diumumkan"],
        )
        result = NewsCreationWorkflow.run(NewsRequest(information="Kegiatan diumumkan"))
        self.assertIsNone(result.article)
        self.assertEqual(result.completeness.missing[0].field, "location")

    @patch.object(OllamaService, "write_news")
    @patch.object(OllamaService, "check_news_completeness")
    def test_completed_clarification_skips_further_questions(self, check, write):
        write.return_value = NewsArticle(
            headline="Judul berita",
            subheadline=None,
            lead="Teras berita",
            body=["Isi berita dengan asumsi konservatif."],
            summary="Ringkasan",
            labels=["umum"],
            language="id",
            sources_used=[],
            warnings=["Sebagian rincian belum dikonfirmasi."],
        )
        request = NewsRequest.model_validate({
            "information": {"information": []},
            "instructions": "Buat berita tentang kegiatan desa",
            "user_facts": [{
                "field": "event",
                "value": "Warga mengadakan kegiatan bersih desa pagi ini",
            }],
            "clarification_completed": True,
        })

        result = NewsCreationWorkflow.run(request)

        check.assert_not_called()
        write.assert_called_once()
        self.assertIsNotNone(result.article)
        self.assertEqual(result.tool_calls, [])

    @patch.object(OllamaService, "check_news_completeness")
    def test_first_clarification_round_combines_up_to_three_questions(self, check):
        check.return_value = CompletenessResult(
            status="needs_information",
            missing=[
                {
                    "field": f"detail_{index}",
                    "importance": "required",
                    "question": f"Pertanyaan {index}?",
                    "options": ["Pilihan A", "Pilihan B"],
                }
                for index in range(1, 4)
            ],
            conflicts=[],
            known_facts=[],
        )

        result = NewsCreationWorkflow.run(NewsRequest(information="Informasi awal"))

        self.assertEqual(len(result.tool_calls), 3)
        self.assertEqual(result.tool_call, result.tool_calls[0])

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

    @patch.object(OllamaService, "_structured_chat")
    def test_structured_information_keeps_evidence_source_metadata(self, chat):
        chat.return_value = NewsArticle(
            headline="Judul",
            subheadline=None,
            lead="Teras berita",
            body=["Isi berita"],
            summary="Ringkasan",
            labels=["kegiatan"],
            language="id",
            sources_used=["page=2"],
            warnings=[],
        )

        result = OllamaService.write_news(
            '{"evidence": [{"source": "page=2", "quote": "Ditetapkan di Punggul"}]}',
            "id",
            "formal",
            "Fokus pada keputusan utama.",
        )
        self.assertEqual(result.sources_used, ["page=2"])


if __name__ == "__main__":
    unittest.main()
