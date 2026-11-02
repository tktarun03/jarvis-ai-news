"""Static HTML rendering. Every edition page is complete without JavaScript; app.js only enhances it."""
from __future__ import annotations

import json
from datetime import datetime
from html import escape

from .common import SCRIPTS_DIR, load_json, parse_iso

RELEASES = load_json(SCRIPTS_DIR.parent / "assets" / "releases.json", {"current": "1.0.0", "releases": []})
ASSET_VERSION = RELEASES["current"]

ICONS = {
    "today": '<path d="M12 3v2M12 19v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M3 12h2M19 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/><circle cx="12" cy="12" r="4"/>',
    "global": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.6 2.8 3.9 5.8 3.9 9s-1.3 6.2-3.9 9c-2.6-2.8-3.9-5.8-3.9-9S9.4 5.8 12 3z"/>',
    "india": '<path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0C18.5 15.4 12 21 12 21z"/><circle cx="12" cy="10" r="2.4"/>',
    "saved": '<path d="M6.5 3.5h11a1 1 0 0 1 1 1V21l-6.5-4.5L5.5 21V4.5a1 1 0 0 1 1-1z"/>',
    "archive": '<rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    "theme": '<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5a8.5 8.5 0 0 1 0 17z" fill="currentColor" stroke="none"/>',
    "refresh": '<path d="M20 11.5A8 8 0 1 0 17.7 17"/><path d="M20 5v6.5h-6.5"/>',
    "about": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.6v.2"/>',
}

MARK_SVG = ('<svg class="mark" viewBox="0 0 44 44" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="2">'
            '<circle cx="22" cy="22" r="20"/><circle cx="22" cy="22" r="13" stroke-dasharray="1.5 4" stroke-linecap="round" opacity=".55"/></g>'
            '<path d="M22 13l2.6 6.4 6.4 2.6-6.4 2.6-2.6 6.4-2.6-6.4-6.4-2.6 6.4-2.6z" fill="var(--accent)"/></svg>')


