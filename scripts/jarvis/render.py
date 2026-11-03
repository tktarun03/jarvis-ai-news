"""Static HTML rendering. Every edition page is complete without JavaScript; app.js only enhances it.

Layout (v1.5 "Reader"): Home = greeting + daily brief, region tabs, a swipeable top-stories card with
page dots, then Global and India story rows. Explore, Saved, Archive and Profile are tab panes.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from html import escape

from .common import SCRIPTS_DIR, load_json, parse_iso

RELEASES = load_json(SCRIPTS_DIR.parent / "assets" / "releases.json", {"current": "1.0.0", "releases": []})
ASSET_VERSION = RELEASES["current"]
FONT_URL = "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&amp;display=swap"
TOP_SLIDES = 3

ICONS = {
    "home": '<path d="M4 10.5 12 4l8 6.5V19a1.5 1.5 0 0 1-1.5 1.5H15v-5.5H9v5.5H5.5A1.5 1.5 0 0 1 4 19z"/>',
    "explore": '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>',
    "saved": '<path d="M6.5 3.5h11a1 1 0 0 1 1 1V21l-6.5-4.5L5.5 21V4.5a1 1 0 0 1 1-1z"/>',
    "archive": '<rect x="3.5" y="5" width="17" height="15.5" rx="3"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    "profile": '<circle cx="12" cy="8.5" r="4"/><path d="M4.5 20.5c1.2-3.6 4-5.5 7.5-5.5s6.3 1.9 7.5 5.5"/>',
    "refresh": '<path d="M20 11.5A8 8 0 1 0 17.7 17"/><path d="M20 5v6.5h-6.5"/>',
    "play": '<path d="M8 5.5v13l10.5-6.5z" fill="currentColor" stroke="none"/>',
    "chev": '<path d="m9 5 7 7-7 7"/>',
    "display": '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/>',
    "bell": '<path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 2h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.6v.2"/>',
    "code": '<path d="m8.5 7-5 5 5 5M15.5 7l5 5-5 5"/>',
    "data": '<ellipse cx="12" cy="6" rx="7.5" ry="2.8"/><path d="M4.5 6v12c0 1.5 3.4 2.8 7.5 2.8s7.5-1.3 7.5-2.8V6M4.5 12c0 1.5 3.4 2.8 7.5 2.8s7.5-1.3 7.5-2.8"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"/>',
    "moon": '<path d="M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10z"/>',
}

MARK_SVG = ('<svg class="mark" viewBox="0 0 44 44" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="2.4">'
            '<circle cx="22" cy="22" r="19"/><circle cx="22" cy="22" r="12.5" stroke-dasharray="1.6 3.8" stroke-linecap="round" opacity=".55"/></g>'
            '<path d="M22 13l2.6 6.4 6.4 2.6-6.4 2.6-2.6 6.4-2.6-6.4-6.4-2.6 6.4-2.6z" fill="var(--accent)"/></svg>')

# Monogram colours for source badges (no publisher logos are used).
BADGE_COLORS = ["#2F6FEB", "#E5484D", "#12A594", "#F76B15", "#8E4EC6", "#0091FF", "#D6409F", "#3E9B4F", "#AB6400", "#5B5BD6"]


def icon(name: str, cls: str = "ic") -> str:
    return (f'<svg class="{cls}" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" '
            f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')


def monogram(name: str) -> str:
    words = [w for w in name.replace("(", " ").replace(")", " ").split() if w.lower() not in ("the", "of", "and")]
    letters = "".join(w[0] for w in words[:2]).upper() or "?"
    return letters


def badge_color(name: str) -> str:
    return BADGE_COLORS[int(hashlib.sha1(name.encode("utf-8")).hexdigest(), 16) % len(BADGE_COLORS)]


def source_badge(name: str, cls: str = "") -> str:
    return f'<span class="mono-badge{(" " + cls) if cls else ""}" style="--b:{badge_color(name)}" aria-hidden="true">{escape(monogram(name))}</span>'


def fmt_local(dt_iso: str, zone, precision: str = "time") -> str:
    dt = parse_iso(dt_iso).astimezone(zone)
    if precision == "date":
        return f"{dt.day} {dt.strftime('%b')}"
    return f"{dt.day} {dt.strftime('%b')}, {dt.strftime('%H:%M')}"


def long_date(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{d.strftime('%A')}, {d.day} {d.strftime('%B %Y')}"


def img_tag(s: dict, base: str, eager: bool = False) -> str:
    im = s["image"]
    src = im["src"] if im["type"] == "publisher" else base + im["src"]
    fb = base + (im.get("fallback") or im["src"])
    extra = ' referrerpolicy="no-referrer"' if im["type"] == "publisher" else ""
    title = f' title="{escape(im["credit"])}"' if im["type"] != "generated" else ""
    return (f'<img src="{escape(src)}" alt="{escape(im["alt"])}" width="1200" height="675" loading="{"eager" if eager else "lazy"}" '
            f'decoding="async"{extra}{title} data-fallback="{escape(fb)}" '
            f'onerror="this.onerror=null;this.src=this.dataset.fallback;var f=this.closest(\'[data-img]\');if(f)f.classList.add(\'is-fallback\')">')


def _detail(s: dict) -> str:
    n = len(s.get("key_insights") or [])
    return f"{n} insight{'s' if n != 1 else ''}" if n else ("Editor-verified" if s.get("summary_mode") == "editor-verified" else "Source summary")


def _time(s: dict, zone) -> str:
    p = s.get("published_precision", "time")
    return f'<time datetime="{s["published_at"]}" data-precision="{p}">{fmt_local(s["published_at"], zone, p)}</time>'


def _attrs(s: dict) -> str:
    return (f'id="s-{s["id"]}" data-id="{s["id"]}" data-region="{s["region"]}" data-category="{s["category"]}" '
            f'data-source="{escape(s["source"]["name"])}"')


def _slide(s: dict, cfg: dict, base: str, zone, n: int) -> str:
    cat = cfg["categories"][s["category"]]
    region = "India" if s["region"] == "india" else "Global"
    credit = f'<span class="credit">{escape(s["image"]["credit"])}</span>' if s["image"]["type"] != "generated" else ""
    return f"""
