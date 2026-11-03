---
name: jarvis-ai-news
description: Run, curate, fix or extend the JARVIS AI NEWS daily edition pipeline in this repo. Use for building an edition (automatic or hand-verified), adding feeds, changing the schedule, correcting a story, re-rendering pages, or diagnosing a failed daily run.
---

# JARVIS AI NEWS: operating skill

This skill gives step-by-step procedures. `AGENTS.md` at the repo root holds the rules and the data contract. Read it first; its non-negotiable rules apply to every procedure here.

Every procedure ends the same way: **tests pass → `python scripts/validate.py` passes → commit**. If validation fails, fix the cause and run it again. Never commit around a failure.

---

## Procedure 0: Check and claim before any edition job

1. `git pull`, then `python scripts/claim-edition.py check --agent <your-name>`.
2. Exit 10 means the edition is already published; report who produced it and stop. Exit 11 means another agent is building it; stop.
3. Exit 0 means it is free: `python scripts/claim-edition.py claim --agent <your-name> --push`, then continue with Procedure 1 or 2, passing `--agent <your-name>` to `generate-news.py`.

## Procedure 1: Run today's edition (automatic)

Use this when a daily run is needed outside the schedule, or to reproduce what Actions does.

1. Run `python -m unittest discover -s tests`. Everything must pass.
2. Run `python scripts/generate-news.py`. Possible outcomes:
   - `Published edition DATE ...` → continue.
   - `SKIP: edition DATE already published` → nothing to do. Use `--force` only if the owner asked for a rebuild.
   - `SKIP: only N stories passed verification` → this is correct behaviour. Go to Procedure 6 to find out why.
3. Run `python scripts/validate.py`.
4. Open `data/DATE.json`. Check that `feeds.failed` is short and that `rejected` reasons make sense.
5. Commit `index.html news data assets/images/covers` with the message `edition: DATE`.

In GitHub Actions, use **Actions → Daily AI News → Run workflow**. Tick `force` only to rebuild.

The edition date is today's date in Asia/Qatar, not UTC.

## Procedure 2: Build a hand-verified edition (curated)

Use this when feeds are down, for a launch or special edition, or when the owner supplies stories. This is how `2026-11-02` was made.

1. **Research.** For each candidate story, open the publisher's own page and confirm:
   - the URL works and is on a trusted domain (`scripts/sources.json` feeds or `extra_trusted_domains`);
   - the publication date is shown on the page;
   - every figure you plan to use appears on the page.
2. **Reject anything you cannot confirm.** Record the title and reason under `rejected`. Typical reasons:
   - stale (first announced earlier and recirculated by an aggregator);
   - AI-generated forecast pages;
   - only reports of talks, not a done deal;
   - primary source unreachable.
3. **Write `scripts/sample/DATE.curated.json`.** Use the shape below. Copy the structure from `scripts/sample/2026-11-02.curated.json`.

```json
{
  "edition_date": "YYYY-MM-DD",
  "window": { "start": "ISO-UTC", "end": "ISO-UTC" },
  "stories": {
    "global": [ {
      "headline": "your own words, ≤110 chars",
      "source_title": "publisher's exact headline",
      "source_name": "Publisher",
      "url": "https://publisher/article",
      "published_at": "ISO-UTC",
      "published_precision": "date or time",
      "category": "research|products|business|policy|infrastructure|safety|applications|startups",
      "trust": 1,
      "summary": "2–3 paraphrased sentences",
      "key_insights": ["≤3 facts from the page, ≤140 chars each"],
      "impact": "who is affected and how, only as far as the source supports; or null",
      "tags": ["lowercase"],
      "corroboration": [ { "name": "Other outlet", "url": "https://…" } ],
      "checks": ["publisher page opened and read", "publication date confirmed on page"]
    } ],
    "india": []
  },
  "rejected": [ { "title": "…", "reason": "…" } ]
}
```

   Field rules:
   - `trust`: 1 (useful but needs corroboration) to 3 (primary source or top-tier newsroom).
   - `published_at`: must fall inside `window`.
   - `published_precision: "date"`: use when the page shows only a date. Set `published_at` to local midnight in Doha, expressed in UTC (for example, 2 Nov 2026 → `2026-11-01T21:00:00Z`). Never invent a time of day.
   - Maximum 10 stories per region. No URL may already appear in an earlier edition.

