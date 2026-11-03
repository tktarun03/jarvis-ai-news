"""Offline end-to-end tests: fixture feeds -> verify -> dedupe -> render -> validate. No network needed."""
import json
import os
import re
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
        for k in ("PIXABAY_API_KEY", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN"):
            os.environ.pop(k, None)
        self.root = Path(tempfile.mkdtemp(prefix="jarvis-test-"))
        for sub in ("assets/css", "assets/js", "assets/images/brand"):
            shutil.copytree(REPO / sub, self.root / sub)
        shutil.copy(REPO / "manifest.webmanifest", self.root / "manifest.webmanifest")
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
            self.assertTrue((self.root / s["image"]["fallback"]).exists())

        # Publisher image: relative og:image resolved, hotlinked with credit; logo-like images ignored.
        self.assertEqual(acme[0]["image"]["type"], "publisher")
        self.assertEqual(acme[0]["image"]["src"], "https://www.bbc.com/images/acme-hero.jpg")
        self.assertEqual(acme[0]["image"]["credit"], "Image: BBC News")
        self.assertTrue((self.root / acme[0]["image"]["fallback"]).exists())
        dm = [s for s in ed["stories"]["global"] if "deepmind" in s["source"]["url"]][0]
        self.assertEqual(dm["image"]["type"], "generated")

        self.assertTrue((self.root / "news" / "2026-11-03.html").exists())
        home = (self.root / "index.html").read_text("utf-8")
        self.assertIn("Published by Arunkumar Thamilarasu", home)
        self.assertEqual(validate.check(self.root, self.cfg, self.sources, check_cron=False), [])

    def test_share_pages(self):
        ed = self.run_once()
        base = self.cfg["site"]["base_url"]
        for s in ed["stories"]["global"] + ed["stories"]["india"]:
            page = self.root / "news" / "2026-11-03" / f"{s['id']}.html"
            self.assertTrue(page.exists(), s["id"])
            html = page.read_text("utf-8")
            self.assertIn(f'<meta property="og:url" content="{base}news/2026-11-03/{s["id"]}.html">', html)
            self.assertIn(f"location.replace('../2026-11-03.html#s-{s['id']}')", html)
            self.assertIn("Published by Arunkumar Thamilarasu", html)
            image = re.search(r'<meta property="og:image" content="([^"]+)"', html).group(1)
            self.assertFalse(image.endswith(".svg"), "link previews cannot show SVG")
        # a forced rebuild that drops a story also drops its share page
        stale = self.root / "news" / "2026-11-03" / "000000000000.html"
        stale.write_text("x", "utf-8")
        self.run_once(force=True)
        self.assertFalse(stale.exists())
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


class ImageModeTest(unittest.TestCase):
    def test_download_mode_copies_image(self):
        root = Path(tempfile.mkdtemp(prefix="jarvis-img-"))
        try:
            for sub in ("assets/css", "assets/js", "assets/images/brand"):
                shutil.copytree(REPO / sub, root / sub)
            shutil.copy(REPO / "manifest.webmanifest", root / "manifest.webmanifest")
            cfg = json.loads(json.dumps(load_config(REPO)))
            cfg["images"]["mode"] = "publisher-download"
            ed = run_daily(root, cfg, load_sources(REPO), NOW, fixtures=FIXTURES, log_fn=lambda *_: None)
            acme = [s for s in ed["stories"]["global"] if "acme" in s["source"]["url"]][0]
            self.assertEqual(acme["image"]["type"], "publisher-copy")
            self.assertTrue((root / acme["image"]["src"]).exists())
            self.assertEqual(validate.check(root, cfg, load_sources(REPO), check_cron=False), [])
        finally:
            shutil.rmtree(root, ignore_errors=True)


class StockImageTest(unittest.TestCase):
    def test_stock_fallback_downloads_labelled_images(self):
        root = Path(tempfile.mkdtemp(prefix="jarvis-stock-"))
        os.environ["PIXABAY_API_KEY"] = "test-key"
        try:
            for sub in ("assets/css", "assets/js", "assets/images/brand"):
                shutil.copytree(REPO / sub, root / sub)
            shutil.copy(REPO / "manifest.webmanifest", root / "manifest.webmanifest")
            cfg, sources = load_config(REPO), load_sources(REPO)
            ed = run_daily(root, cfg, sources, NOW, fixtures=FIXTURES, log_fn=lambda *_: None)
            stories = ed["stories"]["global"] + ed["stories"]["india"]
            kinds = {s["image"]["type"] for s in stories}
            # The BBC story keeps its real publisher image; stories without one get an illustrative stock photo.
            acme = [s for s in stories if "acme" in s["source"]["url"]][0]
            self.assertEqual(acme["image"]["type"], "publisher")
            stock = [s for s in stories if s["image"]["type"] == "stock"]
            self.assertTrue(stock and kinds <= {"publisher", "stock"})
            ids = [s["image"]["stock_id"] for s in stock]
            self.assertEqual(len(ids), len(set(ids)))           # no photo repeated in one edition
            self.assertNotIn("102", ids)                         # people-tagged hit skipped
            for s in stock:
                self.assertTrue((root / s["image"]["src"]).exists())
                self.assertTrue(s["image"]["src"].startswith("assets/images/stock/pixabay-"))
                self.assertIn("Illustrative", s["image"]["credit"])
                self.assertTrue(s["image"]["credit_url"].startswith("https://pixabay.com/"))
                self.assertTrue((root / s["image"]["fallback"]).exists())
            lib = load_json(root / "data" / "stock-library.json")
            self.assertTrue(lib["queries"] and set(ids) <= set(lib["images"]))
            self.assertNotIn("test-key", json.dumps(lib) + json.dumps(ed))  # key never stored
            self.assertEqual(validate.check(root, cfg, sources, check_cron=False), [])
        finally:
            os.environ.pop("PIXABAY_API_KEY", None)
            shutil.rmtree(root, ignore_errors=True)


class AIImageTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="jarvis-ai-"))
        for sub in ("assets/css", "assets/js", "assets/images/brand"):
            shutil.copytree(REPO / sub, self.root / sub)
        shutil.copy(REPO / "manifest.webmanifest", self.root / "manifest.webmanifest")
        os.environ.update({"CLOUDFLARE_ACCOUNT_ID": "acct-test", "CLOUDFLARE_API_TOKEN": "token-test", "PIXABAY_API_KEY": "pix-test"})

    def tearDown(self):
        for k in ("PIXABAY_API_KEY", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN"):
            os.environ.pop(k, None)
        shutil.rmtree(self.root, ignore_errors=True)

    def test_ai_images_fill_gaps_before_stock_and_are_reused(self):
        from jarvis.aiimages import AIImagePicker, SCENES, build_prompt
        cfg, sources = load_config(REPO), load_sources(REPO)
        ed = run_daily(self.root, cfg, sources, NOW, fixtures=FIXTURES, log_fn=lambda *_: None)
        stories = ed["stories"]["global"] + ed["stories"]["india"]
        acme = [s for s in stories if "acme" in s["source"]["url"]][0]
        self.assertEqual(acme["image"]["type"], "publisher")         # real publisher photo still wins
        ai = [s for s in stories if s["image"]["type"] == "ai"]
        self.assertEqual(len(ai), len(stories) - 1)                  # AI fills every gap before Pixabay
        files = [s["image"]["src"] for s in ai]
        self.assertEqual(len(files), len(set(files)))                # no image repeated in one edition
        for s in ai:
            im = s["image"]
            self.assertIn(im["concept"], SCENES)
            self.assertEqual(im["prompt"], build_prompt(im["concept"], im["variant"]))
            self.assertIn("No people", im["prompt"])
            self.assertNotIn(s["source"]["name"], im["prompt"])
            self.assertIn("AI-generated", im["credit"])
            self.assertTrue((self.root / im["src"]).exists())
        blob = json.dumps(ed) + (self.root / "data" / "ai-image-library.json").read_text()
        self.assertNotIn("token-test", blob)
        self.assertNotIn("acct-test", blob)
        self.assertEqual(validate.check(self.root, cfg, sources, check_cron=False), [])

        # A week later the same concept reuses the stored image instead of generating a new one.
        later = AIImagePicker(self.root, cfg, None, "2026-11-10", [])
        story = ai[0]
        got = later.pick(story, story["image"]["fallback"])
        self.assertEqual(got["src"], story["image"]["src"])
        self.assertEqual(later.budget, cfg["images"]["ai"]["max_generations_per_run"])

    def test_validator_rejects_free_form_prompt(self):
        cfg, sources = load_config(REPO), load_sources(REPO)
        run_daily(self.root, cfg, sources, NOW, fixtures=FIXTURES, log_fn=lambda *_: None)
        path = self.root / "data" / "2026-11-03.json"
        ed = json.loads(path.read_text())
        s = next(x for x in ed["stories"]["global"] + ed["stories"]["india"] if x["image"]["type"] == "ai")
        s["image"]["prompt"] = "photo of a named CEO announcing a deal"
        path.write_text(json.dumps(ed))
        errs = validate.check(self.root, cfg, sources, check_cron=False)
        self.assertTrue(any("fixed generic scene prompts" in e for e in errs))


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