<article class="story slide" {_attrs(s)} data-slide="{n}">
  <figure class="slide-media" data-img data-kind="{s['image']['type']}">{img_tag(s, base, eager=(n == 0))}</figure>
  <button class="bm" type="button" data-save="{s['id']}" aria-pressed="false" aria-label="Save story">{icon('saved')}</button>
  {credit}
  <div class="slide-body">
    <span class="slide-kicker"><span class="dot" style="--c:{cat['color']}"></span>{region} · {escape(cat['label'])}</span>
    <h3 class="slide-title"><a class="story-link" href="{escape(s['source']['url'])}" rel="noopener" target="_blank">{escape(s['headline'])}</a></h3>
    <div class="slide-src">{source_badge(s['source']['name'])}<span class="src-name">{escape(s['source']['name'])}</span><span class="slide-when">{_time(s, zone)}</span></div>
    <p class="slide-meta"><span>{escape(cat['label'])}</span><span>{_detail(s)}</span></p>
  </div>
</article>"""


def row_html(s: dict, cfg: dict, base: str, zone) -> str:
    cat = cfg["categories"][s["category"]]
    return f"""
<article class="story row" {_attrs(s)}>
  <figure class="thumb" data-img data-kind="{s['image']['type']}">{img_tag(s, base)}</figure>
  <div class="row-body">
    <p class="src-line">{source_badge(s['source']['name'], 'sm')}<span class="src-name">{escape(s['source']['name'])}</span></p>
    <h3 class="row-title"><a class="story-link" href="{escape(s['source']['url'])}" rel="noopener" target="_blank">{escape(s['headline'])}</a></h3>
    <p class="row-meta">{_time(s, zone)}<span class="sep">·</span><span>{escape(cat['label'])}</span><span class="sep">·</span><span>{_detail(s)}</span>
      <button class="save-btn" type="button" data-save="{s['id']}" aria-pressed="false" aria-label="Save story">{icon('saved')}</button></p>
  </div>
