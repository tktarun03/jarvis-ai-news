"""Per-story share pages: news/DATE/ID.html.

WhatsApp, Telegram, X and iMessage build a link preview from the og: tags of the exact page a
link points to and ignore the #fragment, so a story link needs its own page to show its own
headline, summary and picture. Each page carries those tags, then forwards readers to the story
inside the edition (news/DATE.html#s-ID). Crawlers do not run the script, so they keep the tags.

Preview image, by image type:
  publisher       -> the publisher's https image (hotlinked, as on the site)
  ai / stock / publisher-copy -> the local raster file, as an absolute URL
  generated       -> the category's share card, assets/images/share/CATEGORY.png. Link previews
                     cannot show SVG, and a PNG per story would add ~200 KB a story to a repo that
                     keeps every edition, so there is one reusable card per category (8 files).
                     The cards are committed; a missing one is drawn with `rsvg-convert` (librsvg)
                     if available, otherwise the brand card assets/images/brand/og.png is used.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
from html import escape
from pathlib import Path

RASTER = (".png", ".jpg", ".jpeg", ".webp", ".gif")
PREVIEW_W = 1200
MAX_PNG_BYTES = 290_000  # WhatsApp is unreliable with large preview images


def share_path(date: str, sid: str) -> str:
    return f"news/{date}/{sid}.html"


def share_url(cfg: dict, date: str, sid: str) -> str:
    return cfg["site"]["base_url"] + share_path(date, sid)


def clip(text: str, n: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= n:
        return text
    cut = text[: n - 1].rsplit(" ", 1)[0].rstrip(",;:—-")
    return cut + "…"


def category_card(root: Path, cfg: dict, category: str) -> str | None:
    """Repo path of the category's PNG share card, drawing it once if needed."""
    rel = f"assets/images/share/{category}.png"
    out = root / rel
    if out.exists():
        return rel
    meta = cfg["categories"].get(category)
    exe = shutil.which("rsvg-convert")
    if not meta or not exe:
        return None
    from .covers import render_cover
    sid = hashlib.sha1(category.encode()).hexdigest()[:12]
    svg = render_cover(sid, category, meta["label"], meta["color"], "Daily AI news, verified", "JARVIS AI NEWS")
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        for width in (PREVIEW_W, 800, 600):
            subprocess.run([exe, "-w", str(width), "-o", str(out)], input=svg.encode(), check=True,
                           capture_output=True, timeout=60)
            if out.stat().st_size <= MAX_PNG_BYTES:
                break
    except (subprocess.SubprocessError, OSError):
        out.unlink(missing_ok=True)
        return None
    return rel


def preview_image(root: Path, cfg: dict, s: dict) -> tuple[str, str | None]:
    """(absolute image URL, repo path if local or None)."""
    base = cfg["site"]["base_url"]
    img = s["image"]
    kind, src = img.get("type"), img.get("src", "")
    if kind == "publisher" and src.startswith("https://"):
        return src, None
    if kind in ("ai", "stock", "publisher-copy") and src.lower().endswith(RASTER) and (root / src).exists():
        return base + src, src
    card = category_card(root, cfg, s["category"])
    if card:
        return base + card, card
    return base + "assets/images/brand/og.png", "assets/images/brand/og.png"


def render_share_page(s: dict, date: str, cfg: dict, image_url: str) -> str:
    site = cfg["site"]
    url = share_url(cfg, date, s["id"])
    target = f"../{date}.html#s-{s['id']}"
    region = "India" if s.get("region") == "india" else "Global"
    cat = cfg["categories"].get(s["category"], {}).get("label", "")
    desc = clip(s["summary"], 200)
    title = s["headline"]
    h = escape
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{h(title)} · {h(site['name'])}</title>
<meta name="description" content="{h(desc)}">
<link rel="canonical" href="{h(url)}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="{h(site['name'])}">
<meta property="og:title" content="{h(title)}">
<meta property="og:description" content="{h(desc)}">
<meta property="og:url" content="{h(url)}">
<meta property="og:image" content="{h(image_url)}">
<meta property="og:image:alt" content="{h(s['image'].get('alt') or title)}">
<meta property="article:published_time" content="{h(s['published_at'])}">
<meta property="article:section" content="{h(cat)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{h(title)}">
<meta name="twitter:description" content="{h(desc)}">
<meta name="twitter:image" content="{h(image_url)}">
<meta name="author" content="{h(site['publisher'])}">
<meta name="theme-color" content="#FFFFFF">
<link rel="icon" href="../../assets/images/brand/favicon.svg" type="image/svg+xml">
<script>location.replace({target!r});</script>
<style>
body{{margin:0;background:#fff;color:#14151A;font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
main{{max-width:560px;margin:0 auto;padding:40px 20px}}
.k{{font-size:13px;color:#6B6F7B;margin:0 0 8px}}h1{{font-size:24px;line-height:1.25;margin:0 0 14px}}
a{{color:#4F4BD6;font-weight:600}}.f{{margin-top:32px;font-size:13px;color:#6B6F7B}}
</style>
</head>
<body>
<main>
<p class="k">{h(site['name'])} · {h(region)} · {h(cat)}</p>
<h1>{h(title)}</h1>
<p>{h(s['summary'])}</p>
<p><a href="{h(target)}">Open in {h(site['name'])}</a> · <a href="{h(s['source']['url'])}" rel="noopener">Read at {h(s['source']['name'])}</a></p>
<div class="f"><p>{h(site['signature'])}</p><p>{h(site['agent_credit'])}</p></div>
</main>
</body>
</html>
"""


def write_share_pages(root: Path, edition: dict, cfg: dict) -> int:
    date = edition["edition_date"]
    folder = root / "news" / date
    folder.mkdir(parents=True, exist_ok=True)
    keep = set()
    n = 0
    for region in ("global", "india"):
        for s in edition["stories"].get(region, []):
            image_url, _ = preview_image(root, cfg, s)
            page = folder / f"{s['id']}.html"
            page.write_text(render_share_page(s, date, cfg, image_url), "utf-8")
            keep.add(page.name)
            n += 1
    for old in folder.glob("*.html"):  # a --force rebuild can drop stories
        if old.name not in keep:
            old.unlink()
    return n
