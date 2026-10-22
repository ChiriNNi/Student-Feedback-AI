import unittest

from app.nlp.analyzer import analyze, build_matchers
from app.nlp.lexicons import DEFAULT_TOPICS


class Sprint3AnalyzerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matchers = build_matchers(DEFAULT_TOPICS)

    def test_sentiment_analysis_uses_text_and_rating(self):
        result = analyze("The instructor was excellent and very helpful.", self.matchers, rating=5)
        self.assertEqual(result.sentiment, "positive")
        self.assertGreater(result.score, 0.5)
        self.assertGreater(result.confidence, 0.5)

    def test_topic_detection_is_multilingual(self):
        english = analyze("The course workload and deadlines were difficult.", self.matchers)
        russian = analyze("Преподаватель понятно объяснял материал.", self.matchers)
        kazakh = analyze("Жатақхана бөлмесі өте суық.", self.matchers)
        self.assertIn("Workload", english.topics)
        self.assertIn("Teaching Quality", russian.topics)
        self.assertIn("Accommodation", kazakh.topics)

    def test_aspect_sentiment_splits_contrasting_clauses(self):
        result = analyze(
            "The instructor was excellent, but the workload was terrible and deadlines were stressful.",
            self.matchers,
        )
        self.assertEqual(result.aspects["Teaching Quality"], "positive")
        self.assertEqual(result.aspects["Workload"], "negative")

    def test_common_problem_inputs_are_structured(self):
        results = [
            analyze("The workload is terrible and deadlines are stressful.", self.matchers),
            analyze("Too much homework and an impossible deadline.", self.matchers),
            analyze("Assignments are overwhelming; the workload is bad.", self.matchers),
        ]
        negative_workload = sum(r.aspects.get("Workload") == "negative" for r in results)
        self.assertEqual(negative_workload, 3)

    def test_pii_is_masked_before_analysis_output(self):
        result = analyze("Email me at student@example.com. The lectures were great.", self.matchers)
        self.assertNotIn("student@example.com", result.text)
        self.assertIn("[EMAIL]", result.text)
        self.assertTrue(result.pii_masked)


if __name__ == "__main__":
    unittest.main()
