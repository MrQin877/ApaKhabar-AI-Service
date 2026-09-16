import unittest

from fastapi.testclient import TestClient

from app.main import app


class DocumentApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_batch_rejects_more_than_five_files(self):
        files = [
            ("files", (f"document-{index}.txt", b"content", "text/plain"))
            for index in range(6)
        ]
        response = self.client.post("/documents/batch-extract", files=files)
        self.assertEqual(response.status_code, 422)
        self.assertIn("1 and 5", response.json()["detail"])

    def test_batch_reports_empty_file_failure_without_failing_request(self):
        response = self.client.post(
            "/documents/batch-extract",
            files=[("files", ("empty.txt", b"", "text/plain"))],
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]
        self.assertEqual(result["status"], "failed")
        self.assertIn("empty", result["error"])


if __name__ == "__main__":
    unittest.main()