def icon(name: str, cls: str = "ic") -> str:
    return (f'<svg class="{cls}" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" '
            f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')


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


def _meta(s: dict, cat: dict, zone, rank: int | None = None) -> str:
    rank_html = f'<span class="rank">{rank:02d}</span>' if rank else ""
    return (f'<p class="meta">{rank_html}<span class="dot" style="--c:{cat["color"]}"></span><span>{escape(cat["label"])}</span>'
            f'<span class="sep">·</span><span>{escape(s["source"]["name"])}</span><span class="sep">·</span>'
            f'<time datetime="{s["published_at"]}" data-precision="{s.get("published_precision", "time")}">'
            f'{fmt_local(s["published_at"], zone, s.get("published_precision", "time"))}</time></p>')


def _detail(s: dict) -> str:
    n = len(s.get("key_insights") or [])
    return f"{n} insight{'s' if n != 1 else ''}" if n else "Publisher summary"


def _hero(s: dict, cfg: dict, base: str, zone) -> str:
    cat = cfg["categories"][s["category"]]
    credit = f'<span class="credit">{escape(s["image"]["credit"])}</span>' if s["image"]["type"] != "generated" else ""
    return f"""
<article class="story hero" id="s-{s['id']}" data-id="{s['id']}" data-region="{s['region']}" data-category="{s['category']}">
  <figure class="hero-media" data-img data-kind="{s['image']['type']}">{img_tag(s, base, eager=True)}</figure>
  <div class="hero-shade"></div>
  <button class="save-btn on-image" type="button" data-save="{s['id']}" aria-pressed="false" aria-label="Save story">{icon('saved')}</button>
  <div class="hero-body">
    <span class="badge"><span class="dot" style="--c:{cat['color']}"></span>Lead · {escape(cat['label'])}</span>
    <h3 class="hero-title"><a class="story-link" href="{escape(s['source']['url'])}" rel="noopener" target="_blank">{escape(s['headline'])}</a></h3>
    <p class="hero-sum">{escape(s['summary'])}</p>
    <p class="meta on-image"><span>{escape(s['source']['name'])}</span><span class="sep">·</span><time datetime="{s['published_at']}" data-precision="{s.get('published_precision', 'time')}">{fmt_local(s['published_at'], zone, s.get('published_precision', 'time'))}</time><span class="sep">·</span><span>{_detail(s)}</span></p>
  </div>
  {credit}
</article>"""


def _row(s: dict, cfg: dict, base: str, zone, rank: int) -> str:
    cat = cfg["categories"][s["category"]]
    region_label = "India" if s["region"] == "india" else "Global"
    return f"""
<article class="story row" id="s-{s['id']}" data-id="{s['id']}" data-region="{s['region']}" data-category="{s['category']}">
  <div class="row-text">
    {_meta(s, cat, zone, rank)}
    <h3 class="story-title"><a class="story-link" href="{escape(s['source']['url'])}" rel="noopener" target="_blank">{escape(s['headline'])}</a></h3>
    <p class="story-sum">{escape(s['summary'])}</p>
    <div class="story-foot"><span class="tag">{region_label}</span><span class="hint">{_detail(s)}</span><button class="save-btn" type="button" data-save="{s['id']}" aria-pressed="false" aria-label="Save story">{icon('saved')}</button></div>
  </div>
  <figure class="thumb" data-img data-kind="{s['image']['type']}">{img_tag(s, base)}</figure>
</article>"""


def render_edition(edition: dict, editions_index: list[dict], cfg: dict, zone, base: str) -> str:
    site = cfg["site"]
    date = edition["edition_date"]
    g, i = edition["stories"]["global"], edition["stories"]["india"]
    total = len(g) + len(i)
    cats_present: dict[str, int] = {}
    for s in g + i:
        cats_present[s["category"]] = cats_present.get(s["category"], 0) + 1
    chips = ['<button class="chip" type="button" data-cat="all" aria-pressed="true">All <span class="sub">' + str(total) + '</span></button>']
    for key, meta in cfg["categories"].items():
        if key in cats_present:
            chips.append(f'<button class="chip" type="button" data-cat="{key}" aria-pressed="false"><span class="dot" style="--c:{meta["color"]}"></span>'
                         f'{escape(meta["label"])} <span class="sub">{cats_present[key]}</span></button>')

    def section(region: str, title: str, stories: list[dict]) -> str:
        if not stories:
            body = '<p class="empty">No story met the verification bar in this window. JARVIS publishes fewer stories rather than unverified ones.</p>'
        else:
            body = _hero(stories[0], cfg, base, zone) + "".join(_row(s, cfg, base, zone, n) for n, s in enumerate(stories[1:], start=2))
        return (f'<section class="region" data-region-section="{region}" aria-labelledby="h-{region}">'
                f'<div class="sec-head"><h2 class="sec-title" id="h-{region}">{title}</h2><span class="sec-rule"></span>'
                f'<span class="eyebrow">{len(stories)} stor{"y" if len(stories) == 1 else "ies"}</span></div>'
                f'<div class="stories">{body}</div></section>')

    archive_rows = "".join(
        f'<a class="arow{" current" if e["date"] == date else ""}" href="{base}news/{e["date"]}.html">'
        f'<span class="arow-date"><span class="num">{int(e["date"][8:])}</span><span class="eyebrow">{datetime.strptime(e["date"], "%Y-%m-%d").strftime("%b %Y")}</span></span>'
        f'<span class="grow"><span class="arow-title">{escape(e.get("top_headline") or "Edition " + e["date"])}</span>'
        f'<span class="hint">{e["counts"]["global"]} global · {e["counts"]["india"]} India · Nº {e["number"]:03d}</span></span></a>'
        for e in editions_index[:120])

    win = edition["window"]
    window_note = f"Covering {fmt_local(win['start'], zone)} → {fmt_local(win['end'], zone)} Doha time"
    sample_note = ""
    if edition.get("edition_type") == "launch-sample":
        sample_note = ('<p class="note"><span class="note-mark">Launch edition</span> Stories were hand-verified against their publishers, '
                       'over a wider window than the daily 24 hours. Daily editions are produced automatically.</p>')
    mode_counts: dict[str, int] = {}
    for s in g + i:
        mode_counts[s["summary_mode"]] = mode_counts.get(s["summary_mode"], 0) + 1
    checked = sum(1 for s in g + i if s["verification"].get("checks"))

    data_json = json.dumps({
        "edition": edition, "categories": cfg["categories"], "base": base,
        "site": {k: site[k] for k in ("name", "signature", "agent_credit", "base_url", "publisher")},
        "schedule": cfg["schedule"], "releases": RELEASES,
        "latest": editions_index[0]["date"] if editions_index else date,
    }, ensure_ascii=False).replace("</", "<\\/")
    title = f"{site['name']} · {long_date(date)}"
    desc = f"{total} verified AI stories ({len(g)} global, {len(i)} India) for {long_date(date)}."
    canonical = f"{site['base_url']}news/{date}.html"
    tabs = [("today", "Today"), ("global", "Global"), ("india", "India"), ("saved", "Saved"), ("archive", "Archive")]
    tabbar = "".join(f'<button class="tab" type="button" data-tab="{k}" aria-pressed="{"true" if k == "today" else "false"}">'
                     f'<span class="pill">{icon(k)}</span><span class="tab-lbl">{lbl}</span></button>' for k, lbl in tabs)
    gen_local = fmt_local(edition["generated_at"], zone)
    num = f"{edition['edition_number']:03d}"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{escape(title)}</title>
<meta name="description" content="{escape(desc)}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:title" content="{escape(title)}">
<meta property="og:description" content="{escape(desc)}">
<meta property="og:image" content="{site['base_url']}assets/images/brand/og.png">
<meta name="theme-color" content="#F6F3EE" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0B0A09" media="(prefers-color-scheme: dark)">
<meta name="generator" content="JARVIS AI NEWS {ASSET_VERSION}">
<meta name="author" content="{escape(site['publisher'])}">
<link rel="icon" href="{base}assets/images/brand/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{base}assets/images/brand/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,500;1,9..144,300;1,9..144,400&amp;family=Hanken+Grotesk:wght@300;400;500;600&amp;family=IBM+Plex+Mono:wght@400;500&amp;display=swap">
<link rel="stylesheet" href="{base}assets/css/app.css?v={ASSET_VERSION}">
<script>try{{var t=localStorage.getItem('jarvis_theme');if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t);if(sessionStorage.getItem('jarvis_booted')==='1')document.documentElement.classList.add('booted');}}catch(e){{}}</script>
</head>
<body>
<div class="boot" id="boot" role="status" aria-label="Initialising JARVIS">
  <div class="boot-in">
    <div class="boot-ring"><svg viewBox="0 0 120 120" aria-hidden="true"><circle class="ring-track" cx="60" cy="60" r="54"/><circle class="ring-fill" cx="60" cy="60" r="54"/></svg>{MARK_SVG}</div>
    <p class="boot-name">JARVIS</p>
    <p class="boot-sub">AI NEWS · Nº {num}</p>
    <ol class="boot-log" id="boot-log">
      <li>Initialising JARVIS v{ASSET_VERSION}</li>
      <li>Loading edition Nº {num} · {escape(long_date(date))}</li>
      <li>{total} stories · {checked} source checks passed</li>
      <li>Ready</li>
    </ol>
  </div>
