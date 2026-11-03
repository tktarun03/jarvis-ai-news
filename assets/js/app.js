/* JARVIS AI NEWS v1.6 — progressive enhancement for the static edition pages.
   Without JS every card links straight to its publisher. brief.js (voice, greeting, update banner,
   push) runs alongside and owns #brief-*, #listen/pause/stop-btn, #voice-status, #news-update, #push-*. */
(function () {
  'use strict';

  var dataEl = document.getElementById('edition-data');
  if (!dataEl) return;
  var DATA = JSON.parse(dataEl.textContent);
  var ED = DATA.edition, CATS = DATA.categories, BASE = DATA.base || '', SITE = DATA.site, SCHED = DATA.schedule || {};
  var RELEASES = DATA.releases || { current: '', releases: [] }, BADGES = DATA.badges || {};
  var TZ = ED.timezone || SCHED.timezone || 'Asia/Qatar';
  var ALL = [].concat(ED.stories.global || [], ED.stories.india || []);
  var STORIES = {}; ALL.forEach(function (s) { STORIES[s.id] = s; });

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
  var store = {
    get: function (k, d) { try { var v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { } }
  };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  var PATHS = {
    close: '<path d="M6 6l12 12M18 6L6 18"/>',
    chat: '<path d="M4.5 19.5l1.2-3.6A7.8 7.8 0 1 1 8.6 18.6z"/><path d="M9.2 9.4c.2 1.9 1.9 3.9 4.2 4.6l1-1 1.6.8-.4 1.3c-3.2.3-6.8-3-7-6.2l1.3-.4.7 1.6z"/>',
    copy: '<rect x="8.5" y="8.5" width="11" height="11" rx="2.5"/><path d="M15.5 8.5V6a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 6v8A1.5 1.5 0 0 0 6 15.5h2.5"/>',
    more: '<circle cx="6" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="18" cy="12" r="1.3"/>',
    back: '<path d="M15 5l-7 7 7 7"/>',
    share: '<path d="M12 15V3.5M7.5 8 12 3.5 16.5 8"/><path d="M5 12.5V19a1.5 1.5 0 0 0 1.5 1.5h11A1.5 1.5 0 0 0 19 19v-6.5"/>',
    external: '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v4.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6H10"/>',
    saved: '<path d="M6.5 3.5h11a1 1 0 0 1 1 1V21l-6.5-4.5L5.5 21V4.5a1 1 0 0 1 1-1z"/>',
    sunSm: '<circle cx="12" cy="12" r="3.5"/><path d="M12 4v2M12 18v2M4 12h2M18 12h2"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8"/>',
    moon: '<path d="M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10z"/>'
  };
  function icon(name, cls) { return '<svg class="ic' + (cls ? ' ' + cls : '') + '" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' + PATHS[name] + '</svg>'; }
  function markSvg() { var m = $('.brand .mark'); return m ? m.outerHTML : ''; }
  function badge(name, cls) {
    var b = BADGES[name] || [String(name || '?').split(/\s+/).filter(function (w) { return !/^(the|of|and)$/i.test(w); }).slice(0, 2).map(function (w) { return w[0]; }).join('').toUpperCase(), 'var(--accent)'];
    return '<span class="mono-badge' + (cls ? ' ' + cls : '') + '" style="--b:' + esc(b[1]) + '" aria-hidden="true">' + esc(b[0]) + '</span>';
  }

  /* ---------- time helpers (Doha) ---------- */
  function zoneParts(d) {
    var p = new Intl.DateTimeFormat('en-GB', { timeZone: TZ, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(d), h = 0, m = 0;
    p.forEach(function (x) { if (x.type === 'hour') h = +x.value % 24; if (x.type === 'minute') m = +x.value; });
    return { h: h, m: m };
  }
  function minutesToNextEdition() {
    var t = (SCHED.local_time || '07:30').split(':'), target = (+t[0]) * 60 + (+t[1]);
    var n = zoneParts(new Date()), now = n.h * 60 + n.m, diff = (target - now + 1440) % 1440;
    return diff === 0 ? 1440 : diff;
  }
  function fmtDuration(mins) { var h = Math.floor(mins / 60), m = mins % 60; return (h ? h + 'h ' : '') + m + 'm'; }
  function fmtShort(s) {
    var o = { timeZone: TZ, day: 'numeric', month: 'short' };
    if (s.published_precision !== 'date') { o.hour = '2-digit'; o.minute = '2-digit'; o.hourCycle = 'h23'; }
    try { return new Date(s.published_at).toLocaleString('en-GB', o); } catch (e) { return s.published_at.slice(0, 10); }
  }
  function fmtLong(s) {
    var o = { timeZone: TZ, day: 'numeric', month: 'long', year: 'numeric' };
    if (s.published_precision !== 'date') { o.hour = '2-digit'; o.minute = '2-digit'; o.hourCycle = 'h23'; }
    try { return new Date(s.published_at).toLocaleString('en-GB', o) + (s.published_precision !== 'date' ? ' Doha' : ''); } catch (e) { return s.published_at; }
  }
  function detail(s) {
    var n = (s.key_insights || []).length;
    return n ? n + ' insight' + (n === 1 ? '' : 's') : (s.summary_mode === 'editor-verified' ? 'Editor-verified' : 'Source summary');
  }

  /* ---------- no pinch-zoom (owner's choice). Readers can still enlarge text with Aa → Font size. ---------- */
  ['gesturestart', 'gesturechange', 'gestureend'].forEach(function (t) { document.addEventListener(t, function (e) { e.preventDefault(); }, { passive: false }); });
  document.addEventListener('touchmove', function (e) { if (e.touches.length > 1 || (e.scale && e.scale !== 1)) e.preventDefault(); }, { passive: false });
  document.addEventListener('wheel', function (e) { if (e.ctrlKey) e.preventDefault(); }, { passive: false }); // trackpad pinch

  /* ---------- toast: one at a time, slides up from the bottom, close button, swipe down to dismiss ---------- */
  var toastEl = $('#toast'), toastT = null, toastSticky = false;
  function hideToast() {
    clearTimeout(toastT);
    if (toastEl.hidden || toastEl.classList.contains('leaving')) return;
    toastEl.classList.add('leaving');
    setTimeout(function () { toastEl.hidden = true; toastEl.classList.remove('leaving'); toastEl.style.transform = ''; }, 220);
  }
  function armToast(ms) { clearTimeout(toastT); if (!toastSticky) toastT = setTimeout(hideToast, ms); }
  function toast(msg, action, opts) {
    opts = opts || {};
    toastSticky = !!opts.sticky;
    toastEl.classList.remove('leaving'); toastEl.style.transform = '';
    toastEl.innerHTML = '<span class="toast-msg">' + esc(msg) + '</span>' +
      (action ? '<a class="toast-act" href="' + esc(action.href) + '">' + esc(action.label) + '</a>' : '') +
      '<button class="toast-x" type="button" aria-label="Dismiss notification">' + icon('close') + '</button>';
    toastEl.hidden = false; toastEl.style.animation = 'none'; void toastEl.offsetWidth; toastEl.style.animation = '';
    $('.toast-x', toastEl).addEventListener('click', hideToast);
    armToast(opts.duration || (action ? 6000 : 3200));
  }
  toastEl.addEventListener('mouseenter', function () { clearTimeout(toastT); });
  toastEl.addEventListener('mouseleave', function () { armToast(2000); });
  (function () {
    var y0 = null;
    toastEl.addEventListener('touchstart', function (e) { y0 = e.touches[0].clientY; clearTimeout(toastT); }, { passive: true });
    toastEl.addEventListener('touchmove', function (e) { if (y0 === null) return; var dy = Math.max(0, e.touches[0].clientY - y0); toastEl.style.transform = 'translate(-50%, ' + dy + 'px)'; }, { passive: true });
    toastEl.addEventListener('touchend', function (e) {
      var dy = e.changedTouches[0].clientY - (y0 === null ? 0 : y0); y0 = null;
      if (dy > 40) hideToast(); else { toastEl.style.transform = ''; armToast(2000); }
    });
  })();
  window.JARVIS = { toast: toast, hideToast: hideToast };

  /* ---------- orb reacts while the brief is read aloud (brief.js shows #pause-btn while speaking) ---------- */
  (function () {
    var pause = $('#pause-btn'); if (!pause || !window.MutationObserver) return;
    function sync() { document.documentElement.classList.toggle('speaking', !pause.hidden && pause.textContent.trim() === 'Pause'); }
    new MutationObserver(sync).observe(pause, { attributes: true, attributeFilter: ['hidden'], childList: true, characterData: true, subtree: true });
    sync();
  })();

  /* ---------- live Doha clock in the header chip ---------- */
  var clockEl = $('#live-clock');
  function tickClock() {
    if (!clockEl) return;
    try { clockEl.textContent = new Date().toLocaleString('en-GB', { timeZone: TZ, weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }) + ' · Doha'; } catch (e) { }
  }
  tickClock(); setInterval(tickClock, 30000);

  /* ---------- display settings: theme, auto, brightness, font size ---------- */
  var root = document.documentElement;
  var mq = window.matchMedia ? matchMedia('(prefers-color-scheme: dark)') : null;
  var FONT_STEPS = [0.9, 1, 1.1, 1.2, 1.32];
  var THEME_META = { light: '#FFFFFF', sepia: '#F3EBDD', dim: '#232428', dark: '#000000' };
  var display = store.get('jarvis_display', null) || {};
  if (!display.theme) { try { if (localStorage.getItem('jarvis_theme_v2') === 'dark') display.theme = 'dark'; } catch (e) { } }
  display.theme = display.theme || 'light'; display.font = display.font || 1; display.bright = display.bright || 1;
  function effectiveTheme() { return display.auto && mq ? (mq.matches ? 'dark' : 'light') : display.theme; }
  function isDark(t) { return t === 'dark' || t === 'dim'; }
  function applyDisplay() {
    var t = effectiveTheme();
    root.setAttribute('data-theme', t);
    root.style.setProperty('--read-scale', display.font);
    root.style.setProperty('--dim', (1 - display.bright).toFixed(2));
    var meta = $('meta[name="theme-color"]'); if (meta) meta.content = THEME_META[t] || THEME_META.light;
    var sw = $('#theme-btn'); if (sw) sw.setAttribute('aria-checked', String(isDark(t)));
    store.set('jarvis_display', display);
    syncDisplayCard();
  }
  if (mq && mq.addEventListener) mq.addEventListener('change', function () { if (display.auto) applyDisplay(); });
  $('#theme-btn').addEventListener('click', function () {
    var dark = !isDark(effectiveTheme());
    display.auto = false; display.theme = dark ? 'dark' : 'light'; applyDisplay();
  });

  /* ---------- header ---------- */
  var scroller = $('#scroller'), top = $('#top');
  scroller.addEventListener('scroll', function () { top.classList.toggle('condensed', scroller.scrollTop > 8); }, { passive: true });

  /* ---------- relative times (fresh editions, last 24h only) ---------- */
  function relTimes(scope) {
    if ((Date.now() - Date.parse(ED.generated_at)) > 36 * 3600e3) return;
    $$('time[data-precision="time"]', scope).forEach(function (t) {
      var mins = Math.round((Date.now() - Date.parse(t.getAttribute('datetime'))) / 60000);
      if (mins < 0 || mins > 24 * 60) return;
      if (!t.title) t.title = t.textContent;
      t.textContent = mins < 60 ? mins + 'm ago' : Math.round(mins / 60) + 'h ago';
    });
  }
  relTimes();

  /* ---------- refresh: reload interface and latest edition ---------- */
  var refreshBtn = $('#refresh-btn');
  refreshBtn.addEventListener('click', function () {
    if (refreshBtn.disabled) return;
    refreshBtn.disabled = true; refreshBtn.classList.add('spin');
    fetch(BASE + 'data/index.json?t=' + Date.now(), { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error('offline'); return r.json(); })
      .then(function () {
        try { sessionStorage.removeItem('jarvis_tab'); } catch (e) { }
        var target = new URL(BASE + 'index.html', location.href);
        target.searchParams.set('refresh', Date.now());
        location.replace(target.href);
      })
      .catch(function () { refreshBtn.disabled = false; refreshBtn.classList.remove('spin'); toast('Could not refresh. Check your connection.'); });
  });

  /* ---------- bottom tabs ---------- */
  var state = { tab: 'home', region: 'all' };
  function showTab(name) {
    state.tab = name;
    $$('.tab').forEach(function (x) { x.setAttribute('aria-pressed', String(x.dataset.tab === name)); });
    $$('[data-pane]').forEach(function (el) { el.hidden = el.dataset.pane !== name; });
    if (name === 'saved') renderSaved();
    if (name === 'explore') renderExplore();
    scroller.scrollTo({ top: 0 });
    try { sessionStorage.setItem('jarvis_tab', name); } catch (e) { }
  }
  $$('.tab').forEach(function (b) { b.addEventListener('click', function () { showTab(b.dataset.tab); }); });
  $('#search-btn').addEventListener('click', function () { showTab('explore'); setTimeout(function () { $('#explore-q').focus({ preventScroll: true }); }, 80); });

  /* ---------- home: region tabs, my topics, carousel ---------- */
  var slidesEl = $('#slides'), dotsEl = $('#pdots');
  function topics() { return store.get('jarvis_topics', []).filter(function (k) { return CATS[k]; }); }
  function matchHome(el) {
    var r = state.region, mine = topics();
    var okRegion = r === 'all' || r === 'mine' || el.dataset.region === r;
    var okTopic = r !== 'mine' || mine.indexOf(el.dataset.category) >= 0;
    return okRegion && okTopic;
  }
  function visibleSlides() { return $$('.slide', slidesEl).filter(function (s) { return !s.hidden; }); }
  function syncDots() {
    var vis = visibleSlides();
    dotsEl.innerHTML = vis.length > 1 ? vis.map(function (_, i) { return '<span class="pdot' + (i === 0 ? ' on' : '') + '"></span>'; }).join('') : '';
    onSlideScroll();
  }
  function onSlideScroll() {
    var vis = visibleSlides(), dots = $$('.pdot', dotsEl); if (!dots.length) return;
    var x = slidesEl.scrollLeft, best = 0, bestD = Infinity;
    vis.forEach(function (s, i) { var d = Math.abs(s.offsetLeft - slidesEl.offsetLeft - x); if (d < bestD) { bestD = d; best = i; } });
    if (x + slidesEl.clientWidth >= slidesEl.scrollWidth - 4) best = vis.length - 1;
    dots.forEach(function (d, i) { d.classList.toggle('on', i === best); });
  }
  slidesEl.addEventListener('scroll', onSlideScroll, { passive: true });
  function applyHome() {
    var r = state.region, any = false;
    $$('[data-region-tab]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.regionTab === r)); });
    $$('.slide', slidesEl).forEach(function (s) { s.hidden = !matchHome(s); if (!s.hidden) any = true; });
    $('#carousel').hidden = !visibleSlides().length;
    $$('[data-region-section]').forEach(function (sec) {
      var region = sec.dataset.regionSection;
      var rows = $$('.row', sec), shown = 0;
      rows.forEach(function (row) { row.hidden = !matchHome(row); if (!row.hidden) shown++; });
      var soft = $('.empty', sec);
      if (soft) soft.hidden = r === 'mine';
      sec.hidden = (r === 'global' || r === 'india') ? region !== r : (r === 'mine' && !shown);
      if (shown) any = true;
    });
    $('#mine-empty').hidden = !(r === 'mine' && !any);
    slidesEl.scrollTo({ left: 0 });
    syncDots();
  }
  $$('[data-region-tab]').forEach(function (b) { b.addEventListener('click', function () { state.region = b.dataset.regionTab; applyHome(); }); });
  function syncTopicsUI() {
    var mine = topics(), mineTab = $('[data-region-tab="mine"]');
    mineTab.hidden = !mine.length;
    if (!mine.length && state.region === 'mine') { state.region = 'all'; applyHome(); }
    $('#topic-text').textContent = mine.length
      ? 'Following ' + mine.map(function (k) { return CATS[k].label; }).join(', ') + '.'
      : 'Hey Boss, it seems like you haven’t picked any topics yet.';
    $('#topic-btn span').textContent = mine.length ? 'Edit topics' : 'Add topic';
  }

  /* ---------- rows rendered in JS (explore, saved) ---------- */
  function imgHtml(im, eager) {
    var remote = im.type === 'publisher';
    var src = remote ? im.src : BASE + im.src, fb = BASE + (im.fallback || im.src);
    return '<img src="' + esc(src) + '" alt="' + esc(im.alt || '') + '" loading="' + (eager ? 'eager' : 'lazy') + '" decoding="async"' + (remote ? ' referrerpolicy="no-referrer"' : '') +
      ' data-fallback="' + esc(fb) + '" onerror="this.onerror=null;this.src=this.dataset.fallback;var f=this.closest(\'[data-img]\');if(f)f.classList.add(\'is-fallback\')">';
  }
  function rowHtml(s) {
    var cat = CATS[s.category] || { label: '' };
    return '<article class="story row" data-id="' + esc(s.id) + '" data-region="' + esc(s.region) + '" data-category="' + esc(s.category) + '">' +
      '<figure class="thumb" data-img data-kind="' + esc(s.image.type) + '">' + imgHtml(s.image) + '</figure>' +
      '<div class="row-body"><p class="src-line">' + badge(s.source.name, 'sm') + '<span class="src-name">' + esc(s.source.name) + '</span></p>' +
      '<h3 class="row-title"><a class="story-link" href="' + esc(s.source.url) + '" target="_blank" rel="noopener">' + esc(s.headline) + '</a></h3>' +
      '<p class="row-meta"><time datetime="' + esc(s.published_at) + '" data-precision="' + esc(s.published_precision || 'time') + '">' + esc(fmtShort(s)) + '</time><span class="sep">·</span><span>' + esc(cat.label) + '</span><span class="sep">·</span><span>' + esc(detail(s)) + '</span>' +
      '<button class="save-btn" type="button" data-save="' + esc(s.id) + '" aria-pressed="false" aria-label="Save story">' + icon('saved') + '</button></p></div></article>';
  }

  /* ---------- explore: search, sources, categories ---------- */
  var ex = { q: '', src: 'all', cat: 'all' }, exBuilt = false;
  function buildExplore() {
    var counts = {}; ALL.forEach(function (s) { counts[s.source.name] = (counts[s.source.name] || 0) + 1; });
    var names = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a] || a.localeCompare(b); });
    $('#explore-sources').innerHTML = '<button class="src-btn" type="button" data-src="all" aria-pressed="true"><span class="src-ring"><span class="src-all">Discover</span></span><span class="src-lbl">All</span></button>' +
      names.map(function (n) { return '<button class="src-btn" type="button" data-src="' + esc(n) + '" aria-pressed="false"><span class="src-ring">' + badge(n, 'lg') + '</span><span class="src-lbl">' + esc(n) + '</span></button>'; }).join('');
    var cats = {}; ALL.forEach(function (s) { cats[s.category] = 1; });
    $('#explore-cats').innerHTML = '<button type="button" data-xcat="all" aria-pressed="true">All</button>' +
      Object.keys(CATS).filter(function (k) { return cats[k]; }).map(function (k) { return '<button type="button" data-xcat="' + k + '" aria-pressed="false">' + esc(CATS[k].label) + '</button>'; }).join('');
    $$('[data-src]').forEach(function (b) { b.addEventListener('click', function () { ex.src = b.dataset.src; $$('[data-src]').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); }); renderExplore(); }); });
    $$('[data-xcat]').forEach(function (b) { b.addEventListener('click', function () { ex.cat = b.dataset.xcat; $$('[data-xcat]').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); }); renderExplore(); }); });
    $('#explore-q').addEventListener('input', function (e) { ex.q = e.target.value.trim().toLowerCase(); renderExplore(); });
    exBuilt = true;
  }
  function renderExplore() {
    if (!exBuilt) buildExplore();
    var words = ex.q.split(/\s+/).filter(Boolean);
    var list = ALL.filter(function (s) {
      if (ex.src !== 'all' && s.source.name !== ex.src) return false;
      if (ex.cat !== 'all' && s.category !== ex.cat) return false;
      var hay = [s.headline, s.summary, s.source.name, (CATS[s.category] || {}).label, s.region, (s.tags || []).join(' ')].join(' ').toLowerCase();
      return words.every(function (w) { return hay.indexOf(w) >= 0; });
    });
    var wrap = $('#explore-list');
    wrap.innerHTML = list.map(rowHtml).join('');
    $('#explore-empty').hidden = list.length > 0;
    syncSaveButtons(); relTimes(wrap);
  }

  /* ---------- saved stories (this browser only) ---------- */
  function savedList() { return store.get('jarvis_saved', []); }
  function toggleSave(id) {
    var list = savedList(), s = STORIES[id];
    var i = list.findIndex(function (x) { return x.id === id; });
    if (i >= 0) { list.splice(i, 1); toast('Removed from Saved'); }
    else if (s) {
      list.unshift({ id: s.id, headline: s.headline, summary: s.summary, url: s.source.url, source: s.source.name, category: s.category,
        region: s.region, published_at: s.published_at, published_precision: s.published_precision, edition: ED.edition_date,
        image: { type: s.image.type, src: s.image.src, fallback: s.image.fallback, alt: s.image.alt } });
      toast('Saved on this device');
    }
    store.set('jarvis_saved', list.slice(0, 200));
    syncSaveButtons();
    if (state.tab === 'saved') renderSaved();
  }
  function syncSaveButtons() {
    var ids = {}; savedList().forEach(function (s) { ids[s.id] = 1; });
    $$('[data-save]').forEach(function (b) {
      var on = !!ids[b.dataset.save]; b.setAttribute('aria-pressed', String(on)); b.setAttribute('aria-label', on ? 'Remove from saved' : 'Save story');
      var lbl = $('.save-lbl', b); if (lbl) lbl.textContent = on ? 'Saved' : 'Save';
    });
  }
  function renderSaved() {
    var list = savedList(), wrap = $('#saved-list');
    $('#saved-empty').hidden = list.length > 0;
    wrap.innerHTML = list.map(function (x) {
      var s = STORIES[x.id];
      if (s) return rowHtml(s);
      var cat = CATS[x.category] || { label: '' };
      var thumb = x.image ? '<figure class="thumb" data-img data-kind="' + esc(x.image.type) + '">' + imgHtml(x.image) + '</figure>' : '<figure class="thumb"></figure>';
      return '<article class="story row" data-saved="' + esc(x.id) + '">' + thumb +
        '<div class="row-body"><p class="src-line">' + badge(x.source, 'sm') + '<span class="src-name">' + esc(x.source) + '</span></p>' +
        '<h3 class="row-title"><a class="story-link" href="' + BASE + 'news/' + esc(x.edition) + '.html#s-' + esc(x.id) + '">' + esc(x.headline) + '</a></h3>' +
        '<p class="row-meta"><span>Edition ' + esc(x.edition) + '</span><span class="sep">·</span><span>' + esc(cat.label) + '</span>' +
        '<button class="save-btn" type="button" data-save="' + esc(x.id) + '" aria-pressed="true" aria-label="Remove from saved">' + icon('saved') + '</button></p></div></article>';
    }).join('');
    syncSaveButtons();
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-save]');
    if (!b) return;
    e.preventDefault(); e.stopPropagation();
    var id = b.dataset.save;
    if (!STORIES[id]) { store.set('jarvis_saved', savedList().filter(function (x) { return x.id !== id; })); toast('Removed from Saved'); renderSaved(); return; }
    toggleSave(id);
  }, true);
  syncSaveButtons();

  /* ---------- floating cards (display, topics, about) ---------- */
  var floatEl = null, floatFocus = null;
  function openFloat(title, inner, wide) {
    closeFloat(true);
    floatFocus = document.activeElement;
    floatEl = document.createElement('div');
    floatEl.className = 'float-wrap';
    floatEl.innerHTML = '<div class="float' + (wide ? ' wide' : '') + '" role="dialog" aria-modal="true" aria-label="' + esc(title) + '">' +
      '<div class="float-head"><p class="float-title">' + esc(title) + '</p><button class="round-btn" type="button" data-fclose aria-label="Close">' + icon('close') + '</button></div>' + inner + '</div>';
    document.body.appendChild(floatEl);
    floatEl.addEventListener('click', function (e) { if (e.target === floatEl || e.target.closest('[data-fclose]')) closeFloat(); });
    $('[data-fclose]', floatEl).focus({ preventScroll: true });
    return floatEl;
  }
  function closeFloat(instant) {
    if (!floatEl) return;
    var el = floatEl; floatEl = null;
    if (instant) el.remove(); else { el.classList.add('out'); setTimeout(function () { el.remove(); }, 160); }
    if (floatFocus && floatFocus.focus) floatFocus.focus({ preventScroll: true });
  }

  function setRangeFill(r) { var p = (r.value - r.min) / (r.max - r.min) * 100; r.style.setProperty('--p', p + '%'); }
  function syncDisplayCard() {
    if (!floatEl || !$('#d-bright', floatEl)) return;
    var t = effectiveTheme();
    var b = $('#d-bright', floatEl); b.value = Math.round(display.bright * 100); setRangeFill(b);
    var f = $('#d-font', floatEl); f.value = Math.max(0, FONT_STEPS.indexOf(display.font)); setRangeFill(f);
    $('#d-dark', floatEl).setAttribute('aria-checked', String(isDark(t)));
    $('#d-auto', floatEl).setAttribute('aria-checked', String(!!display.auto));
    $$('[data-sw]', floatEl).forEach(function (s) { s.setAttribute('aria-pressed', String(!display.auto && s.dataset.sw === display.theme)); });
  }
  function openDisplay() {
    var sw = [['light', '#FFFFFF', 'White'], ['sepia', '#E7CFA8', 'Sepia'], ['dim', '#3E3F44', 'Graphite'], ['dark', '#050505', 'Black']];
    var el = openFloat('Display',
      '<div class="opt"><span class="opt-lbl">Brightness</span><div class="slider-row">' + icon('sunSm') + '<input id="d-bright" type="range" min="50" max="100" step="1" aria-label="Brightness">' + icon('sun', 'big') + '</div></div>' +
      '<div class="opt-row"><span class="opt-lbl">Reading theme</span><button class="switch" id="d-dark" type="button" role="switch" aria-label="Dark reading theme"><span class="knob"></span></button></div>' +
      '<div class="opt"><span class="opt-lbl">Font size</span><div class="slider-row"><span class="a-sm">A</span><input id="d-font" type="range" min="0" max="4" step="1" aria-label="Font size"><span class="a-lg">A</span></div></div>' +
      '<div class="opt-row"><span class="opt-lbl">Theme automate</span><button class="switch" id="d-auto" type="button" role="switch" aria-label="Follow device theme"><span class="knob"></span></button></div>' +
      '<div class="opt"><span class="opt-lbl">Theme color</span><div class="swatches">' +
      sw.map(function (x) { return '<button class="swatch" type="button" data-sw="' + x[0] + '" style="--sw:' + x[1] + '" aria-label="' + x[2] + ' theme"></button>'; }).join('') + '</div></div>');
    syncDisplayCard();
    $('#d-bright', el).addEventListener('input', function (e) { display.bright = +e.target.value / 100; applyDisplay(); });
    $('#d-font', el).addEventListener('input', function (e) { display.font = FONT_STEPS[+e.target.value]; applyDisplay(); });
    $('#d-dark', el).addEventListener('click', function () {
      var dark = !isDark(effectiveTheme());
      display.auto = false; display.theme = dark ? (display.theme === 'dim' ? 'dim' : 'dark') : (display.theme === 'sepia' ? 'sepia' : 'light'); applyDisplay();
    });
    $('#d-auto', el).addEventListener('click', function () { display.auto = !display.auto; applyDisplay(); });
    $$('[data-sw]', el).forEach(function (b) { b.addEventListener('click', function () { display.auto = false; display.theme = b.dataset.sw; applyDisplay(); }); });
  }
  $('#display-btn').addEventListener('click', openDisplay);

  function openTopics() {
    var mine = topics();
    var el = openFloat('Your topics',
      '<p class="hint">Pick what you care about. “My topics” on Home then shows only these. Saved on this device.</p>' +
      '<div class="topic-grid">' + Object.keys(CATS).map(function (k) {
        return '<button class="topic-chip" type="button" data-topic="' + k + '" aria-pressed="' + (mine.indexOf(k) >= 0) + '"><span class="dot" style="--c:' + esc(CATS[k].color) + '"></span>' + esc(CATS[k].label) + '</button>';
      }).join('') + '</div><button class="pill-btn primary" type="button" id="topics-save">Save topics</button>');
    $$('[data-topic]', el).forEach(function (b) { b.addEventListener('click', function () { b.setAttribute('aria-pressed', String(b.getAttribute('aria-pressed') !== 'true')); }); });
    $('#topics-save', el).addEventListener('click', function () {
      var pick = $$('[data-topic]', el).filter(function (b) { return b.getAttribute('aria-pressed') === 'true'; }).map(function (b) { return b.dataset.topic; });
      store.set('jarvis_topics', pick); syncTopicsUI(); closeFloat();
      toast(pick.length ? 'Topics saved. See “My topics” on Home.' : 'Topics cleared');
    });
  }
  $('#topic-btn').addEventListener('click', openTopics);

  function openAbout() {
    var sumOn = ED.summarizer && ED.summarizer.enabled;
    var kinds = {}; ALL.forEach(function (s) { kinds[s.image.type] = (kinds[s.image.type] || 0) + 1; });
    var names = { generated: 'JARVIS covers', publisher: 'from publishers', 'publisher-copy': 'publisher copies', stock: 'illustrative stock', ai: 'AI-generated' };
    var rels = (RELEASES.releases || []).map(function (r) {
      return '<li><div class="rel-head"><span class="rel-ver">v' + esc(r.version) + '</span><span class="rel-name">' + esc(r.name || '') + '</span><span class="hint">' + esc(r.date) + '</span></div>' +
        '<ul class="rel-notes">' + (r.notes || []).map(function (n) { return '<li>' + esc(n) + '</li>'; }).join('') + '</ul></li>';
    }).join('');
    openFloat('About', '<div class="about-head">' + markSvg() + '<div><p class="about-name">JARVIS</p><p class="hint">AI NEWS · <span class="ver-pill">v' + esc(RELEASES.current) + '</span></p></div></div>' +
      '<p>' + esc(SITE.signature) + '. ' + esc(SITE.agent_credit) + '</p>' +
      '<dl class="kv"><dt>Edition</dt><dd>Nº ' + String(ED.edition_number).padStart(3, '0') + ' · ' + esc(ED.edition_date) + '</dd>' +
      '<dt>Generated</dt><dd>' + esc(new Date(ED.generated_at).toLocaleString('en-GB', { timeZone: TZ, day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })) + ' Doha</dd>' +
      '<dt>Next edition</dt><dd>' + esc(SCHED.local_time || '07:30') + ' Doha · in ' + fmtDuration(minutesToNextEdition()) + '</dd>' +
      (ED.produced_by ? '<dt>Produced by</dt><dd>' + esc(ED.produced_by.agent) + ' · ' + esc(ED.produced_by.method) + '</dd>' : '') +
      '<dt>Summaries</dt><dd>' + (ED.edition_type !== 'daily' ? 'Hand-verified' : sumOn ? 'AI, grounded in source' : 'Publisher’s own') + '</dd>' +
      '<dt>Images</dt><dd>' + esc(Object.keys(kinds).map(function (k) { return kinds[k] + ' ' + (names[k] || k); }).join(' · ')) + '</dd>' +
      '<dt>Edition log</dt><dd><a href="https://github.com/tktarun03/jarvis-ai-news/commits/main/data/' + esc(ED.edition_date) + '.json" target="_blank" rel="noopener">Change history</a></dd></dl>' +
      '<p class="r-h">Version history</p><ol class="timeline">' + rels + '</ol>', true);
  }
  $('#about-btn').addEventListener('click', openAbout);

  /* ---------- reader ---------- */
  var sheetRoot = $('#sheet-root'), readerFocus = null;
  function imageCredit(im) {
    if (im.type === 'ai') return '<p class="img-credit">AI-generated image of a generic scene, not from the event (' + esc(im.model || 'image model') + ').</p>';
    if (im.type === 'stock') return '<p class="img-credit">Illustrative image, not from the event. ' + (im.credit_url ? '<a href="' + esc(im.credit_url) + '" target="_blank" rel="noopener">' + esc(im.credit) + '</a>' : esc(im.credit)) + '</p>';
    if (im.type === 'publisher' || im.type === 'publisher-copy') return '<p class="img-credit">' + (im.credit_url ? '<a href="' + esc(im.credit_url) + '" target="_blank" rel="noopener">' + esc(im.credit) + '</a>' : esc(im.credit)) + '</p>';
    return '<p class="img-credit">Cover artwork generated by JARVIS.</p>';
  }
  function openStory(id, push) {
    var s = STORIES[id]; if (!s) return;
    readerFocus = document.activeElement;
    var cat = CATS[s.category], im = s.image;
    var chip = im.type !== 'generated' ? '<span class="credit">' + esc(im.credit) + '</span>' : '';
    var insights = (s.key_insights || []).length
      ? '<ol class="insights">' + s.key_insights.map(function (x, i) { return '<li><span class="n">' + (i + 1) + '</span><span>' + esc(x) + '</span></li>'; }).join('') + '</ol>'
      : '<p class="unavailable">Key insights are only published when they can be checked against the publisher’s text. Read the source for the full reporting.</p>';
    var impact = s.impact ? '<p class="impact">' + esc(s.impact) + '</p>' : '<p class="unavailable">No impact statement: the source did not support one.</p>';
    var also = (s.corroboration || []).length ? '<div class="r-block"><p class="r-h">Also reported by</p><div class="also">' +
      s.corroboration.map(function (c) { return '<a href="' + esc(c.url) + '" target="_blank" rel="noopener">' + esc(c.name) + '</a>'; }).join('') + '</div></div>' : '';
    var mode = { 'ai-grounded': 'AI summary, checked against publisher text', 'editor-verified': 'Hand-verified by the editor', 'publisher-blurb': 'Publisher’s own summary' }[s.summary_mode] || s.summary_mode;
    sheetRoot.innerHTML = '<div class="reader-wrap"><div class="reader" role="dialog" aria-modal="true" aria-labelledby="r-title">' +
      '<div class="reader-top" id="reader-top"><button class="round-btn" type="button" data-rclose aria-label="Back">' + icon('back') + '</button><span class="r-brand">JARVIS</span>' +
      '<button class="round-btn" type="button" data-display aria-label="Display settings">Aa</button><button class="round-btn" type="button" data-share aria-label="Share">' + icon('share') + '</button></div>' +
      '<div class="reader-scroll" id="reader-scroll">' +
      '<div class="reader-hero" data-img data-kind="' + esc(im.type) + '">' + imgHtml(im, true) + chip + '</div>' +
      '<article class="reader-panel">' +
      '<p class="r-kicker"><span class="dot" style="--c:' + esc(cat.color) + '"></span>' + esc(cat.label) + ' · ' + (s.region === 'india' ? 'India' : 'Global') + '</p>' +
      '<h2 class="r-title" id="r-title">' + esc(s.headline) + '</h2>' +
      '<div class="r-byline">' + badge(s.source.name) + '<span class="src-name">' + esc(s.source.name) + '</span><span class="hint">' + esc(fmtLong(s)) + '</span></div>' +
      '<p class="r-text">' + esc(s.summary) + '</p>' +
      '<div class="r-block"><p class="r-h">Key insights</p>' + insights + '</div>' +
      '<div class="r-block"><p class="r-h">Real-world impact</p>' + impact + '</div>' + also +
      '<div class="r-block"><p class="r-h">How this was checked</p><ul class="checks">' + (s.verification.checks || []).map(function (c) { return '<li>' + esc(c) + '</li>'; }).join('') + '<li>' + esc(mode) + '</li></ul>' + imageCredit(im) + '</div>' +
      '</article></div>' +
      '<div class="reader-bar"><button class="save-pill" type="button" data-save="' + esc(s.id) + '" aria-pressed="false"><span class="circ">' + icon('saved') + '</span><span class="save-lbl">Save</span></button>' +
      '<a class="pill-btn primary read-src" href="' + esc(s.source.url) + '" target="_blank" rel="noopener">' + icon('external') + '<span>Read at ' + esc(s.source.name) + '</span></a>' +
      '<div class="ring" aria-label="Reading progress"><svg viewBox="0 0 46 46"><circle class="rt" cx="23" cy="23" r="20"/><circle class="rf" cx="23" cy="23" r="20"/></svg><span id="ring-n">0</span></div></div>' +
      '</div></div>';
    var wrap = $('.reader-wrap', sheetRoot), sc = $('#reader-scroll'), bar = $('#reader-top'), rf = $('.rf', wrap), rn = $('#ring-n');
    function progress() {
      var max = sc.scrollHeight - sc.clientHeight, p = max > 0 ? Math.min(1, sc.scrollTop / max) : 1;
      rf.style.strokeDashoffset = (125.7 * (1 - p)).toFixed(1); rn.textContent = Math.round(p * 100);
      bar.classList.toggle('solid', sc.scrollTop > $('.reader-hero', wrap).offsetHeight - 70);
    }
    sc.addEventListener('scroll', progress, { passive: true }); progress();
    wrap.addEventListener('click', function (e) { if (e.target === wrap || e.target.closest('[data-rclose]')) closeStory(); });
    $('[data-display]', wrap).addEventListener('click', openDisplay);
    $('[data-share]', wrap).addEventListener('click', function () { share(s); });
    syncSaveButtons();
    $('[data-rclose]', wrap).focus({ preventScroll: true });
    if (push) { try { history.pushState({ story: id }, '', '#s-' + id); } catch (e) { } }
  }
  function closeStory(fromPop) {
    var wrap = $('.reader-wrap', sheetRoot); if (!wrap) return;
    wrap.classList.add('out');
    setTimeout(function () { sheetRoot.innerHTML = ''; if (readerFocus && readerFocus.focus) readerFocus.focus({ preventScroll: true }); }, 190);
    if (!fromPop && location.hash.indexOf('#s-') === 0) { try { history.back(); } catch (e) { } }
  }
  /* ---------- share: per-story link (news/DATE/ID.html carries the preview) + editable message ---------- */
  function shareUrl(s) { return (SITE.base_url || '') + 'news/' + ED.edition_date + '/' + s.id + '.html'; }
  function clip(t, n) { t = String(t || '').replace(/\s+/g, ' ').trim(); if (t.length <= n) return t; t = t.slice(0, n - 1); return t.slice(0, Math.max(t.lastIndexOf(' '), n * .6)).replace(/[,;:—-]+$/, '') + '…'; }
  function sentences(t, n) { // whole sentences up to n chars; the first sentence always survives
    var parts = String(t || '').replace(/\s+/g, ' ').trim().match(/[^.!?]+[.!?]+(?=\s|$)|[^.!?]+$/g) || [], out = '';
    for (var i = 0; i < parts.length; i++) { var next = (out + ' ' + parts[i].trim()).trim(); if (out && next.length > n) break; out = next; }
    return clip(out, n + 120);
  }
  function shareMessage(s, note) {
    var lines = [];
    if (note) lines.push(note.trim(), '');
    lines.push('*' + s.headline + '*', '', sentences(s.summary, 300));
    if (s.impact) lines.push('', '_Why it matters:_ ' + sentences(s.impact, 220));
    lines.push('', 'Source: ' + s.source.name, shareUrl(s), '', '— via ' + (SITE.name || 'JARVIS AI NEWS'));
    return lines.join('\n');
  }
  function copyText(text, done) {
    function fallback() {
      var ta = document.createElement('textarea'); ta.value = text; ta.setAttribute('readonly', ''); ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0;font-size:16px';
      document.body.appendChild(ta); ta.select(); var ok = false; try { ok = document.execCommand('copy'); } catch (e) { } ta.remove();
      toast(ok ? done : 'Could not copy. Long-press to copy instead.');
    }
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(function () { toast(done); }, fallback); else fallback();
  }
  function share(s) {
    var el = openFloat('Share story',
      '<div class="share-prev"><p class="share-k">' + esc(CATS[s.category].label) + ' · ' + esc(s.source.name) + '</p><p class="share-h">' + esc(s.headline) + '</p><p class="share-u">' + esc(shareUrl(s).replace(/^https?:\/\//, '')) + '</p></div>' +
      '<label class="share-note"><span class="opt-lbl">Your note <span class="hint">(optional, added above the story)</span></span>' +
      '<textarea id="sh-note" rows="2" maxlength="400" placeholder="e.g. Saw this and thought of you"></textarea></label>' +
      '<div class="share-acts">' +
      '<a class="pill-btn wa" id="sh-wa" href="#" target="_blank" rel="noopener">' + icon('chat') + '<span>WhatsApp</span></a>' +
      '<button class="pill-btn' + (navigator.share ? '' : ' solo') + '" type="button" id="sh-copy">' + icon('copy') + '<span>Copy message</span></button>' +
      (navigator.share ? '<button class="pill-btn" type="button" id="sh-more">' + icon('more') + '<span>More apps</span></button>' : '') +
      '<button class="pill-btn ghost" type="button" id="sh-link">' + icon('external') + '<span>Copy link only</span></button>' +
      '</div>');
    var note = $('#sh-note', el), wa = $('#sh-wa', el);
    function msg() { return shareMessage(s, note.value); }
    function syncWa() { wa.href = 'https://wa.me/?text=' + encodeURIComponent(msg()); }
    note.addEventListener('input', syncWa);
    syncWa();
    wa.addEventListener('click', function () { setTimeout(closeFloat, 300); });
    $('#sh-copy', el).addEventListener('click', function () { copyText(msg(), 'Message copied. Paste it in WhatsApp.'); });
    $('#sh-link', el).addEventListener('click', function () { copyText(shareUrl(s), 'Link copied'); });
    if ($('#sh-more', el)) $('#sh-more', el).addEventListener('click', function () {
      // Link inside the text: some apps (WhatsApp on iOS) drop `text` when `url` is passed separately.
      navigator.share({ title: s.headline, text: msg() }).then(function () { closeFloat(); }, function () { });
    });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-qshare]');
    if (!b) return;
    e.preventDefault(); e.stopPropagation();
    if (STORIES[b.dataset.qshare]) share(STORIES[b.dataset.qshare]);
  }, true);
  document.addEventListener('click', function (e) {
    var card = e.target.closest('.story[data-id]');
    if (!card || !STORIES[card.dataset.id]) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) return;
    e.preventDefault();
    openStory(card.dataset.id, true);
  });
  document.addEventListener('keydown', function (e) { if (e.key !== 'Escape') return; if (floatEl) closeFloat(); else if ($('.reader-wrap', sheetRoot)) closeStory(); else hideToast(); });
  window.addEventListener('popstate', function () {
    var m = location.hash.match(/^#s-([0-9a-f]{12})$/);
    if (m) openStory(m[1], false); else closeStory(true);
  });

  /* ---------- archive ---------- */
  function renderArchive(idx) {
    if (!idx || !idx.editions) return;
    $('#archive-list').innerHTML = idx.editions.map(function (e) {
      var d = new Date(e.date + 'T12:00:00Z');
      return '<a class="arow' + (e.date === ED.edition_date ? ' current' : '') + '" href="' + BASE + 'news/' + e.date + '.html">' +
        '<span class="date-tile"><span class="dt-day">' + Number(e.date.slice(8)) + '</span><span class="dt-mon">' + d.toLocaleDateString('en-GB', { month: 'short', timeZone: 'UTC' }) + '</span></span>' +
        '<span class="grow"><span class="arow-title">' + esc(e.top_headline || ('Edition ' + e.date)) + '</span>' +
        '<span class="hint">Nº ' + String(e.number).padStart(3, '0') + ' · ' + e.counts.global + ' global · ' + e.counts.india + ' India</span></span></a>';
    }).join('');
  }
  fetch(BASE + 'data/index.json', { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).then(renderArchive).catch(function () { });

  /* ---------- start ---------- */
  applyDisplay();
  syncTopicsUI();
  applyHome();
  try { var t = sessionStorage.getItem('jarvis_tab'); if (t && t !== 'home' && $('.tab[data-tab="' + t + '"]')) showTab(t); } catch (e) { }
  var initial = location.hash.match(/^#s-([0-9a-f]{12})$/);
  if (initial && STORIES[initial[1]]) {
    try { history.replaceState(null, '', location.pathname + location.search); history.pushState({ story: initial[1] }, '', '#s-' + initial[1]); } catch (e) { }
    openStory(initial[1], false);
  }
})();
