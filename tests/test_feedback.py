import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("fs", Path(__file__).resolve().parents[1] / "scripts" / "feedback-summary.py")
fs = importlib.util.module_from_spec(spec); spec.loader.exec_module(fs)


class FeedbackSummaryTest(unittest.TestCase):
    def test_counts_worker_labels_and_issue_forms(self):
        issues = [
            {"labels": [{"name": "feedback"}, {"name": "rating-5"}], "body": "x"},
            {"labels": [{"name": "feedback"}], "body": "### Rating\n\n4 - Really good\n\n### What should we improve?"},
            {"labels": [{"name": "feedback"}, {"name": "rating-1"}, {"name": "spam"}], "body": ""},
            {"labels": [{"name": "feedback"}], "body": "no rating here"},
            {"labels": [{"name": "feedback"}, {"name": "rating-3"}], "body": "", "pull_request": {}},
        ]
        s = fs.summarize(issues)
        self.assertEqual(s["count"], 2)
        self.assertEqual(s["average"], 4.5)
        self.assertEqual(s["distribution"], {"1": 0, "2": 0, "3": 0, "4": 1, "5": 1})

    def test_empty(self):
        self.assertEqual(fs.summarize([])["count"], 0)


if __name__ == "__main__":
    unittest.main()
