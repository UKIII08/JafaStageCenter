/* Pick — wybór z listy w stylu panelu zamiast systemowego <select>
   (który w Windows/Chrome rozwija się na biało i wygląda technicznie).

   Z szablonu:
     <div class="pick" data-pick data-name="role">
       <button type="button" class="pick-btn"><span class="pick-label">Gram</span><b class="pick-val">Wokal 2</b></button>
       <div class="pick-menu" hidden>
         <button type="button" class="pick-opt" data-value="Wokal 2" aria-selected="true">Wokal 2</button>
       </div>
     </div>
   Wybór wysyła zdarzenie 'pick' z detail.value na elemencie .pick.

   Z JS: Pick.create({label, options: [{value, text}], value, onChange}) -> element */
(function () {
    'use strict';
    var CHEVRON = '<svg class="pick-chev" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
    var CHECK = '<svg class="pick-check" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12l5 5L20 7"/></svg>';
    var open = null;

    function close() {
        if (!open) return;
        open.classList.remove('open');
        open.querySelector('.pick-menu').hidden = true;
        open.querySelector('.pick-btn').setAttribute('aria-expanded', 'false');
        open = null;
    }

    function choose(pick, opt) {
        pick.querySelectorAll('.pick-opt').forEach(function (o) {
            o.setAttribute('aria-selected', o === opt ? 'true' : 'false');
        });
        var v = pick.querySelector('.pick-val');
        if (v) v.textContent = opt.dataset.short || opt.textContent.trim();
        pick.classList.toggle('empty', !opt.dataset.value);
        close();
        pick.dispatchEvent(new CustomEvent('pick', { detail: { value: opt.dataset.value }, bubbles: true }));
    }

    function enhance(pick) {
        if (pick._pick) return pick;
        pick._pick = true;
        var btn = pick.querySelector('.pick-btn'), menu = pick.querySelector('.pick-menu');
        if (!btn.querySelector('.pick-chev')) btn.insertAdjacentHTML('beforeend', CHEVRON);
        btn.setAttribute('aria-haspopup', 'listbox');
        btn.setAttribute('aria-expanded', 'false');
        menu.setAttribute('role', 'listbox');
        pick.querySelectorAll('.pick-opt').forEach(function (o) {
            o.setAttribute('role', 'option');
            if (!o.querySelector('.pick-check')) o.insertAdjacentHTML('beforeend', CHECK);
            o.addEventListener('click', function () { choose(pick, o); });
        });
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            if (open === pick) { close(); return; }
            close();
            open = pick;
            pick.classList.add('open');
            menu.hidden = false;
            btn.setAttribute('aria-expanded', 'true');
            var sel = menu.querySelector('[aria-selected="true"]') || menu.querySelector('.pick-opt');
            if (sel) sel.focus();
        });
        menu.addEventListener('keydown', function (e) {
            var opts = Array.prototype.slice.call(menu.querySelectorAll('.pick-opt'));
            var i = opts.indexOf(document.activeElement);
            if (e.key === 'ArrowDown') { e.preventDefault(); (opts[i + 1] || opts[0]).focus(); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); (opts[i - 1] || opts[opts.length - 1]).focus(); }
            else if (e.key === 'Escape') { close(); btn.focus(); }
        });
        return pick;
    }

    function create(o) {
        var pick = document.createElement('div');
        pick.className = 'pick' + (o.cls ? ' ' + o.cls : '');
        var cur = o.options.find(function (x) { return x.value === o.value; }) || o.options[0];
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'pick-btn';
        if (o.label) { var l = document.createElement('span'); l.className = 'pick-label'; l.textContent = o.label; btn.appendChild(l); }
        var v = document.createElement('b'); v.className = 'pick-val'; v.textContent = cur.short || cur.text; btn.appendChild(v);
        if (o.title) btn.title = o.title;
        var menu = document.createElement('div');
        menu.className = 'pick-menu';
        menu.hidden = true;
        o.options.forEach(function (x) {
            var b = document.createElement('button');
            b.type = 'button';
            b.className = 'pick-opt';
            b.dataset.value = x.value;
            if (x.short) b.dataset.short = x.short;
            b.textContent = x.text;
            b.setAttribute('aria-selected', x === cur ? 'true' : 'false');
            menu.appendChild(b);
        });
        pick.appendChild(btn);
        pick.appendChild(menu);
        pick.classList.toggle('empty', !cur.value);
        enhance(pick);
        if (o.onChange) pick.addEventListener('pick', function (e) { o.onChange(e.detail.value); });
        return pick;
    }

    document.addEventListener('click', function (e) { if (open && !open.contains(e.target)) close(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
    function init() { document.querySelectorAll('[data-pick]').forEach(enhance); }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();

    window.Pick = { create: create, enhance: enhance, close: close };
})();
