"""Static HTML rendering. Every edition page is complete without JavaScript; app.js only enhances it."""
from __future__ import annotations

import json
from datetime import datetime
from html import escape

from .common import parse_iso

ASSET_VERSION = "1.0.0"

ICONS = {
    "today": '<path d="M12 3v2M12 19v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M3 12h2M19 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/><circle cx="12" cy="12" r="4"/>',
    "global": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.6 2.8 3.9 5.8 3.9 9s-1.3 6.2-3.9 9c-2.6-2.8-3.9-5.8-3.9-9S9.4 5.8 12 3z"/>',
    "india": '<path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0C18.5 15.4 12 21 12 21z"/><circle cx="12" cy="10" r="2.4"/>',
    "saved": '<path d="M6.5 3.5h11a1 1 0 0 1 1 1V21l-6.5-4.5L5.5 21V4.5a1 1 0 0 1 1-1z"/>',
    "archive": '<rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    "theme": '<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5a8.5 8.5 0 0 1 0 17z" fill="currentColor" stroke="none"/>',
    "share": '<path d="M12 15V3.5M7.5 8 12 3.5 16.5 8"/><path d="M5 12.5V19a1.5 1.5 0 0 0 1.5 1.5h11A1.5 1.5 0 0 0 19 19v-6.5"/>',
    "external": '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v4.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6H10"/>',
}

