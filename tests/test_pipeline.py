"""Offline end-to-end tests: fixture feeds -> verify -> dedupe -> render -> validate. No network needed."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from jarvis.common import load_config, load_json, load_sources, parse_iso, save_json  # noqa: E402
from jarvis.pipeline import Skip, run_daily  # noqa: E402
from jarvis.summarize import grounding_problems  # noqa: E402
import validate  # noqa: E402

FIXTURES = REPO / "tests" / "fixtures"
NOW = parse_iso("2026-11-03T04:30:00Z")  # 07:30 in Doha


class PipelineTest(unittest.TestCase):
    def setUp(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        self.root = Path(tempfile.mkdtemp(prefix="jarvis-test-"))
        for sub in ("assets/css", "assets/js", "assets/images/brand"):
            shutil.copytree(REPO / sub, self.root / sub)
        save_json(self.root / "data" / "seen.json", {
            "urls": {"https://medianama.com/2026/11/223-telcos-third-party-trais-anthropic": "2026-11-02"}, "titles": {}})
        self.cfg, self.sources = load_config(REPO), load_sources(REPO)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def run_once(self, **kw):
        return run_daily(self.root, self.cfg, self.sources, kw.pop("now", NOW), fixtures=FIXTURES, log_fn=lambda *_: None, **kw)

    def test_full_run(self):
        ed = self.run_once()
        g = [s["source"]["url"] for s in ed["stories"]["global"]]
        i = [s["source"]["url"] for s in ed["stories"]["india"]]
        reasons = " | ".join(r["reason"] for r in ed["rejected"])

        # Same story from BBC and TechCrunch is merged; the more trusted outlet leads, the other corroborates.
        acme = [s for s in ed["stories"]["global"] if "acme" in s["source"]["url"]]
        self.assertEqual(len(acme), 1)
        self.assertEqual(acme[0]["source"]["name"], "BBC News")
        self.assertEqual(acme[0]["corroboration"][0]["name"], "TechCrunch")

        self.assertIn("https://deepmind.google/discover/blog/science-benchmark/", g)
        self.assertIn("https://techcrunch.com/2026/11/02/gearbox-series-b/", g)  # 403 from a trusted feed: accepted, noted
        self.assertEqual(len(g), 3)

        self.assertEqual(len(i), 3)  # MeitY draft, Vaani (India keywords), Chennai hospital
        self.assertTrue(all(s["region"] == "india" for s in ed["stories"]["india"]))

        for expected in ("disagrees with feed date", "link check failed", "not on trusted list", "blocked content pattern",
                         "future", "no publication date", "already published"):
            self.assertIn(expected, reasons)
        joined = json.dumps(ed)
        for absent in ("old-chatbots", "phone-sales", "qc-dark-stores", "spectrum"):
            self.assertNotIn(absent, joined)

        # Without an API key nothing is invented: publisher blurb only, no insights or impact.
        for s in ed["stories"]["global"] + ed["stories"]["india"]:
            self.assertEqual(s["summary_mode"], "publisher-blurb")
            self.assertEqual(s["key_insights"], [])
            self.assertIsNone(s["impact"])
            self.assertTrue((self.root / s["image"]["src"]).exists())

        self.assertTrue((self.root / "news" / "2026-11-03.html").exists())
        home = (self.root / "index.html").read_text("utf-8")
        self.assertIn("Published by Arunkumar Thamilarasu", home)
        self.assertEqual(validate.check(self.root, self.cfg, self.sources, check_cron=False), [])

    def test_idempotent_and_no_duplicates_next_day(self):
        self.run_once()
        with self.assertRaises(Skip):
            self.run_once()  # second run the same day publishes nothing
        ed = self.run_once(force=True)
        self.assertEqual(ed["edition_number"], 1)  # rebuild keeps its number
        # The next morning the same feed items are inside a 24h window only partly, and never republished.
        with self.assertRaises(Skip):
            self.run_once(now=parse_iso("2026-11-04T04:30:00Z"))
        idx = load_json(self.root / "data" / "index.json")
        self.assertEqual([e["date"] for e in idx["editions"]], ["2026-11-03"])

    def test_skips_when_too_few_stories(self):
        cfg = json.loads(json.dumps(self.cfg))
        cfg["edition"]["min_stories_to_publish"] = 50
        with self.assertRaises(Skip):
            run_daily(self.root, cfg, self.sources, NOW, fixtures=FIXTURES, log_fn=lambda *_: None)
        self.assertFalse((self.root / "data" / "2026-11-03.json").exists())


class GroundingTest(unittest.TestCase):
    SRC = "The company raised $40 million in a Series B and will open 12 new sites in 2027."

    def test_grounded_summary_passes(self):
        res = {"headline": "Firm raises $40 million", "summary": "It will open 12 sites in 2027.", "key_insights": [], "impact": None}
        self.assertEqual(grounding_problems(res, self.SRC), [])

    def test_invented_number_fails(self):
        res = {"headline": "Firm raises $45 million", "summary": "It will open 12 sites.", "key_insights": ["Valued at 300 million"], "impact": None}
        problems = grounding_problems(res, self.SRC)
        self.assertTrue(any("45" in p for p in problems))
        self.assertTrue(any("300" in p for p in problems))

    def test_invented_quote_fails(self):
        res = {"headline": "x", "summary": 'CEO said "this changes everything for our customers"', "key_insights": [], "impact": None}
        self.assertIn("quotation not found in source", grounding_problems(res, self.SRC))


if __name__ == "__main__":
    unittest.main()
