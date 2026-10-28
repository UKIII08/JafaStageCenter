// Riff jako tabulatura: edytor (klik w kratkę + klawiatura progów),
// podgląd ASCII i odtwarzanie dźwiękiem szarpanej struny (Karplus-Strong,
// bez bibliotek). Dane: {inst: "guitar"|"bass", cols: [[próg, …], …]} —
// kolumna = szesnastka, w niej próg dla każdej struny od najwyższej.
// Zapis próbu: 3 · 12 · 5h7 (hammer-on) · 7p5 (pull-off) · 5/7 i 7\5
// (slajd) · 7b (podciągnięcie o cały ton) · 7~ (wibrato) · x (stłumiona).
(function (global) {
    'use strict';
    var TUNING = {
        guitar: { names: ['e', 'B', 'G', 'D', 'A', 'E'], hz: [329.63, 246.94, 196.0, 146.83, 110.0, 82.41] },
        bass: { names: ['G', 'D', 'A', 'E'], hz: [98.0, 73.42, 55.0, 41.2] }
    };
    var CELL = /^(x|\d{1,2}(?:[hp\/\\]\d{1,2}|b\d{0,2}|~)?)$/;
    var STEP = 16;     // szesnastki w takcie

    function empty(inst, bars) {
        var n = TUNING[inst].names.length, cols = [];
        for (var i = 0; i < (bars || 1) * STEP; i++) cols.push(fill(n));
        return { inst: inst, cols: cols };
    }
    function fill(n) { var a = []; for (var i = 0; i < n; i++) a.push(''); return a; }
    function hasNotes(r) { return !!(r && r.cols && r.cols.some(function (c) { return c.some(Boolean); })); }

    // ── ASCII (podgląd w kafelku i w ćwiczeniu) ──────────────────────────
    function ascii(r, maxCols) {
        if (!hasNotes(r)) return '';
        var t = TUNING[r.inst] || TUNING.guitar, cols = r.cols.slice(0, maxCols || r.cols.length);
        return t.names.map(function (name, s) {
            var line = name + '|';
            cols.forEach(function (c, i) {
                var v = c[s] || '';
                line += v ? v + '-'.repeat(Math.max(1, 3 - v.length)) : '---';
                if ((i + 1) % STEP === 0) line += '|';
            });
            return line;
        }).join('\n');
    }

    // ── Dźwięk: szarpana struna ──────────────────────────────────────────
    var ctx = null, cache = {};
    function audio() {
        if (!ctx) ctx = new (global.AudioContext || global.webkitAudioContext)();
        if (ctx.state === 'suspended') ctx.resume();
        return ctx;
    }
    function pluck(freq, dur, muted) {
        var c = audio(), key = Math.round(freq * 10) + (muted ? 'm' : '') + dur;
        if (cache[key]) return cache[key];
        var sr = c.sampleRate, len = Math.floor(sr * dur), buf = c.createBuffer(1, len, sr);
        var d = buf.getChannelData(0), period = Math.max(2, Math.round(sr / freq));
        var ring = new Float32Array(period);
        for (var i = 0; i < period; i++) ring[i] = Math.random() * 2 - 1;
        var damp = muted ? 0.9 : 0.996, idx = 0;
        for (var j = 0; j < len; j++) {
            var nxt = (idx + 1) % period;
            var v = (ring[idx] + ring[nxt]) * 0.5 * damp;
            d[j] = ring[idx];
            ring[idx] = v;
            idx = nxt;
        }
        // łagodny początek i koniec (bez trzasków)
        for (var k = 0; k < 64 && k < len; k++) { d[k] *= k / 64; d[len - 1 - k] *= k / 64; }
        cache[key] = buf;
        return buf;
    }
    function playAt(freq, when, dur, gain, muted) {
        var c = audio(), src = c.createBufferSource(), g = c.createGain();
        src.buffer = pluck(freq, Math.min(2.5, dur + 0.6), muted);
        g.gain.value = gain;
        src.connect(g); g.connect(c.destination);
        src.start(when);
        return src;
    }
    function fretHz(open, fret) { return open * Math.pow(2, fret / 12); }

    var playing = [];
    function stop() {
        playing.forEach(function (s) { try { s.stop(); } catch (e) {} });
        playing = [];
    }
    // Gra riff w tempie piosenki; onStep(i) podświetla kolumnę
    function play(r, bpm, onStep, onEnd) {
        stop();
        if (!hasNotes(r)) return;
        var c = audio(), t = TUNING[r.inst] || TUNING.guitar;
        var step = 60 / (bpm || 90) / 4, start = c.currentTime + 0.08;
        var last = 0;
        r.cols.forEach(function (col, i) { if (col.some(Boolean)) last = i; });
        var timers = [];
        r.cols.slice(0, last + 1).forEach(function (col, i) {
            var when = start + i * step;
            col.forEach(function (v, s) {
                if (!v) return;
                var open = t.hz[s];
                if (v === 'x') { playing.push(playAt(open * 2, when, 0.08, 0.25, true)); return; }
                var m = v.match(/^(\d+)(?:([hp\/\\])(\d+)|b(\d*)|(~))?$/);
                if (!m) return;
                var f1 = +m[1];
                playing.push(playAt(fretHz(open, f1), when, step * 2, 0.55));
                if (m[2]) {                         // hammer/pull/slajd: druga nuta w połowie
                    playing.push(playAt(fretHz(open, +m[3]), when + step / 2, step * 2, 0.4));
                } else if (m[4] !== undefined) {    // podciągnięcie: +2 półtony
                    playing.push(playAt(fretHz(open, f1 + (+m[4] ? (+m[4] - f1) : 2)), when + step / 2, step * 2, 0.4));
                }
            });
            if (onStep) timers.push(setTimeout(function () { onStep(i); }, (when - c.currentTime) * 1000));
        });
        var endMs = (start - c.currentTime + (last + 2) * step) * 1000;
        timers.push(setTimeout(function () { if (onEnd) onEnd(); }, endMs));
        playing.push({ stop: function () { timers.forEach(clearTimeout); if (onEnd) onEnd(); } });
    }

    // ── Edytor ───────────────────────────────────────────────────────────
    // mount(el, riff, {bpm, onChange, L}) → {get(), destroy()}
    function mount(el, riff, opts) {
        opts = opts || {};
        var L = opts.L || {};
        var r = riff && riff.cols ? JSON.parse(JSON.stringify(riff)) : empty('guitar', 1);
        if (!r.cols.length) r = empty(r.inst || 'guitar', 1);
        var sel = { c: 0, s: 0 }, typed = '';

        function n() { return TUNING[r.inst].names.length; }
        function changed() { if (opts.onChange) opts.onChange(hasNotes(r) ? r : null); }
        function render() {
            var t = TUNING[r.inst];
            var html = '<div class="rf-bar">' +
                '<div class="seg rf-inst">' +
                '<button type="button" data-inst="guitar" class="' + (r.inst === 'guitar' ? 'active' : '') + '">' + (L.guitar || 'Guitar') + '</button>' +
                '<button type="button" data-inst="bass" class="' + (r.inst === 'bass' ? 'active' : '') + '">' + (L.bass || 'Bass') + '</button></div>' +
                '<button type="button" class="btn btn-sm rf-play" data-act="play">▶ ' + (L.play || 'Play') + '</button>' +
                '<span class="rf-bpm">' + (opts.bpm || 90) + ' BPM</span>' +
                '<span class="rf-gap"></span>' +
                '<button type="button" class="btn btn-ghost btn-sm" data-act="addbar">＋ ' + (L.bar || 'Bar') + '</button>' +
                (r.cols.length > STEP ? '<button type="button" class="btn btn-ghost btn-sm" data-act="delbar">− ' + (L.bar || 'Bar') + '</button>' : '') +
                '<button type="button" class="btn btn-ghost btn-sm" data-act="clear">' + (L.clear || 'Clear') + '</button>' +
                '</div><div class="rf-scroll"><table class="rf-grid"><tbody>';
            t.names.forEach(function (name, s) {
                html += '<tr><th>' + name + '</th>';
                r.cols.forEach(function (col, c) {
                    var cls = 'rf-c' + (c % 4 === 0 ? ' beat' : '') + (c % STEP === 0 ? ' bar' : '') +
                        (sel.c === c && sel.s === s ? ' sel' : '') + (col[s] ? ' on' : '');
                    html += '<td class="' + cls + '" data-c="' + c + '" data-s="' + s + '">' + (col[s] ? escHtml(col[s]) : '') + '</td>';
                });
                html += '</tr>';
            });
            html += '</tbody></table></div>' +
                '<div class="rf-pad">' +
                ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '12'].map(function (k) {
                    return '<button type="button" data-k="' + k + '">' + k + '</button>';
                }).join('') +
                ['h', 'p', '/', 'b', '~', 'x'].map(function (k) {
                    return '<button type="button" class="tech" data-k="' + k + '" title="' + escHtml((L.tech || {})[k] || '') + '">' + k + '</button>';
                }).join('') +
                '<button type="button" class="tech" data-k="⌫" title="' + escHtml(L.del || '') + '">⌫</button>' +
                '</div><div class="rf-help">' + escHtml(L.help || '') + '</div>';
            el.innerHTML = html;
        }
        function escHtml(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
        function setCell(v) {
            // dopuszczamy stan pośredni „5h" (zaraz dojdzie druga nuta)
            if (v && !CELL.test(v) && !/^\d{1,2}[hp\/\\b]$/.test(v)) return false;
            r.cols[sel.c][sel.s] = v;
            var td = el.querySelector('td[data-c="' + sel.c + '"][data-s="' + sel.s + '"]');
            if (td) { td.textContent = v; td.classList.toggle('on', !!v); }
            if (!v || CELL.test(v)) changed();
            return true;
        }
        function select(c, s) {
            sel = { c: Math.max(0, Math.min(r.cols.length - 1, c)), s: Math.max(0, Math.min(n() - 1, s)) };
            typed = '';
            el.querySelectorAll('td.sel').forEach(function (x) { x.classList.remove('sel'); });
            var td = el.querySelector('td[data-c="' + sel.c + '"][data-s="' + sel.s + '"]');
            if (td) { td.classList.add('sel'); td.scrollIntoView({ block: 'nearest', inline: 'nearest' }); }
        }
        // Wpisywanie: cyfra, druga cyfra (próg 10–24), technika (h p / \ b ~),
        // druga nuta techniki; x = stłumiona; ⌫ cofa znak.
        function key(k) {
            var cur = r.cols[sel.c][sel.s] || '';
            if (k === '⌫' || k === 'Backspace') { typed = cur.slice(0, -1); setCell(typed); return; }
            if (k === 'Delete') { typed = ''; setCell(''); return; }
            if (k === 'x') { typed = ''; setCell('x'); return; }
            if (/^[hp\/\\b~]$/.test(k)) {
                if (/^\d{1,2}$/.test(cur)) { typed = cur + k; setCell(typed); }
                return;
            }
            if (!/^\d+$/.test(k)) return;
            var cand = k, tail = typed.match(/[hp\/\\b](\d*)$/);
            if (k.length === 1 && /^\d$/.test(typed) && +(typed + k) <= 24) cand = typed + k;
            else if (tail && (tail[1] + k).length <= 2) cand = typed + k;
            typed = cand;
            setCell(cand);
        }
        el.addEventListener('click', function (e) {
            var td = e.target.closest('td[data-c]');
            if (td) { select(+td.dataset.c, +td.dataset.s); el.focus(); return; }
            var b = e.target.closest('button');
            if (!b) return;
            if (b.dataset.k) { key(b.dataset.k); return; }
            if (b.dataset.inst && b.dataset.inst !== r.inst) {
                var nn = TUNING[b.dataset.inst].names.length;
                r.cols = r.cols.map(function (c) { return c.slice(0, nn).concat(fill(Math.max(0, nn - c.length))); });
                r.inst = b.dataset.inst; sel.s = Math.min(sel.s, nn - 1);
                render(); changed(); return;
            }
            var act = b.dataset.act;
            if (act === 'addbar') { for (var i = 0; i < STEP; i++) r.cols.push(fill(n())); render(); return; }
            if (act === 'delbar') {
                var tail = r.cols.slice(-STEP);
                if (tail.some(function (c) { return c.some(Boolean); }) && !global.confirm(L.delBar || 'Delete the last bar?')) return;
                r.cols = r.cols.slice(0, -STEP); sel.c = Math.min(sel.c, r.cols.length - 1); render(); changed(); return;
            }
            if (act === 'clear') {
                if (hasNotes(r) && !global.confirm(L.clearQ || 'Clear the riff?')) return;
                r = empty(r.inst, 1); sel = { c: 0, s: 0 }; render(); changed(); return;
            }
            if (act === 'play') {
                if (b.classList.contains('on')) { stop(); return; }
                b.classList.add('on'); b.textContent = '■ ' + (L.stop || 'Stop');
                play(r, opts.bpm, function (i) {
                    el.querySelectorAll('td.now').forEach(function (x) { x.classList.remove('now'); });
                    el.querySelectorAll('td[data-c="' + i + '"]').forEach(function (x) { x.classList.add('now'); });
                }, function () {
                    el.querySelectorAll('td.now').forEach(function (x) { x.classList.remove('now'); });
                    var pb = el.querySelector('[data-act="play"]');
                    if (pb) { pb.classList.remove('on'); pb.textContent = '▶ ' + (L.play || 'Play'); }
                });
            }
        });
        el.tabIndex = 0;
        el.addEventListener('keydown', function (e) {
            if (e.target !== el) return;
            var k = e.key;
            if (k === 'ArrowRight' || k === 'Tab' && !e.shiftKey) { e.preventDefault(); select(sel.c + 1, sel.s); }
            else if (k === 'ArrowLeft' || k === 'Tab' && e.shiftKey) { e.preventDefault(); select(sel.c - 1, sel.s); }
            else if (k === 'ArrowUp') { e.preventDefault(); select(sel.c, sel.s - 1); }
            else if (k === 'ArrowDown') { e.preventDefault(); select(sel.c, sel.s + 1); }
            else if (k === ' ') { e.preventDefault(); el.querySelector('[data-act="play"]').click(); }
            else if (/^[0-9hpbx~\/\\]$/.test(k) || k === 'Backspace' || k === 'Delete') { e.preventDefault(); key(k); }
        });
        render();
        return {
            get: function () { return hasNotes(r) ? r : null; },
            destroy: function () { stop(); el.innerHTML = ''; }
        };
    }

    global.JRiff = { mount: mount, ascii: ascii, play: play, stop: stop, hasNotes: hasNotes, TUNING: TUNING };
})(window);
