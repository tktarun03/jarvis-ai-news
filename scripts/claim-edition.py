#!/usr/bin/env python3
"""Coordinate edition jobs between agents. Run this BEFORE doing any edition work.

  python scripts/claim-edition.py check                      # today's Doha date
  python scripts/claim-edition.py claim --agent chatgpt --push
  python scripts/claim-edition.py release --agent chatgpt --push   # if you give up

Exit codes:  0 = free (check) / claimed by you (claim)
            10 = already published: the job is complete, stop and report who did it
            11 = another agent holds a live claim: stop, do not start a second run
             1 = error (for example the claim could not be pushed)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jarvis import claims  # noqa: E402
from jarvis.common import DEFAULT_ROOT, load_config, tz  # noqa: E402

CODES = {"free": 0, "mine": 0, "published": 10, "claimed": 11}


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=DEFAULT_ROOT, capture_output=True, text=True)


def sync() -> None:
    """Get the latest claims and editions from GitHub before deciding anything."""
    git("pull", "--rebase", "--autostash", "-q", "origin", "main")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["check", "claim", "release"])
    ap.add_argument("--date", help="edition date YYYY-MM-DD (default: today in the configured timezone)")
    ap.add_argument("--agent", default="unknown", help="who you are: claude, chatgpt, github-actions, a person's name")
    ap.add_argument("--minutes", type=int, default=claims.DEFAULT_MINUTES, help="claim lifetime")
    ap.add_argument("--push", action="store_true", help="pull first, then commit and push the claim file")
    args = ap.parse_args()

    cfg = load_config(DEFAULT_ROOT)
    now = claims.utcnow()
    date = args.date or now.astimezone(tz(cfg)).date().isoformat()
    if args.push:
        sync()
    st = claims.status(DEFAULT_ROOT, date, args.agent, now)

    if args.action == "check" or st["state"] in ("published", "claimed"):
        print(st["message"])
        return CODES[st["state"]]

    if args.action == "release":
        claims.finish(DEFAULT_ROOT, date, args.agent, now, state="released")
        msg = f"release: {date} by {args.agent}"
    else:
        claims.claim(DEFAULT_ROOT, date, args.agent, now, args.minutes)
        msg = f"claim: {date} by {args.agent}"

    if args.push:
        git("add", str(claims.claim_path(DEFAULT_ROOT, date)))
        git("commit", "-q", "-m", msg)
        if git("push", "-q", "origin", "HEAD:main").returncode != 0:
            # Someone pushed first. Re-read their state; give way if they now hold the job.
            # Undo only our claim commit and file; never touch other work in the tree.
            path = claims.claim_path(DEFAULT_ROOT, date)
            git("reset", "-q", "HEAD~1")
            if git("ls-files", "--error-unmatch", str(path)).returncode == 0:
                git("checkout", "--", str(path))
            else:
                path.unlink(missing_ok=True)
            sync()
            st = claims.status(DEFAULT_ROOT, date, args.agent, claims.utcnow())
            if st["state"] in ("published", "claimed"):
                print(st["message"])
                return CODES[st["state"]]
            print("Could not push the claim; try again.", file=sys.stderr)
            return 1
    print(f"{msg} (expires in {args.minutes} min)" if args.action == "claim" else msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
