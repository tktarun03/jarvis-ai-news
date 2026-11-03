#!/usr/bin/env python3
"""Point the app at the feedback Worker: python scripts/set-feedback-endpoint.py https://jarvis-feedback.NAME.workers.dev
An empty argument ("") switches back to the GitHub issue form. Re-render afterwards."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
url = (sys.argv[1] if len(sys.argv) > 1 else "").strip().rstrip("/")
if url and not re.fullmatch(r"https://[A-Za-z0-9.-]+(/[A-Za-z0-9._/-]*)?", url):
    sys.exit(f"not an https URL: {url!r}")
p = ROOT / "scripts" / "config.json"
cfg = json.loads(p.read_text("utf-8"))
cfg.setdefault("feedback", {})["endpoint"] = url
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", "utf-8")
print(f"feedback endpoint: {url or '(none: GitHub issue form)'}")
