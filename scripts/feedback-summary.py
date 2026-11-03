#!/usr/bin/env python3
"""Write data/feedback.json: the rating summary the app shows in Profile.

Reads GitHub issues labelled `feedback` (state: all) from config.feedback.repo with GITHUB_TOKEN.
A rating comes from a `rating-N` label (feedback Worker) or the issue form's "### Rating" answer.
Issues labelled spam, invalid or duplicate are ignored. Only counts are published, never the text.
Never fails the build: on any error it keeps the existing file and exits 0.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jarvis.common import DEFAULT_ROOT, load_config, save_json  # noqa: E402

IGNORE = {"spam", "invalid", "duplicate"}
FORM_RATING = re.compile(r"###\s*Rating\s+([1-5])\b")


def rating_of(issue: dict) -> int | None:
    labels = {l["name"] for l in issue.get("labels", [])}
    if labels & IGNORE or "pull_request" in issue:
        return None
    for name in labels:
        m = re.fullmatch(r"rating-([1-5])", name)
        if m:
            return int(m.group(1))
    m = FORM_RATING.search(issue.get("body") or "")
    return int(m.group(1)) if m else None


def summarize(issues: list[dict]) -> dict:
    ratings = [r for r in (rating_of(i) for i in issues) if r]
    dist = {str(n): ratings.count(n) for n in range(1, 6)}
    return {"count": len(ratings), "average": round(sum(ratings) / len(ratings), 2) if ratings else 0,
            "distribution": dist, "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}


def fetch_issues(repo: str, label: str, token: str) -> list[dict]:
    out, page = [], 1
    while page <= 20:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/issues?labels={label}&state=all&per_page=100&page={page}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                     "User-Agent": "jarvis-feedback-summary"})
        with urllib.request.urlopen(req, timeout=20) as r:
            batch = json.load(r)
        out += batch
        if len(batch) < 100:
            break
        page += 1
    return out


def main() -> int:
    root = DEFAULT_ROOT
    fb = load_config(root).get("feedback", {})
    token = os.environ.get("GITHUB_TOKEN")
    if not token or not fb.get("repo"):
        print("feedback summary: no GITHUB_TOKEN or repo; kept existing file")
        return 0
    try:
        summary = summarize(fetch_issues(fb["repo"], fb.get("label", "feedback"), token))
    except Exception as exc:  # network, rate limit, permissions: never block the edition
        print(f"feedback summary: skipped ({type(exc).__name__})")
        return 0
    save_json(root / "data" / "feedback.json", summary)
    print(f"feedback summary: {summary['count']} rating(s), average {summary['average']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
