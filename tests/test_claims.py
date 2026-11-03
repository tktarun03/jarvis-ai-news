"""Agents must not build the same edition twice: published editions and live claims block other agents."""
import json
import shutil
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from jarvis import claims  # noqa: E402
from jarvis.common import parse_iso, save_json  # noqa: E402

NOW = parse_iso("2026-11-03T05:00:00Z")
DATE = "2026-11-03"


class ClaimTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="jarvis-claims-"))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_free_then_claimed_by_other(self):
        self.assertEqual(claims.status(self.root, DATE, "chatgpt", NOW)["state"], "free")
        claims.claim(self.root, DATE, "claude", NOW)
        st = claims.status(self.root, DATE, "chatgpt", NOW + timedelta(minutes=30))
        self.assertEqual(st["state"], "claimed")
        self.assertIn("claude", st["message"])
        self.assertEqual(claims.status(self.root, DATE, "claude", NOW)["state"], "mine")

    def test_expired_claim_frees_the_job(self):
        claims.claim(self.root, DATE, "claude", NOW, minutes=90)
        self.assertEqual(claims.status(self.root, DATE, "chatgpt", NOW + timedelta(minutes=91))["state"], "free")

    def test_published_edition_means_done_whoever_made_it(self):
        save_json(self.root / "data" / f"{DATE}.json", {"edition_date": DATE, "generated_at": "2026-11-03T04:40:00Z",
                                                        "produced_by": {"agent": "github-actions"}})
        st = claims.status(self.root, DATE, "chatgpt", NOW)
        self.assertEqual(st["state"], "published")
        self.assertIn("github-actions", st["message"])

    def test_finish_never_overwrites_anothers_live_claim(self):
        claims.claim(self.root, DATE, "claude", NOW)
        claims.finish(self.root, DATE, "chatgpt", NOW)
        self.assertEqual(claims.read(self.root, DATE)["agent"], "claude")
        claims.finish(self.root, DATE, "claude", NOW)
        self.assertEqual(claims.read(self.root, DATE)["status"], "completed")


if __name__ == "__main__":
    unittest.main()