4. Run `python scripts/generate-news.py --curated scripts/sample/DATE.curated.json` (add `--force` to rebuild).
5. Run `python scripts/validate.py`, then commit with a message that says the edition is hand-verified.

## Procedure 3: Write or review a summary (editorial standard)

This standard applies both to curated stories and to reviewing `ai-grounded` output.

- **Headline:** factual and specific, in your own words. Name the actor and the action. No hype words ("revolutionary", "game-changer") and no question headlines.
- **Summary:** 2–3 sentences that say what happened, who did it, and the key figure. Paraphrase. Don't reproduce the publisher's sentences.
- **Key insights:** up to 3 facts from the source that are not already in the summary. If there are fewer, list fewer.
- **Impact:** who is affected and how, kept within what the source supports. Use hedged wording ("could", "points to") for anything forward-looking. Use `null` if the source doesn't support an impact statement.
- **Numbers:** every number must appear in the source. The automatic grounding check rejects unknown numbers. Apply the same standard by hand.
- **Quotes:** at most one per story, under 10 words, copied exactly.
- **Conflicts:** if the source contradicts itself (for example, a headline total that differs from the body total), use the body figure and note the mismatch in an insight or a check.
- **Balance:** report negative news about any company, including AI labs, as plainly as positive news.

## Procedure 4: Add, fix or remove a feed

1. Open `scripts/sources.json` and add an entry:
   `{ "id": "kebab-id", "name": "Display Name", "region": "global|india", "trust": 1-3, "ai_only": true|false, "url": "https://…/feed" }`.
   - Set `ai_only: true` only for feeds that contain nothing but AI stories. General tech feeds are passed through the AI keyword filter.
   - If the publisher's article links use a different host from its feed, add that host to `extra_trusted_domains`.
2. If you can, add a fixture to `tests/fixtures/feeds/<id>.xml` and extend `tests/test_pipeline.py`.
3. Run the tests and the validator, then commit with `sources: add <name>`.

To find broken feeds, look at `feeds.failed` in the latest `data/DATE.json`. Each entry has an `id` and an `error`. Fix the URL or remove the feed. A failing feed never breaks the run.

## Procedure 5: Change the schedule, limits or signature

- **Run time:** edit `scripts/config.json` → `schedule.local_time` (`HH:MM`) and/or `schedule.timezone` (an IANA name). Then run `python scripts/set-schedule.py`, which rewrites the UTC cron line, and run `python scripts/validate.py`, which checks the cron matches the config.
- **Limits:** edit `config.json` → `edition`: `lookback_hours`, `max_global`, `max_india`, `min_stories_to_publish`, `max_per_source`, `dedupe_memory_days`.
- **Signature or branding:** edit `config.json` → `site`. Then run `python scripts/generate-news.py --rerender` so past pages pick up the change.

## Procedure 6: Diagnose a failed or empty daily run

1. Open the latest Actions run and read the log of the step that failed.
   - **Offline pipeline tests failed:** a code change broke the pipeline. Fix the code. Don't skip the tests.
   - **Generate printed `SKIP: only N stories`:** check how many feeds failed (in the log line). If most feeds failed, suspect a network or GitHub outage and re-run later. If feeds are fine, the day was thin or the filters are rejecting too much: run locally and inspect the reasons in `rejected`.
   - **Validate failed:** the error message names the file and the story id. Fix the data or the code, then re-run.
   - **The configure-pages or deploy step failed:** Pages is not enabled. Set **Settings → Pages → Source: GitHub Actions**.
   - **Images are all JARVIS covers:** the publishers may not expose `og:image`, or `images.mode` is `generated`. Check `image.type` in the JSON.
   - **Summaries are all `publisher-blurb`:** the `ANTHROPIC_API_KEY` secret is missing or invalid. Look for `summarizer HTTP 401` in `rejected`.
