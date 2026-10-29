// Edytor piosenki: numery linii, problemy z numerem linii (klik = zaznacz
// linię), podpowiedź notacji, wykrycie „akordów nad tekstem" i podgląd na
// żywo — dokładnie ta sama ścieżka co zapis (POST /api/songs/analyze).
// Teksty przez window.SONG_EDITOR_I18N (patrz songs/form.html).
(function () {
    'use strict';
    var ta = document.getElementById('song-content');
    if (!ta) return;
    var L = window.SONG_EDITOR_I18N || {};
    var $ = function (id) { return document.getElementById(id); };
    var gutter = $('gutter'), status = $('chord-status'), issuesEl = $('issues');
    var notationInput = $('f-notation'), keyInput = $('song-key');
    var timer = null, seq = 0, errLines = {};

    function esc(s) {
        return String(s).replace(/[&<>"]/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
        });
    }
    function fill(tpl, vars) {
        return String(tpl).replace(/%\((\w+)\)s/g, function (_, k) { return vars[k] != null ? vars[k] : ''; });
    }

    // ── Numery linii ──
    function paintGutter() {
        var n = ta.value.split('\n').length, out = [];
        for (var i = 1; i <= n; i++) out.push(errLines[i] ? '<b>' + i + '</b>' : String(i));
        gutter.innerHTML = out.join('\n');
        gutter.scrollTop = ta.scrollTop;
    }
    ta.addEventListener('scroll', function () { gutter.scrollTop = ta.scrollTop; });

    function selectLine(n) {
        var lines = ta.value.split('\n'), start = 0;
        for (var i = 0; i < n - 1 && i < lines.length; i++) start += lines[i].length + 1;
        var end = start + (lines[n - 1] || '').length;
        ta.focus();
        ta.setSelectionRange(start, end);
        var lh = parseFloat(getComputedStyle(ta).lineHeight) || 22;
        ta.scrollTop = Math.max(0, (n - 4) * lh);
    }

    // ── Notacja (przełącznik) ──
    function setNotation(v) {
        notationInput.value = v;
        document.querySelectorAll('#notation-seg button').forEach(function (b) {
            b.classList.toggle('active', b.dataset.v === v);
        });
        analyze();
    }
    document.querySelectorAll('#notation-seg button').forEach(function (b) {
        b.addEventListener('click', function () { setNotation(b.dataset.v); });
    });
    $('hint-notation-btn').addEventListener('click', function () { setNotation('polish'); });

    // ── Zakładki: podgląd / jak pisać ──
    document.querySelectorAll('#side-tabs button').forEach(function (b) {
        b.addEventListener('click', function () {
            document.querySelectorAll('#side-tabs button').forEach(function (x) { x.classList.toggle('active', x === b); });
            $('tab-preview').hidden = b.dataset.tab !== 'preview';
            $('tab-help').hidden = b.dataset.tab !== 'help';
        });
    });

    // ── Wynik analizy ──
    function render(d) {
        errLines = {};
        var text = ta.value;
        if (!text.trim()) {
            status.textContent = ''; issuesEl.innerHTML = '';
            $('hint-notation').hidden = true; $('hint-above').hidden = true;
            $('preview').className = 'pv-empty'; $('preview').textContent = L.empty;
            paintGutter();
            return;
        }
        // 1) Podsumowanie
        var parts = [];
        if (!d.total) parts.push(L.noChords);
        else {
            parts.push('<b>' + d.total + '</b> ' + esc(L.chords));
            parts.push('<b>' + d.sections.length + '</b> ' + esc(L.sections));
            if (!d.invalid.length) parts.push(esc(L.allValid));
            if (d.key) parts.push(esc(L.keyLabel) + ': <b>' + esc(d.key) + '</b>');
        }
        status.innerHTML = parts.join(' · ');
        if (keyInput && !keyInput.value) keyInput.placeholder = d.key || '';
        // Wklejony ChordPro niesie tytuł, tonację i tempo — wpisz je w puste pola
        var meta = d.meta || {};
        var titleInput = $('f-title'), bpmInput = $('f-bpm');
        if (meta.title && titleInput && !titleInput.value) titleInput.value = meta.title;
        if (meta.key && keyInput && !keyInput.value) keyInput.value = meta.key;
        if (meta.bpm && bpmInput && !bpmInput.value) bpmInput.value = meta.bpm;

        // 2) Problemy z numerami linii
        var rows = [];
        d.issues.forEach(function (i) {
            var kind = { unclosed: ['err', L.unclosed], stray_close: ['', L.stray],
                         double_brackets: ['fix', L.dbl], label_brackets: ['fix', L.labelBr],
                         capo_line: ['', L.capo], empty_part: ['', L.emptyPart] }[i.kind];
            if (!kind) return;
            if (kind[0] === 'err') errLines[i.line] = true;
            rows.push({ line: i.line, cls: kind[0], html: '<b>' + esc(i.text) + '</b> · ' + esc(kind[1]) });
        });
        d.invalid.forEach(function (inv) {
            inv.lines.forEach(function (n) { errLines[n] = true; });
            rows.push({ line: inv.lines[0], cls: 'err', html: '<b>[' + esc(inv.chord) + ']</b> · ' + esc(L.invalid) +
                        (inv.lines.length > 1 ? ' (×' + inv.lines.length + ')' : '') });
        });
        rows.sort(function (a, b) { return a.line - b.line; });
        issuesEl.innerHTML = rows.map(function (r) {
            return '<li class="' + r.cls + '" data-line="' + r.line + '"><span class="ln">' + esc(L.line) + ' ' + r.line +
                   '</span><span class="t">' + r.html + '</span></li>';
        }).join('');

        // 3) Podpowiedź notacji
        var h = d.notation_hint;
        $('hint-notation').hidden = !h;
        if (h) {
            $('hint-notation-text').textContent = fill(L.notationPl, { ex: h.examples.join(', ') }) +
                (h.has_b ? ' ' + L.notationB : '');
        }
        // 4) Akordy nad tekstem
        $('hint-above').hidden = !d.above_lyrics.length;
        if (d.above_lyrics.length) {
            $('hint-above-text').textContent = fill(L.above, { lines: d.above_lyrics.slice(0, 6).join(', ') });
        }
        // 5) Podgląd (te same pary akord+sylaba co u zespołu)
        var pv = $('preview');
        if (!d.sections.length) { pv.className = 'pv-empty'; pv.textContent = L.empty; }
        else {
            pv.className = '';
            pv.innerHTML = d.sections.map(function (s) {
                var label = s.auto ? '<span class="auto">' + esc(L.auto) + '</span>' : esc(s.label);
                var warn = (!s.known && !s.auto) ? '<span class="pv-warn">' + esc(L.labelQ) + '</span>' : '';
                if (s.lines > 8) warn += '<span class="pv-warn">' + esc(fill(L.tooLong, { n: s.lines })) + '</span>';
                return '<div class="pv-sec"><div class="pv-label">' + label + warn + '</div>' +
                       '<div class="song-render">' + s.html + '</div></div>';
            }).join('');
            if (window.applyChordPrefs) {
                pv.querySelectorAll('.song-render').forEach(function (el) {
                    window.applyChordPrefs(el, { notation: notationInput.value });
                });
            }
        }
        paintGutter();
    }

    function analyze() {
        paintGutter();
        var my = ++seq;
        fetch('/api/songs/analyze', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: ta.value, notation: notationInput.value })
        }).then(function (r) { return r.json(); })
          .then(function (d) { if (my === seq) render(d); })
          .catch(function () {});
    }

    issuesEl.addEventListener('click', function (e) {
        var li = e.target.closest('li[data-line]');
        if (li) selectLine(+li.dataset.line);
    });
    ta.addEventListener('input', function () {
        paintGutter();
        clearTimeout(timer);
        timer = setTimeout(analyze, 350);
    });

    $('convert-format-btn').addEventListener('click', function () {
        var btn = this;
        fetch('/api/songs/convert-format', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: ta.value })
        }).then(function (r) { return r.json(); }).then(function (d) {
            if (d.changed) { ta.value = d.text; analyze(); btn.textContent = L.converted; }
        });
    });

    // Niezapisane zmiany: ostrzeżenie przy wyjściu ze strony (edytor nie
    // zapisuje sam, w przeciwieństwie do Formy i kratek)
    var form = document.getElementById('song-form'), initial = null, submitting = false;
    function snapshot() {
        return Array.prototype.map.call(form.querySelectorAll('input[name], textarea[name]'),
            function (e) { return e.name + '=' + e.value; }).join('|');
    }
    if (form) {
        setTimeout(function () { initial = snapshot(); }, 0);
        form.addEventListener('submit', function () { submitting = true; });
        window.addEventListener('beforeunload', function (e) {
            if (submitting || initial === null || snapshot() === initial) return;
            e.preventDefault();
            e.returnValue = '';
        });
    }
    // Konflikt zapisu: „Wczytaj ich wersję" podmienia treść w edytorze
    var useTheirs = $('use-theirs');
    if (useTheirs && window.SONG_THEIRS != null) {
        useTheirs.addEventListener('click', function () {
            ta.value = window.SONG_THEIRS;
            ta.dispatchEvent(new Event('input'));
            if (window.SongTiles && document.getElementById('tiles') && !document.getElementById('tiles').hidden) {
                document.querySelector('#mode-seg [data-mode="text"]').click();
                document.querySelector('#mode-seg [data-mode="tiles"]').click();
            }
        });
    }

    paintGutter();
    if (ta.value.trim()) analyze();
})();
