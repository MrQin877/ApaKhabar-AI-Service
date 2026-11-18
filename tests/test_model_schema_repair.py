import json
import unittest
from unittest.mock import patch
from pydantic import BaseModel
from app.providers.models import GenerationModel, ModelError
from app.core.config import Settings


class Result(BaseModel):
    body: list[str]


class SchemaRepairTests(unittest.TestCase):
    def gemma(self):
        return GenerationModel(Settings(_env_file=None,
            ai_base_url='https://generativelanguage.googleapis.com/v1beta/openai',
            ai_model='gemma-4-26b-a4b-it'))

    def test_gemma_validates_final_json_outside_thought(self):
        for final in ['{"body":["final"]}', '```json\n{"body":["final"]}\n```']:
            with self.subTest(final=final):
                model = self.gemma()
                with patch.object(model, '_chat', return_value='<thought>{"body":["wrong"]}</thought>'+final) as chat:
                    self.assertEqual(model.structured(Result, 'system', 'data').body, ['final'])
                    chat.assert_called_once()

    def test_gemma_rejects_unfinished_thought_and_invalid_final_schema(self):
        for raw in ['<thought>{"body":["not final"]}',
                    '<thought>analysis</thought>{"body":"wrong type"}',
                    '<thought>analysis</thought>Commentary {"body":["value"]}']:
            with self.subTest(raw=raw):
                model = self.gemma()
                with patch.object(model, '_chat', return_value=raw) as chat:
                    with self.assertRaises(ModelError):
                        model.structured(Result, 'system', 'data')
                    self.assertEqual(chat.call_count, 2)

    def test_repair_keeps_evidence_and_field_errors_without_growing_history(self):
        model = GenerationModel(Settings(_env_file=None))
        calls = []
        def chat(messages, schema, temperature):
            calls.append([dict(m) for m in messages])
            return '{"body":"supported fact"}' if len(calls) == 1 else '{"body":["supported fact"]}'
        with patch.object(model, '_chat', side_effect=chat):
            self.assertEqual(model.structured(Result, 'system', 'evidence').body, ['supported fact'])
        self.assertEqual(len(calls[1]), 2)
        self.assertEqual(calls[1][1], {'role': 'user', 'content': 'evidence'})
        self.assertIn('body', calls[1][0]['content'])
        self.assertIn('list_type', calls[1][0]['content'])
        self.assertNotIn('supported fact', calls[1][0]['content'])

    def test_failure_is_bounded_and_diagnostics_exclude_values(self):
        model = GenerationModel(Settings(_env_file=None))
        with patch.object(model, '_chat', return_value='{"body":"PRIVATE_SOURCE_VALUE"}') as chat:
            with self.assertRaises(ModelError) as raised:
                model.structured(Result, 'system', 'evidence')
        self.assertEqual(chat.call_count, 2)
        self.assertIn('body', str(raised.exception))
        self.assertNotIn('PRIVATE_SOURCE_VALUE', str(raised.exception))
