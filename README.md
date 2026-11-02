# JARVIS AI NEWS

A mobile-first daily AI news app that publishes itself. Every morning at **07:30 Doha time** a GitHub Action reads trusted publishers' feeds for the previous 24 hours, verifies each story, picks up to 10 global and 10 India stories, writes a dated page and a dated JSON file, commits them, and deploys to GitHub Pages. Editions accumulate in the repo as a permanent archive.

**Live site:** https://tktarun03.github.io/jarvis-ai-news/

Published by **Arunkumar Thamilarasu**. JARVIS is an AI agent created by Arunkumar Thamilarasu.

---

## What a story contains

| Field | Where it comes from |
|---|---|
| Headline, summary | Claude, written only from the publisher's text (or the publisher's own blurb when no API key is set) |
| Key insights (≤3), real-world impact | Claude, grounded in the publisher's text; left empty rather than guessed |
| Cover image | Original artwork generated per story (category motif, source domain). No publisher photos |
| Source link, publication date | Publisher feed, link checked, date confirmed on the article page where available |
| Also reported by | Other trusted outlets covering the same story (merged, not duplicated) |
| How this was checked | Every check the pipeline ran, shown on the story sheet |

## How accuracy is enforced

1. **Trusted sources only.** Feeds and domains are listed in `scripts/sources.json` with a trust tier. Links to any other domain are rejected.
2. **Date window.** Only items published inside the last 24 hours (configurable) are eligible. Future-dated and undated items are rejected.
3. **Stale and republished stories.** If the article page's own publication date disagrees with the feed by more than 48 hours, the story is rejected.
4. **Dead links.** Links returning 404/5xx are rejected. Sites that block bots (403/429) are only accepted from higher-trust feeds and are labelled.
5. **No duplicates.** Same-day duplicates are clustered across outlets; anything published in the last 45 days (by URL or headline fingerprint) is never republished. Re-running the job on the same day publishes nothing unless forced.
6. **No invented facts.** Claude's output is checked: any number, or any quotation, that does not appear in the publisher's text fails the story back to the publisher's own summary. Without an API key, insights and impact are left empty, never made up.
7. **Blocked content.** Sponsored posts, advertorials and AI-generated "forecast" pieces are filtered.
8. **Publication gate.** `scripts/validate.py` must pass before anything is committed: schema, caps, windows, trusted domains, cross-edition duplicates, missing files, broken local links, signature present, cron matches config.
9. **Thin days.** If fewer than 3 stories pass, nothing is published and yesterday's edition stays live.

Every edition's JSON keeps a `rejected` list with the reason for each story that was dropped, so the filtering is auditable.

## Setup (one time)

1. **Enable Pages:** repo **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. **Add the summariser key (recommended):** **Settings → Secrets and variables → Actions → New repository secret**, name `ANTHROPIC_API_KEY`. Optional repository *variable* `JARVIS_MODEL` overrides the model in `scripts/config.json`.
   Without the key the site still publishes daily, using each publisher's own summary, with insights and impact marked unavailable.
3. **Run it once now:** **Actions → Daily AI News → Run workflow**.

The key is read only from the Actions secret, sent only to the Anthropic API, and never logged or written to the repo.

## Schedule

`scripts/config.json` → `schedule.local_time` (default `07:30`) and `schedule.timezone` (default `Asia/Qatar`).
GitHub cron is UTC, so after changing either value run:

```bash
python scripts/set-schedule.py   # rewrites the cron line: 07:30 Asia/Qatar = 04:30 UTC
```

Qatar has no daylight saving, so the conversion is exact all year. GitHub may start scheduled runs a few minutes late at busy times. Scheduled workflows on a repo with no activity for 60 days are paused by GitHub; the daily commits keep this one active.

## Run locally

```bash
python scripts/generate-news.py                 # build today's edition (Doha date) from live feeds
python scripts/generate-news.py --force         # rebuild today's edition
python scripts/generate-news.py --rerender      # re-render all pages from JSON after a design change
python scripts/validate.py                      # the publication gate
python -m unittest discover -s tests -v         # offline tests with fixture feeds
python -m http.server 8000                      # then open http://localhost:8000
```

Python 3.11+ standard library only. No dependencies to install.

## Folder structure

```
jarvis-ai-news/
├── index.html                     latest edition (re-rendered each run)
├── news/YYYY-MM-DD.html           one static page per day, readable without JavaScript
├── data/
│   ├── YYYY-MM-DD.json            one structured edition per day
│   ├── index.json                 archive manifest (newest first)
│   └── seen.json                  45-day dedupe memory
├── assets/
│   ├── css/app.css                design tokens and components
│   ├── js/app.js                  tabs, filters, story sheet, saved, archive, theme
│   └── images/
│       ├── brand/                 mark, favicon, social card
│       └── covers/YYYY-MM-DD/     generated cover per story
├── scripts/
│   ├── generate-news.py           entry point
│   ├── validate.py                publication gate
│   ├── set-schedule.py            Doha time → UTC cron
│   ├── config.json                limits, schedule, categories, signature
│   ├── sources.json               feeds, trust tiers, extra trusted domains
│   ├── jarvis/                    pipeline modules (feeds, select, summarize, covers, render)
│   └── sample/                    hand-verified launch edition input
├── tests/                         offline end-to-end tests and fixtures
└── .github/workflows/daily-news.yml
```

## Edition JSON (abridged)

```json
{
  "edition_date": "2026-11-02", "edition_number": 1, "edition_type": "daily",
  "window": { "start": "…Z", "end": "…Z" },
  "publisher": { "name": "Arunkumar Thamilarasu", "signature": "Published by Arunkumar Thamilarasu" },
  "counts": { "global": 5, "india": 5 },
  "stories": { "global": [ {
      "id": "6a815c95c6b8", "rank": 1, "region": "global", "category": "business",
      "headline": "…", "summary": "…", "key_insights": ["…"], "impact": "…",
      "source": { "name": "The National", "domain": "thenationalnews.com", "url": "https://…" },
      "published_at": "2026-11-01T21:00:00Z", "published_precision": "date",
      "image": { "type": "generated", "src": "assets/images/covers/2026-11-02/6a815c95c6b8.svg" },
      "corroboration": [ { "name": "CNBC", "url": "https://…" } ],
      "summary_mode": "ai-grounded | publisher-blurb | editor-verified",
      "verification": { "link_status": 200, "date_source": "article", "checks": ["…"] }
  } ], "india": [] },
  "rejected": [ { "title": "…", "reason": "article date disagrees with feed date (stale or republished)" } ]
}
```

## Customising

- **Sources:** add a feed to `scripts/sources.json` (`region`: `global` or `india`, `trust`: 1–3, `ai_only` for AI-only feeds). A broken feed is logged and skipped; it never fails the run.
- **Counts and window:** `scripts/config.json` → `edition`.
- **Signature:** `scripts/config.json` → `site`. Run `--rerender` to apply it to past pages.
- **Publisher images:** `images.use_publisher_images` is off by default because publisher photos are copyrighted.

## The launch edition

`2026-11-02` was built from `scripts/sample/2026-11-02.curated.json`: ten stories checked by hand against their publisher pages, with a wider 72-hour window because it is the first issue. It is labelled as a launch edition on the page and in its JSON. All later editions are produced automatically.
