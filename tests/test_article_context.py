import json
import tempfile
import unittest
from pathlib import Path
from app.core.config import Settings
from app.schemas.news import NewsArticle, NewsRequest
from app.schemas.agent import ResumeRequest
from app.services.agent_service import AgentService
from app.services.article_length import enforce_word_limit, word_count
from test_agent_workflow import ScriptedModel


class ContextAndLengthTests(unittest.TestCase):
    def test_length_limit_keeps_complete_sentences_and_excludes_title(self):
        article = NewsArticle(headline='Judul ' * 30, lead='Pembukaan kegiatan.', body=[' '.join(['Peserta mengikuti latihan foto produk.'] * 60)], summary='Ringkasan', labels=[], language='id', sources_used=['provided:information'], warnings=[])
        result = enforce_word_limit(article)
        self.assertLessEqual(word_count(result), 250)
        self.assertTrue(result.body[-1].endswith('.'))
        self.assertTrue(result.warnings)

    def test_history_reaches_writer_and_judge_and_is_removed_on_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(_env_file=None, agent_db_path=str(Path(tmp) / 'checkpoint.sqlite'))
            model = ScriptedModel(missing=True)
            service = AgentService(settings, model=model)
            request = NewsRequest(information='Pelatihan direncanakan tahun 2026.', run_id='history', include_historical_context=True, historical_sources=[{'source_id': 'history:news:1', 'title': 'Pelatihan 2025', 'content': 'Tahun 2025 hadir 22 orang.'}])
            self.assertEqual(service.run(request).status, 'awaiting_answers')
            model.missing = False
            service.run(run_id='history', resume=ResumeRequest(owner_id='local', answers=[{'field': 'location', 'value': 'Balai desa'}]))
            writer = next(data for schema, data in model.calls if schema == 'NewsArticle')
            self.assertNotIn('history:news:1', writer['sources'])
            second = ScriptedModel()
            AgentService(settings, model=second).run(request.model_copy(update={'run_id': 'history-visible'}))
            for schema, data in second.calls:
                if schema in ('NewsArticle', 'Reflection'):
                    self.assertIn('history:news:1', data['sources'])

    def test_history_excluded_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = ScriptedModel()
            settings = Settings(_env_file=None, agent_db_path=str(Path(tmp) / 'checkpoint.sqlite'))
            request = NewsRequest(information='Current file has 64 records.', historical_sources=[{
                'source_id': 'history:news:1', 'title': 'Old screening', 'content': '120 visits at Punggul.'}])
            AgentService(settings, model=model).run(request)
            for schema, data in model.calls:
                if 'sources' in data:
                    self.assertNotIn('history:news:1', data['sources'])

    def test_overlong_generation_and_revision_are_limited_before_review(self):
        class LongWriter(ScriptedModel):
            def structured(self, schema, system, data, *args):
                result = super().structured(schema, system, data, *args)
                if schema is NewsArticle:
                    result.body = [' '.join(['Warga berlatih memotret produk lokal.'] * 70)]
                return result
        with tempfile.TemporaryDirectory() as tmp:
            model = LongWriter(bad_first=True)
            settings = Settings(_env_file=None, agent_db_path=str(Path(tmp) / 'graph.sqlite'))
            result = AgentService(settings, model=model).run(NewsRequest(information='Warga berlatih memotret produk lokal.'))
            self.assertLessEqual(word_count(result.article), 250)
            reviews = [data for schema, data in model.calls if schema == 'Reflection']
            self.assertGreaterEqual(len(reviews), 2)
            for review in reviews:
                self.assertLessEqual(word_count(NewsArticle(**review['draft'])), 250)