2. Never "fix" a run by hand-writing stories without doing Procedure 2's verification, and never by loosening `validate.py`.

## Procedure 7: Change the design

1. Edit `assets/css/app.css` (tokens on `:root`, dark mode under `prefers-color-scheme` and `[data-theme="dark"]`), `assets/js/app.js`, or `scripts/jarvis/render.py`.
2. Keep the v1.5 "Reader" design language:
   - white and light-grey surfaces with one indigo accent (`--accent`); four reading themes on `data-theme`: `light`, `sepia`, `dim`, `dark`;
   - Plus Jakarta Sans throughout, bold (700–800) headlines with tight tracking;
   - 26px image cards with the headline over the photo, 18–22px radius elsewhere;
   - Home: greeting and daily brief, underline region tabs (Top stories, Global, India, My topics), a swipeable top-stories card with page dots, then "Explore Global/India" thumbnail rows;
   - bottom tabs: Home, Explore (search, source circles, category tabs), Saved, Archive, Profile (publisher card, topic picker, settings, about);
   - reader: photo on top, white panel sliding over it, bottom bar with Save, Read source and a reading-progress ring;
   - "Aa" Display card: brightness, dark reading theme, font size (`--read-scale`), follow-device theme, theme colour swatches;
   - source badges are coloured monograms; never use publisher logos;
   - 40px or larger tap targets.
   - Logo (v1.7.2): a liquid colour sphere (`MARK_SVG` in render.py, `.orb` in app.css). `.orb-fluid` is the clipped, feather-masked sphere; four blurred lobes `.ob1`–`.ob4` (magenta, cyan, blue, lavender) turn inside it at different speeds and directions on a 5.4 s rhythm; `.orb-fluid::after` is the white top light and `.orb::before` the lavender halo. Size the blur with `--soft` / `--halo`. Colours animate transform only (the edge wobble animates border-radius); still under reduced motion; faster while the brief is read (`html.speaking`). Static copies: `assets/images/brand/favicon.svg`, `mark.svg`, `apple-touch-icon.png`, `og.png`. Keep it original.
   - Share (v1.8): a share button on every card (`data-qshare`) and in the reader opens a share card (`share()` in app.js): optional note, WhatsApp (`https://wa.me/?text=`), Copy message, More apps (Web Share, link inside `text` because WhatsApp on iOS drops a separate `url`), Copy link only. The message is note, *headline*, whole-sentence summary, _Why it matters:_ impact, source, share link, `— via JARVIS AI NEWS`. The link is the per-story share page `news/DATE/ID.html` (`scripts/jarvis/share.py`), written on publish and on `--rerender`.
   - Minimal (v1.7): the light theme is pure white (`--bg: #FFFFFF`); use hairline borders (`--line`), not shadows; one accent colour; headline weights 600–700. The brief card is a plain bordered white card.
   - Home header (v1.6): live Doha date chip (`#live-clock`), large greeting (`#greet-hello`, set by brief.js), and a gradient brief card (`--card-a`/`--card-b` per theme) with counts and Listen controls; the top bar has search, refresh and the theme switch.
   - Notifications: always use `window.JARVIS.toast(message, action?, {sticky?, duration?})`. Toasts slide up from the bottom, have a close button and can be swiped down. Do not add top banners or browser alerts.
   - Pinch and double-tap zoom are disabled at the owner's request (viewport meta, `touch-action: pan-x pan-y`, and gesture handlers in app.js). Keep inputs at 16px or larger so iOS does not zoom on focus, and keep Aa → Font size working as the readability alternative.
   - Check 320, 360, 390 and 430px widths, phone landscape, 768px and 1440px for horizontal overflow.
   - Keep the IDs that `assets/js/brief.js` uses (`greet-hello`, `brief-title`, `brief-greeting`, `listen-btn`, `pause-btn`, `stop-btn`, `voice-status`, `news-update`, `push-btn`, `push-status`).
