#!/usr/bin/env python3
"""Publication gate. The workflow commits nothing unless this exits 0.

Checks every dated edition: schema, limits, https links on trusted domains, publication dates
inside the edition window, unique ids, no story repeated across editions, files present for
every image and page, archive index consistent, local links in HTML resolve, signature present,
and the workflow cron matches scripts/config.json.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jarvis.common import (DATE_RE, DEFAULT_ROOT, domain_allowed, domain_of, load_config, load_json,  # noqa: E402
                           load_sources, normalize_url, parse_iso)
from jarvis.pipeline import allowed_domains  # noqa: E402

REQ_STORY = ["id", "rank", "headline", "summary", "key_insights", "impact", "category", "source",
             "published_at", "image", "summary_mode", "verification", "region"]
REQ_EDITION = ["schema_version", "edition_date", "edition_number", "edition_type", "generated_at",
               "window", "publisher", "counts", "stories"]
LOCAL_REF = re.compile(r'(?:src|href)="(?!https?:|mailto:|#|data:)([^"?#]+)')


def check(root: Path, cfg: dict, sources: dict, check_cron: bool = True) -> list[str]:
    errs: list[str] = []
    allowed = allowed_domains(sources)
    valid_cats = set(cfg["categories"])
    data_files = sorted(p for p in (root / "data").glob("*.json") if DATE_RE.match(p.stem))
    seen_urls: dict[str, str] = {}

    for path in data_files:
        ed = load_json(path)
        tag = path.name
        miss = [k for k in REQ_EDITION if k not in ed]
        if miss:
            errs.append(f"{tag}: missing edition keys {miss}"); continue
        if ed["edition_date"] != path.stem:
            errs.append(f"{tag}: edition_date {ed['edition_date']} does not match file name")
        w0, w1 = parse_iso(ed["window"]["start"]), parse_iso(ed["window"]["end"])
        for region, cap in (("global", cfg["edition"]["max_global"]), ("india", cfg["edition"]["max_india"])):
            stories = ed["stories"].get(region, [])
            if len(stories) > cap:
                errs.append(f"{tag}: {len(stories)} {region} stories exceeds cap {cap}")
            if ed["counts"][region] != len(stories):
                errs.append(f"{tag}: counts.{region} mismatch")
            ids = set()
            for s in stories:
                sid = s.get("id", "?")
                miss = [k for k in REQ_STORY if k not in s]
                if miss:
                    errs.append(f"{tag}/{sid}: missing {miss}"); continue
                if sid in ids:
                    errs.append(f"{tag}/{sid}: duplicate id in edition")
                ids.add(sid)
                if s["region"] != region:
                    errs.append(f"{tag}/{sid}: region field {s['region']} filed under {region}")
                url = s["source"]["url"]
                if not url.startswith("https://"):
                    errs.append(f"{tag}/{sid}: source url not https")
                if not domain_allowed(domain_of(url), allowed):
                    errs.append(f"{tag}/{sid}: domain {domain_of(url)} not trusted")
                key = normalize_url(url)
                if key in seen_urls and seen_urls[key] != ed["edition_date"]:
                    errs.append(f"{tag}/{sid}: duplicate of a story already published on {seen_urls[key]}")
                seen_urls.setdefault(key, ed["edition_date"])
                pub = parse_iso(s["published_at"])
                if not (w0 <= pub <= w1):
                    errs.append(f"{tag}/{sid}: published_at {s['published_at']} outside edition window")
                if s["category"] not in valid_cats:
                    errs.append(f"{tag}/{sid}: unknown category {s['category']}")
                if not s["headline"].strip() or not s["summary"].strip():
                    errs.append(f"{tag}/{sid}: empty headline or summary")
                if len(s["key_insights"]) > 3:
                    errs.append(f"{tag}/{sid}: more than 3 key insights")
                if s["summary_mode"] == "publisher-blurb" and (s["key_insights"] or s["impact"]):
                    errs.append(f"{tag}/{sid}: insights/impact present without a grounded summary")
                if not s["verification"].get("checks"):
                    errs.append(f"{tag}/{sid}: no verification checks recorded")
                img = s["image"]
                kind = img.get("type")
                fallback = img.get("fallback") or (img["src"] if kind == "generated" else None)
                if kind not in ("generated", "publisher", "publisher-copy"):
                    errs.append(f"{tag}/{sid}: unknown image type {kind}")
                if not fallback:
                    errs.append(f"{tag}/{sid}: no generated fallback cover recorded")
                else:
                    cover = root / fallback
                    if not cover.exists():
                        errs.append(f"{tag}/{sid}: cover image missing {fallback}")
                    else:
                        try:
                            ET.parse(cover)
                        except ET.ParseError as exc:
                            errs.append(f"{tag}/{sid}: cover SVG is not well-formed ({exc})")
                if kind == "publisher":
                    if not img["src"].startswith("https://"):
                        errs.append(f"{tag}/{sid}: publisher image is not https")
                    if not img.get("credit"):
                        errs.append(f"{tag}/{sid}: publisher image has no credit")
                if kind == "publisher-copy":
                    if cfg["images"]["mode"] != "publisher-download":
                        errs.append(f"{tag}/{sid}: downloaded publisher image present but download mode is off")
                    if not (root / img["src"]).exists():
                        errs.append(f"{tag}/{sid}: downloaded image missing {img['src']}")
        if not (root / "news" / f"{path.stem}.html").exists():
            errs.append(f"{tag}: news/{path.stem}.html missing")

    for page in (root / "news").glob("*.html"):
        if DATE_RE.match(page.stem) and not (root / "data" / f"{page.stem}.json").exists():
            errs.append(f"news/{page.name}: no matching data JSON")

    idx = load_json(root / "data" / "index.json")
    if data_files:
        if not idx:
            errs.append("data/index.json missing")
        else:
            dates = [e["date"] for e in idx["editions"]]
            if dates != sorted(dates, reverse=True):
                errs.append("data/index.json editions not sorted newest first")
            if set(dates) != {p.stem for p in data_files}:
                errs.append("data/index.json does not list exactly the editions in data/")
            if idx.get("latest") != max(dates):
                errs.append("data/index.json latest is not the newest edition")
            nums = [e["number"] for e in idx["editions"]]
            if len(set(nums)) != len(nums):
                errs.append("edition numbers are not unique")
            home = (root / "index.html").read_text("utf-8") if (root / "index.html").exists() else ""
            if f'"edition_date": "{idx["latest"]}"' not in home:
                errs.append("index.html does not show the latest edition")

    sig = cfg["site"]["signature"]
    pages = [root / "index.html"] + sorted((root / "news").glob("*.html"))
    for page in pages:
        if not page.exists():
            continue
        text = page.read_text("utf-8")
        rel = page.relative_to(root)
        if sig not in text or cfg["site"]["agent_credit"] not in text:
            errs.append(f"{rel}: publisher signature missing")
        for ref in set(LOCAL_REF.findall(text)):
            if not (page.parent / ref).resolve().exists():
                errs.append(f"{rel}: broken local link {ref}")

    if check_cron:
        spec = importlib.util.spec_from_file_location("set_schedule", root / "scripts" / "set-schedule.py")
        if spec and (root / ".github" / "workflows" / "daily-news.yml").exists():
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            want = mod.expected_cron(cfg)
            wf = (root / ".github" / "workflows" / "daily-news.yml").read_text("utf-8")
            if f'cron: "{want}"' not in wf:
                errs.append(f"workflow cron does not match config schedule (expected '{want}'); run scripts/set-schedule.py")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--no-cron", action="store_true")
    args = ap.parse_args()
    root = args.root.resolve()
    errs = check(root, load_config(DEFAULT_ROOT), load_sources(DEFAULT_ROOT), check_cron=not args.no_cron)
    if errs:
        print(f"VALIDATION FAILED ({len(errs)} problem(s)):")
        for e in errs:
            print("  -", e)
        return 1
    n = len([p for p in (root / "data").glob("*.json") if DATE_RE.match(p.stem)])
    print(f"validation passed: {n} edition(s) OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
