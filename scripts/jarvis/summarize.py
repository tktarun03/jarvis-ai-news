"""Grounded summaries.

With ANTHROPIC_API_KEY set, Claude writes summary / key insights / impact strictly from the
publisher's text, and every figure it writes is checked against that text. Without a key,
or when a summary fails the checks, the story falls back to the publisher's own feed
description and insights/impact are left empty and marked unavailable. Nothing is invented.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from .common import truncate

API_URL = "https://api.anthropic.com/v1/messages"

SYSTEM = (
    "You are the fact-checking desk of JARVIS AI NEWS. You summarise one news article using ONLY the "
    "SOURCE TEXT given. Never add facts, numbers, names, dates or quotes that are not in the source text. "
    "If the source text is too thin to support an insight or an impact statement, return an empty list or "
    "null for it rather than guessing. Paraphrase in your own words; do not copy any sentence, and never "
    "quote more than 10 consecutive words. Neutral tone, no hype, no opinions. "
    "Reply with one JSON object and nothing else."
)

PROMPT = """HEADLINE: {title}
PUBLISHER: {source}
CATEGORIES (choose one key): {categories}

SOURCE TEXT:
<<<
{text}
>>>

Return JSON with exactly these keys:
{{"headline": "a clear, accurate headline in your own words, max 90 characters",
  "summary": "2-3 sentences, max 320 characters",
  "key_insights": ["up to 3 short factual points from the source, each max 140 characters"],
  "impact": "1-2 sentences on who is affected and how, ONLY as far as the source supports it, max 240 characters; or null",
  "category": "one key from CATEGORIES",
  "tags": ["up to 4 short lowercase tags"],
  "supported": true or false  // false if the source text does not clearly describe a real news event
}}"""

NUM_RE = re.compile(r"\d[\d,.]*")


def _numbers(text: str) -> set[str]:
    out = set()
    for raw in NUM_RE.findall(text or ""):
        n = raw.rstrip(".,").replace(",", "")
        if n:
            out.add(n)
    return out


def grounding_problems(result: dict, source_text: str) -> list[str]:
    """Return reasons the summary is not supported by the source text (empty list = grounded)."""
    problems = []
    src_nums = _numbers(source_text)
    written = " ".join([result.get("headline") or "", result.get("summary") or "", result.get("impact") or ""]
                       + list(result.get("key_insights") or []))
    for n in _numbers(written):
        if n not in src_nums and len(n) > 1:
            problems.append(f"number '{n}' not found in source")
    low_src = source_text.lower()
    for chunk in re.findall(r"[“\"]([^”\"]{20,})[”\"]", written):
        if chunk.lower() not in low_src:
            problems.append("quotation not found in source")
    return problems


class Summarizer:
    def __init__(self, cfg: dict, log: list):
        sc = cfg["summarizer"]
        self.key = os.environ.get(sc["env_key"], "").strip()
        self.model = os.environ.get("JARVIS_MODEL", sc["model"])
        self.max_chars = sc["max_source_chars"]
        self.budget = sc["max_calls_per_run"]
        self.categories = cfg["categories"]
        self.log = log

    @property
    def enabled(self) -> bool:
        return bool(self.key)

    def _call(self, title: str, source: str, text: str) -> dict | None:
        if self.budget <= 0:
            return None
        self.budget -= 1
        body = json.dumps({
            "model": self.model,
            "max_tokens": 900,
            "system": SYSTEM,
            "messages": [{"role": "user", "content": PROMPT.format(
                title=title, source=source, text=text[: self.max_chars],
                categories=", ".join(self.categories))}],
        }).encode("utf-8")
        req = urllib.request.Request(API_URL, data=body, method="POST", headers={
            "x-api-key": self.key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Never print the key or request headers; status code only.
            self.log.append({"title": title, "reason": f"summarizer HTTP {exc.code}"})
            return None
        except Exception as exc:
            self.log.append({"title": title, "reason": f"summarizer error {type(exc).__name__}"})
            return None
        text_out = "".join(b.get("text", "") for b in payload.get("content", []) if b.get("type") == "text")
        m = re.search(r"\{.*\}", text_out, re.S)
        if not m:
            return None
        try:
            # tolerate a trailing // comment copied from the schema
            return json.loads(re.sub(r"//[^\n]*", "", m.group(0)))
        except json.JSONDecodeError:
            return None

    def summarize(self, title: str, source_name: str, description: str, body: str, fallback_category: str) -> dict:
        source_text = f"{title}\n{description}\n{body}".strip()
        if self.enabled and len(source_text) > 200:
            for _attempt in range(2):
                res = self._call(title, source_name, source_text)
                if not res:
                    continue
                if res.get("supported") is False:
                    return {"rejected": "summarizer judged source text not to describe a real news event"}
                problems = grounding_problems(res, source_text)
                if problems:
                    self.log.append({"title": title, "reason": "summary failed grounding: " + "; ".join(problems[:3])})
                    continue
                cat = res.get("category") if res.get("category") in self.categories else fallback_category
                return {
                    "headline": truncate(res.get("headline") or title, 110),
                    "summary": truncate(res.get("summary") or "", 360),
                    "key_insights": [truncate(x, 160) for x in (res.get("key_insights") or [])][:3],
                    "impact": truncate(res["impact"], 260) if res.get("impact") else None,
                    "category": cat,
                    "tags": [str(t).lower()[:24] for t in (res.get("tags") or [])][:4],
                    "summary_mode": "ai-grounded",
                }
        # Extractive fallback: the publisher's own syndication blurb, clearly labelled.
        return {
            "headline": truncate(title, 110),
            "summary": truncate(description or title, 320),
            "key_insights": [],
            "impact": None,
            "category": fallback_category,
            "tags": [],
            "summary_mode": "publisher-blurb",
        }
