/* Jonathan — hover hints (coach marks).
 *
 * Any element with a `data-hint="..."` attribute shows a small explanatory
 * bubble on hover. Hints appear automatically for the first few times the app
 * is opened, then quietly switch off. The user can turn them back on (or off)
 * from Settings — see window.JonathanHints below.
 *
 * State (localStorage):
 *   jonathan-hints-mode : 'auto' | 'on' | 'off'   (default 'auto')
 *   jonathan-hints-uses : number of app opens so far
 * A "use" is counted once per browser session (sessionStorage guard), so it
 * tracks opening the app, not every click between pages.
 */
(function () {
  'use strict';

  var AUTO_LIMIT = 10;           // pokazuj automatycznie przez pierwsze 10 uruchomień
  var SHOW_DELAY = 260;          // ms — mały delay, żeby nie migało przy przelocie
  var LS_MODE = 'jonathan-hints-mode';
  var LS_USES = 'jonathan-hints-uses';
  var SS_COUNTED = 'jonathan-hints-counted';

  function lsGet(k, d) { try { var v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

  // Policz to uruchomienie raz na sesję przeglądarki.
  function countUse() {
    try {
      if (sessionStorage.getItem(SS_COUNTED)) return;
      sessionStorage.setItem(SS_COUNTED, '1');
    } catch (e) { /* brak sessionStorage — licz normalnie */ }
    var n = parseInt(lsGet(LS_USES, '0'), 10) || 0;
    lsSet(LS_USES, String(n + 1));
  }

  function uses() { return parseInt(lsGet(LS_USES, '0'), 10) || 0; }
  function mode() { return lsGet(LS_MODE, 'auto'); }

  // Czy podpowiedzi mają się teraz pokazywać?
  function active() {
    var m = mode();
    if (m === 'on') return true;
    if (m === 'off') return false;
    return uses() <= AUTO_LIMIT;   // 'auto'
  }

  // ── Publiczne API (używane w Ustawieniach) ──
  window.JonathanHints = {
    isActive: active,
    getMode: mode,
    getUses: uses,
    autoLimit: AUTO_LIMIT,
    setMode: function (m) { lsSet(LS_MODE, m); },       // 'on' | 'off' | 'auto'
    reset: function () { lsSet(LS_MODE, 'auto'); lsSet(LS_USES, '0'); }
  };

  // ── Bąbelek podpowiedzi ──
  var tip = null, tipTimer = null, curEl = null;

  function ensureTip() {
    if (tip) return tip;
    tip = document.createElement('div');
    tip.className = 'jhint-bubble';
    tip.setAttribute('role', 'tooltip');
    document.body.appendChild(tip);
    return tip;
  }

  function place(el) {
    var b = ensureTip();
    var r = el.getBoundingClientRect();
    b.style.visibility = 'hidden';
    b.style.display = 'block';
    var bw = b.offsetWidth, bh = b.offsetHeight;
    var gap = 10;
    var left = r.left + r.width / 2 - bw / 2;
    var top = r.bottom + gap;
    var below = true;
    if (top + bh > window.innerHeight - 8) { top = r.top - bh - gap; below = false; }
    left = Math.max(8, Math.min(left, window.innerWidth - bw - 8));
    b.style.left = Math.round(left) + 'px';
    b.style.top = Math.round(top + window.scrollY) + 'px';
    b.classList.toggle('jhint-above', !below);
    // strzałka wskazuje środek elementu
    var arrow = Math.max(12, Math.min(r.left + r.width / 2 - left, bw - 12));
    b.style.setProperty('--jhint-arrow', Math.round(arrow) + 'px');
    b.style.visibility = 'visible';
  }

  function show(el) {
    var text = el.getAttribute('data-hint');
    if (!text) return;
    var b = ensureTip();
    b.textContent = text;
    curEl = el;
    place(el);
    b.classList.add('jhint-show');
  }

  function hide() {
    if (tipTimer) { clearTimeout(tipTimer); tipTimer = null; }
    curEl = null;
    if (tip) { tip.classList.remove('jhint-show'); tip.style.display = 'none'; }
  }

  function onEnter(e) {
    if (!active()) return;
    var el = e.currentTarget;
    if (tipTimer) clearTimeout(tipTimer);
    tipTimer = setTimeout(function () { show(el); }, SHOW_DELAY);
  }

  function bind(el) {
    if (el._jhintBound) return;
    el._jhintBound = true;
    el.addEventListener('mouseenter', onEnter);
    el.addEventListener('mouseleave', hide);
    el.addEventListener('focus', onEnter);
    el.addEventListener('blur', hide);
    // nie pokazuj natywnego title-a razem z bąbelkiem
    if (el.hasAttribute('title') && !el.hasAttribute('data-jhint-title')) {
      el.setAttribute('data-jhint-title', el.getAttribute('title'));
      el.removeAttribute('title');
    }
  }

  function scan() { document.querySelectorAll('[data-hint]').forEach(bind); }

  function init() {
    countUse();
    scan();
    // elementy dodawane dynamicznie (np. modale)
    if (window.MutationObserver) {
      new MutationObserver(function () {
        if (curEl && !document.contains(curEl)) hide();
        scan();
      }).observe(document.body, { childList: true, subtree: true });
    }
    window.addEventListener('scroll', hide, true);
    window.addEventListener('resize', hide);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else { init(); }
})();
