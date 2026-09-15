import unittest
from collections import Counter

from evaluation.metrics import score_extraction, score_news_rating


class EvaluationMetricTests(unittest.TestCase):
    def test_extraction_precision_recall_and_f1(self):
        expected = Counter({("location", "kuala lumpur"): 1, ("amount", "100"): 1})
        actual = Counter({("location", "kuala lumpur"): 1, ("amount", "200"): 1})
        result = score_extraction(expected, actual)
        self.assertEqual(result.true_positive, 1)
        self.assertEqual(result.false_positive, 1)
        self.assertEqual(result.false_negative, 1)
        self.assertEqual(result.f1, 0.5)

    def test_news_requires_score_and_no_critical_hallucination(self):
        rating = {
            "factual_grounding": 5,
            "fact_coverage": 5,
            "structure": 5,
            "language_style": 5,
            "source_attribution": 5,
            "critical_hallucination": True,
        }
        result = score_news_rating(rating)
        self.assertEqual(result["score"], 100)
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
