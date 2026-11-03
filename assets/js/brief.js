/* Device voice, accurate daily greeting and opt-in notifications. */
(function () {
  'use strict';
  var data = JSON.parse(document.getElementById('edition-data').textContent);
  var ed = data.edition, base = data.base || '', tz = ed.timezone || 'Asia/Qatar';
  var byId = function (id) { return document.getElementById(id); };
  function greeting() {
    var hour = +new Intl.DateTimeFormat('en-GB', { timeZone: tz, hour: '2-digit', hourCycle: 'h23' }).format(new Date());
    return hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  }
  function isToday() {
    var parts = new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
    var values = {}; parts.forEach(function (p) { values[p.type] = p.value; });
    return [values.year, values.month, values.day].join('-') === ed.edition_date;
  }
  function updateGreeting() {
    byId('brief-title').textContent = isToday() ? 'Today’s brief' : 'Edition brief';
    byId('brief-greeting').textContent = greeting() + '. ' + (isToday() ? 'Here’s your AI update for today.' : 'Here’s your AI update for ' + new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: tz }).format(new Date(ed.edition_date + 'T12:00:00Z')) + '.');
  }
  updateGreeting();
  document.addEventListener('visibilitychange', function () { if (!document.hidden) updateGreeting(); });

  var listen = byId('listen-btn'), pause = byId('pause-btn'), stop = byId('stop-btn'), status = byId('voice-status');
  var synth = window.speechSynthesis, active = false, paused = false, generation = 0, queue = [], current;
  function resetVoice(message) {
    active = false; paused = false; listen.disabled = false; pause.hidden = stop.hidden = true;
    pause.textContent = 'Pause'; status.textContent = message;
  }
  function stopVoice() { generation++; synth.cancel(); resetVoice('Ready to read the headlines and summaries.'); }
  function speakNext(token) {
    if (token !== generation || !active) return;
    if (!queue.length) { resetVoice('Brief finished.'); return; }
    current = new SpeechSynthesisUtterance(queue.shift()); current.lang = 'en-GB'; current.rate = 1;
    var voices = synth.getVoices();
    current.voice = voices.find(function (v) { return /^en-(GB|IN)$/i.test(v.lang) && v.localService; }) || voices.find(function (v) { return /^en/i.test(v.lang); }) || null;
    current.onend = function () { speakNext(token); };
    current.onerror = function () { if (token === generation) { generation++; synth.cancel(); resetVoice('Voice could not play. Tap Listen to retry.'); } };
    synth.speak(current);
  }
  if (synth && window.SpeechSynthesisUtterance) {
    listen.disabled = false; status.textContent = 'Headlines & summaries · Device voice';
    listen.addEventListener('click', function () {
      generation++; synth.cancel(); active = true; paused = false; listen.disabled = true;
      pause.hidden = stop.hidden = false; pause.textContent = 'Pause'; status.textContent = 'Reading your brief…';
      queue = [greeting() + '. Here is your JARVIS AI News brief for ' + ed.edition_date + '.'];
      ['global','india'].forEach(function (region) {
        if (!ed.stories[region].length) return;
        queue.push(region === 'india' ? 'From India.' : 'Around the world.');
        ed.stories[region].forEach(function (story) {
          queue.push(story.headline + '.');
          // Short utterances avoid long-speech timeouts on mobile browsers.
          (story.summary.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [story.summary]).forEach(function (sentence) { queue.push(sentence); });
        });
      });
      queue.push('That is your brief. Open a story to read its publisher source.'); speakNext(generation);
    });
    pause.addEventListener('click', function () {
      if (!active) return;
      paused = !paused; if (paused) synth.pause(); else synth.resume();
      pause.textContent = paused ? 'Resume' : 'Pause'; status.textContent = paused ? 'Reading paused.' : 'Reading your brief…';
    });
    stop.addEventListener('click', stopVoice);
    window.addEventListener('pagehide', stopVoice);
  } else { status.textContent = 'Read-aloud is not supported in this browser. Try Safari or Chrome.'; }

  /* Poll only visible pages. This banner is not a substitute for background push. */
  var checking = false;
  async function checkNews() {
    if (document.hidden || checking) return; checking = true;
    try {
      var response = await fetch(base + 'data/index.json?check=' + Date.now(), { cache: 'no-store' });
      if (!response.ok) return;
      var idx = await response.json();
      var latest = (idx.editions || []).find(function (e) { return e.date === idx.latest; });
      if (latest && (idx.latest > ed.edition_date || (idx.latest === ed.edition_date && latest.generated_at !== ed.generated_at))) {
        var banner = byId('news-update'); banner.textContent = 'A news update is available.';
        var link = document.createElement('a'); link.textContent = 'Read update'; link.href = base + 'index.html?update=' + encodeURIComponent(latest.generated_at);
        banner.appendChild(link); banner.hidden = false;
      }
    } catch (e) { /* Keep the current edition usable offline. */ } finally { checking = false; }
  }
  setInterval(checkNews, 120000);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) checkNews(); });
  checkNews();

  var pushButton = byId('push-btn'), pushStatus = byId('push-status');
  fetch(base + 'assets/push-config.json', { cache: 'no-store' }).then(function (r) { if (!r.ok) throw new Error(); return r.json(); }).then(function (config) {
    if (!config.appId) { pushStatus.textContent = 'Device notifications are not active yet. News updates appear in this page while it is open.'; pushButton.hidden = true; return; }
    if (!('serviceWorker' in navigator) || !('Notification' in window)) {
      pushStatus.textContent = 'Open JARVIS from your Home Screen on iPhone, or use a browser that supports web notifications.'; pushButton.hidden = true; return;
    }
    // Do not load the third-party SDK until the reader asks to set up alerts.
    pushButton.disabled = false; pushButton.textContent = 'Set up notifications';
    pushStatus.textContent = 'Choose Set up notifications to connect this device to OneSignal. You can turn alerts off here.';
    var sdk;
    pushButton.addEventListener('click', async function () {
      if (sdk) {
        pushButton.disabled = true;
        try {
          if (sdk.User.PushSubscription.optedIn) await sdk.User.PushSubscription.optOut();
          else await sdk.User.PushSubscription.optIn();
          syncPush();
        } catch (e) { pushStatus.textContent = 'Notifications could not be enabled. Check browser notification permissions.'; }
        pushButton.disabled = false; return;
      }
      pushButton.disabled = true; pushStatus.textContent = 'Connecting notification service…';
      var timer = setTimeout(failed, 15000);
      function failed() { clearTimeout(timer); pushStatus.textContent = 'Notification service could not load. Refresh and try again.'; }
      window.OneSignalDeferred = window.OneSignalDeferred || [];
      window.OneSignalDeferred.push(async function (OneSignal) {
        try {
          var rootPath = new URL(base || './', location.href).pathname;
          await OneSignal.init({ appId: config.appId, serviceWorkerPath: rootPath + 'OneSignalSDKWorker.js', serviceWorkerParam: { scope: rootPath }, notifyButton: { enable: false }, welcomeNotification: { disable: true }, promptOptions: { slidedown: { prompts: [{ type: 'push', autoPrompt: false }] } } });
          clearTimeout(timer); sdk = OneSignal;
          sdk.User.PushSubscription.addEventListener('change', syncPush);
          syncPush(); pushButton.disabled = false;
        } catch (e) { failed(); }
      });
      var script = document.createElement('script'); script.src = 'https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js'; script.defer = true; script.onerror = failed; document.head.appendChild(script);
    });
    function syncPush() {
      var enabled = sdk.User.PushSubscription.optedIn;
      pushButton.textContent = enabled ? 'Turn off notifications' : 'Enable notifications';
      pushStatus.textContent = enabled ? 'News notifications are enabled on this device.' : 'Tap Enable notifications and allow the browser permission request.';
    }
  }).catch(function () { pushStatus.textContent = 'Notification settings could not load. Refresh to try again.'; pushButton.hidden = true; });
})();
