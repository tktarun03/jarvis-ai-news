"""Royalty-free illustrative photos from Pixabay, stored in the repo (assets/images/stock/).

Why Pixabay: its API terms require downloading images to your own server (no permanent hotlinking),
which is exactly what committing them to this repo does, and its Content License allows free use
without attribution. Unsplash's API terms require hotlinking instead, so it is not used.

Safeguards (see AGENTS.md rule 4):
  * Queries are built from generic topic words only (category + concept keywords such as "data center"),
    never from company, product or person names, so a photo never suggests a real party was involved.
  * Hits tagged with people (man, woman, face, portrait ...) are skipped.
  * Every stock image is labelled "Illustrative" and credits the photographer with a link to Pixabay.
  * API responses are cached for 24 hours (Pixabay requirement) in data/stock-library.json.
  * Images are reused from the library when possible to keep the repo small; the same photo is not used
    twice in one edition, and not again within `reuse_after_days` unless nothing else fits.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

from .common import load_json, save_json

API = "https://pixabay.com/api/"
LIBRARY = "data/stock-library.json"
EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
PEOPLE = re.compile(r"\b(man|men|woman|women|people|person|persons|girl|boy|child|children|kid|kids|face|portrait|model|"
                    r"businessman|businesswoman|couple|family|selfie|crowd|student|doctor|worker|lady|guy)\b", re.I)

# Concept hints: specific generic scenes first. Patterns are matched against headline + summary.
HINTS = [
    (r"data ?cent(?:er|re)s?|datacent|server farm|supercluster", "data center"),
    (r"\bchips?\b|semiconductor|\bgpus?\b|processor|silicon", "computer chip"),
    (r"optical|photonic|fib(?:er|re)", "fiber optic"),
    (r"robot|humanoid|embodied", "robot"),
    (r"hospital|medical|health|triage|patient|clinic|drug", "medical technology"),
    (r"school|education|student|classroom|universit", "classroom technology"),
    (r"farm|agricultur|crop", "agriculture technology"),
    (r"telecom|\btelcos?\b|5g|mobile network|spectrum", "telecommunication tower"),
    (r"energy|\boil\b|\bgas\b|power grid|solar|electricity|adnoc", "energy industry"),
    (r"satellite|space|orbit", "satellite"),
    (r"self-driving|autonomous (?:car|vehicle)|\bev\b|vehicle", "self driving car"),
    (r"\bdrones?\b", "drone"),
    (r"speech|voice|audio|transcri", "microphone sound wave"),
    (r"cyber|breach|malware|backdoor|hack|phishing|ransomware|vulnerab", "cyber security"),
    (r"deepfake|misinformation|fake", "digital privacy"),
    (r"court|lawsuit|regulat|guideline|consultation|policy|ministry|law\b|draft rules", "law justice"),
    (r"cloud", "cloud computing"),
    (r"language model|\bllm|chatbot|assistant|benchmark|model", "artificial intelligence"),
    # Generic business scenes: used ahead of category queries only for business and startup stories.
    (r"\b(?:banks?|fintech|payments?|gst|tax|revenue|earnings|loss|profits?|ipo|valuation|funding|raises?|crore)\b", "finance chart"),
    (r"\b(?:merger|acquisition|acquires?|deal)\b", "business handshake"),
]
GENERIC = {"finance chart", "business handshake", "artificial intelligence"}
CATEGORY_QUERIES = {
    "research": ["artificial intelligence", "neural network", "laboratory"],
    "products": ["technology", "smartphone", "software"],
    "business": ["finance chart", "business", "stock market"],
    "policy": ["law justice", "government building"],
    "infrastructure": ["data center", "computer chip", "server"],
    "safety": ["cyber security", "padlock"],
    "applications": ["technology", "digital"],
    "startups": ["startup", "workspace"],
}


def queries_for(story: dict) -> list[str]:
    text = f"{story.get('headline', '')} {story.get('summary', '')}".lower()
    found = [q for pattern, q in HINTS if re.search(pattern, text)]
    specific = [q for q in found if q not in GENERIC][:2]
    generic = [q for q in found if q in GENERIC][:1]
    cat = story.get("category")
    order = specific + (generic if cat in ("business", "startups") else []) + CATEGORY_QUERIES.get(cat, ["technology"]) + generic
    out: list[str] = []
    for q in order:
        if q not in out:
            out.append(q)
    return out[:4]


class StockPicker:
    def __init__(self, root: Path, cfg: dict, fetcher, edition_date: str, log: list, now: datetime | None = None):
        sc = cfg["images"].get("stock", {})
        self.root, self.cfg, self.fetcher, self.date, self.log = root, sc, fetcher, edition_date, log
        self.key = os.environ.get(sc.get("env_key", "PIXABAY_API_KEY"), "").strip()
        self.enabled = bool(sc.get("enabled")) and sc.get("provider") == "pixabay" and bool(self.key)
        self.role = sc.get("role", "fallback")
        self.folder = sc.get("folder", "assets/images/stock")
        self.reuse_days = int(sc.get("reuse_after_days", 3))
        self.budget = int(sc.get("max_requests_per_run", 40))
        self.max_bytes = int(cfg["images"].get("max_download_bytes", 3_000_000))
        self.now = now or datetime.now(timezone.utc)
        self.lib = load_json(root / LIBRARY, {"images": {}, "queries": {}})
        self.used_now: set[str] = set()
        self.dirty = False

    def wanted(self, publisher_found: bool) -> bool:
        return self.enabled and (self.role == "primary" or not publisher_found)

    # -- API with 24h cache ------------------------------------------------------------------
    def _hits(self, q: str) -> list[dict]:
        cached = self.lib["queries"].get(q)
        if cached and self.now - datetime.fromisoformat(cached["fetched_at"]) < timedelta(hours=24):
            return cached["hits"]
        if self.budget <= 0:
            return cached["hits"] if cached else []
        self.budget -= 1
        url = API + "?" + urlencode({"key": self.key, "q": q, "image_type": "photo", "orientation": "horizontal",
                                     "safesearch": "true", "order": "popular", "per_page": 30, "min_width": 960})
        resp = self.fetcher.get(url, accept="application/json")
        if resp.status != 200 or not resp.text:
            # Status only: never log the URL, it contains the API key.
            self.log.append({"title": f"stock query '{q}'", "reason": f"Pixabay request failed ({resp.status})"})
            return cached["hits"] if cached else []
        try:
            raw = json.loads(resp.text).get("hits", [])
        except json.JSONDecodeError:
            return []
        hits = [{"id": str(h["id"]), "page": h.get("pageURL", ""), "user": h.get("user", "Pixabay"), "tags": h.get("tags", ""),
                 "web": h.get("webformatURL", "")} for h in raw if h.get("id") and h.get("webformatURL")]
        self.lib["queries"][q] = {"fetched_at": self.now.replace(microsecond=0).isoformat(), "hits": hits}
        self.dirty = True
        return hits

    def _recent(self, hid: str) -> bool:
        last = self.lib["images"].get(hid, {}).get("last_used")
        if not last or last == self.date:
            return False
        return (datetime.fromisoformat(self.date) - datetime.fromisoformat(last)).days < self.reuse_days

    def _download(self, hit: dict) -> str | None:
        known = self.lib["images"].get(hit["id"])
        if known and (self.root / known["file"]).exists():
            return known["file"]
        for url in (hit["web"].replace("_640.", "_960."), hit["web"]):
            status, ctype, data = self.fetcher.get_bytes(url, self.max_bytes)
            ext = EXT.get((ctype or "").split(";")[0].strip().lower())
            if status == 200 and ext and data:
                rel = f"{self.folder}/pixabay-{hit['id']}.{ext}"
                (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
                (self.root / rel).write_bytes(data)
                return rel
        return None

    def pick(self, story: dict, fallback_rel: str) -> dict | None:
        if not self.enabled:
            return None
        for strict in (True, False):
            for q in queries_for(story):
                for hit in self._hits(q):
                    hid = hit["id"]
                    if hid in self.used_now or PEOPLE.search(hit["tags"]) or not hit["page"].startswith("https://pixabay.com/"):
                        continue
                    if strict and self._recent(hid):
                        continue
                    rel = self._download(hit)
                    if not rel:
                        continue
                    self.used_now.add(hid)
                    entry = self.lib["images"].setdefault(hid, {"file": rel, "page": hit["page"], "user": hit["user"],
                                                                "tags": hit["tags"], "first_used": self.date})
                    entry["last_used"] = self.date
                    self.dirty = True
                    return {"type": "stock", "src": rel, "fallback": fallback_rel, "provider": "pixabay", "stock_id": hid,
                            "alt": f"Illustrative photo ({hit['tags']}); not from the event",
                            "credit": f"Illustrative · {hit['user']} / Pixabay", "credit_url": hit["page"],
                            "license": "Pixabay Content License", "query": q}
        return None

    def save(self) -> None:
        if self.dirty:
            save_json(self.root / LIBRARY, self.lib)
