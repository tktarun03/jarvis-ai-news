"""Story images.

Modes (scripts/config.json -> images.mode):
  generated           original JARVIS cover only (no third-party images at all)
  publisher-hotlink   show the publisher's own og:image, loaded from the publisher's server, with credit;
                      the generated cover is the fallback if it fails to load (default)
  publisher-download  copy the publisher's image into assets/images/news/DATE/ (off by default: this
                      redistributes copyrighted photos from a public repo; enable only with rights)
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from .feeds import page_meta

IMAGE_KEYS = ("og:image:secure_url", "og:image", "og:image:url", "twitter:image", "twitter:image:src", "thumbnailurl")
SKIP_RE = re.compile(r"(logo|favicon|sprite|placeholder|default[-_]?(og|share|image)|blank|spacer|avatar)", re.I)
EXT_BY_TYPE = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif", "image/avif": "avif"}


def find_publisher_image(html_text: str, page_url: str) -> str | None:
    meta = page_meta(html_text)
    for key in IMAGE_KEYS:
        raw = (meta.get(key) or "").strip()
        if not raw:
            continue
        url = urljoin(page_url, raw)
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.netloc:
            continue
        if SKIP_RE.search(parts.path) or parts.path.lower().endswith(".svg"):
            continue
        return url
    return None


def publisher_image(mode: str, image_url: str | None, story: dict, fallback_rel: str, root: Path,
                    date: str, fetcher, max_bytes: int) -> dict | None:
    """Return the image block for a publisher image, or None to keep the generated cover."""
    if mode == "generated" or not image_url:
        return None
    credit = f"Image: {story['source']['name']}"
    base = {"alt": f"Image from {story['source']['name']} for: {story['headline']}", "credit": credit,
            "credit_url": story["source"]["url"], "fallback": fallback_rel, "original_url": image_url}
    if mode == "publisher-hotlink":
        return {"type": "publisher", "src": image_url, **base}
    if mode == "publisher-download":
        status, ctype, data = fetcher.get_bytes(image_url, max_bytes)
        ext = EXT_BY_TYPE.get((ctype or "").split(";")[0].strip().lower())
        if status != 200 or not ext or not data:
            return None
        rel = f"assets/images/news/{date}/{story['id']}.{ext}"
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {"type": "publisher-copy", "src": rel, **base}
    return None
