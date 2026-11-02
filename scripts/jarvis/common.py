"""Shared helpers: paths, JSON IO, time, URL and title normalisation."""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = SCRIPTS_DIR.parent
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "utm_id",
    "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src", "cmpid", "ito", "src", "taid",
}

STOPWORDS = set(
    "a an the and or of to in on for with by at from as is are was were be been it its this that "
    "into over after amid says said new how why what will can could may vs via up out about than "
    "his her their our your more most just now".split()
)


def load_json(path: Path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default


def save_json(path: Path, data) -> None:
    """Atomic write so a crashed run never leaves half a JSON file behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def load_config(root: Path) -> dict:
    return load_json(root / "scripts" / "config.json")


def load_sources(root: Path) -> dict:
    return load_json(root / "scripts" / "sources.json")


def tz(config: dict) -> ZoneInfo:
    return ZoneInfo(config["schedule"]["timezone"])


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    parts = urlsplit(url)
    scheme = "https" if parts.scheme in ("http", "https") else parts.scheme
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    if netloc.startswith("amp."):
        netloc = netloc[4:]
    path = re.sub(r"/amp/?$", "/", parts.path) or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if k.lower() not in TRACKING_PARAMS])
    return urlunsplit((scheme, netloc, path, query, ""))


def public_url(url: str) -> str:
    """URL to publish: https, tracking stripped, host kept as the publisher wrote it."""
    parts = urlsplit((url or "").strip())
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if k.lower() not in TRACKING_PARAMS])
    scheme = "https" if parts.scheme in ("http", "https") else parts.scheme
    return urlunsplit((scheme, parts.netloc, parts.path, query, ""))


def domain_of(url: str) -> str:
    host = urlsplit(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def domain_allowed(domain: str, allowed: set[str]) -> bool:
    return any(domain == d or domain.endswith("." + d) for d in allowed)


def story_id(url: str) -> str:
    return hashlib.sha1(normalize_url(url).encode("utf-8")).hexdigest()[:12]


def clean_text(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    value = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", value).strip()


def title_tokens(title: str) -> set[str]:
    words = re.findall(r"[a-z0-9$₹€£%.]+", clean_text(title).lower())
    return {w.strip(".") for w in words if w.strip(".") and w not in STOPWORDS and len(w) > 1}


def title_fingerprint(title: str) -> str:
    return hashlib.sha1(" ".join(sorted(title_tokens(title))).encode("utf-8")).hexdigest()[:16]


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(",;:—-")
    return cut + "…"


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"“‘(])", clean_text(text))
    return [p.strip() for p in parts if len(p.strip()) > 20]
