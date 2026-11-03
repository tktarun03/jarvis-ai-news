/* JARVIS AI NEWS v1.1 — progressive enhancement for the static edition pages.
   Without JS each card links straight to its publisher; everything here is optional. */
(function () {
  'use strict';

  var dataEl = document.getElementById('edition-data');
  if (!dataEl) return;
  var DATA = JSON.parse(dataEl.textContent);
  var ED = DATA.edition, CATS = DATA.categories, BASE = DATA.base || '', SITE = DATA.site, SCHED = DATA.schedule || {};
  var RELEASES = DATA.releases || { current: '', releases: [] };
  var TZ = ED.timezone || SCHED.timezone || 'Asia/Qatar';
  var STORIES = {};
  ['global', 'india'].forEach(function (r) { (ED.stories[r] || []).forEach(function (s) { STORIES[s.id] = s; }); });
  var reduced = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
  var store = {
    get: function (k, d) { try { var v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { } }
  };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  var PATHS = {
    close: '<path d="M6 6l12 12M18 6L6 18"/>',
    share: '<path d="M12 15V3.5M7.5 8 12 3.5 16.5 8"/><path d="M5 12.5V19a1.5 1.5 0 0 0 1.5 1.5h11A1.5 1.5 0 0 0 19 19v-6.5"/>',
    external: '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v4.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6H10"/>',
    saved: '<path d="M6.5 3.5h11a1 1 0 0 1 1 1V21l-6.5-4.5L5.5 21V4.5a1 1 0 0 1 1-1z"/>'
  };
  function icon(name) { return '<svg class="ic" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' + PATHS[name] + '</svg>'; }
  function markSvg() { var m = $('.brand .mark'); return m ? m.outerHTML : ''; }

  /* ---------- time helpers (Doha) ---------- */
  function zoneParts(d) {
    var f = new Intl.DateTimeFormat('en-GB', { timeZone: TZ, hour: '2-digit', minute: '2-digit', hour12: false });
    var p = f.formatToParts(d), h = 0, m = 0;
    p.forEach(function (x) { if (x.type === 'hour') h = +x.value % 24; if (x.type === 'minute') m = +x.value; });
    return { h: h, m: m };
  }
  function minutesToNextEdition() {
    var t = (SCHED.local_time || '07:30').split(':'), target = (+t[0]) * 60 + (+t[1]);
    var n = zoneParts(new Date()), now = n.h * 60 + n.m;
    var diff = (target - now + 1440) % 1440;
    return diff === 0 ? 1440 : diff;
  }
  function fmtDuration(mins) { var h = Math.floor(mins / 60), m = mins % 60; return (h ? h + 'h ' : '') + m + 'm'; }

  /* ---------- toast ---------- */
  var toastEl = $('#toast'), toastT;
  function toast(msg, action) {
    toastEl.innerHTML = '<span class="toast-msg">' + esc(msg) + '</span>' +
      (action ? '<a class="toast-act" href="' + esc(action.href) + '">' + esc(action.label) + '</a>' : '');
    toastEl.hidden = false; toastEl.style.animation = 'none'; void toastEl.offsetWidth; toastEl.style.animation = '';
    clearTimeout(toastT); toastT = setTimeout(function () { toastEl.hidden = true; }, action ? 6000 : 2600);
  }

  /* ---------- header: condense on scroll, greeting ---------- */
  var scroller = $('#scroller'), top = $('#top');
  scroller.addEventListener('scroll', function () { top.classList.toggle('condensed', scroller.scrollTop > 24); }, { passive: true });
  /* Light by default; dark is an explicit, remembered choice. */
  var root = document.documentElement, themeBtn = $('#theme-btn');
  function syncTheme() {
    var dark = root.getAttribute('data-theme') === 'dark';
    themeBtn.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
    themeBtn.title = dark ? 'Switch to light theme' : 'Switch to dark theme';
    document.querySelector('meta[name="theme-color"]').content = dark ? '#111211' : '#F8F9F6';
  }
  syncTheme();
  themeBtn.addEventListener('click', function () {
    var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('jarvis_theme_v2', next); } catch (e) { }
    syncTheme();
    toast('Theme: ' + next);
  });

  /* ---------- relative times (fresh editions, last 24h only) ---------- */
  function relTimes() {
    var fresh = (Date.now() - Date.parse(ED.generated_at)) < 36 * 3600e3;
    if (!fresh) return;
    $$('time[data-precision="time"]').forEach(function (t) {
      var mins = Math.round((Date.now() - Date.parse(t.getAttribute('datetime'))) / 60000);
      if (mins < 0 || mins > 24 * 60) return;
      if (!t.title) t.title = t.textContent;
      t.textContent = mins < 60 ? mins + 'm ago' : Math.round(mins / 60) + 'h ago';
    });
  }
  relTimes();

  /* ---------- refresh: look for a newer edition ---------- */
  var refreshBtn = $('#refresh-btn');
  refreshBtn.addEventListener('click', function () {
    if (refreshBtn.classList.contains('spin')) return;
    refreshBtn.classList.add('spin');
    var started = Date.now();
    fetch(BASE + 'data/index.json?t=' + started, { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (idx) {
        var latest = idx.latest, onHome = !/\/news\/\d{4}-\d{2}-\d{2}\.html$/.test(location.pathname);
        var wait = Math.max(0, 650 - (Date.now() - started));
        setTimeout(function () {
          refreshBtn.classList.remove('spin');
          renderArchive(idx);
          relTimes();
          if (latest && latest > ED.edition_date) {
            if (onHome) { toast('New edition found. Loading…'); setTimeout(function () { location.replace(location.pathname + '?v=' + latest); }, 700); }
            else toast('A newer edition is out (' + latest + ')', { label: 'Open', href: BASE + 'news/' + latest + '.html' });
          } else if (latest === ED.edition_date) {
            toast('Up to date. Next edition in ' + fmtDuration(minutesToNextEdition()) + ' (' + (SCHED.local_time || '07:30') + ' Doha)');
          } else {
            toast('This is an archived edition', { label: 'Latest', href: BASE + 'index.html' });
          }
        }, wait);
      })
      .catch(function () { refreshBtn.classList.remove('spin'); toast('Offline. Showing the edition saved in this page.'); });
  });

  /* ---------- tabs and category filter ---------- */
  var state = { tab: 'today', cat: 'all' };
  function applyFilter() {
    var newsTab = state.tab === 'today' || state.tab === 'global' || state.tab === 'india';
    $$('[data-pane]').forEach(function (el) { el.hidden = el.getAttribute('data-pane') !== (newsTab ? 'news' : state.tab); });
    if (!newsTab) return;
    $$('[data-region-section]').forEach(function (sec) {
      var region = sec.getAttribute('data-region-section');
      var shown = 0, cards = $$('.story', sec);
      cards.forEach(function (card) {
        var ok = state.cat === 'all' || card.getAttribute('data-category') === state.cat;
        card.hidden = !ok; if (ok) shown++;
      });
      var empty = $('.filter-empty', sec);
      if (!shown && cards.length) {
        if (!empty) { empty = document.createElement('p'); empty.className = 'empty filter-empty'; $('.stories', sec).after(empty); }
        empty.textContent = 'No ' + (CATS[state.cat] ? CATS[state.cat].label.toLowerCase() : '') + ' stories in this section today.';
        empty.hidden = false;
      } else if (empty) { empty.hidden = true; }
      sec.hidden = !(state.tab === 'today' || state.tab === region);
    });
  }
  $$('.tab').forEach(function (b) {
    b.addEventListener('click', function () {
      state.tab = b.getAttribute('data-tab');
      $$('.tab').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
      if (state.tab === 'saved') renderSaved();
      applyFilter();
      scroller.scrollTo({ top: 0 });
      try { sessionStorage.setItem('jarvis_tab', state.tab); } catch (e) { }
    });
  });
  $$('.chip').forEach(function (c) {
    c.addEventListener('click', function () {
      state.cat = c.getAttribute('data-cat');
      $$('.chip').forEach(function (x) { x.setAttribute('aria-pressed', String(x === c)); });
      applyFilter();
    });
  });

  /* ---------- saved stories (this browser only) ---------- */
  function savedList() { return store.get('jarvis_saved', []); }
  function toggleSave(id) {
    var list = savedList(), s = STORIES[id];
    var i = list.findIndex(function (x) { return x.id === id; });
    if (i >= 0) { list.splice(i, 1); toast('Removed from Saved'); }
    else if (s) {
      list.unshift({ id: s.id, headline: s.headline, summary: s.summary, url: s.source.url, source: s.source.name,
        category: s.category, published_at: s.published_at, edition: ED.edition_date });
      toast('Saved on this device');
    }
    store.set('jarvis_saved', list.slice(0, 200));
    syncSaveButtons();
  }
  function syncSaveButtons() {
    var ids = {}; savedList().forEach(function (s) { ids[s.id] = 1; });
    $$('[data-save]').forEach(function (b) { var on = !!ids[b.getAttribute('data-save')]; b.setAttribute('aria-pressed', String(on)); b.setAttribute('aria-label', on ? 'Remove from saved' : 'Save story'); });
  }
  function renderSaved() {
    var list = savedList(), wrap = $('#saved-list');
    $('#saved-empty').hidden = list.length > 0;
    wrap.innerHTML = list.map(function (s) {
      var cat = CATS[s.category] || { label: '', color: 'var(--accent)' };
      return '<article class="story row" data-id="' + esc(s.id) + '"><div class="row-text">' +
        '<p class="meta"><span class="dot" style="--c:' + esc(cat.color) + '"></span><span>' + esc(cat.label) + '</span><span class="sep">·</span><span>' + esc(s.source) + '</span><span class="sep">·</span><span>Edition ' + esc(s.edition) + '</span></p>' +
        '<h3 class="story-title"><a class="story-link" href="' + BASE + 'news/' + esc(s.edition) + '.html#s-' + esc(s.id) + '">' + esc(s.headline) + '</a></h3>' +
        '<p class="story-sum">' + esc(s.summary) + '</p>' +
        '<div class="story-foot"><span class="hint">' + esc(new Date(s.published_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: TZ })) + '</span>' +
        '<button class="save-btn" type="button" data-unsave="' + esc(s.id) + '" aria-pressed="true" aria-label="Remove from saved">' + icon('saved') + '</button></div></div></article>';
    }).join('');
    $$('[data-unsave]', wrap).forEach(function (b) {
      b.addEventListener('click', function (e) {
        e.preventDefault(); e.stopPropagation();
        store.set('jarvis_saved', savedList().filter(function (x) { return x.id !== b.getAttribute('data-unsave'); }));
        renderSaved(); syncSaveButtons(); toast('Removed from Saved');
      });
    });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-save]');
    if (b) { e.preventDefault(); e.stopPropagation(); toggleSave(b.getAttribute('data-save')); }
  }, true);
  syncSaveButtons();

  /* ---------- sheets ---------- */
  var sheetRoot = $('#sheet-root'), lastFocus = null;
  function openSheet(inner, meta, onReady) {
    lastFocus = document.activeElement;
    sheetRoot.innerHTML = '<div class="sheet-wrap" role="dialog" aria-modal="true" aria-labelledby="sheet-title"><div class="sheet">' +
      '<span class="grab"></span><div class="sheet-top">' + (meta || '<span></span>') +
      '<button class="icon-btn" type="button" data-close aria-label="Close">' + icon('close') + '</button></div>' +
      '<div class="sheet-body">' + inner + '</div></div></div>';
    var wrap = $('.sheet-wrap', sheetRoot), body = $('.sheet-body', sheetRoot), topBar = $('.sheet-top', sheetRoot);
    var hasHero = !!$('.sheet-hero', body);
    topBar.classList.toggle('scrolled', !hasHero);
    body.addEventListener('scroll', function () { topBar.classList.toggle('scrolled', !hasHero || body.scrollTop > 180); }, { passive: true });
    wrap.addEventListener('click', function (e) { if (e.target === wrap || e.target.closest('[data-close]')) closeSheet(); });
    $('[data-close]', wrap).focus({ preventScroll: true });
    if (onReady) onReady(wrap);
  }
  function closeSheet(fromPop) {
    var wrap = $('.sheet-wrap', sheetRoot); if (!wrap) return;
    wrap.classList.add('out');
    setTimeout(function () { sheetRoot.innerHTML = ''; if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true }); }, 190);
    if (!fromPop && location.hash.indexOf('#s-') === 0) { try { history.back(); } catch (e) { } }
  }
  function imgSrc(im) { return im.type === 'publisher' ? im.src : BASE + im.src; }
  function fmtWhen(s) {
    var opts = { timeZone: TZ, day: 'numeric', month: 'long', year: 'numeric' };
    if (s.published_precision !== 'date') { opts.hour = '2-digit'; opts.minute = '2-digit'; }
    try { return new Date(s.published_at).toLocaleString('en-GB', opts) + (s.published_precision !== 'date' ? ' Doha' : ''); } catch (e) { return s.published_at; }
  }

  function openStory(id, push) {
    var s = STORIES[id]; if (!s) return;
    var cat = CATS[s.category], im = s.image;
    var fb = BASE + (im.fallback || im.src);
    var credit = im.type !== 'generated' ? '<span class="credit">' + esc(im.credit) + '</span>' : '';
    var insights = (s.key_insights || []).length
      ? '<ol class="insights">' + s.key_insights.map(function (x, i) { return '<li><span class="n">' + (i + 1) + '.</span><span>' + esc(x) + '</span></li>'; }).join('') + '</ol>'
      : '<p class="unavailable">Key insights are only published when they can be checked against the publisher\'s text. Read the source for the full reporting.</p>';
    var impact = s.impact ? '<p class="impact">' + esc(s.impact) + '</p>' : '<p class="unavailable">No impact statement: the source did not support one.</p>';
    var also = (s.corroboration || []).length
      ? '<div class="block"><p class="eyebrow block-title">Also reported by</p><div class="also">' + s.corroboration.map(function (c) { return '<a href="' + esc(c.url) + '" target="_blank" rel="noopener">' + esc(c.name) + '</a>'; }).join('') + '</div></div>' : '';
    var modeLabel = { 'ai-grounded': 'AI summary, checked against publisher text', 'editor-verified': 'Hand-verified by the editor', 'publisher-blurb': "Publisher's own summary" }[s.summary_mode] || s.summary_mode;
    var meta = '<p class="meta"><span class="dot" style="--c:' + esc(cat.color) + '"></span><span>' + esc(cat.label) + '</span></p>';
    var inner =
      '<div class="sheet-hero" data-img data-kind="' + esc(im.type) + '"><img src="' + esc(imgSrc(im)) + '" alt="' + esc(im.alt) + '"' + (im.type === 'publisher' ? ' referrerpolicy="no-referrer"' : '') +
      ' data-fallback="' + esc(fb) + '" onerror="this.onerror=null;this.src=this.dataset.fallback;this.parentNode.classList.add(\'is-fallback\');var c=this.parentNode.querySelector(\'.credit\');if(c)c.remove()">' + credit + '</div>' +
      '<p class="sheet-kicker"><span class="badge"><span class="dot" style="--c:' + esc(cat.color) + '"></span>' + esc(cat.label) + ' · ' + (s.region === 'india' ? 'India' : 'Global') + '</span></p>' +
      '<h2 class="sheet-title" id="sheet-title">' + esc(s.headline) + '</h2>' +
      '<div class="byline"><span class="src">' + esc(s.source.name) + '</span><span class="hint">' + esc(fmtWhen(s)) + '</span></div>' +
      '<p class="sheet-sum">' + esc(s.summary) + '</p>' +
      '<div class="block"><p class="eyebrow block-title">Key insights</p>' + insights + '</div>' +
      '<div class="block"><p class="eyebrow block-title">Real-world impact</p>' + impact + '</div>' +
      also +
      '<div class="actions"><a class="btn wide" href="' + esc(s.source.url) + '" target="_blank" rel="noopener">' + icon('external') + 'Read at ' + esc(s.source.name) + '</a>' +
      '<button class="btn ghost" type="button" data-share>' + icon('share') + 'Share</button>' +
      '<button class="btn ghost" type="button" data-save="' + esc(s.id) + '" aria-pressed="false">' + icon('saved') + 'Save</button></div>' +
      '<div class="block"><p class="eyebrow block-title">How this was checked</p><ul class="checks">' +
      (s.verification.checks || []).map(function (c) { return '<li>' + esc(c) + '</li>'; }).join('') +
      '<li>' + esc(modeLabel) + '</li></ul></div>';
    openSheet(inner, meta, function (wrap) {
      syncSaveButtons();
      $('[data-share]', wrap).addEventListener('click', function () { share(s); });
    });
    if (push) { try { history.pushState({ story: id }, '', '#s-' + id); } catch (e) { } }
  }

  function openAbout() {
    var mins = minutesToNextEdition();
    var sumOn = ED.summarizer && ED.summarizer.enabled;
    var imgTypes = {}; Object.keys(STORIES).forEach(function (k) { imgTypes[STORIES[k].image.type] = (imgTypes[STORIES[k].image.type] || 0) + 1; });
    var rels = (RELEASES.releases || []).map(function (r) {
      return '<li><div class="rel-head"><span class="rel-ver">v' + esc(r.version) + '</span><span class="rel-name">' + esc(r.name || '') + '</span><span class="hint">' + esc(r.date) + '</span></div>' +
        '<ul class="rel-notes">' + (r.notes || []).map(function (n) { return '<li>' + esc(n) + '</li>'; }).join('') + '</ul></li>';
    }).join('');
    var inner =
      '<div class="about-head">' + markSvg() + '<div><p class="about-name">JARVIS</p><p class="hint">AI NEWS · <span class="ver-pill">v' + esc(RELEASES.current) + '</span></p></div></div>' +
      '<p class="sheet-sum">' + esc(SITE.signature) + '. <em>' + esc(SITE.agent_credit) + '</em></p>' +
      '<dl class="kv">' +
      '<dt>Edition</dt><dd>Nº ' + String(ED.edition_number).padStart(3, '0') + ' · ' + esc(ED.edition_date) + '</dd>' +
      '<dt>Generated</dt><dd>' + esc(new Date(ED.generated_at).toLocaleString('en-GB', { timeZone: TZ, day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })) + ' Doha</dd>' +
      '<dt>Next edition</dt><dd>' + esc(SCHED.local_time || '07:30') + ' Doha · in ' + fmtDuration(mins) + '</dd>' +
      '<dt>Summaries</dt><dd>' + (ED.edition_type === 'launch-sample' ? 'Hand-verified' : sumOn ? 'AI, grounded in source' : "Publisher's own") + '</dd>' +
      '<dt>Images</dt><dd>' + esc(Object.keys(imgTypes).map(function (k) { var n = imgTypes[k]; return n + ' ' + ({ generated: n === 1 ? 'JARVIS cover' : 'JARVIS covers', publisher: 'from publishers', 'publisher-copy': n === 1 ? 'publisher copy' : 'publisher copies' }[k] || k); }).join(' · ')) + '</dd>' +
      '<dt>Edition log</dt><dd><a href="https://github.com/tktarun03/jarvis-ai-news/commits/main/data/' + esc(ED.edition_date) + '.json" target="_blank" rel="noopener">Change history</a></dd>' +
      '</dl>' +
      '<div class="block"><p class="eyebrow block-title" id="sheet-title">Version history</p><ol class="timeline">' + rels + '</ol></div>' +
      '<div class="actions"><a class="btn ghost wide" href="https://github.com/tktarun03/jarvis-ai-news" target="_blank" rel="noopener">' + icon('external') + 'Source on GitHub</a></div>';
    openSheet(inner, '<p class="meta"><span>About</span></p>');
  }
  $('#about-btn').addEventListener('click', openAbout);

  function share(s) {
    var url = location.href.split('#')[0].split('?')[0] + '#s-' + s.id;
    if (navigator.share) { navigator.share({ title: s.headline, text: s.summary, url: url }).catch(function () { }); return; }
    if (navigator.clipboard) { navigator.clipboard.writeText(url).then(function () { toast('Link copied'); }, function () { toast(url); }); }
    else toast(url);
  }
  document.addEventListener('click', function (e) {
    var card = e.target.closest('.story[data-id]');
    if (!card || !STORIES[card.getAttribute('data-id')]) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) return;
    e.preventDefault();
    openStory(card.getAttribute('data-id'), true);
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeSheet(); });
  window.addEventListener('popstate', function () {
    var m = location.hash.match(/^#s-([0-9a-f]{12})$/);
    if (m) openStory(m[1], false); else closeSheet(true);
  });

  /* ---------- archive ---------- */
  function renderArchive(idx) {
    if (!idx || !idx.editions) return;
    $('#archive-list').innerHTML = idx.editions.map(function (e) {
      var d = new Date(e.date + 'T12:00:00Z');
      return '<a class="arow' + (e.date === ED.edition_date ? ' current' : '') + '" href="' + BASE + 'news/' + e.date + '.html">' +
        '<span class="arow-date"><span class="num">' + Number(e.date.slice(8)) + '</span><span class="eyebrow">' + d.toLocaleDateString('en-GB', { month: 'short', year: 'numeric', timeZone: 'UTC' }) + '</span></span>' +
        '<span class="grow"><span class="arow-title">' + esc(e.top_headline || ('Edition ' + e.date)) + '</span>' +
        '<span class="hint">' + e.counts.global + ' global · ' + e.counts.india + ' India · Nº ' + String(e.number).padStart(3, '0') + '</span></span></a>';
    }).join('');
  }
  fetch(BASE + 'data/index.json', { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).then(renderArchive).catch(function () { });

  /* ---------- start ---------- */
  try { var t = sessionStorage.getItem('jarvis_tab'); if (t && t !== 'today') { var tb = $('.tab[data-tab="' + t + '"]'); if (tb) tb.click(); } } catch (e) { }
  applyFilter();
  var initial = location.hash.match(/^#s-([0-9a-f]{12})$/);
  if (initial && STORIES[initial[1]]) {
    try { history.replaceState(null, '', location.pathname + location.search); history.pushState({ story: initial[1] }, '', '#s-' + initial[1]); } catch (e) { }
    openStory(initial[1], false);
  }
})();