MARK_SVG = ('<svg class="mark" viewBox="0 0 44 44" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="2.2">'
            '<circle cx="22" cy="22" r="20"/><circle cx="22" cy="22" r="13" stroke-dasharray="1.5 4" stroke-linecap="round" opacity=".6"/></g>'
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


def _card(s: dict, cfg: dict, base: str, zone, lead: bool) -> str:
    cat = cfg["categories"][s["category"]]
    n_ins = len(s.get("key_insights") or [])
    detail = f"{n_ins} insight{'s' if n_ins != 1 else ''}" if n_ins else "Publisher summary"
    region_label = "India" if s["region"] == "india" else "Global"
    return f"""
<article class="story{' lead' if lead else ''}" id="s-{s['id']}" data-id="{s['id']}" data-region="{s['region']}" data-category="{s['category']}">
  <figure class="cover"><img src="{base}{escape(s['image']['src'])}" alt="{escape(s['image']['alt'])}" width="1200" height="675" loading="{'eager' if lead else 'lazy'}" decoding="async"></figure>
  <div class="story-body">
    <p class="meta"><span class="dot" style="--c:{cat['color']}"></span><span>{escape(cat['label'])}</span><span class="sep">·</span><span>{escape(s['source']['name'])}</span><span class="sep">·</span><time datetime="{s['published_at']}" data-precision="{s.get('published_precision', 'time')}">{fmt_local(s['published_at'], zone, s.get('published_precision', 'time'))}</time></p>
    <h3 class="story-title"><a class="story-link" href="{escape(s['source']['url'])}" rel="noopener" target="_blank">{escape(s['headline'])}</a></h3>
    <p class="story-sum">{escape(s['summary'])}</p>
    <div class="story-foot"><span class="tag">{region_label}</span><span class="hint">{detail}</span><button class="save-btn" type="button" data-save="{s['id']}" aria-pressed="false" aria-label="Save story">{icon('saved')}</button></div>
  </div>
</article>"""


def render_edition(edition: dict, editions_index: list[dict], cfg: dict, zone, base: str) -> str:
    site = cfg["site"]
    date = edition["edition_date"]
    g, i = edition["stories"]["global"], edition["stories"]["india"]
    total = len(g) + len(i)
    cats_present = {}
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
            body = "".join(_card(s, cfg, base, zone, lead=(region == "global" and n == 0)) for n, s in enumerate(stories))
        return (f'<section class="region" data-region-section="{region}" aria-labelledby="h-{region}">'
                f'<div class="region-head"><h2 class="h3" id="h-{region}">{title}</h2><span class="eyebrow">{len(stories)} stor{"y" if len(stories) == 1 else "ies"}</span></div>'
                f'<div class="stories">{body}</div></section>')

    archive_rows = "".join(
        f'<a class="arow{" current" if e["date"] == date else ""}" href="{base}news/{e["date"]}.html">'
        f'<span class="arow-date"><span class="num">{int(e["date"][8:])}</span><span class="eyebrow">{datetime.strptime(e["date"], "%Y-%m-%d").strftime("%b %Y")}</span></span>'
        f'<span class="grow"><span class="arow-title">{escape(e.get("top_headline") or "Edition " + e["date"])}</span>'
        f'<span class="hint">{e["counts"]["global"]} global · {e["counts"]["india"]} India · No. {e["number"]:03d}</span></span></a>'
        for e in editions_index[:120])

    win = edition["window"]
    window_note = f"Covering {fmt_local(win['start'], zone)} → {fmt_local(win['end'], zone)} Doha time"
    sample_note = ""
    if edition.get("edition_type") == "launch-sample":
        sample_note = ('<p class="note">Launch edition: stories were hand-verified against their publishers and the window '
                       'is wider than the daily 24 hours. Daily editions are produced automatically.</p>')
    mode_counts = {}
    for s in g + i:
        mode_counts[s["summary_mode"]] = mode_counts.get(s["summary_mode"], 0) + 1

    data_json = json.dumps({"edition": edition, "categories": cfg["categories"], "base": base,
                            "site": {k: site[k] for k in ("name", "signature", "agent_credit", "base_url")}},
                           ensure_ascii=False).replace("</", "<\\/")
    title = f"{site['name']} · {long_date(date)}"
    desc = f"{total} verified AI stories ({len(g)} global, {len(i)} India) for {long_date(date)}."
    canonical = f"{site['base_url']}news/{date}.html"
    tabs = [("today", "Today"), ("global", "Global"), ("india", "India"), ("saved", "Saved"), ("archive", "Archive")]
    tabbar = "".join(f'<button class="tab" type="button" data-tab="{k}" aria-pressed="{"true" if k == "today" else "false"}">'
                     f'<span class="pill">{icon(k)}</span><span class="tab-lbl">{lbl}</span></button>' for k, lbl in tabs)
    gen_local = fmt_local(edition["generated_at"], zone)

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
<meta name="theme-color" content="#F4F5F6" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0A0A0B" media="(prefers-color-scheme: dark)">
<meta name="generator" content="JARVIS AI NEWS pipeline">
<meta name="author" content="{escape(site['publisher'])}">
<link rel="icon" href="{base}assets/images/brand/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{base}assets/images/brand/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@200;300;400;500;600&amp;family=IBM+Plex+Mono:wght@400;500&amp;display=swap">
<link rel="stylesheet" href="{base}assets/css/app.css?v={ASSET_VERSION}">
<script>try{{var t=localStorage.getItem('jarvis_theme');if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}</script>
</head>
<body>
<div class="splash" id="splash" aria-hidden="true"><div class="splash-in"><span class="splash-mark">{MARK_SVG}</span><span class="splash-name">JARVIS</span><span class="splash-bar"><i></i></span></div></div>
<div class="app" id="app">
  <div class="scroller" id="scroller">
    <main class="col">
      <header class="top">
        <a class="brand" href="{base}index.html" aria-label="{escape(site['name'])} home">{MARK_SVG}<span class="brand-name">JARVIS<span class="brand-sub">AI NEWS</span></span></a>
        <div class="head-actions">
          <button class="icon-btn" type="button" id="theme-btn" aria-label="Change theme" title="Theme">{icon('theme')}</button>
        </div>
      </header>

      <section class="masthead" data-pane="news">
        <p class="eyebrow">No. {edition['edition_number']:03d} · {escape(long_date(date))}</p>
        <h1 class="h-display">Today in AI</h1>
        <div class="stat-row">
          <span class="num big">{total}</span>
          <span class="stat-text"><span>verified stories</span><span class="hint">{len(g)} global · {len(i)} India</span></span>
        </div>
        <p class="fine">{escape(window_note)}</p>
        {sample_note}
      </section>

      <nav class="chips" id="chips" aria-label="Filter by category" data-pane="news">{''.join(chips)}</nav>

      <div class="regions" data-pane="news">
        {section('global', 'Global', g)}
        {section('india', 'India', i)}
      </div>

      <section class="pane" data-pane="saved" hidden>
        <p class="eyebrow">On this device</p>
        <h1 class="h-display">Saved</h1>
        <div class="stories" id="saved-list"></div>
        <p class="empty" id="saved-empty">Tap the bookmark on any story to keep it here. Saved stories stay in this browser only.</p>
      </section>

      <section class="pane" data-pane="archive" hidden>
        <p class="eyebrow">Every edition</p>
        <h1 class="h-display">Archive</h1>
        <div class="card tight archive" id="archive-list">{archive_rows}</div>
      </section>

      <footer class="sig">
        <div class="sig-mark">{MARK_SVG}</div>
        <p class="sig-line">{escape(site['signature'])}</p>
        <p class="sig-credit">{escape(site['agent_credit'])}</p>
        <p class="fine">Summaries are written only from each publisher's own text and checked against it; open the source before relying on a story. Cover images are original artwork generated by JARVIS, not publisher photos.</p>
        <p class="fine mono-line">Generated {escape(gen_local)} Doha · {escape(", ".join(f"{v} {k}" for k, v in sorted(mode_counts.items())) or "no stories")} · <a href="{base}data/{date}.json">edition data</a> · <a href="https://github.com/tktarun03/jarvis-ai-news" rel="noopener">source</a></p>
      </footer>
    </main>
  </div>
  <nav class="tabbar" aria-label="Sections"><div class="tabbar-inner">{tabbar}</div></nav>
</div>
<div id="sheet-root"></div>
<div id="toast" class="toast" role="status" aria-live="polite" hidden></div>
<noscript><style>.splash{{display:none}}</style></noscript>
<script type="application/json" id="edition-data">{data_json}</script>
<script src="{base}assets/js/app.js?v={ASSET_VERSION}" defer></script>
</body>
</html>
"""
