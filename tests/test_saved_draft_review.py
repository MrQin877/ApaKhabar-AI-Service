import unittest
from unittest.mock import Mock, patch
from app.api.news import DraftReviewRequest, review_draft
from app.schemas.agent import Reflection
from app.providers.models import ModelError
from fastapi import HTTPException


class SavedDraftReviewTests(unittest.TestCase):
    def result(self, supported=True, ids=None):
        return Reflection(dimensions={k:95 for k in ['accuracy','completeness','relevance','readability','structure','language','safety']},
            claim_checks=[{'claim':'PDF records 40; sheet records 36.', 'supported':supported,
                           'source_ids': ids or ['information:1']}], improvements=[], warnings=[], needs_revision=False)

    def test_attributed_conflict_is_not_automatically_blocked(self):
        model=Mock(name='judge');model.name='test';model.structured.return_value=self.result()
        with patch('app.providers.evaluator.build_evaluator',return_value=model), patch('app.providers.models.GenerationModel',return_value=model):
            result=review_draft(DraftReviewRequest(title='Training',content='PDF records 40; sheet records 36.',sources={'information:1':{'content':'PDF:40; sheet:36'}}))
        self.assertFalse(result['quality']['publish_blocked'])
        self.assertIn('PDF records 40', model.structured.call_args.args[2])

    def test_unsupported_and_unknown_citations_remain_blocked(self):
        for review in [self.result(False),self.result(ids=['unknown'])]:
            model=Mock();model.name='test';model.structured.return_value=review
            with patch('app.providers.evaluator.build_evaluator',return_value=model), patch('app.providers.models.GenerationModel',return_value=model):
                result=review_draft(DraftReviewRequest(title='Training',content='40 attended',sources={'information:1':{}}))
            self.assertTrue(result['quality']['publish_blocked'])

    def test_provider_failure_cannot_return_a_passing_review(self):
        model=Mock();model.structured.side_effect=ModelError('Unavailable')
        with patch('app.providers.evaluator.build_evaluator',return_value=model), patch('app.providers.models.GenerationModel',return_value=model):
            with self.assertRaises(HTTPException) as exc:
                review_draft(DraftReviewRequest(title='Training',content='Text'))
        self.assertEqual(exc.exception.status_code,503)
