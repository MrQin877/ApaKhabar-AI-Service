import json
import unittest
from unittest.mock import patch
from pydantic import BaseModel
from app.providers.models import GenerationModel, ModelError
from app.core.config import Settings


class Result(BaseModel):
    body: list[str]


class SchemaRepairTests(unittest.TestCase):
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
