import io
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.providers.models import ModelError
from app.schemas.information import ExtractionResponse, InformationItem
from app.schemas.news import CompletenessResult, NewsArticle, NewsGenerationResponse
from app.services.agent_service import AgentService
from app.services.ai_service import AIService


class IntelligentNewsValidationTests(unittest.TestCase):
    """Positive and negative validation tests for ApaKhabar-AI-Service.

    Positive Test Cases : TC-AIS-01 to TC-AIS-07
    Negative Test Cases : TC-AIS-08 to TC-AIS-14
    """

    def setUp(self) -> None:
        self.client = TestClient(app)

    # ================================================================
    # POSITIVE TEST CASES
    # ================================================================

    def test_tc_ais_01_health_endpoint_returns_ok(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", response.json())

    def test_tc_ais_02_upload_valid_text_document_normalizes_content(self) -> None:
        files = {"file": ("notulen.txt", io.BytesIO(b"Gotong royong desa hari Minggu."), "text/plain")}
        response = self.client.post("/documents/upload", files=files)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["filename"], "notulen.txt")
        self.assertGreater(len(body["elements"]), 0)
        self.assertIn("Gotong royong", body["elements"][0]["content"])

    @patch("app.api.document.extract_document")
    def test_tc_ais_03_extract_information_from_valid_document(self, mock_extract) -> None:
        mock_extract.return_value = ExtractionResponse(
            information=[
                InformationItem(
                    type="Announcement",
                    title="Gotong Royong Desa",
                    summary="Warga membersihkan saluran air.",
                    labels=["lingkungan"],
                    fields={"date": "Minggu"},
                    evidence=[],
                    confidence=0.95,
                )
            ]
        )
        files = {"file": ("info.txt", io.BytesIO(b"Gotong royong hari Minggu."), "text/plain")}
        response = self.client.post("/documents/extract-information", files=files)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["extraction"]["information"]), 1)

    @patch.object(AIService, "check_news_completeness")
    def test_tc_ais_04_check_completeness_returns_valid_result(self, mock_check) -> None:
        mock_check.return_value = CompletenessResult(
            status="ready",
            missing=[],
            conflicts=[],
            known_facts=["Gotong royong pada hari Minggu di Balai Desa"],
        )
        response = self.client.post(
            "/news/check-completeness",
            json={"information": "Gotong royong pada hari Minggu di Balai Desa."},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")

    @patch.object(AgentService, "run")
    def test_tc_ais_05_generate_news_returns_article_for_valid_request(self, mock_run) -> None:
        mock_run.return_value = NewsGenerationResponse(
            completeness=CompletenessResult(
                status="ready",
                missing=[],
                conflicts=[],
                known_facts=["Desa mengadakan lokakarya digital."],
            ),
            article=NewsArticle(
                headline="Desa Adakan Lokakarya Digital",
                subheadline="Diikuti 50 Warga",
                lead="Pemerintah desa menyelenggarakan lokakarya literasi digital.",
                body=["Kegiatan berlangsung di balai desa dengan antusiasme tinggi."],
                summary="Lokakarya literasi digital desa berjalan sukses.",
                labels=["teknologi"],
                language="id",
                sources_used=["info:1"],
                warnings=[],
            ),
            run_id="run-ais-05",
            status="completed",
        )
        response = self.client.post(
            "/news/generate",
            json={
                "information": "Pemerintah desa mengadakan lokakarya literasi digital untuk 50 warga.",
                "language": "id",
                "tone": "formal",
                "instructions": "Buat artikel berita singkat",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "completed")
        self.assertEqual(response.json()["article"]["headline"], "Desa Adakan Lokakarya Digital")

    @patch.object(AgentService, "run")
    def test_tc_ais_06_resume_agent_run_with_clarification_answers(self, mock_resume) -> None:
        mock_resume.return_value = NewsGenerationResponse(
            completeness=CompletenessResult(
                status="ready",
                missing=[],
                conflicts=[],
                known_facts=["Lokasi: Balai Desa"],
            ),
            article=None,
            run_id="run-ais-06",
            status="completed",
        )
        response = self.client.post(
            "/agent/runs/run-ais-06/resume",
            json={"owner_id": "1", "answers": [{"field": "location", "value": "Balai Desa"}]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["run_id"], "run-ais-06")

    def test_tc_ais_07_agent_skills_endpoint_lists_skills(self) -> None:
        response = self.client.get("/agent/skills")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json()["skills"], list)

    # ================================================================
    # NEGATIVE TEST CASES
    # ================================================================

    def test_tc_ais_08_upload_empty_file_returns_422(self) -> None:
        files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
        response = self.client.post("/documents/upload", files=files)
        self.assertEqual(response.status_code, 422)
        self.assertIn("empty", response.json()["detail"].lower())

    def test_tc_ais_09_upload_unsupported_extension_returns_422(self) -> None:
        files = {"file": ("script.exe", io.BytesIO(b"MZ..."), "application/octet-stream")}
        response = self.client.post("/documents/upload", files=files)
        self.assertEqual(response.status_code, 422)

    def test_tc_ais_10_check_completeness_rejects_empty_information(self) -> None:
        response = self.client.post("/news/check-completeness", json={"information": ""})
        self.assertEqual(response.status_code, 422)

    def test_tc_ais_11_generate_news_rejects_blank_payload(self) -> None:
        response = self.client.post(
            "/news/generate",
            json={"information": "   ", "instructions": "  ", "user_facts": []},
        )
        self.assertEqual(response.status_code, 422)

    def test_tc_ais_12_generate_news_rejects_ineligible_information_ids(self) -> None:
        response = self.client.post(
            "/news/generate",
            json={
                "information": {
                    "information": [
                        {
                            "information_id": "999",
                            "type": "Announcement",
                            "title": "Unapproved",
                            "summary": "Unapproved item",
                            "labels": [],
                            "fields": {},
                            "evidence": [],
                        }
                    ]
                },
                "eligible_information_ids": ["1"],
                "instructions": "Buat berita",
            },
        )
        self.assertEqual(response.status_code, 422)

    @patch.object(AgentService, "inspect", side_effect=KeyError("missing"))
    def test_tc_ais_13_inspect_unknown_agent_run_returns_404(self, _mock_inspect) -> None:
        response = self.client.get("/agent/runs/unknown-run-id?owner_id=1")
        self.assertEqual(response.status_code, 404)

    @patch.object(AgentService, "run", side_effect=ModelError("LLM provider unavailable"))
    def test_tc_ais_14_generate_news_returns_503_when_model_fails(self, _mock_run) -> None:
        response = self.client.post(
            "/news/generate",
            json={
                "information": "Informasi desa lengkap untuk dibuat berita.",
                "instructions": "Buat berita",
            },
        )
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