</div>
<div class="app" id="app">
  <div class="scroller" id="scroller">
    <header class="top" id="top">
      <a class="brand" href="{base}index.html" aria-label="{escape(site['name'])} home">{MARK_SVG}<span class="brand-name">JARVIS<span class="brand-sub">AI NEWS</span></span></a>
      <span class="top-date" aria-hidden="true">Nº {num} · {datetime.strptime(date, "%Y-%m-%d").strftime("%d %b")}</span>
      <div class="head-actions">
        <button class="icon-btn" type="button" id="refresh-btn" aria-label="Check for a newer edition" title="Refresh">{icon('refresh')}</button>
        <button class="icon-btn" type="button" id="about-btn" aria-label="About and version history" title="About">{icon('about')}</button>
        <button class="icon-btn" type="button" id="theme-btn" aria-label="Change theme" title="Theme">{icon('theme')}</button>
      </div>
    </header>
    <main class="col">
      <section class="masthead" data-pane="news">
        <p class="eyebrow" id="greet">Nº {num} · {escape(long_date(date))}</p>
        <h1 class="h-display">Today in <em>AI</em></h1>
        <div class="stats">
          <div class="stat"><span class="num">{total}</span><span class="stat-lbl">Verified stories</span></div>
          <div class="stat"><span class="num">{len(g)}</span><span class="stat-lbl">Global</span></div>
          <div class="stat"><span class="num">{len(i)}</span><span class="stat-lbl">India</span></div>
        </div>
        <p class="fine window-note"><span class="live-dot"></span>{escape(window_note)}</p>
        {sample_note}
      </section>

      <nav class="chips" id="chips" aria-label="Filter by category" data-pane="news">{''.join(chips)}</nav>

      <div class="regions" data-pane="news">
        {section('global', 'Global', g)}
        {section('india', 'India', i)}
      </div>

      <section class="pane" data-pane="saved" hidden>
        <p class="eyebrow">On this device</p>
        <h1 class="h-display"><em>Saved</em></h1>
        <div class="stories" id="saved-list"></div>
        <p class="empty" id="saved-empty">Tap the bookmark on any story to keep it here. Saved stories stay in this browser only.</p>
      </section>

      <section class="pane" data-pane="archive" hidden>
        <p class="eyebrow">Every edition</p>
        <h1 class="h-display"><em>Archive</em></h1>
        <div class="card tight archive" id="archive-list">{archive_rows}</div>
      </section>

      <footer class="sig">
        <div class="sig-mark">{MARK_SVG}</div>
        <p class="sig-line">{escape(site['signature'])}</p>
        <p class="sig-credit">{escape(site['agent_credit'])}</p>
        <p class="fine">Summaries are written only from each publisher's own text and checked against it; open the source before relying on a story. Images are shown from their publishers with credit; JARVIS covers stand in where none is available.</p>
        <p class="fine mono-line">v{ASSET_VERSION} · Generated {escape(gen_local)} Doha · {escape(", ".join(f"{v} {k}" for k, v in sorted(mode_counts.items())) or "no stories")} · <a href="{base}data/{date}.json">edition data</a> · <a href="https://github.com/tktarun03/jarvis-ai-news" rel="noopener">source</a></p>
      </footer>
    </main>
  </div>
  <nav class="tabbar" aria-label="Sections"><div class="tabbar-inner">{tabbar}</div></nav>
</div>
<div id="sheet-root"></div>
<div id="toast" class="toast" role="status" aria-live="polite" hidden></div>
<noscript><style>.boot{{display:none}}</style></noscript>
<script type="application/json" id="edition-data">{data_json}</script>
<script src="{base}assets/js/app.js?v={ASSET_VERSION}" defer></script>
</body>
</html>
"""
