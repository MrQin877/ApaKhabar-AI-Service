import unittest
from unittest.mock import patch

from app.schemas.news import (
    MissingInformation,
    NewsArticle,
    NewsQualityAssessment,
    NewsQualityDimensions,
    NewsQualityEvaluation,
    NewsRequest,
    QualityDimension,
)
from app.schemas.information import ExtractionContext
from app.services.ai_service import OllamaService
from app.agent.news_workflow import NewsCreationWorkflow, load_skill_prompt
from app.schemas.news import CompletenessResult
from app.schemas.tools import WebSearchResult
from app.services.web_search_service import WebSearchService


class AIServiceTests(unittest.TestCase):
    def test_targeted_extraction_requires_query(self):
        with self.assertRaises(ValueError):
            OllamaService.extract_information(
                "[source: page=1] Content",
                ExtractionContext(mode="targeted"),
            )

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

    def test_historical_request_uses_background_search_without_freshness(self):
        payload = WebSearchService.discovery_input(
            "make the news about Desa Punggul history"
        )
        self.assertIn("Desa Punggul", payload.query)
        self.assertIn("sejarah", payload.query)
        self.assertIsNone(payload.freshness)

    def test_historical_request_gets_historical_profile_format(self):
        content_type = NewsCreationWorkflow._infer_content_type(
            "Buat berita tentang sejarah Desa Punggul"
        )
        self.assertEqual(content_type, "historical_profile")

    @patch.object(OllamaService, "check_news_completeness")
    def test_workflow_passes_historical_format_to_completeness(self, check):
        check.return_value = CompletenessResult(
            status="ready", missing=[], conflicts=[], known_facts=[]
        )
        with patch.object(OllamaService, "write_news") as write, patch.object(
            OllamaService, "evaluate_news_quality"
        ) as evaluate:
            write.return_value = NewsArticle(
                headline="Sejarah Desa Punggul",
                subheadline=None,
                lead="Desa Punggul memiliki perjalanan sejarah.",
                body=["Riwayat desa disusun dari sumber yang disetujui."],
                summary="Profil sejarah Desa Punggul.",
                labels=["sejarah"],
                language="id",
                sources_used=["page=1"],
                warnings=[],
                content_type="historical_profile",
            )
            evaluate.return_value = self._quality_evaluation()
            NewsCreationWorkflow.run(
                NewsRequest(
                    information="[source: page=1] Desa Punggul dibentuk pada masa X.",
                    instructions="Buat berita tentang sejarah Desa Punggul",
                )
            )

        self.assertEqual(check.call_args.kwargs["content_type"], "historical_profile")
        self.assertEqual(write.call_args.kwargs["content_type"], "historical_profile")

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

    @patch.object(OllamaService, "evaluate_news_quality")
    @patch.object(OllamaService, "write_news")
    @patch.object(OllamaService, "check_news_completeness")
    def test_completed_clarification_skips_further_questions(
        self, check, write, evaluate
    ):
        evaluate.return_value = self._quality_evaluation()
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
        evaluate.assert_called_once()
        self.assertIsNotNone(result.article)
        self.assertEqual(result.quality.quality_score, 90)
        self.assertEqual(result.tool_calls, [])

    def test_quality_score_is_calculated_from_fixed_weights(self):
        dimensions = NewsQualityDimensions(
            accuracy=QualityDimension(score=90, explanation="Grounded."),
            completeness=QualityDimension(score=80, explanation="Mostly complete."),
            relevance=QualityDimension(score=85, explanation="Relevant."),
            readability=QualityDimension(score=88, explanation="Readable."),
            structure=QualityDimension(score=95, explanation="Well structured."),
            language=QualityDimension(score=90, explanation="Good Indonesian."),
            safety=QualityDimension(score=100, explanation="No safety issue."),
        )
        result = NewsQualityEvaluation.from_assessment(
            NewsQualityAssessment(dimensions=dimensions),
            evaluator_model="test-model",
        )

        self.assertEqual(result.quality_score, 88.05)
        self.assertEqual(result.quality_label, "good")
        self.assertFalse(result.publish_blocked)

    def test_unsupported_claim_blocks_publication(self):
        assessment = NewsQualityAssessment(
            dimensions=self._quality_evaluation().dimensions,
            claim_checks=[{
                "claim": "Jumlah korban 100 orang.",
                "status": "unsupported",
                "source": None,
                "reason": "No approved evidence contains this number.",
            }],
        )
        result = NewsQualityEvaluation.from_assessment(assessment, "test-model")

        self.assertTrue(result.publish_blocked)
        self.assertEqual(result.dimensions.accuracy.score, 0)

    @staticmethod
    def _quality_evaluation() -> NewsQualityEvaluation:
        dimension = lambda: QualityDimension(score=90, explanation="Validated.")
        return NewsQualityEvaluation.from_assessment(
            NewsQualityAssessment(
                dimensions=NewsQualityDimensions(
                    accuracy=dimension(),
                    completeness=dimension(),
                    relevance=dimension(),
                    readability=dimension(),
                    structure=dimension(),
                    language=dimension(),
                    safety=dimension(),
                )
            ),
            evaluator_model="test-model",
        )

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
