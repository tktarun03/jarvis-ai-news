"""Job claims: so several agents (Claude, ChatGPT, the GitHub schedule, a person) never build the same edition.

One small file per edition date: data/claims/YYYY-MM-DD.json
  {"date", "agent", "status": "in_progress" | "completed" | "released", "claimed_at", "expires_at",
   "completed_at"?, "note"?}

Rules
  * The edition file data/YYYY-MM-DD.json is the source of truth for "done". If it exists, the job is complete,
    whoever made it.
  * An "in_progress" claim blocks other agents until it expires (default 90 minutes), so a crashed agent cannot
    block the day forever.
  * Claims are pushed to GitHub before work starts; a rejected push means someone else got there first.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from .common import iso, load_json, parse_iso, save_json

DEFAULT_MINUTES = 90


def claim_path(root: Path, date: str) -> Path:
    return root / "data" / "claims" / f"{date}.json"


def read(root: Path, date: str) -> dict | None:
    return load_json(claim_path(root, date))


def is_active(claim: dict | None, now: datetime) -> bool:
    return bool(claim) and claim.get("status") == "in_progress" and parse_iso(claim["expires_at"]) > now


def status(root: Path, date: str, agent: str, now: datetime) -> dict:
    """Return {"state": "published" | "claimed" | "free" | "mine", ...} for this agent."""
    ed = load_json(root / "data" / f"{date}.json")
    claim = read(root, date)
    if ed:
        by = (ed.get("produced_by") or {}).get("agent") or (claim or {}).get("agent") or "unknown agent"
        return {"state": "published", "by": by, "generated_at": ed.get("generated_at"),
                "message": f"Edition {date} is already published (by {by}, generated {ed.get('generated_at')}). Nothing to do."}
    if is_active(claim, now):
        if claim["agent"] == agent:
            return {"state": "mine", "claim": claim, "message": f"You already hold the claim for {date}."}
        return {"state": "claimed", "by": claim["agent"], "claim": claim,
                "message": f"Edition {date} is being built by {claim['agent']} (claimed {claim['claimed_at']}, "
                           f"expires {claim['expires_at']}). Do not start another run."}
    return {"state": "free", "claim": claim, "message": f"Edition {date} is free to build."}


def claim(root: Path, date: str, agent: str, now: datetime, minutes: int = DEFAULT_MINUTES, note: str = "") -> dict:
    data = {"date": date, "agent": agent, "status": "in_progress", "claimed_at": iso(now),
            "expires_at": iso(now + timedelta(minutes=minutes))}
    if note:
        data["note"] = note
    save_json(claim_path(root, date), data)
    return data


def finish(root: Path, date: str, agent: str, now: datetime, state: str = "completed") -> None:
    c = read(root, date) or {"date": date, "agent": agent, "claimed_at": iso(now), "expires_at": iso(now)}
    if c.get("agent") != agent and is_active(c, now):
        return  # never overwrite another agent's live claim
    c.update({"agent": agent, "status": state, ("completed_at" if state == "completed" else "released_at"): iso(now)})
    save_json(claim_path(root, date), c)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
