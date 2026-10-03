import unittest
from unittest.mock import Mock
from scripts.score_api_cases import Assessment, score_stage, evaluate

class BenchmarkTests(unittest.TestCase):
    def test_score_and_unknown(self):
        judge=Mock()
        judge.structured.side_effect=[Assessment(verdict=v,reason='test',evidence='quote') for v in ['pass','partial','fail']]
        self.assertEqual(score_stage(judge,['a','b','c'],{},1000)['score'],50)
        judge.structured.side_effect=None
        judge.structured.return_value=Assessment(verdict='unverifiable',reason='missing',evidence='No source')
        self.assertIsNone(score_stage(judge,['a'],{},1000)['score'])
    def test_error_is_not_zero_quality(self):
        judge=Mock(name='judge')
        r=evaluate({'case':{'id':'TC10'},'status':'error','error':'503'},judge)
        self.assertEqual(r['status'],'unavailable');self.assertIsNone(r['response']);judge.structured.assert_not_called()
    def test_oversized_source_not_silently_truncated(self):
        with self.assertRaises(ValueError):score_stage(Mock(),['a'],{'source':'x'*1000},100)
