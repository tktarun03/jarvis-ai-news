"""Fetching (live or fixture-backed) and RSS/Atom parsing. Standard library only."""
from __future__ import annotations

import gzip
import json
import re
import ssl
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from .common import clean_text, parse_iso, story_id

USER_AGENT = "JARVIS-AI-News/1.0 (+https://github.com/tktarun03/jarvis-ai-news; daily AI news digest)"
ATOM = "{http://www.w3.org/2005/Atom}"
MEDIA = "{http://search.yahoo.com/mrss/}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"
DC = "{http://purl.org/dc/elements/1.1/}"


@dataclass
class Response:
    status: int | None
    url: str
    text: str = ""
    error: str = ""


@dataclass
class FeedItem:
    title: str
    url: str
    published: datetime | None
    description: str
    source: dict
    id: str = field(init=False)

    def __post_init__(self):
        self.id = story_id(self.url)


class Fetcher:
    """Live HTTP fetcher. FixtureFetcher below swaps in local files for tests."""

    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.ctx = ssl.create_default_context()

    def get(self, url: str, accept: str = "*/*") -> Response:
        req = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
            "Accept-Encoding": "gzip",
            "Accept-Language": "en;q=0.9",
        })
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self.ctx) as resp:
                raw = resp.read(4_000_000)
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                charset = resp.headers.get_content_charset() or "utf-8"
                return Response(resp.status, resp.geturl(), raw.decode(charset, "replace"))
        except urllib.error.HTTPError as exc:
            return Response(exc.code, url, error=f"HTTP {exc.code}")
        except Exception as exc:  # timeouts, DNS, TLS: never fatal for the run
            return Response(None, url, error=f"{type(exc).__name__}: {exc}"[:200])


class FixtureFetcher(Fetcher):
    """Serves feeds from fixtures/feeds/<source-id>.xml and articles from fixtures/articles.json."""

    def __init__(self, fixtures: Path):
        super().__init__()
        self.fixtures = fixtures
        self.articles = json.loads((fixtures / "articles.json").read_text("utf-8"))
        self.feed_map: dict[str, str] = {}

    def register_feed(self, url: str, source_id: str):
        self.feed_map[url] = source_id

    def get(self, url: str, accept: str = "*/*") -> Response:
        if url in self.feed_map:
            path = self.fixtures / "feeds" / f"{self.feed_map[url]}.xml"
            if path.exists():
                return Response(200, url, path.read_text("utf-8"))
            return Response(None, url, error="fixture missing (simulated outage)")
        art = self.articles.get(url)
        if art is None:
            return Response(404, url, error="HTTP 404")
        return Response(art.get("status", 200), url, art.get("html", ""))


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        try:
            dt = parse_iso(value)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _text(el, *tags) -> str:
    for tag in tags:
        found = el.find(tag)
        if found is not None and (found.text or "").strip():
            return found.text.strip()
    return ""


def parse_feed(xml_text: str, source: dict) -> list[FeedItem]:
    # Some feeds ship a BOM or leading junk before the XML declaration.
    xml_text = xml_text.lstrip("﻿ \r\n\t")
    xml_text = re.sub(r"&(?!(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);)", "&amp;", xml_text)
    root = ET.fromstring(xml_text)
    items: list[FeedItem] = []
    if root.tag == f"{ATOM}feed":
        for entry in root.findall(f"{ATOM}entry"):
            link = ""
            for ln in entry.findall(f"{ATOM}link"):
                if ln.get("rel", "alternate") == "alternate" and ln.get("href"):
                    link = ln.get("href")
                    break
            items.append(FeedItem(
                title=clean_text(_text(entry, f"{ATOM}title")),
                url=link,
                published=_parse_date(_text(entry, f"{ATOM}published", f"{ATOM}updated")),
                description=clean_text(_text(entry, f"{ATOM}summary", f"{ATOM}content")),
                source=source,
            ))
    else:
        channel = root.find("channel")
        for it in (channel if channel is not None else root).iter("item"):
            items.append(FeedItem(
                title=clean_text(_text(it, "title")),
                url=_text(it, "link") or _text(it, "guid"),
                published=_parse_date(_text(it, "pubDate", f"{DC}date")),
                description=clean_text(_text(it, "description", f"{CONTENT}encoded")),
                source=source,
            ))
    return [i for i in items if i.title and i.url.startswith(("http://", "https://"))]


# ---- article page inspection -------------------------------------------------

META_RE = re.compile(r"<meta\s+[^>]*>", re.I)
ATTR_RE = re.compile(r'([a-zA-Z:_-]+)\s*=\s*("([^"]*)"|\'([^\']*)\')')
P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.I | re.S)
JSONLD_RE = re.compile(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.I | re.S)


def page_meta(html_text: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for tag in META_RE.findall(html_text[:400_000]):
        attrs = {m.group(1).lower(): (m.group(3) if m.group(3) is not None else m.group(4)) for m in ATTR_RE.finditer(tag)}
        key = attrs.get("property") or attrs.get("name") or attrs.get("itemprop")
        if key and "content" in attrs and key.lower() not in meta:
            meta[key.lower()] = attrs["content"]
    return meta


def article_published(html_text: str) -> datetime | None:
    meta = page_meta(html_text)
    for key in ("article:published_time", "datepublished", "og:published_time", "pubdate", "date", "dc.date"):
        dt = _parse_date(meta.get(key))
        if dt:
            return dt
    for block in JSONLD_RE.findall(html_text[:600_000]):
        m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', block)
        if m:
            dt = _parse_date(m.group(1))
            if dt:
                return dt
    return None


def article_text(html_text: str, limit: int) -> str:
    body = re.sub(r"<(script|style|nav|footer|header|aside|form)[^>]*>.*?</\1>", " ", html_text, flags=re.I | re.S)
    paras = [clean_text(p) for p in P_RE.findall(body)]
    paras = [p for p in paras if len(p) > 60 and "cookie" not in p.lower() and "subscribe" not in p.lower()]
    return "\n".join(paras)[:limit]
