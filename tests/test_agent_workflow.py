import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from app.core.config import Settings
from app.schemas.news import NewsRequest, NewsArticle, CompletenessResult
from app.schemas.agent import ExecutionPlan, Reflection, ToolAction, ResumeRequest, RequestUnderstanding
from app.services.agent_service import AgentService, RunConflict
from app.skills.registry import SkillRegistry
from app.providers.models import ModelError


class ScriptedModel:
    name = 'scripted-test-model'

    def __init__(self, missing=False, bad_first=False, actions=None):
        self.calls = []
        self.missing = missing
        self.bad_first = bad_first
        self.reviews = 0
        self.actions = list(actions or [])

    def structured(self, schema, system, data, *args):
        payload = json.loads(data)
        self.calls.append((schema.__name__, payload))
        if schema is RequestUnderstanding:
            return schema(content_format='news_article', explicit_fact_quotes=[])
        if schema is ExecutionPlan:
            return schema(steps=[{'task': 'Find approved event facts', 'skill': 'evidence-research'}])
        if schema is ToolAction:
            return schema(**(self.actions.pop(0) if self.actions else {'action': 'finish'}))
        if schema is CompletenessResult:
            return schema(status='needs_information' if self.missing else 'ready',
                missing=[{'field': 'location', 'importance': 'required', 'question': 'Di mana?'}] if self.missing else [],
                conflicts=[], known_facts=['A workshop is planned'] if payload['sources'] else [])
        if schema is NewsArticle:
            return schema(headline='Lokakarya diumumkan', lead='Desa mengumumkan lokakarya.', body=['Lokakarya akan diselenggarakan.'],
                          summary='Pengumuman lokakarya.', labels=['pendidikan'], language='id', sources_used=list(payload['sources']), warnings=[], category='Invented')
        if schema is Reflection:
            self.reviews += 1
            bad = self.bad_first and self.reviews == 1
            return schema(dimensions={k: 40 if bad else 90 for k in ['accuracy', 'completeness', 'relevance', 'readability', 'structure', 'language', 'safety']},
                claim_checks=[{'claim': 'Lokakarya', 'supported': not bad, 'source_ids': list(payload['sources'])}],
                improvements=['Fix unsupported claim'] if bad else [], warnings=[], needs_revision=bad)
        raise AssertionError(schema)


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = Settings(_env_file=None, agent_db_path=str(Path(self.temp.name) / 'graph.sqlite'), agent_max_revisions=2)

    def tearDown(self):
        self.temp.cleanup()

    def service(self, model=None, knowledge=None):
        return AgentService(self.settings, model or ScriptedModel(), knowledge_factory=lambda: knowledge)

    def test_complete_and_idempotent(self):
        model = ScriptedModel()
        service = self.service(model)
        request = NewsRequest(information='Desa mengumumkan lokakarya.', run_id='test', available_categories=['Lainnya'], default_category='Lainnya')
        result = service.run(request)
        self.assertEqual(result.status, 'completed')
        self.assertEqual(result.article.category, 'Lainnya')
        self.assertEqual(result.quality['quality_score'], 90)
        calls = len(model.calls)
        self.assertEqual(self.service(model).run(request), result)
        self.assertEqual(len(model.calls), calls)
        self.assertTrue(result.skills_used)
        with self.assertRaises(RunConflict):
            service.run(request.model_copy(update={'instructions': 'Changed request'}))
        with self.assertRaises(KeyError):
            service.inspect('test', 'other-user')

    def test_clarification_survives_restart_and_never_repeats(self):
        service = self.service(ScriptedModel(missing=True))
        result = service.run(NewsRequest(information='A workshop.', run_id='clarify'))
        self.assertEqual(result.status, 'awaiting_answers')
        result = self.service(ScriptedModel(missing=True)).run(run_id='clarify', resume=ResumeRequest(owner_id='local', answers=[{'field': 'location', 'value': 'Unknown'}]))
        self.assertEqual(result.status, 'completed')
        self.assertIsNotNone(result.article)
        self.assertTrue(result.article.warnings)

    def test_reflection_revises_then_stops(self):
        model = ScriptedModel(bad_first=True)
        result = self.service(model).run(NewsRequest(information='A workshop.'))
        self.assertEqual(model.reviews, 2)
        self.assertEqual(result.quality['quality_score'], 90)
        self.assertIn('draft-revision', [s['name'] for s in result.skills_used])

    def test_react_uses_only_eligible_knowledge(self):
        knowledge = Mock()
        knowledge.search.return_value = [{'source_id': 'information:42', 'summary': 'A workshop.'}]
        model = ScriptedModel(actions=[{'action': 'search_information', 'query': 'workshop'}, {'action': 'inspect_source', 'source_id': 'information:42'}, {'action': 'finish'}])
        result = self.service(model, knowledge).run(NewsRequest(instructions='Write workshop news', owner_id='7', eligible_information_ids=['42']))
        knowledge.search.assert_called_once_with('workshop', '7', ['42'])
        self.assertIn('information:42', result.article.sources_used)
        self.assertEqual(len([e for e in result.events if e['event_type'] == 'tool']), 2)

    def test_revoked_source_is_removed_on_resume(self):
        knowledge = Mock()
        knowledge.search.return_value = [{'source_id': 'information:42', 'summary': 'A workshop.'}]
        service = self.service(ScriptedModel(missing=True, actions=[{'action': 'search_information', 'query': 'workshop'}]), knowledge)
        result = service.run(NewsRequest(instructions='Write news', run_id='revoked', eligible_information_ids=['42']))
        self.assertEqual(result.status, 'awaiting_answers')
        result = self.service(ScriptedModel()).run(run_id='revoked', resume=ResumeRequest(owner_id='local', eligible_information_ids=[]))
        self.assertEqual(result.status, 'insufficient_evidence')
        self.assertIsNone(result.article)

    def test_web_requires_approval_and_unknown_approvals_rejected(self):
        self.settings.web_search_url = 'http://configured-adapter.test/search'
        model = ScriptedModel(actions=[{'action': 'web_search', 'query': 'workshop'}])
        service = self.service(model)
        service.tools.execute = Mock(return_value=[{'source_id': 'web:one', 'snippet': 'A workshop.', 'approved': False}])
        result = service.run(NewsRequest(instructions='Research workshop', run_id='web', allow_web=True))
        self.assertEqual(result.status, 'awaiting_approval')
        self.assertFalse(any(s == 'NewsArticle' for s, _ in model.calls))
        result = self.service(model).run(run_id='web', resume=ResumeRequest(owner_id='local', approved_web_source_ids=['web:one']))
        self.assertEqual(result.status, 'completed')
        self.assertIn('web:one', result.article.sources_used)

    def test_failed_node_can_resume_without_rewriting_completed_draft(self):
        model = ScriptedModel()
        original = model.structured
        def fail_review(schema, *args):
            if schema is Reflection:
                raise ModelError('Temporary model failure')
            return original(schema, *args)
        model.structured = fail_review
        request = NewsRequest(information='A workshop.', run_id='retry')
        with self.assertRaises(ModelError):
            self.service(model).run(request)
        recovered = ScriptedModel()
        result = self.service(recovered).run(request)
        self.assertEqual(result.status, 'completed')
        self.assertFalse(any(schema == 'NewsArticle' for schema, _ in recovered.calls))

    def test_tool_limit_stops_repeated_actions(self):
        self.settings.agent_max_tool_calls = 2
        model = ScriptedModel(actions=[{'action': 'search_information', 'query': 'event'}] * 10)
        knowledge = Mock()
        knowledge.search.return_value = []
        result = self.service(model, knowledge).run(NewsRequest(information='A workshop.', eligible_information_ids=['1']))
        self.assertEqual(result.status, 'completed')
        self.assertEqual(knowledge.search.call_count, 1)
        self.assertEqual(result.metrics['tool_calls'], 2)

    def test_invalid_approval_does_not_destroy_paused_run(self):
        self.settings.web_search_url = 'http://configured-adapter.test/search'
        model = ScriptedModel(actions=[{'action': 'web_search', 'query': 'workshop'}])
        service = self.service(model)
        service.tools.execute = Mock(return_value=[{'source_id': 'web:one', 'snippet': 'A workshop.', 'approved': False}])
        service.run(NewsRequest(instructions='Research workshop', run_id='bad-approval', allow_web=True))
        with self.assertRaises(ValueError):
            self.service().run(run_id='bad-approval', resume=ResumeRequest(owner_id='local', approved_web_source_ids=['web:unknown']))
        self.assertEqual(self.service().inspect('bad-approval', 'local')['status'], 'awaiting_approval')
        result = self.service().run(run_id='bad-approval', resume=ResumeRequest(owner_id='local', approved_web_source_ids=['web:one']))
        self.assertEqual(result.status, 'completed')

    def test_reflection_never_exceeds_revision_budget(self):
        model = ScriptedModel()
        original = model.structured
        def always_bad(schema, *args):
            result = original(schema, *args)
            if schema is Reflection:
                result.needs_revision = True
                result.claim_checks[0].supported = False
            return result
        model.structured = always_bad
        result = self.service(model).run(NewsRequest(information='A workshop.'))
        self.assertEqual(model.reviews, 3)
        self.assertTrue(result.quality['publish_blocked'])
        self.assertEqual(result.metrics['revisions'], 2)

    def test_resume_can_retry_model_failure_after_clarification(self):
        self.service(ScriptedModel(missing=True)).run(NewsRequest(information='A workshop.', run_id='resume-failure'))
        model = ScriptedModel()
        original = model.structured
        def fail_review(schema, *args):
            if schema is Reflection:
                raise ModelError('Temporary failure')
            return original(schema, *args)
        model.structured = fail_review
        resume = ResumeRequest(owner_id='local', answers=[{'field': 'location', 'value': 'Village hall'}])
        with self.assertRaises(ModelError):
            self.service(model).run(run_id='resume-failure', resume=resume)
        result = self.service().run(run_id='resume-failure', resume=resume)
        self.assertEqual(result.status, 'completed')

    def test_skill_discovery_and_path_boundary(self):
        registry = SkillRegistry(self.settings.agent_skills_path)
        self.assertEqual(len(registry.discover()), 5)
        self.assertNotIn('instructions', registry.discover()[0])
        with self.assertRaises(ValueError):
            registry.resource('evidence-research', '../../app/main.py')
        self.assertIn('content', registry.resource('evidence-research', 'references/research.md'))


if __name__ == '__main__':
    unittest.main()