</article>"""


def top_stories(g: list[dict], i: list[dict], limit: int = TOP_SLIDES) -> list[dict]:
    """Interleave the regions so the top card shows the lead of each: G1, I1, G2, I2 ..."""
    out = []
    for n in range(max(len(g), len(i))):
        for region in (g, i):
            if n < len(region):
                out.append(region[n])
    return out[:limit]


def render_edition(edition: dict, editions_index: list[dict], cfg: dict, zone, base: str) -> str:
    site = cfg["site"]
    date = edition["edition_date"]
    g, i = edition["stories"]["global"], edition["stories"]["india"]
    total = len(g) + len(i)
    tops = top_stories(g, i)
    top_ids = {s["id"] for s in tops}

    slides = "".join(_slide(s, cfg, base, zone, n) for n, s in enumerate(tops))
    dots = "".join(f'<span class="pdot{" on" if n == 0 else ""}" data-dot="{n}"></span>' for n in range(len(tops)))

    def section(region: str, title: str, stories: list[dict]) -> str:
        rest = [s for s in stories if s["id"] not in top_ids]
        if not stories:
            body = '<p class="empty">No story met the verification bar in this window. JARVIS publishes fewer stories rather than unverified ones.</p>'
        elif not rest:
            body = f'<p class="empty soft">All {len(stories)} {title} stor{"y is" if len(stories) == 1 else "ies are"} in the top stories above.</p>'
        else:
            body = "".join(row_html(s, cfg, base, zone) for s in rest)
        return (f'<section class="region" data-region-section="{region}" aria-labelledby="h-{region}">'
                f'<div class="sec-head"><h2 class="sec-title" id="h-{region}">Explore {title}</h2>'
                f'<span class="sec-count">{len(stories)} stor{"y" if len(stories) == 1 else "ies"}</span></div>'
                f'<div class="rows">{body}</div></section>')

    archive_rows = "".join(
        f'<a class="arow{" current" if e["date"] == date else ""}" href="{base}news/{e["date"]}.html">'
        f'<span class="date-tile"><span class="dt-day">{int(e["date"][8:])}</span><span class="dt-mon">{datetime.strptime(e["date"], "%Y-%m-%d").strftime("%b")}</span></span>'
        f'<span class="grow"><span class="arow-title">{escape(e.get("top_headline") or "Edition " + e["date"])}</span>'
        f'<span class="hint">Nº {e["number"]:03d} · {e["counts"]["global"]} global · {e["counts"]["india"]} India</span></span>'
        f'{icon("chev", "ic chev")}</a>'
        for e in editions_index[:120])

    win = edition["window"]
    window_note = f"{fmt_local(win['start'], zone)} → {fmt_local(win['end'], zone)} Doha"
    mode_counts: dict[str, int] = {}
    for s in g + i:
        mode_counts[s["summary_mode"]] = mode_counts.get(s["summary_mode"], 0) + 1

    data_json = json.dumps({
        "edition": edition, "categories": cfg["categories"], "base": base,
        "site": {k: site[k] for k in ("name", "signature", "agent_credit", "base_url", "publisher")},
        "schedule": cfg["schedule"], "releases": RELEASES,
        "latest": editions_index[0]["date"] if editions_index else date,
        "badges": {s["source"]["name"]: [monogram(s["source"]["name"]), badge_color(s["source"]["name"])] for s in g + i},
    }, ensure_ascii=False).replace("</", "<\\/")
    title = f"{site['name']} · {long_date(date)}"
    desc = f"{total} verified AI stories ({len(g)} global, {len(i)} India) for {long_date(date)}."
    canonical = f"{site['base_url']}news/{date}.html"
    tabs = [("home", "Home"), ("explore", "Explore"), ("saved", "Saved"), ("archive", "Archive"), ("profile", "Profile")]
    tabbar = "".join(f'<button class="tab" type="button" data-tab="{k}" aria-pressed="{"true" if k == "home" else "false"}">'
                     f'{icon(k)}<span class="tab-lbl">{lbl}</span></button>' for k, lbl in tabs)
    gen_local = fmt_local(edition["generated_at"], zone)
    num = f"{edition['edition_number']:03d}"
    publisher = site["publisher"]
    initials = "".join(w[0] for w in publisher.split()[:2]).upper()
    signature = (f'<p class="sig-line">{escape(site["signature"])}</p>'
                 f'<p class="sig-credit">{escape(site["agent_credit"])}</p>')

    def setting_row(icon_name: str, tone: str, title_: str, sub: str, attrs: str, tag: str = "button") -> str:
        type_attr = ' type="button"' if tag == "button" else ""
        return (f'<{tag} class="set-row"{type_attr} {attrs}><span class="set-ic" style="--t:{tone}">{icon(icon_name)}</span>'
                f'<span class="grow"><span class="set-title">{title_}</span><span class="hint">{sub}</span></span>{icon("chev", "ic chev")}</{tag}>')

    return f"""<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<title>{escape(title)}</title>
