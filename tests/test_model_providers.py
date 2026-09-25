import unittest
from unittest.mock import Mock, patch

from pydantic import BaseModel

from app.core.config import Settings
from app.services.ai_service import AIService
from app.services.model_providers.embedding_providers import EmbeddingGemmaProvider
from app.services.model_providers.factory import (
    get_embedding_provider,
    get_generation_provider,
)
from app.services.model_providers.gemma_provider import GemmaProvider
from app.services.model_providers.llama_cpp_provider import LlamaCppProvider
from app.services.model_providers.base import ModelProviderError
from app.services.model_providers.ollama_provider import OllamaProvider
from app.services.model_providers.vllm_provider import VllmProvider


class ModelProviderTests(unittest.TestCase):
    def tearDown(self) -> None:
        get_generation_provider.cache_clear()
        get_embedding_provider.cache_clear()

    def test_ollama_is_the_default_provider(self):
        with patch(
            "app.services.model_providers.factory.get_settings",
            return_value=Settings(ai_provider="ollama"),
        ):
            provider = get_generation_provider()
        self.assertIsInstance(provider, OllamaProvider)

    def test_gemma_provider_is_lazy(self):
        with patch(
            "app.services.model_providers.factory.get_settings",
            return_value=Settings(ai_provider="gemma"),
        ):
            provider = get_generation_provider()
        self.assertIsInstance(provider, GemmaProvider)
        self.assertIsNone(provider._model)
        self.assertIsNone(provider._processor)

    def test_vllm_provider_is_selected(self):
        with patch(
            "app.services.model_providers.factory.get_settings",
            return_value=Settings(ai_provider="vllm"),
        ):
            provider = get_generation_provider()
        self.assertIsInstance(provider, VllmProvider)

    def test_llama_cpp_provider_is_selected(self):
        with patch(
            "app.services.model_providers.factory.get_settings",
            return_value=Settings(ai_provider="llama_cpp"),
        ):
            provider = get_generation_provider()
        self.assertIsInstance(provider, LlamaCppProvider)

    def test_vllm_sends_structured_output_schema(self):
        with patch(
            "app.services.model_providers.vllm_provider.get_settings",
            return_value=Settings(
                ai_provider="vllm",
                vllm_base_url="http://vllm:8000/v1/",
                vllm_api_key="secret",
                vllm_model="apakhabar-gemma",
            ),
        ):
            provider = VllmProvider()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": '{"status":"ready"}'}}]
        }
        provider._session.post = Mock(return_value=response)

        result = provider.generate(
            [{"role": "user", "content": "Check this."}],
            response_schema={
                "type": "object",
                "properties": {"status": {"type": "string"}},
                "required": ["status"],
            },
        )

        self.assertEqual(result, '{"status":"ready"}')
        request = provider._session.post.call_args
        self.assertEqual(request.args[0], "http://vllm:8000/v1/chat/completions")
        self.assertEqual(request.kwargs["headers"]["Authorization"], "Bearer secret")
        self.assertEqual(
            request.kwargs["json"]["response_format"]["type"],
            "json_schema",
        )

    def test_llama_cpp_uses_its_own_endpoint_and_model_alias(self):
        with patch(
            "app.services.model_providers.llama_cpp_provider.get_settings",
            return_value=Settings(
                ai_provider="llama_cpp",
                llama_cpp_base_url="http://localhost:8080/v1/",
                llama_cpp_model="apakhabar-gemma",
            ),
        ):
            provider = LlamaCppProvider()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": "Berhasil"}}]
        }
        provider._session.post = Mock(return_value=response)

        self.assertEqual(
            provider.generate([{"role": "user", "content": "Tes"}]),
            "Berhasil",
        )
        request = provider._session.post.call_args
        self.assertEqual(request.args[0], "http://localhost:8080/v1/chat/completions")
        self.assertEqual(request.kwargs["json"]["model"], "apakhabar-gemma")

    def test_llama_cpp_reports_truncated_output(self):
        provider = LlamaCppProvider()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {"content": '{"headline":"unfinished"'},
                }
            ]
        }
        provider._session.post = Mock(return_value=response)

        with self.assertRaisesRegex(ModelProviderError, "output limit"):
            provider.generate([{"role": "user", "content": "Tulis berita"}])

    def test_json_fences_and_surrounding_text_are_removed(self):
        result = AIService._clean_json_response(
            'Result:\n```json\n{"status": "ready"}\n```'
        )
        self.assertEqual(result, '{"status": "ready"}')

    def test_structured_chat_repairs_one_invalid_model_response(self):
        class ExampleResponse(BaseModel):
            status: str

        provider = Mock()
        provider.generate.side_effect = [
            '{"wrong": true}',
            '{"status": "ready"}',
        ]
        with patch(
            "app.services.ai_service.get_generation_provider",
            return_value=provider,
        ):
            result = AIService._structured_chat(
                ExampleResponse,
                "Return status.",
                "Ready?",
            )

        self.assertEqual(result.status, "ready")
        self.assertEqual(provider.generate.call_count, 2)
        repair_messages = provider.generate.call_args_list[1].kwargs["messages"]
        self.assertIn("previous response was invalid", repair_messages[-1]["content"])

    def test_unknown_provider_is_rejected(self):
        with patch(
            "app.services.model_providers.factory.get_settings",
            return_value=Settings(ai_provider="unknown"),
        ):
            with self.assertRaises(ValueError):
                get_generation_provider()

    def test_embedding_gemma_formats_documents_and_queries_differently(self):
        provider = EmbeddingGemmaProvider()
        with patch.object(provider, "_encode") as encode:
            encode.side_effect = [[[0.1, 0.2]], [[0.3, 0.4]]]
            provider.embed_documents(["Isi dokumen"], titles=["Laporan Desa"])
            provider.embed_query("sejarah desa")

        self.assertEqual(
            encode.call_args_list[0].args[0],
            ["title: Laporan Desa | text: Isi dokumen"],
        )
        self.assertEqual(
            encode.call_args_list[1].args[0],
            ["task: search result | query: sejarah desa"],
        )


if __name__ == "__main__":
    unittest.main()
