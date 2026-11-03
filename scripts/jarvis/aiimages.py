"""AI-generated generic images (photorealistic scenes, not illustrations), stored in the repo.

Provider: Cloudflare Workers AI, model @cf/black-forest-labs/flux-1-schnell (Apache-2.0), which fits in the
free daily allocation. Runs only inside GitHub Actions with the CLOUDFLARE_ACCOUNT_ID and
CLOUDFLARE_API_TOKEN secrets; without them this step is skipped.

Safeguards (see AGENTS.md rule 4):
  * Prompts come only from the fixed SCENES table below (generic places and objects). Story text, company,
    product and person names never reach the prompt, so an image cannot depict or imply a real party.
    The validator re-builds the prompt from (concept, variant) and rejects anything else.
  * Every prompt asks for no people, faces, text, logos or watermarks.
  * Every image is labelled "AI-generated · not from the event".
  * A library of up to `max_variants_per_concept` images per concept is reused across editions, which keeps
    the repo small and the free quota untouched on most days. The same image is not used twice in one
    edition, and not again within `reuse_after_days` unless nothing else fits.
"""
from __future__ import annotations

import base64
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from .common import load_json, save_json
from .stock import queries_for

LIBRARY = "data/ai-image-library.json"
STYLE = ("photorealistic editorial photograph, natural light, shallow depth of field, high detail, 16:9 composition. "
         "No people, no faces, no hands, no text, no letters, no logos, no brand names, no watermarks.")
VARIANTS = ["wide establishing shot", "close-up detail shot", "low-angle view", "overhead view",
            "soft morning light", "moody evening light", "side view with depth", "minimal clean composition"]

SCENES = {
    "data center": "rows of illuminated server racks in a modern data center corridor, cool blue light",
    "fiber optic": "glowing fiber optic cables bundled in a network room",
    "computer chip": "macro photograph of a silicon microchip on a green circuit board",
    "server": "close view of network switches and blinking server lights in a rack",
    "robot": "a sleek industrial robot arm in a clean modern factory",
    "medical technology": "an empty modern hospital room with medical monitors and equipment",
    "classroom technology": "an empty modern classroom with laptops and tablets on the desks",
    "agriculture technology": "green crop fields with a farming drone hovering above at sunrise",
    "telecommunication tower": "a telecommunication tower with antennas against a clear sky",
    "energy industry": "an energy facility with pipelines and power lines at dusk",
    "satellite": "a communications satellite orbiting above the curved Earth",
    "self driving car": "a modern electric car on an empty city road at night with light trails",
    "drone": "a quadcopter drone flying over a landscape",
    "microphone sound wave": "a studio microphone in front of soft glowing lights",
    "cyber security": "a glowing padlock symbol over dark computer circuitry",
    "digital privacy": "a dark computer screen with abstract blurred data, a padlock on the keyboard",
    "padlock": "a metal padlock resting on a laptop keyboard",
    "law justice": "a wooden judge's gavel on a desk with law books",
    "government building": "a classical government building with columns under a blue sky",
    "cloud computing": "abstract white clouds above a city skyline connected by faint light lines",
    "artificial intelligence": "an abstract glowing neural network of light points in a dark room",
    "neural network": "abstract interconnected glowing nodes and lines on a dark background",
    "laboratory": "a clean modern research laboratory with computers and glassware",
    "finance chart": "a financial trading screen showing rising line charts, out of focus",
    "stock market": "an out-of-focus stock market display board with numbers and charts",
    "business": "a modern glass office tower reflecting the evening sky",
    "business handshake": "an empty boardroom table with chairs and a city view at dusk",
    "technology": "a modern workspace with a laptop and soft ambient light",
    "digital": "abstract flowing streams of light data in blue and violet",
    "smartphone": "a smartphone lying on a desk beside a laptop, screen glowing",
    "software": "a laptop screen showing blurred lines of code in a dark room",
    "startup": "a bright open-plan startup office with desks and plants, empty",
    "workspace": "a tidy desk with a laptop, notebook and coffee by a window",
}


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def build_prompt(concept: str, variant: int) -> str:
    return f"{SCENES[concept]}, {VARIANTS[variant % len(VARIANTS)]}. {STYLE}"


