#!/usr/bin/env python3
"""JARVIS AI NEWS: build today's dated edition (Asia/Qatar date) and update the archive.

  python scripts/generate-news.py                 # daily run (what GitHub Actions calls)
  python scripts/generate-news.py --force         # rebuild today's edition
  python scripts/generate-news.py --rerender      # re-render all HTML from JSON (after design changes)
  python scripts/generate-news.py --curated scripts/sample/2026-11-02.curated.json
  python scripts/generate-news.py --fixtures tests/fixtures --now 2026-11-03T04:30:00Z --root /tmp/x

Exit codes: 0 = published or nothing to do (skip), 1 = error.
Writes a one-line status to $GITHUB_OUTPUT (published=true|false) when running in Actions.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from jarvis.common import DEFAULT_ROOT, load_config, load_sources, parse_iso, utcnow  # noqa: E402
from jarvis.pipeline import Skip, build_from_curated, rerender_all, run_daily  # noqa: E402


def gh_output(**kv):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            for k, v in kv.items():
                fh.write(f"{k}={v}\n")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary and "message" in kv:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"### JARVIS AI NEWS\n\n{kv['message']}\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="site root (default: repo root)")
    ap.add_argument("--force", action="store_true", help="rebuild an edition that already exists")
    ap.add_argument("--now", help="override the current time (ISO 8601, for tests and backfills)")
    ap.add_argument("--fixtures", type=Path, help="serve feeds/articles from a fixtures folder (offline)")
    ap.add_argument("--curated", type=Path, help="build from a hand-verified curated JSON file")
    ap.add_argument("--rerender", action="store_true", help="re-render every edition page from JSON")
    args = ap.parse_args()

    root = args.root.resolve()
    cfg_root = root if (root / "scripts" / "config.json").exists() else DEFAULT_ROOT
    cfg, sources = load_config(cfg_root), load_sources(cfg_root)
    now = parse_iso(args.now) if args.now else utcnow()

    try:
        if args.rerender:
            n = rerender_all(root, cfg)
            print(f"re-rendered {n} edition page(s)")
            return 0
        if args.curated:
            ed = build_from_curated(root, cfg, sources, args.curated, now, force=args.force)
        else:
            ed = run_daily(root, cfg, sources, now, force=args.force, fixtures=args.fixtures)
    except Skip as skip:
        print(f"SKIP: {skip}")
        gh_output(published="false", message=f"Skipped: {skip}")
        return 0

    msg = (f"Published edition {ed['edition_date']} (No. {ed['edition_number']}): "
           f"{ed['counts']['global']} global, {ed['counts']['india']} India, {len(ed['rejected'])} rejected.")
    print(msg)
    gh_output(published="true", date=ed["edition_date"], message=msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
