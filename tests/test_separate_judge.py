import tempfile
import unittest
from pathlib import Path
from app.core.config import Settings
from app.providers.evaluator import build_evaluator
from app.providers.models import ModelError
from app.schemas.news import NewsRequest
from app.services.agent_service import AgentService
from test_agent_workflow import ScriptedModel


class SeparateJudgeTests(unittest.TestCase):
    def test_configuration_does_not_modify_writer(self):
        settings = Settings(_env_file=None, ai_model='writer', ai_api_key='writer-key', evaluator_model='judge', evaluator_api_key='judge-key')
        judge = build_evaluator(settings)
        self.assertEqual(judge.name, 'judge')
        self.assertEqual(judge.settings.ai_api_key, 'judge-key')
        self.assertEqual(settings.ai_api_key, 'writer-key')
        self.assertEqual(judge.settings.ai_base_url, 'https://api.groq.com/openai/v1')
        self.assertEqual(settings.ai_base_url, 'https://generativelanguage.googleapis.com/v1beta/openai')

    def test_same_model_rejected(self):
        with self.assertRaises(ValueError):
            build_evaluator(Settings(_env_file=None, ai_model='same-model', evaluator_model='same-model'))

    def run_draft(self, judge):
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(_env_file=None, agent_db_path=str(Path(directory)/'graph.sqlite'))
            writer = ScriptedModel()
            result = AgentService(settings, writer, evaluator=judge).run(NewsRequest(
                information='Desa mengumumkan lokakarya pada 28 September 2026 di balai desa.'))
            return writer, result

    def test_judge_only_evaluates_and_does_not_receive_previous_score(self):
        judge = ScriptedModel()
        judge.name = 'separate-test-judge'
        writer, result = self.run_draft(judge)
        self.assertTrue(judge.calls)
        self.assertTrue(all(name == 'Reflection' for name, _ in judge.calls))
        self.assertFalse(any(name == 'Reflection' for name, _ in writer.calls))
        self.assertTrue(all('quality' not in data and 'review' not in data for _, data in judge.calls))
        self.assertEqual(result.quality['evaluator_model'], judge.name)
        self.assertEqual(result.quality['evaluation_version'], 'separate-judge-v1')

    def test_failure_keeps_draft_and_blocks_publishing_without_self_review(self):
        class Unavailable(ScriptedModel):
            name = 'unavailable-judge'
            def structured(self, *args):
                raise ModelError('Unavailable')
        writer, result = self.run_draft(Unavailable())
        self.assertIsNotNone(result.article)
        self.assertTrue(result.quality['publish_blocked'])
        self.assertEqual(result.quality['quality_label'], 'evaluation_unavailable')
        self.assertFalse(any(name == 'Reflection' for name, _ in writer.calls))
