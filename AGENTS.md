# AGENTS.md — JARVIS AI NEWS

Instructions for any AI agent or coding assistant working in this repository. Read this file first, then `skills/jarvis-ai-news/SKILL.md` for step-by-step procedures.

Published by Arunkumar Thamilarasu. JARVIS is an AI agent created by Arunkumar Thamilarasu.

## What this project is

A static, mobile-first daily AI news site on GitHub Pages. No backend, no database, no build step.

Once a day (07:30 Asia/Qatar = 04:30 UTC), `.github/workflows/daily-news.yml` runs `scripts/generate-news.py`, which:

1. reads the RSS/Atom feeds in `scripts/sources.json`;
2. keeps AI stories published in the last 24 hours;
3. checks each link and publication date, and removes duplicates and repeats;
4. ranks the stories and picks up to 10 global and 10 India stories;
5. writes grounded summaries (Claude via `ANTHROPIC_API_KEY`, or the publisher's own blurb when no key is set);
6. generates an original SVG cover for each story;
7. writes `data/DATE.json` and `news/DATE.html`, and updates `index.html` and the archive;
8. runs `scripts/validate.py`;
9. commits and deploys.

Editions are never deleted. The repo is the archive.

## Non-negotiable rules

These protect the site's credibility. Do not weaken them, even when asked to "just get it working."

1. **Never publish fabricated or unverified content as fact.** Every headline, summary, insight, impact statement and number must be supported by the publisher's text. If the source does not support an insight or an impact statement, leave it empty (`[]` / `null`). Do not guess.
2. **Never invent sources, URLs, dates, quotes or figures.** A story needs a real, reachable URL on a trusted domain and a real publication date.
3. **Never republish a story.** Deduplication uses `data/seen.json` (45 days) and cross-edition checks in `validate.py`.
4. **Images follow `config.json` → `images.mode`, set by the owner.** The default is `publisher-hotlink`: the publisher's own `og:image` is shown from the publisher's server, credited `Image: <Publisher>`, with the generated cover (`scripts/jarvis/covers.py`) as the fallback. `publisher-download` copies photos into this public repo, which redistributes copyrighted images. Do not enable it unless the owner confirms they hold the rights. Never use screenshots of publisher pages, and never strip an image's credit.
   **Illustrative stock photos** (`images.stock`, Pixabay, downloaded into `assets/images/stock/` as Pixabay's API terms require) fill in when there is no publisher image (`role: fallback`), or replace publisher images (`role: primary`). They are never photos of the event, so:
   - they must be credited `Illustrative · <photographer> / Pixabay` with a link to the Pixabay page (the validator checks this);
   - search queries use generic topic words only, never company, product or person names (`scripts/jarvis/stock.py`);
   - hits tagged with people are skipped;
   - never use Unsplash for this (its API terms require hotlinking).
   The key is the `PIXABAY_API_KEY` Actions secret; without it stock photos are skipped.
5. **Paraphrase; don't copy.** Summaries must be in your own words. No quote longer than 10 words, and at most one quote per story.
6. **Never commit secrets.** `ANTHROPIC_API_KEY` and `PIXABAY_API_KEY` live only in GitHub Actions secrets. Never print it, log it, or write it to a file.
7. **`scripts/validate.py` must pass before any commit that touches `data/`, `news/`, `index.html` or `assets/`.** If it fails, fix the cause. Do not edit the validator to make it pass.
8. **Keep the signature.** Every page must show `Published by Arunkumar Thamilarasu` and `JARVIS is an AI agent created by Arunkumar Thamilarasu.` (set in `scripts/config.json` → `site`).
9. **Fewer stories beats unverified stories.** If fewer than `min_stories_to_publish` (3) pass, the run publishes nothing. That is correct behaviour, not a bug.

## Commands

```bash
python -m unittest discover -s tests -v                 # offline tests (no network)
python scripts/validate.py                              # publication gate
python scripts/generate-news.py                         # build today's edition from live feeds
python scripts/generate-news.py --force                 # rebuild today's edition
python scripts/generate-news.py --rerender              # re-render every page from JSON (after template/CSS changes)
python scripts/generate-news.py --curated FILE.json     # build a hand-verified edition
python scripts/generate-news.py --refresh-images DATE   # look up publisher images for an existing edition (needs network)
python scripts/generate-news.py --now 2026-11-03T04:30:00Z --fixtures tests/fixtures --root /tmp/x   # deterministic offline run
python scripts/set-schedule.py                          # after changing schedule in config.json
python -m http.server 8000                              # preview at http://localhost:8000
```

Python 3.11+ standard library only. Do not add dependencies without a strong reason. The workflow installs nothing.

Exit codes: `generate-news.py` returns 0 on publish or on an intentional skip, and 1 on error. `validate.py` returns 1 if it finds any problem.

## Repository map

| Path | Purpose | Edit by hand? |
|---|---|---|
| `index.html` | Latest edition (generated) | No. Re-render instead |
| `news/YYYY-MM-DD.html` | One page per day (generated) | No |
| `data/YYYY-MM-DD.json` | One edition per day (source of truth for the pages) | Only to correct an error, then `--rerender` |
| `data/index.json` | Archive manifest, newest first | No |
| `data/seen.json` | Dedupe memory: `{urls: {normalizedUrl: date}, titles: {fingerprint: date}}` | No |
| `assets/css/app.css` | Design tokens and components (v1.5 "Reader" design language; see SKILL.md Procedure 7) | Yes |
| `assets/images/stock/` | Downloaded Pixabay illustrative photos, shared and reused across editions | No |
| `data/stock-library.json` | Pixabay 24-hour query cache and per-photo usage (for reuse and credits) | No |
| `scripts/jarvis/stock.py` | Illustrative stock photo search, safeguards and download | Yes, carefully |
| `assets/js/app.js` | Progressive enhancement: tabs, filters, sheet, saved, archive, theme | Yes |
| `assets/images/covers/DATE/ID.svg` | Generated covers (also the fallback for publisher images) | No |
| `assets/images/news/DATE/` | Downloaded publisher images (download mode only) | No |
| `assets/releases.json` | App version history shown in the About sheet | Yes, on every release |
| `assets/images/brand/` | Mark, favicon, social card | Yes |
| `scripts/config.json` | Limits, window, schedule, categories, signature, model | Yes |
| `scripts/sources.json` | Feeds, trust tiers, extra trusted domains, blocked patterns | Yes |
| `scripts/jarvis/feeds.py` | HTTP fetch, RSS/Atom parsing, article date and text extraction | Yes |
| `scripts/jarvis/select.py` | AI and India detection, clustering, ranking, categorisation | Yes |
| `scripts/jarvis/summarize.py` | Claude prompt and grounding checks | Yes, carefully |
| `scripts/jarvis/covers.py` | Cover art generator | Yes |
| `scripts/jarvis/images.py` | Publisher image discovery (`og:image`), hotlink and download modes | Yes, carefully |
| `scripts/jarvis/render.py` | Static HTML template | Yes, then `--rerender` |
| `scripts/jarvis/pipeline.py` | Orchestration, archive and seen updates | Yes, carefully |
| `scripts/validate.py` | Publication gate | Only to add checks, never to loosen them |
| `scripts/sample/` | Hand-verified curated inputs | Yes |
| `tests/` | Offline tests and fixtures | Yes |
| `skills/jarvis-ai-news/SKILL.md` | Step-by-step procedures for agents | Yes |

## Data contract

Every story object in `data/DATE.json` → `stories.global[]` / `stories.india[]` contains:

- `id`: first 12 hex characters of the SHA-1 of the normalized URL.
- `rank`, `region` (`global` | `india`), `category`: a key from `config.json` → `categories`: `research`, `products`, `business`, `policy`, `infrastructure`, `safety`, `applications`, `startups`.
- `headline` (≤110 chars), `source_title` (the publisher's original headline), `summary` (2–3 sentences).
- `key_insights` (0–3 strings), `impact` (string or `null`).
- `source`: `{name, domain, url, feed, trust}`; `url` must be https.
- `published_at` (ISO UTC, inside `window`), `published_precision` (`time` | `date`).
- `image`: `{type, src, alt, credit, fallback}`, where `type` is one of:
  - `generated`: `src` is a local SVG;
  - `publisher`: `src` is the publisher's https URL, with `credit_url` and `original_url`;
  - `publisher-copy`: `src` is a local copy, allowed only in download mode;
  - `stock`: `src` is a local Pixabay photo, with `credit` (`Illustrative · …`), `credit_url`, `provider`, `stock_id`, `license` and `query`.

  `fallback` is always a local generated SVG.
- `corroboration`: `[{name, url}]`, the other outlets that covered the same story.
- `summary_mode`: one of three values:
  - `ai-grounded`: Claude wrote it and it passed the checks;
  - `publisher-blurb`: the publisher's own summary; insights must be empty and impact `null`;
  - `editor-verified`: a hand-curated story.
- `verification`: `{link_status, date_source, checks: [...]}`. `checks` must not be empty.

Edition-level fields: `schema_version`, `edition_date`, `edition_number`, `edition_type` (`daily` | `launch-sample`), `timezone`, `generated_at`, `window {start, end}`, `publisher`, `summarizer`, `counts`, `stories`, `rejected [{title, url?, reason}]`, `feeds {ok, failed}`.

If you change this contract, update `render.py`, `app.js`, `validate.py`, the tests, and this section together, and bump `schema_version`.

## How to make common changes

- **Design or template change:** edit `assets/` or `scripts/jarvis/render.py`, run `--rerender`, run `validate.py`, then preview at phone width (390px) in light and dark mode.
- **Add or fix a feed:** edit `scripts/sources.json`. Check `feeds.failed` in the latest edition JSON to find broken feeds.
- **Change the run time:** edit `schedule.local_time` in `config.json`, then run `scripts/set-schedule.py`. Never hand-edit the cron line; the validator checks it against the config.
- **Change limits:** `config.json` → `edition`.
- **Correct a published story:** edit that `data/DATE.json`, run `--rerender`, run `validate.py`, and commit with a message saying what was corrected and why.

## Version history

- **App releases** live in `assets/releases.json`, newest first. Its `current` value becomes the asset cache-buster and the version shown on the initialising screen and in the About sheet.
- **For any user-visible change:** add a release entry, bump `current`, run `--rerender`, and commit.
- **Edition history** is the git history of each `data/DATE.json`; the About sheet links to it.

## Commit conventions

- The Actions bot commits daily editions as `edition: YYYY-MM-DD`.
- Human or agent changes: use a short imperative subject (`fix: …`, `feat: …`, `docs: …`, `sources: …`) and explain why in the body.
- Never force-push `main`. Never rewrite past editions except to correct a factual error, and say so in the commit.

## When you are unsure

Prefer the conservative option: skip the story, leave the field empty, keep the old edition live, and record the reason in `rejected`. Ask the owner before changing trust rules, deleting editions, enabling publisher images, or loosening validation.