def concept_for(story: dict) -> str:
    for q in queries_for(story):
        if q in SCENES:
            return q
    return "technology"


class AIImagePicker:
    def __init__(self, root: Path, cfg: dict, fetcher, edition_date: str, log: list, now: datetime | None = None):
        ac = cfg["images"].get("ai", {})
        self.root, self.fetcher, self.date, self.log = root, fetcher, edition_date, log
        self.account = os.environ.get(ac.get("env_account", "CLOUDFLARE_ACCOUNT_ID"), "").strip()
        self.token = os.environ.get(ac.get("env_token", "CLOUDFLARE_API_TOKEN"), "").strip()
        self.enabled = bool(ac.get("enabled")) and ac.get("provider") == "cloudflare" and bool(self.account and self.token)
        self.model = ac.get("model", "@cf/black-forest-labs/flux-1-schnell")
        self.steps = int(ac.get("steps", 4))
        self.folder = ac.get("folder", "assets/images/ai")
        self.max_variants = int(ac.get("max_variants_per_concept", 6))
        self.reuse_days = int(ac.get("reuse_after_days", 3))
        self.budget = int(ac.get("max_generations_per_run", 12))
        self.now = now or datetime.now(timezone.utc)
        self.lib = load_json(root / LIBRARY, {"concepts": {}})
        self.used_now: set[str] = set()
        self.dirty = False

    def _recent(self, entry: dict) -> bool:
        last = entry.get("last_used")
        if not last or last == self.date:
            return False
        return (datetime.fromisoformat(self.date) - datetime.fromisoformat(last)).days < self.reuse_days

    def _generate(self, concept: str, variant: int) -> str | None:
        if self.budget <= 0:
            return None
        self.budget -= 1
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.account}/ai/run/{self.model}"
        status, payload = self.fetcher.post_json(url, {"prompt": build_prompt(concept, variant), "steps": self.steps},
                                                 {"Authorization": f"Bearer {self.token}"})
        if status != 200 or not isinstance(payload, dict):
            # Status only: never log the URL (it contains the account id) or headers (the token).
            self.log.append({"title": f"AI image '{concept}'", "reason": f"image generation failed ({status})"})
            return None
        b64 = (payload.get("result") or {}).get("image") if isinstance(payload.get("result"), dict) else payload.get("image")
        try:
            data = base64.b64decode(b64 or "", validate=True)
        except (ValueError, TypeError):
            data = b""
        if data[:3] == b"\xff\xd8\xff":
            ext = "jpg"
        elif data[:8] == b"\x89PNG\r\n\x1a\n":
            ext = "png"
        elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            ext = "webp"
        else:
            self.log.append({"title": f"AI image '{concept}'", "reason": "image generation returned no image"})
            return None
        rel = f"{self.folder}/{slug(concept)}-{variant + 1}.{ext}"
        (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
        (self.root / rel).write_bytes(data)
        return rel

    def pick(self, story: dict, fallback_rel: str) -> dict | None:
        if not self.enabled:
            return None
        concept = concept_for(story)
        entries = self.lib["concepts"].setdefault(concept, [])
        live = [e for e in entries if (self.root / e["file"]).exists() and e["file"] not in self.used_now]
        choice = next((e for e in sorted(live, key=lambda e: e.get("last_used") or "") if not self._recent(e)), None)
        if choice is None and len(entries) < self.max_variants:
            variant = len(entries)
            rel = self._generate(concept, variant)
            if rel:
                choice = {"file": rel, "variant": variant, "prompt": build_prompt(concept, variant), "model": self.model,
                          "created": self.date}
                entries.append(choice)
        if choice is None and live:
            choice = sorted(live, key=lambda e: e.get("last_used") or "")[0]
        if choice is None:
            return None
        choice["last_used"] = self.date
        self.used_now.add(choice["file"])
        self.dirty = True
        return {"type": "ai", "src": choice["file"], "fallback": fallback_rel, "provider": "cloudflare-workers-ai",
                "model": choice["model"], "concept": concept, "variant": choice["variant"], "prompt": choice["prompt"],
                "alt": f"AI-generated image: {SCENES[concept]}; not from the event",
                "credit": "AI-generated · not from the event"}

    def save(self) -> None:
        if self.dirty:
            save_json(self.root / LIBRARY, self.lib)