3. Keep pages readable without JavaScript: cards link straight to the publisher.
4. If you changed `render.py`, run `--rerender`.
5. Run `validate.py`, then preview with `python -m http.server`. Check 390px width and desktop in the light, sepia and dark themes, plus the reader, Display card, Explore filters, My topics, saved stories and the archive.

## Procedure 8: Publisher images

1. The mode is set in `scripts/config.json` → `images.mode`:
   - `generated`: JARVIS covers only.
   - `publisher-hotlink` (default): the publisher's `og:image`, loaded from their server, credited, with the JARVIS cover as fallback.
   - `publisher-download`: copies images into the repo. Owner approval is required; see `AGENTS.md` rule 4.
2. To add publisher images to an edition built without them (for example, the hand-curated launch edition), run `python scripts/generate-news.py --refresh-images DATE`. In GitHub, use **Run workflow** with `refresh_images_date` set. This needs network access to the publishers.
3. In curated files, an optional `"image_url"` per story sets the publisher image directly. Use only the page's own `og:image`.
4. Images are skipped when they are not https, are SVG, or look like a logo or placeholder. Broken images fall back to the cover in the browser automatically.
5. **Illustrative stock photos (Pixabay)** are set in `config.json` → `images.stock`:
   - `role: fallback` (default): used only when no publisher image was found;
   - `role: primary`: used for every story.

   They need the `PIXABAY_API_KEY` Actions secret. Photos are downloaded to `assets/images/stock/pixabay-<id>.jpg` and reused across editions; queries are cached for 24 hours in `data/stock-library.json`. `--refresh-images DATE` also fills stock photos. Never change the queries to include company, product or person names, and never remove the "Illustrative" credit.
6. **AI-generated images** are set in `config.json` → `images.ai`, and tried first by default (`images.fallback_order`: `["ai", "stock"]`). They need the `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` Actions secrets, and run on Cloudflare's free daily allowance.
   - To add a scene, add an entry to `SCENES` in `scripts/jarvis/aiimages.py`: a generic place or object, with no people and no brands. The concept key must match a query produced by `stock.queries_for`.
   - Never pass story text or names into a prompt; the validator will reject it.
   - Images are reused per concept (up to `max_variants_per_concept`), so most days generate nothing new.
   - `--refresh-images DATE` also fills AI images for an existing edition.

## Procedure 9: Ship an app release

1. Make the change (Procedure 7 for design).
2. Add an entry at the top of `assets/releases.json` (`version`, `date`, `name`, `notes`) and set `current` to that version.
3. Run `python scripts/generate-news.py --rerender`, then `python scripts/validate.py`.
4. Commit with `feat: vX.Y.Z <name>`.

## Procedure 10: Correct a published story

1. Edit the story in `data/DATE.json`. Change only what is wrong.
2. Add a `verification.checks` entry such as `"corrected YYYY-MM-DD: <what changed>"`.
3. Run `python scripts/generate-news.py --rerender`, then `python scripts/validate.py`.
4. Commit with `fix: correct <story> in DATE edition`, and explain the error in the commit body.
5. If the story should not have been published at all, remove it, update `counts` in that edition and in its `data/index.json` entry (plus `top_headline` if it was the lead), and re-render. Leave its URL in `data/seen.json` so it is not republished.

---

## Quick reference

| Need | Command |
|---|---|
| Tests | `python -m unittest discover -s tests -v` |
| Gate | `python scripts/validate.py` |
| Today | `python scripts/generate-news.py` |
| Rebuild today | `python scripts/generate-news.py --force` |
| Hand-verified edition | `python scripts/generate-news.py --curated scripts/sample/DATE.curated.json` |
| Re-render all pages | `python scripts/generate-news.py --rerender` |
| Publisher images for an edition | `python scripts/generate-news.py --refresh-images DATE` |
| New schedule | edit `config.json`, then `python scripts/set-schedule.py` |
| Preview | `python -m http.server 8000` |
