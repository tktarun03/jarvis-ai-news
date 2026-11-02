/* JARVIS AI NEWS — progressive enhancement for the static edition pages.
   Everything here is optional: without JS each card links straight to its publisher. */
(function () {
  'use strict';

  var dataEl = document.getElementById('edition-data');
  if (!dataEl) return;
  var DATA = JSON.parse(dataEl.textContent);
  var ED = DATA.edition, CATS = DATA.categories, BASE = DATA.base || '';
  var STORIES = {};
  ['global', 'india'].forEach(function (r) { (ED.stories[r] || []).forEach(function (s) { STORIES[s.id] = s; }); });

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
  var store = {
    get: function (k, d) { try { var v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { } }
  };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function icon(name) {
    var p = {
      close: '<path d="M6 6l12 12M18 6L6 18"/>',
      share: '<path d="M12 15V3.5M7.5 8 12 3.5 16.5 8"/><path d="M5 12.5V19a1.5 1.5 0 0 0 1.5 1.5h11A1.5 1.5 0 0 0 19 19v-6.5"/>',
      external: '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v4.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6H10"/>',
      saved: '<path d="M6.5 3.5h11a1 1 0 0 1 1 1V21l-6.5-4.5L5.5 21V4.5a1 1 0 0 1 1-1z"/>'
    }[name];
    return '<svg class="ic" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' + p + '</svg>';
  }

  /* ---- splash: once per session, never blocks reading ---- */
  var splash = $('#splash');
  var seen = false; try { seen = sessionStorage.getItem('jarvis_seen') === '1'; sessionStorage.setItem('jarvis_seen', '1'); } catch (e) { }
  if (splash) { if (seen) splash.remove(); else setTimeout(function () { splash.classList.add('out'); setTimeout(function () { splash.remove(); }, 400); }, 450); }

  /* ---- toast ---- */
  var toastEl = $('#toast'), toastT;
  function toast(msg) { toastEl.textContent = msg; toastEl.hidden = false; toastEl.style.animation = 'none'; void toastEl.offsetWidth; toastEl.style.animation = ''; clearTimeout(toastT); toastT = setTimeout(function () { toastEl.hidden = true; }, 2200); }

  /* ---- theme: auto -> light -> dark ---- */
  var root = document.documentElement;
  $('#theme-btn').addEventListener('click', function () {
    var cur = root.getAttribute('data-theme') || 'auto';
    var next = cur === 'auto' ? 'light' : cur === 'light' ? 'dark' : 'auto';
    if (next === 'auto') { root.removeAttribute('data-theme'); try { localStorage.removeItem('jarvis_theme'); } catch (e) { } }
    else { root.setAttribute('data-theme', next); try { localStorage.setItem('jarvis_theme', next); } catch (e) { } }
    toast('Theme: ' + (next === 'auto' ? 'match device' : next));
  });

  /* ---- relative times for a fresh edition ---- */
  var fresh = (Date.now() - Date.parse(ED.generated_at)) < 36 * 3600e3;
  if (fresh) {
    $$('time[data-precision="time"]').forEach(function (t) {
      var mins = Math.round((Date.now() - Date.parse(t.getAttribute('datetime'))) / 60000);
      if (mins < 0 || mins > 24 * 60) return;
      t.title = t.textContent;
      t.textContent = mins < 60 ? mins + 'm ago' : Math.round(mins / 60) + 'h ago';
    });
  }

  /* ---- tabs and category filter ---- */
  var state = { tab: 'today', cat: 'all' };
  var scroller = $('#scroller');
  function applyFilter() {
    var newsTab = state.tab === 'today' || state.tab === 'global' || state.tab === 'india';
    $$('[data-pane]').forEach(function (el) { el.hidden = el.getAttribute('data-pane') !== (newsTab ? 'news' : state.tab); });
    if (!newsTab) return;
    $$('[data-region-section]').forEach(function (sec) {
      var region = sec.getAttribute('data-region-section');
      var show = state.tab === 'today' || state.tab === region;
      var shown = 0;
      $$('.story', sec).forEach(function (card) {
        var ok = state.cat === 'all' || card.getAttribute('data-category') === state.cat;
        card.hidden = !ok; if (ok) shown++;
      });
      var empty = $('.filter-empty', sec);
      if (!shown && $$('.story', sec).length) {
        if (!empty) { empty = document.createElement('p'); empty.className = 'empty filter-empty'; $('.stories', sec).after(empty); }
        empty.textContent = 'No ' + (CATS[state.cat] ? CATS[state.cat].label.toLowerCase() : '') + ' stories in this section today.';
        empty.hidden = false;
      } else if (empty) { empty.hidden = true; }
      sec.hidden = !show;
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
  try { var t = sessionStorage.getItem('jarvis_tab'); if (t && t !== 'today') { var tb = $('.tab[data-tab="' + t + '"]'); if (tb) tb.click(); } } catch (e) { }

  /* ---- saved stories (this browser only) ---- */
  function savedList() { return store.get('jarvis_saved', []); }
  function isSaved(id) { return savedList().some(function (s) { return s.id === id; }); }
  function toggleSave(id) {
    var list = savedList(), s = STORIES[id];
    var i = list.findIndex(function (x) { return x.id === id; });
    if (i >= 0) { list.splice(i, 1); toast('Removed from Saved'); }
    else if (s) {
      list.unshift({ id: s.id, headline: s.headline, summary: s.summary, url: s.source.url, source: s.source.name,
        category: s.category, published_at: s.published_at, edition: ED.edition_date, cover: s.image.src });
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
      return '<article class="story" data-id="' + esc(s.id) + '"><div class="story-body">' +
        '<p class="meta"><span class="dot" style="--c:' + esc(cat.color) + '"></span><span>' + esc(cat.label) + '</span><span class="sep">·</span><span>' + esc(s.source) + '</span><span class="sep">·</span><span>Edition ' + esc(s.edition) + '</span></p>' +
        '<h3 class="story-title"><a class="story-link" href="' + BASE + 'news/' + esc(s.edition) + '.html#s-' + esc(s.id) + '">' + esc(s.headline) + '</a></h3>' +
        '<p class="story-sum">' + esc(s.summary) + '</p>' +
        '<div class="story-foot"><span class="hint">' + esc(new Date(s.published_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })) + '</span>' +
        '<button class="save-btn" type="button" data-unsave="' + esc(s.id) + '" aria-pressed="true" aria-label="Remove from saved">' + icon('saved') + '</button></div></div></article>';
    }).join('');
    $$('[data-unsave]', wrap).forEach(function (b) {
      b.addEventListener('click', function (e) {
        e.stopPropagation();
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

  /* ---- story sheet ---- */
  var sheetRoot = $('#sheet-root'), lastFocus = null;
  function fmtWhen(s) {
    var d = new Date(s.published_at);
    var opts = { timeZone: ED.timezone || 'Asia/Qatar', day: 'numeric', month: 'long', year: 'numeric' };
    if (s.published_precision !== 'date') { opts.hour = '2-digit'; opts.minute = '2-digit'; }
    try { return d.toLocaleString('en-GB', opts) + (s.published_precision !== 'date' ? ' Doha' : ''); } catch (e) { return s.published_at; }
  }
  function openStory(id, push) {
    var s = STORIES[id]; if (!s) return;
    lastFocus = document.activeElement;
    var cat = CATS[s.category];
    var insights = (s.key_insights || []).length
      ? '<ol class="insights">' + s.key_insights.map(function (x, i) { return '<li><span class="n">0' + (i + 1) + '</span><span>' + esc(x) + '</span></li>'; }).join('') + '</ol>'
      : '<p class="unavailable">Key insights are only published when they can be checked against the publisher\'s text. This story carries the publisher\'s own summary.</p>';
    var impact = s.impact ? '<p class="impact">' + esc(s.impact) + '</p>'
      : '<p class="unavailable">No impact statement: the source did not support one.</p>';
    var also = (s.corroboration || []).length
      ? '<div class="block"><p class="eyebrow">Also reported by</p><div class="also">' + s.corroboration.map(function (c) { return '<a href="' + esc(c.url) + '" target="_blank" rel="noopener">' + esc(c.name) + '</a>'; }).join('') + '</div></div>' : '';
    var modeLabel = { 'ai-grounded': 'AI summary, checked against publisher text', 'editor-verified': 'Hand-verified by the editor', 'publisher-blurb': "Publisher's own summary" }[s.summary_mode] || s.summary_mode;
    var html = '<div class="sheet-wrap" role="dialog" aria-modal="true" aria-labelledby="sheet-title">' +
      '<div class="sheet"><div class="sheet-top" style="position:relative"><span class="grab"></span>' +
      '<p class="meta"><span class="dot" style="--c:' + esc(cat.color) + '"></span><span>' + esc(cat.label) + '</span><span class="sep">·</span><span>' + (s.region === 'india' ? 'India' : 'Global') + '</span></p>' +
      '<button class="icon-btn" type="button" data-close aria-label="Close">' + icon('close') + '</button></div>' +
      '<div class="sheet-body">' +
      '<div class="sheet-cover"><img src="' + BASE + esc(s.image.src) + '" alt="' + esc(s.image.alt) + '" width="1200" height="675"></div>' +
      '<h2 class="sheet-title" id="sheet-title">' + esc(s.headline) + '</h2>' +
      '<p class="hint">' + esc(s.source.name) + ' · ' + esc(fmtWhen(s)) + '</p>' +
      '<p class="sheet-sum">' + esc(s.summary) + '</p>' +
      '<div class="block"><p class="eyebrow">Key insights</p>' + insights + '</div>' +
      '<div class="block"><p class="eyebrow">Real-world impact</p>' + impact + '</div>' +
      also +
      '<div class="actions"><a class="btn grow-1" href="' + esc(s.source.url) + '" target="_blank" rel="noopener">' + icon('external') + 'Read at ' + esc(s.source.name) + '</a>' +
      '<button class="btn ghost" type="button" data-share>' + icon('share') + 'Share</button>' +
      '<button class="btn ghost" type="button" data-save="' + esc(s.id) + '" aria-pressed="false">' + icon('saved') + 'Save</button></div>' +
      '<div class="block"><p class="eyebrow">How this was checked</p><ul class="checks">' +
      (s.verification.checks || []).map(function (c) { return '<li>' + esc(c) + '</li>'; }).join('') +
      '<li>' + esc(modeLabel) + '</li></ul></div>' +
      '</div></div></div>';
    sheetRoot.innerHTML = html;
    syncSaveButtons();
    var wrap = $('.sheet-wrap', sheetRoot), body = $('.sheet-body', sheetRoot), top = $('.sheet-top', sheetRoot);
    body.addEventListener('scroll', function () { top.classList.toggle('scrolled', body.scrollTop > 4); });
    wrap.addEventListener('click', function (e) { if (e.target === wrap || e.target.closest('[data-close]')) closeStory(); });
    $('[data-share]', wrap).addEventListener('click', function () { share(s); });
    $('[data-close]', wrap).focus();
    if (push) { try { history.pushState({ story: id }, '', '#s-' + id); } catch (e) { } }
  }
  function closeStory(fromPop) {
    var wrap = $('.sheet-wrap', sheetRoot); if (!wrap) return;
    wrap.classList.add('out');
    setTimeout(function () { sheetRoot.innerHTML = ''; if (lastFocus && lastFocus.focus) lastFocus.focus(); }, 190);
    if (!fromPop && location.hash.indexOf('#s-') === 0) { try { history.back(); } catch (e) { } }
  }
  function share(s) {
    var url = location.href.split('#')[0] + '#s-' + s.id;
    if (navigator.share) { navigator.share({ title: s.headline, text: s.summary, url: url }).catch(function () { }); return; }
    if (navigator.clipboard) { navigator.clipboard.writeText(url).then(function () { toast('Link copied'); }, function () { toast(url); }); }
    else toast(url);
  }
  document.addEventListener('click', function (e) {
    var card = e.target.closest('.story[data-id]');
    if (!card || !STORIES[card.getAttribute('data-id')]) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) return; // let power users open the source
    e.preventDefault();
    openStory(card.getAttribute('data-id'), true);
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeStory(); });
  window.addEventListener('popstate', function () {
    var m = location.hash.match(/^#s-([0-9a-f]{12})$/);
    if (m) openStory(m[1], false); else closeStory(true);
  });
  var initial = location.hash.match(/^#s-([0-9a-f]{12})$/);
  if (initial && STORIES[initial[1]]) {
    try { history.replaceState(null, '', location.pathname + location.search); history.pushState({ story: initial[1] }, '', '#s-' + initial[1]); } catch (e) { }
    openStory(initial[1], false);
  }

  /* ---- archive: refresh from data/index.json so old pages see new editions ---- */
  fetch(BASE + 'data/index.json', { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (idx) {
    if (!idx || !idx.editions) return;
    var list = $('#archive-list');
    list.innerHTML = idx.editions.map(function (e) {
      var d = new Date(e.date + 'T12:00:00Z');
      return '<a class="arow' + (e.date === ED.edition_date ? ' current' : '') + '" href="' + BASE + 'news/' + e.date + '.html">' +
        '<span class="arow-date"><span class="num">' + Number(e.date.slice(8)) + '</span><span class="eyebrow">' + d.toLocaleDateString('en-GB', { month: 'short', year: 'numeric', timeZone: 'UTC' }) + '</span></span>' +
        '<span class="grow"><span class="arow-title">' + esc(e.top_headline || ('Edition ' + e.date)) + '</span>' +
        '<span class="hint">' + e.counts.global + ' global · ' + e.counts.india + ' India · No. ' + String(e.number).padStart(3, '0') + '</span></span></a>';
    }).join('');
  }).catch(function () { /* offline or file:// — the server-rendered archive stays */ });

  applyFilter();
})();
