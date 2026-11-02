#!/usr/bin/env python3
"""Convert schedule.local_time in scripts/config.json (Asia/Qatar by default) to a UTC cron
and write it into .github/workflows/daily-news.yml.

GitHub Actions cron is always UTC. Qatar has no daylight saving, so a fixed offset is exact;
for zones with DST this script uses the offset in effect today and prints a warning.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jarvis.common import DEFAULT_ROOT, load_config  # noqa: E402

WORKFLOW = DEFAULT_ROOT / ".github" / "workflows" / "daily-news.yml"
CRON_LINE = re.compile(r'(- cron: ")([^"]+)("\s*# jarvis-schedule.*)')


def utc_cron(local_time: str, zone_name: str) -> tuple[str, str]:
    hh, mm = (int(x) for x in local_time.split(":"))
    zone = ZoneInfo(zone_name)
    today = datetime.now(zone).replace(hour=hh, minute=mm, second=0, microsecond=0)
    utc = today.astimezone(ZoneInfo("UTC"))
    jan, jul = datetime(today.year, 1, 15, tzinfo=zone), datetime(today.year, 7, 15, tzinfo=zone)
    dst = jan.utcoffset() != jul.utcoffset()
    note = f"{local_time} {zone_name} = {utc:%H:%M} UTC"
    if dst:
        note += " (zone observes DST: re-run this script when clocks change)"
    return f"{utc.minute} {utc.hour} * * *", note


def expected_cron(cfg: dict) -> str:
    return utc_cron(cfg["schedule"]["local_time"], cfg["schedule"]["timezone"])[0]


def main() -> int:
    cfg = load_config(DEFAULT_ROOT)
    cron, note = utc_cron(cfg["schedule"]["local_time"], cfg["schedule"]["timezone"])
    text = WORKFLOW.read_text("utf-8")
    new, n = CRON_LINE.subn(lambda m: f'{m.group(1)}{cron}"  # jarvis-schedule: {note}', text)
    if n != 1:
        print("could not find the '# jarvis-schedule' cron line in the workflow", file=sys.stderr)
        return 1
    WORKFLOW.write_text(new, "utf-8")
    print(f"cron set to '{cron}'  ({note})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