<meta name="theme-color" content="#F5F6FA">
<link rel="manifest" href="{base}manifest.webmanifest">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="description" content="{escape(desc)}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:title" content="{escape(title)}">
<meta property="og:description" content="{escape(desc)}">
<meta property="og:image" content="{site['base_url']}assets/images/brand/og.png">
<meta name="generator" content="JARVIS AI NEWS {ASSET_VERSION}">
<meta name="author" content="{escape(publisher)}">
<link rel="icon" href="{base}assets/images/brand/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{base}assets/images/brand/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONT_URL}">
<link rel="stylesheet" href="{base}assets/css/app.css?v={ASSET_VERSION}">
<script>try{{var r=document.documentElement,p=JSON.parse(localStorage.getItem('jarvis_display')||'null')||{{}};if(!p.theme&&localStorage.getItem('jarvis_theme_v2')==='dark')p.theme='dark';var t=p.theme||'light';if(p.auto&&window.matchMedia)t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';r.setAttribute('data-theme',t);if(p.font)r.style.setProperty('--read-scale',p.font);if(p.bright&&p.bright<1)r.style.setProperty('--dim',(1-p.bright).toFixed(2));}}catch(e){{}}</script>
</head>
<body>
<div class="app" id="app">
  <div class="scroller" id="scroller">
    <header class="top" id="top">
      <a class="brand" href="{base}index.html" aria-label="{escape(site['name'])} home">{MARK_SVG}<span class="brand-name">JARVIS</span></a>
      <span class="top-title" aria-hidden="true">Nº {num} · {datetime.strptime(date, "%Y-%m-%d").strftime("%d %b")}</span>
      <div class="head-actions">
        <button class="icon-btn" type="button" id="search-btn" aria-label="Search stories" title="Search">{icon('explore')}</button>
        <button class="icon-btn" type="button" id="refresh-btn" aria-label="Refresh page and news" title="Refresh">{icon('refresh')}</button>
        <button class="switch theme-switch" type="button" id="theme-btn" role="switch" aria-checked="false" aria-label="Dark mode"><span class="knob">{icon('sun', 'ic k-sun')}{icon('moon', 'ic k-moon')}</span></button>
      </div>
    </header>
    <main class="col">

      <div class="pane" data-pane="home">
        <section class="hero-head">
          <div class="hh-row">
            <p class="date-chip"><span class="live-dot"></span><span id="live-clock">{escape(long_date(date))}</span></p>
            <span class="ed-chip">Nº {num}</span>
          </div>
          <h1 class="hh-hello" id="greet-hello">Hello, Boss</h1>
          <p class="hh-sub" id="brief-greeting">Here’s your verified AI update for {escape(long_date(date))}.</p>
          <div class="brief-card">
            <svg class="bc-deco" viewBox="0 0 200 200" aria-hidden="true"><g fill="none" stroke="currentColor"><circle cx="100" cy="100" r="96" stroke-width="1.5"/><circle cx="100" cy="100" r="66" stroke-width="1.5" stroke-dasharray="2 7" stroke-linecap="round"/><circle cx="100" cy="100" r="36" stroke-width="1.5"/></g><path d="M100 78l6 16 16 6-16 6-6 16-6-16-16-6 16-6z" fill="currentColor"/></svg>
            <div class="bc-top"><span class="bc-label" id="brief-title">Today’s brief</span><span class="bc-window">{escape(window_note)}</span></div>
            <div class="bc-stats">
              <div><b>{total}</b><span>Stories</span></div>
              <div><b>{len(g)}</b><span>Global</span></div>
              <div><b>{len(i)}</b><span>India</span></div>
            </div>
            <div class="brief-actions">
              <button class="pill-btn light" id="listen-btn" type="button" disabled>{icon('play')}<span>Listen to headlines</span></button>
              <button class="pill-btn glass" id="pause-btn" type="button" hidden>Pause</button>
              <button class="pill-btn glass" id="stop-btn" type="button" hidden>Stop</button>
            </div>
            <p class="brief-status" id="voice-status" role="status">Enable JavaScript to listen.</p>
          </div>
        </section>

        <aside class="update-banner" id="news-update" role="status" hidden></aside>

        <nav class="utabs" id="region-tabs" aria-label="News region">
          <button type="button" data-region-tab="all" aria-pressed="true">Top stories</button>
          <button type="button" data-region-tab="global" aria-pressed="false">Global</button>
          <button type="button" data-region-tab="india" aria-pressed="false">India</button>
          <button type="button" data-region-tab="mine" aria-pressed="false" hidden>My topics</button>
        </nav>

        <section class="carousel" id="carousel" aria-label="Top stories">
          <div class="slides" id="slides">{slides}</div>
          <div class="pdots" id="pdots" aria-hidden="true">{dots}</div>
        </section>

        <div class="regions">
          {section('global', 'Global', g)}
          {section('india', 'India', i)}
        </div>
        <p class="empty" id="mine-empty" hidden>None of today’s stories match your topics. Edit them in Profile.</p>

        <footer class="sig">{signature}
          <p class="fine">Summaries are written only from each publisher's own text and checked against it; open the source before relying on a story. Images are the publisher's own (credited); otherwise an AI-generated generic scene or a Pixabay photo, each labelled as not from the event; JARVIS covers stand in when neither is available.</p>
          <p class="fine mono-line">v{ASSET_VERSION} · Generated {escape(gen_local)} Doha · {escape(", ".join(f"{v} {k}" for k, v in sorted(mode_counts.items())) or "no stories")}</p>
        </footer>
      </div>

      <div class="pane" data-pane="explore" hidden>
        <h1 class="pane-title">Explore</h1>
        <label class="search"><span class="sr-only">Search stories</span>{icon('explore')}<input id="explore-q" type="search" placeholder="Topic, source or keyword" autocomplete="off"></label>
        <div class="sources" id="explore-sources" aria-label="Sources"></div>
        <nav class="utabs" id="explore-cats" aria-label="Categories"></nav>
        <div class="rows" id="explore-list"></div>
        <p class="empty" id="explore-empty" hidden>No stories match. Try another word or source.</p>
      </div>

      <div class="pane" data-pane="saved" hidden>
        <h1 class="pane-title">Saved</h1>
        <div class="rows" id="saved-list"></div>
        <p class="empty" id="saved-empty">Tap the bookmark on any story to keep it here. Saved stories stay in this browser only.</p>
      </div>

      <div class="pane" data-pane="archive" hidden>
        <h1 class="pane-title">Archive</h1>
        <div class="card list" id="archive-list">{archive_rows}</div>
      </div>

      <div class="pane" data-pane="profile" hidden>
        <h1 class="pane-title center">Profile</h1>
        <div class="profile-head">
          <span class="avatar" aria-hidden="true">{escape(initials)}</span>
          <p class="profile-name">{escape(publisher)}</p>
          <p class="hint">Publisher · {escape(site['name'])}</p>
        </div>
        <div class="topic-card" id="topic-card">
          <div class="grow">
            <p class="topic-text" id="topic-text">Hey Boss, it seems like you haven’t picked any topics yet.</p>
            <button class="pill-btn dark" type="button" id="topic-btn">{icon('plus')}<span>Add topic</span></button>
          </div>
          <svg class="topic-art" viewBox="0 0 120 120" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="60" cy="60" r="38"/><circle cx="60" cy="60" r="26" stroke-dasharray="2 6" opacity=".6"/><path d="M60 34l5 13 13 5-13 5-5 13-5-13-13-5 13-5z" fill="currentColor" stroke="none" opacity=".85"/><path d="M98 22l2 6 6 2-6 2-2 6-2-6-6-2 6-2zM20 88l1.5 4.5L26 94l-4.5 1.5L20 100l-1.5-4.5L14 94l4.5-1.5z" fill="currentColor" stroke="none" opacity=".6"/></g></svg>
        </div>

        <p class="set-head">App settings</p>
        <div class="card list">
          {setting_row('display', '#5B5BD6', 'Display preferences', 'Theme, brightness and font size', 'id="display-btn"')}
          <details class="set-details" id="push-settings">
            <summary class="set-row"><span class="set-ic" style="--t:#E5484D">{icon('bell')}</span><span class="grow"><span class="set-title">Notifications</span><span class="hint">News alerts on this device</span></span>{icon('chev', 'ic chev')}</summary>
            <div class="set-more">
              <p id="push-status" role="status">Notification setup is being checked.</p>
              <p class="hint">On iPhone or iPad, add JARVIS to your Home Screen, open it there, then enable notifications. Alerts are delivered by OneSignal after you opt in.</p>
              <button class="pill-btn" id="push-btn" type="button" disabled>Enable notifications</button>
            </div>
          </details>
        </div>

        <p class="set-head">About</p>
        <div class="card list">
          {setting_row('info', '#12A594', 'About & version history', f'v{ASSET_VERSION} · release notes', 'id="about-btn"')}
          {setting_row('data', '#F76B15', 'Edition data', f'Nº {num} as JSON', f'href="{base}data/{date}.json"', 'a')}
          {setting_row('code', '#14151A', 'Source code', 'github.com/tktarun03/jarvis-ai-news', 'href="https://github.com/tktarun03/jarvis-ai-news" rel="noopener"', 'a')}
        </div>
        <footer class="sig center">{MARK_SVG}{signature}</footer>
      </div>

    </main>
  </div>
  <nav class="tabbar" aria-label="Sections"><div class="tabbar-inner">{tabbar}</div></nav>
</div>
<div class="dim-layer" aria-hidden="true"></div>
<div id="sheet-root"></div>
<div id="toast" class="toast" role="status" aria-live="polite" hidden></div>
<script type="application/json" id="edition-data">{data_json}</script>
<script src="{base}assets/js/app.js?v={ASSET_VERSION}" defer></script>
<script src="{base}assets/js/brief.js?v={ASSET_VERSION}" defer></script>
</body>
</html>
"""
