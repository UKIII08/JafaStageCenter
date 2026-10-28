// Nuty na pięciolinii: rysowanie (SVG, bez bibliotek), edytor (klawiatura
// fortepianu + długości) i odtwarzanie. Dane:
// {kind: "staff", clef: "treble"|"bass", notes: [{k: "C#4"|"r", d: 1|2|4|8|16, dot}]}
// — jedna linia melodyczna (wokal, klawisze, skrzypce, dęte), metrum 4/4.
(function (global) {
    'use strict';
    var NS = 'http://www.w3.org/2000/svg';
    var LETTERS = ['C', 'D', 'E', 'F', 'G', 'A', 'B'];
    var SEMI = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
    var REF = { treble: 4 * 7 + 2, bass: 2 * 7 + 4 };      // dolna linia: E4 / G2
    var WIDTH = { 1: 58, 2: 46, 4: 36, 8: 30, 16: 26 };
    var UNITS = { 1: 16, 2: 8, 4: 4, 8: 2, 16: 1 };         // w szesnastkach
    var GAP = 10, H = GAP / 2;

    function parseKey(k) {
        var m = /^([A-G])(#|b)?([1-7])$/.exec(k || '');
        return m ? { l: m[1], acc: m[2] || '', o: +m[3] } : null;
    }
    function step(p) { return p.o * 7 + LETTERS.indexOf(p.l); }
    function midi(p) { return 12 * (p.o + 1) + SEMI[p.l] + (p.acc === '#' ? 1 : p.acc === 'b' ? -1 : 0); }
    function units(n) { return UNITS[n.d] * (n.dot ? 1.5 : 1); }
    function hasNotes(d) { return !!(d && d.notes && d.notes.some(function (n) { return n.k !== 'r'; })); }
    function svgEl(tag, attrs, parent) {
        var e = document.createElementNS(NS, tag);
        for (var a in attrs) e.setAttribute(a, attrs[a]);
        if (parent) parent.appendChild(e);
        return e;
    }

    // ── Rysowanie ────────────────────────────────────────────────────────
    // render(el, data, {width, sel, now, compact}) → mapa nuta→element (do zaznaczania)
    function render(el, data, opts) {
        opts = opts || {};
        el.innerHTML = '';
        var clef = data && data.clef === 'bass' ? 'bass' : 'treble';
        var notes = (data && data.notes) || [];
        var width = Math.max(240, opts.width || el.clientWidth || 600);
        var sysH = opts.compact ? 86 : 110, top0 = opts.compact ? 24 : 34;
        var x0 = 48, rows = [[]], x = x0, used = 0;
        // podział na linie (systemy) i takty
        notes.forEach(function (n, i) {
            var w = WIDTH[n.d] + (n.dot ? 8 : 0);
            if (x + w > width - 12 && rows[rows.length - 1].length) { rows.push([]); x = x0; }
            rows[rows.length - 1].push({ n: n, i: i, x: x + 14 });
            x += w;
            used += units(n);
            if (used >= 16) { used -= 16; rows[rows.length - 1].push({ bar: true, x: x + 4 }); x += 8; }
        });
        if (opts.compact) rows = rows.slice(0, 1);
        var svg = svgEl('svg', { width: width, height: rows.length * sysH + 6, class: 'stf-svg', role: 'img' });
        var nodes = {};
        rows.forEach(function (row, ri) {
            var bottom = ri * sysH + top0 + 4 * GAP;
            for (var l = 0; l < 5; l++) svgEl('line', { x1: 4, x2: width - 4, y1: bottom - l * GAP, y2: bottom - l * GAP, class: 'stf-line' }, svg);
            var cl = svgEl('text', { x: 8, y: clef === 'treble' ? bottom + 7 : bottom - GAP * 1.2, class: 'stf-clef' }, svg);
            cl.textContent = clef === 'treble' ? '𝄞' : '𝄢';
            svgEl('line', { x1: width - 4, x2: width - 4, y1: bottom, y2: bottom - 4 * GAP, class: 'stf-bar' }, svg);
            row.forEach(function (it) {
                if (it.bar) { svgEl('line', { x1: it.x, x2: it.x, y1: bottom, y2: bottom - 4 * GAP, class: 'stf-bar' }, svg); return; }
                var g = svgEl('g', { class: 'stf-note' + (opts.sel === it.i ? ' sel' : '') + (opts.now === it.i ? ' now' : ''), 'data-i': it.i }, svg);
                svgEl('rect', { x: it.x - 12, y: bottom - 7 * GAP, width: 26, height: 10 * GAP, class: 'stf-hit' }, g);
                drawNote(g, it.n, it.x, bottom, clef);
                nodes[it.i] = g;
            });
        });
        el.appendChild(svg);
        return nodes;
    }
    function drawNote(g, n, x, bottom, clef) {
        if (n.k === 'r') { drawRest(g, n, x, bottom); return; }
        var p = parseKey(n.k);
        var s = step(p) - REF[clef], y = bottom - s * H;
        // linie dodane
        for (var ls = -2; ls >= s; ls -= 2) svgEl('line', { x1: x - 10, x2: x + 10, y1: bottom - ls * H, y2: bottom - ls * H, class: 'stf-line' }, g);
        for (var hs = 10; hs <= s; hs += 2) svgEl('line', { x1: x - 10, x2: x + 10, y1: bottom - hs * H, y2: bottom - hs * H, class: 'stf-line' }, g);
        var hollow = n.d <= 2;
        svgEl('ellipse', { cx: x, cy: y, rx: 6.2, ry: 4.4, transform: 'rotate(-20 ' + x + ' ' + y + ')',
            class: hollow ? 'stf-head hollow' : 'stf-head' }, g);
        if (p.acc) {
            var a = svgEl('text', { x: x - 17, y: y + 5, class: 'stf-acc' }, g);
            a.textContent = p.acc === '#' ? '♯' : '♭';
        }
        if (n.dot) svgEl('circle', { cx: x + 10, cy: s % 2 === 0 ? y - H / 1.4 : y, r: 1.8, class: 'stf-fill' }, g);
        if (n.d === 1) return;
        var up = s < 4, sx = up ? x + 5.6 : x - 5.6, sy = up ? y - 34 : y + 34;
        svgEl('line', { x1: sx, x2: sx, y1: y, y2: sy, class: 'stf-stem' }, g);
        var flags = n.d === 8 ? 1 : n.d === 16 ? 2 : 0;
        for (var f = 0; f < flags; f++) {
            var fy = sy + (up ? f * 7 : -f * 7);
            svgEl('path', { d: up ? 'M' + sx + ' ' + fy + ' c 2 8, 11 10, 7 20' : 'M' + sx + ' ' + fy + ' c 2 -8, 11 -10, 7 -20', class: 'stf-flag' }, g);
        }
    }
    function drawRest(g, n, x, bottom) {
        var mid = bottom - 2 * GAP;
        if (n.d === 1) svgEl('rect', { x: x - 6, y: bottom - 3 * GAP, width: 12, height: 5, class: 'stf-fill' }, g);
        else if (n.d === 2) svgEl('rect', { x: x - 6, y: mid - 5, width: 12, height: 5, class: 'stf-fill' }, g);
        else if (n.d === 4) svgEl('path', { d: 'M' + (x - 2) + ' ' + (mid - 14) + ' l 6 8 l -6 6 l 6 8 c -6 -3 -9 1 -4 6', class: 'stf-rest' }, g);
        else {
            for (var f = 0; f < (n.d === 16 ? 2 : 1); f++) {
                var yy = mid - 6 + f * 8;
                svgEl('circle', { cx: x - 3, cy: yy, r: 2.6, class: 'stf-fill' }, g);
                svgEl('path', { d: 'M' + (x - 3) + ' ' + (yy + 1) + ' q 5 1 7 -3 l -6 ' + (18 - f * 4), class: 'stf-rest' }, g);
            }
        }
        if (n.dot) svgEl('circle', { cx: x + 9, cy: mid - 3, r: 1.8, class: 'stf-fill' }, g);
    }

    // ── Dźwięk ───────────────────────────────────────────────────────────
    var ctx = null, active = [];
    function audio() {
        if (!ctx) ctx = new (global.AudioContext || global.webkitAudioContext)();
        if (ctx.state === 'suspended') ctx.resume();
        return ctx;
    }
    function tone(freq, when, dur) {
        var c = audio(), o = c.createOscillator(), o2 = c.createOscillator(), g = c.createGain();
        o.type = 'triangle'; o.frequency.value = freq;
        o2.type = 'sine'; o2.frequency.value = freq * 2;
        var g2 = c.createGain(); g2.gain.value = 0.15;
        o.connect(g); o2.connect(g2); g2.connect(g); g.connect(c.destination);
        g.gain.setValueAtTime(0.0001, when);
        g.gain.exponentialRampToValueAtTime(0.32, when + 0.02);
        g.gain.exponentialRampToValueAtTime(0.18, when + 0.15);
        g.gain.setValueAtTime(0.18, Math.max(when + 0.16, when + dur - 0.06));
        g.gain.exponentialRampToValueAtTime(0.0001, when + dur);
        o.start(when); o2.start(when); o.stop(when + dur + 0.02); o2.stop(when + dur + 0.02);
        active.push(o, o2);
    }
    function stop() {
        active.forEach(function (o) { try { o.stop(); } catch (e) {} });
        active = [];
        if (stop.timers) stop.timers.forEach(clearTimeout);
        stop.timers = [];
        if (stop.onEnd) { var f = stop.onEnd; stop.onEnd = null; f(); }
    }
    function play(data, bpm, onNote, onEnd) {
        stop();
        if (!hasNotes(data)) return;
        var c = audio(), q = 60 / (bpm || 90), t = c.currentTime + 0.08;
        stop.timers = []; stop.onEnd = onEnd;
        data.notes.forEach(function (n, i) {
            var dur = q * 4 / n.d * (n.dot ? 1.5 : 1);
            var p = parseKey(n.k);
            if (p) tone(440 * Math.pow(2, (midi(p) - 69) / 12), t, dur * 0.95);
            var at = (t - c.currentTime) * 1000;
            if (onNote) stop.timers.push(setTimeout(function () { onNote(i); }, at));
            t += dur;
        });
        stop.timers.push(setTimeout(function () { stop.onEnd = null; if (onEnd) onEnd(); }, (t - c.currentTime) * 1000 + 50));
    }
    function preview(k) {
        var p = parseKey(k);
        if (p) tone(440 * Math.pow(2, (midi(p) - 69) / 12), audio().currentTime + 0.01, 0.35);
    }

    // ── Edytor ───────────────────────────────────────────────────────────
    function mount(el, data, opts) {
        opts = opts || {};
        var L = opts.L || {};
        var d = data && data.kind === 'staff' ? JSON.parse(JSON.stringify(data))
            : { kind: 'staff', clef: opts.clef || 'treble', notes: [] };
        var dur = 4, dot = false, acc = '', oct = d.clef === 'bass' ? 2 : 4, sel = null;
        var names = L.names || LETTERS;     // po polsku H zamiast B

        function changed() { if (opts.onChange) opts.onChange(hasNotes(d) ? d : null); }
        function ui() {
            // telefon: jedna oktawa (klawisze do trafienia palcem), komputer: dwie
            var octs = global.matchMedia && global.matchMedia('(max-width: 760px)').matches ? 1 : 2;
            var keys = '';
            for (var o = 0; o < octs; o++) {
                LETTERS.forEach(function (l, li) {
                    keys += '<button type="button" class="pk-w" data-k="' + l + (oct + o) + '">' + names[li] + '<small>' + (oct + o) + '</small></button>';
                });
            }
            var blacks = '';
            for (var o2 = 0; o2 < octs; o2++) {
                ['C#', 'D#', '', 'F#', 'G#', 'A#', ''].forEach(function (b, bi) {
                    blacks += b ? '<button type="button" class="pk-b" style="--i:' + (o2 * 7 + bi) + '" data-k="' + b + (oct + o2) + '" aria-label="' + b + (oct + o2) + '"></button>' : '';
                });
            }
            el.innerHTML =
                '<div class="rf-bar">' +
                '<div class="seg"><button type="button" data-clef="treble" class="' + (d.clef === 'treble' ? 'active' : '') + '">' + (L.treble || 'Treble') + '</button>' +
                '<button type="button" data-clef="bass" class="' + (d.clef === 'bass' ? 'active' : '') + '">' + (L.bassClef || 'Bass') + '</button></div>' +
                '<button type="button" class="btn btn-sm" data-act="play">▶ ' + (L.play || 'Play') + '</button>' +
                '<span class="rf-bpm">' + (opts.bpm || 90) + ' BPM</span><span class="rf-gap"></span>' +
                '<button type="button" class="btn btn-ghost btn-sm" data-act="clear">' + (L.clear || 'Clear') + '</button></div>' +
                '<div class="stf-view" data-view></div>' +
                '<div class="stf-tools">' +
                '<div class="seg stf-dur">' + [1, 2, 4, 8, 16].map(function (v) {
                    return '<button type="button" data-dur="' + v + '" class="' + (dur === v ? 'active' : '') + '" title="' + ((L.durs || {})[v] || '') + '">' + ({ 1: '1', 2: '½', 4: '¼', 8: '⅛', 16: '1/16' })[v] + '</button>';
                }).join('') + '</div>' +
                '<button type="button" class="btn btn-ghost btn-sm' + (dot ? ' on' : '') + '" data-act="dot" title="' + (L.dot || '') + '">•</button>' +
                '<button type="button" class="btn btn-ghost btn-sm' + (acc === '#' ? ' on' : '') + '" data-act="sharp">♯</button>' +
                '<button type="button" class="btn btn-ghost btn-sm' + (acc === 'b' ? ' on' : '') + '" data-act="flat">♭</button>' +
                '<button type="button" class="btn btn-ghost btn-sm" data-act="rest">' + (L.rest || 'Rest') + '</button>' +
                '<button type="button" class="btn btn-ghost btn-sm" data-act="del" title="' + (L.del || '') + '">⌫</button>' +
                '</div>' +
                '<div class="pk-wrap"><button type="button" class="btn btn-ghost btn-sm pk-oct" data-act="down" title="' + (L.octDown || '') + '">−8</button>' +
                '<div class="pk" style="--w:' + (7 * octs) + '">' + keys + blacks + '</div>' +
                '<button type="button" class="btn btn-ghost btn-sm pk-oct" data-act="up" title="' + (L.octUp || '') + '">+8</button></div>' +
                '<div class="rf-help">' + (L.help || '') + '</div>';
            draw();
        }
        function draw(now) {
            var v = el.querySelector('[data-view]');
            if (!v) return;
            render(v, d, { sel: sel, now: now, width: v.clientWidth || 560 });
            if (!d.notes.length) v.insertAdjacentHTML('beforeend', '<div class="stf-empty">' + (L.empty || '') + '</div>');
        }
        function addNote(k) {
            var n = { k: k, d: dur, dot: dot };
            if (sel != null) { d.notes[sel] = n; sel = sel + 1 < d.notes.length ? sel + 1 : null; }
            else d.notes.push(n);
            if (k !== 'r') preview(k);
            draw(); changed();
        }
        function withAcc(k) {
            // klawisz biały + wybrany ♯/♭ (jednorazowo)
            if (!acc || k.length !== 2) return k;
            var out = k[0] + acc + k[1];
            acc = '';
            el.querySelectorAll('[data-act=sharp],[data-act=flat]').forEach(function (b) { b.classList.remove('on'); });
            return out;
        }
        el.addEventListener('click', function (e) {
            var g = e.target.closest('.stf-note');
            if (g) { sel = sel === +g.dataset.i ? null : +g.dataset.i; draw(); el.focus(); return; }
            var b = e.target.closest('button');
            if (!b) return;
            if (b.dataset.k) { addNote(withAcc(b.dataset.k)); return; }
            if (b.dataset.dur) {
                dur = +b.dataset.dur;
                el.querySelectorAll('[data-dur]').forEach(function (x) { x.classList.toggle('active', x === b); });
                if (sel != null) { d.notes[sel].d = dur; draw(); changed(); }
                return;
            }
            if (b.dataset.clef && b.dataset.clef !== d.clef) {
                d.clef = b.dataset.clef; oct = d.clef === 'bass' ? 2 : 4; ui(); changed(); return;
            }
            var act = b.dataset.act;
            if (act === 'dot') { dot = !dot; b.classList.toggle('on', dot); if (sel != null) { d.notes[sel].dot = dot; draw(); changed(); } }
            else if (act === 'sharp' || act === 'flat') {
                var a = act === 'sharp' ? '#' : 'b';
                if (sel != null && d.notes[sel].k !== 'r') {
                    var p = parseKey(d.notes[sel].k);
                    d.notes[sel].k = p.l + (p.acc === a ? '' : a) + p.o; draw(); changed(); return;
                }
                acc = acc === a ? '' : a;
                el.querySelectorAll('[data-act=sharp],[data-act=flat]').forEach(function (x) { x.classList.toggle('on', x.dataset.act === act && !!acc); });
            }
            else if (act === 'rest') addNote('r');
            else if (act === 'del') {
                if (sel != null) { d.notes.splice(sel, 1); sel = sel < d.notes.length ? sel : null; }
                else d.notes.pop();
                draw(); changed();
            }
            else if (act === 'up' || act === 'down') { oct = Math.max(1, Math.min(6, oct + (act === 'up' ? 1 : -1))); ui(); }
            else if (act === 'clear') {
                if (hasNotes(d) && !global.confirm(L.clearQ || 'Clear?')) return;
                d.notes = []; sel = null; draw(); changed();
            }
            else if (act === 'play') {
                if (b.classList.contains('on')) { stop(); return; }
                b.classList.add('on'); b.textContent = '■ ' + (L.stop || 'Stop');
                play(d, opts.bpm, function (i) { draw(i); }, function () {
                    draw();
                    var pb = el.querySelector('[data-act="play"]');
                    if (pb) { pb.classList.remove('on'); pb.textContent = '▶ ' + (L.play || 'Play'); }
                });
            }
        });
        // klawiatura komputera: c d e f g a h/b, 1–5 długość, . kropka,
        // r pauza, + / − oktawa, ↑ ↓ przesuwa zaznaczoną nutę
        el.tabIndex = 0;
        el.addEventListener('keydown', function (e) {
            if (e.target !== el) return;
            var k = e.key.toLowerCase();
            var letter = { c: 'C', d: 'D', e: 'E', f: 'F', g: 'G', a: 'A', h: 'B', b: 'B' }[k];
            if (letter && !e.ctrlKey && !e.metaKey) { e.preventDefault(); addNote(withAcc(letter + oct)); return; }
            if (/^[1-5]$/.test(k)) { e.preventDefault(); el.querySelector('[data-dur="' + [1, 2, 4, 8, 16][+k - 1] + '"]').click(); return; }
            if (k === '.') { e.preventDefault(); el.querySelector('[data-act=dot]').click(); return; }
            if (k === 'r') { e.preventDefault(); addNote('r'); return; }
            if (k === '+' || k === '=') { e.preventDefault(); el.querySelector('[data-act=up]').click(); return; }
            if (k === '-') { e.preventDefault(); el.querySelector('[data-act=down]').click(); return; }
            if (k === 'backspace' || k === 'delete') { e.preventDefault(); el.querySelector('[data-act=del]').click(); return; }
            if (k === ' ') { e.preventDefault(); el.querySelector('[data-act=play]').click(); return; }
            if (sel != null && (k === 'arrowup' || k === 'arrowdown') && d.notes[sel].k !== 'r') {
                e.preventDefault();
                var p = parseKey(d.notes[sel].k), st = step(p) + (k === 'arrowup' ? 1 : -1);
                var np = { l: LETTERS[((st % 7) + 7) % 7], acc: '', o: Math.floor(st / 7) };
                if (np.o >= 1 && np.o <= 7) { d.notes[sel].k = np.l + np.o; preview(d.notes[sel].k); draw(); changed(); }
                return;
            }
            if (k === 'arrowleft' || k === 'arrowright') {
                e.preventDefault();
                if (!d.notes.length) return;
                sel = sel == null ? d.notes.length - 1 : Math.max(0, Math.min(d.notes.length - 1, sel + (k === 'arrowright' ? 1 : -1)));
                draw();
            }
            if (k === 'escape' && sel != null) { e.stopPropagation(); sel = null; draw(); }
        });
        ui();
        // większe / mniejsze okno → pięciolinia na nową szerokość
        var onResize = function () { draw(); };
        global.addEventListener('resize', onResize);
        return { get: function () { return hasNotes(d) ? d : null; },
                 destroy: function () { stop(); global.removeEventListener('resize', onResize); el.innerHTML = ''; } };
    }

    global.JStaff = { mount: mount, render: render, play: play, stop: stop, hasNotes: hasNotes };
})(window);
