"""Regression checks for bounded evidence recovery through the real graph."""
import unittest
from unittest.mock import Mock
from app.schemas.agent import Reflection, ToolAction, ResumeRequest
from app.schemas.news import NewsRequest
from tests import test_agent_workflow as fixtures
from tests.test_agent_workflow import ScriptedModel


class EvidenceModel(ScriptedModel):
    def structured(self, schema, system, data, *args):
        if schema is ToolAction and self.reviews:
            if not self.actions:
                self.actions = [{'action': 'search_information', 'query': 'previous workshop'}]
        result = super().structured(schema, system, data, *args)
        if schema is Reflection:
            result.evidence_gaps = ['Find the previous workshop attendance source.']
            result.needs_revision = True
        return result


class ReplanningTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.AgentTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def test_research_reenters_once_and_rechecks_evidence(self):
        model = EvidenceModel()
        knowledge = Mock()
        knowledge.search.return_value = [{'source_id': 'information:42', 'summary': 'Previous workshop had 20 attendees.'}]
        result = self.fixture.service(model, knowledge).run(NewsRequest(
            information='A workshop.', eligible_information_ids=['42']))
        self.assertEqual(result.status, 'completed')
        self.assertEqual(result.metrics['replans'], 1)
        self.assertLessEqual(result.metrics['tool_calls'], self.fixture.settings.agent_max_tool_calls)
        self.assertEqual(sum(name == 'ExecutionPlan' for name, _ in model.calls), 2)
        checks = [payload for name, payload in model.calls if name == 'CompletenessResult']
        self.assertNotIn('information:42', checks[0]['sources'])
        self.assertIn('information:42', checks[1]['sources'])
        knowledge.search.assert_called_once_with('previous workshop', 'local', ['42'])
        self.assertTrue(result.quality['needs_revision'])

    def test_no_replan_without_eligible_research_or_tool_budget(self):
        for eligible, budget in [([], 5), (['42'], 0)]:
            with self.subTest(eligible=eligible):
                self.fixture.settings.agent_max_tool_calls = budget
                result = self.fixture.service(EvidenceModel()).run(NewsRequest(
                    information='A workshop.', eligible_information_ids=eligible))
                self.assertEqual(result.metrics['replans'], 0)

    def test_writing_feedback_does_not_replan(self):
        result = self.fixture.service(ScriptedModel(bad_first=True)).run(NewsRequest(
            information='A workshop.', eligible_information_ids=['42']))
        self.assertEqual(result.metrics['replans'], 0)
        self.assertEqual(result.metrics['revisions'], 1)

    def test_new_web_evidence_pauses_before_rewrite(self):
        self.fixture.settings.web_search_url = 'http://configured-adapter.test/search'
        model = EvidenceModel()
        original = model.structured
        def web_action(schema, *args):
            if schema is ToolAction and model.reviews:
                return ToolAction(action='web_search', query='previous workshop')
            return original(schema, *args)
        model.structured = web_action
        service = self.fixture.service(model)
        service.tools.execute = Mock(return_value=[{
            'source_id': 'web:previous', 'snippet': '20 attendees.', 'approved': False}])
        result = service.run(NewsRequest(information='A workshop.', run_id='replan-web', allow_web=True))
        self.assertEqual(result.status, 'awaiting_approval')
        self.assertEqual(sum(name == 'NewsArticle' for name, _ in model.calls), 1)
        result = self.fixture.service(ScriptedModel()).run(run_id='replan-web', resume=ResumeRequest(
            owner_id='local', approved_web_source_ids=['web:previous']))
        self.assertEqual(result.status, 'completed')
        self.assertIn('web:previous', result.article.sources_used)
        self.assertEqual(result.metrics['replans'], 1)
