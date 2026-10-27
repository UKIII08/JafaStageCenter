// Edytor piosenki — tryb „Kafelki": części jako karty, akordy klikane nad
// sylabą z palety tonacji. Źródłem prawdy zostaje pole tekstowe (#song-content)
// w formacie [Akord]tekst — kafelki tylko je czytają i zapisują, więc zapis,
// podgląd, Studio i aplikacja desktop działają jak dotąd.
// Podział na części = ta sama reguła co Studio (control_logic.js) i serwer
// (music_core.parse_song_sections): pusta linia dzieli, pierwsza krótka linia
// bez akordu to nazwa części.
(function () {
    'use strict';
    var ta = document.getElementById('song-content');
    var root = document.getElementById('tiles');
    if (!ta || !root) return;
    var L = (window.SONG_EDITOR_I18N || {}).tiles || {};
    var $ = function (id) { return document.getElementById(id); };
    var notationInput = $('f-notation'), keyInput = $('song-key');
    var C = window.jafaChords || {};
    var sections = [];
    var editing = {};          // indeksy kafelków w trybie edycji tekstu
    var picker = null;         // otwarta paleta {sec, line, pos, chordIdx}

    function esc(s) {
        return String(s).replace(/[&<>"]/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
        });
    }

    // ── Model ────────────────────────────────────────────────────────────
    function parseSong(text) {
        text = (text || '').replace(/\r/g, '').replace(/(\n\s*){2,}\n/g, '\n\n');
        return text.split(/\n\s*\n/).filter(function (b) { return b.trim(); }).map(function (block) {
            var lines = block.replace(/^\n+|\s+$/g, '').split('\n');
            var label = '';
            if (lines.length && lines[0].indexOf('[') < 0 && lines[0].trim().length < 30) {
                label = lines.shift().trim();
            }
            return { label: label, lines: lines };
        });
    }
    function serialize(secs) {
        return secs.map(function (s) {
            var out = [];
            if (s.label.trim()) out.push(s.label.trim());
            s.lines.forEach(function (l) { out.push(l.replace(/\s+$/, '')); });
            while (out.length && !out[out.length - 1].trim()) out.pop();
            return out.join('\n');
        }).filter(function (b) { return b.trim(); }).join('\n\n');
    }
    // Linia „Ła[G/B]ska" ↔ {text: "Łaska", chords: [{pos: 2, name: "G/B"}]}
    function parseLine(line) {
        var text = '', chords = [], re = /\[([^\[\]]*)\]/g, last = 0, m;
        while ((m = re.exec(line))) {
            text += line.slice(last, m.index);
            if (m[1].trim()) chords.push({ pos: text.length, name: m[1].trim() });
            last = re.lastIndex;
        }
        text += line.slice(last);
        return { text: text, chords: chords };
    }
    function buildLine(p) {
        var out = '', i = 0, cs = p.chords.slice().sort(function (a, b) { return a.pos - b.pos; });
        cs.forEach(function (c) {
            out += p.text.slice(i, c.pos) + '[' + c.name + ']';
            i = c.pos;
        });
        return out + p.text.slice(i);
    }

    // Zapis z kafelków do pola tekstowego → podgląd i analiza (song-editor.js)
    function commit() {
        ta.value = serialize(sections);
        ta.dispatchEvent(new Event('input'));
    }
    function load() {
        sections = parseSong(ta.value);
        render();
    }

    // ── Paleta akordów tonacji ───────────────────────────────────────────
    function songKey() {
        var k = (keyInput && (keyInput.value || keyInput.placeholder) || '').trim();
        if (!k) return null;
        var minor = /m$/.test(k) && !/maj$/i.test(k) || /^[a-h]/.test(k);
        var rootName = k.replace(/m$/, '');
        rootName = rootName.charAt(0).toUpperCase() + rootName.slice(1);
        if (C.convert) rootName = C.convert(rootName, 'international');
        return { root: rootName, minor: minor };
    }
    // Pisownia zależna od tonacji: w H-dur jest Dis-moll, nie Es-moll.
    var PC = { C: 0, 'C#': 1, Db: 1, D: 2, 'D#': 3, Eb: 3, E: 4, F: 5, 'F#': 6, Gb: 6, G: 7,
               'G#': 8, Ab: 8, A: 9, 'A#': 10, Bb: 10, B: 11, Cb: 11 };
    var SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    var FLAT = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B'];
    var FLAT_MAJORS = { 5: 1, 10: 1, 3: 1, 8: 1, 1: 1, 6: 1 };   // F Bb Eb Ab Db Gb
    function palette() {
        var k = songKey();
        var pc = k ? PC[k.root] : undefined;
        if (pc === undefined) {
            return ['C', 'D', 'Em', 'F', 'G', 'Am', 'A', 'Dm', 'E', 'Bm'].map(shown);
        }
        // tonacja molowa → pisownia jak w równoległej durowej
        var major = k.minor ? (pc + 3) % 12 : pc;
        var names = FLAT_MAJORS[major] || (k.root.indexOf('b') > 0) ? FLAT : SHARP;
        var deg = k.minor
            ? [[0, 'm'], [3, ''], [5, 'm'], [7, 'm'], [7, ''], [8, ''], [10, '']]      // i III iv v V VI VII
            : [[0, ''], [2, 'm'], [4, 'm'], [5, ''], [7, ''], [9, 'm'], [7, '7'], [0, 'sus4']];  // I ii iii IV V vi V7 Isus4
        return deg.map(function (d) { return shown(names[(pc + d[0]) % 12] + d[1]); });
    }
    // Nazwa w notacji, w której użytkownik pisze (polska: H, B, Fis)
    function shown(ch) {
        return (notationInput.value === 'polish' && C.convert) ? C.convert(ch, 'polish') : ch;
    }
    function usedChords() {
        var seen = {}, out = [];
        (ta.value.match(/\[([^\[\]]+)\]/g) || []).forEach(function (m) {
            var c = m.slice(1, -1).trim();
            if (c && !seen[c]) { seen[c] = 1; out.push(c); }
        });
        return out.slice(0, 16);
    }
    var CHORD_OK = /^([A-Ha-h](#|b|is|es|s)?|[AaEe]s)(m|maj|min|dim|aug|sus|add|\+|°|ø|△|[0-9#b()\/,-]|[A-Ha-h](#|b|is|es)?)*$|^N\.?C\.?$/;

    // ── Rysowanie ────────────────────────────────────────────────────────
    function render() {
        closePicker();
        if (!sections.length) { renderStart(); return; }
        var html = sections.map(renderTile).join('');
        html += '<div class="tl-add">' +
            '<span class="tl-add-lbl">' + esc(L.addPart) + '</span>' +
            ['intro', 'verse', 'chorus', 'bridge', 'outro'].map(function (k) {
                return '<button type="button" class="btn btn-ghost btn-sm" data-add="' + k + '">' + esc(L.names[k]) + '</button>';
            }).join('') + '</div>';
        root.innerHTML = html;
    }
    function renderStart() {
        root.innerHTML =
            '<div class="tl-start">' +
            '<div class="tl-start-t">' + esc(L.startTitle) + '</div>' +
            '<p class="hint">' + esc(L.startHint) + '</p>' +
            '<textarea id="tl-paste" rows="9" spellcheck="false" placeholder="' + esc(L.pastePh) + '"></textarea>' +
            '<div class="tl-start-or"><span>' + esc(L.or) + '</span>' +
            '<button type="button" class="btn btn-ghost" data-add="verse">' + esc(L.startEmpty) + '</button></div>' +
            '</div>';
        var box = $('tl-paste'), t = null;
        box.addEventListener('paste', function () { setTimeout(function () { takePaste(box.value); }, 0); });
        box.addEventListener('input', function () {
            clearTimeout(t);
            t = setTimeout(function () { if (box.value.split('\n').length > 2) takePaste(box.value); }, 900);
        });
    }
    function renderTile(s, si) {
        var name = s.label || '';
        var body;
        if (editing[si] || !s.lines.length) {
            body = '<textarea class="tl-text" data-sec="' + si + '" rows="' + Math.max(3, s.lines.length + 1) +
                '" spellcheck="false" placeholder="' + esc(L.textPh) + '">' + esc(s.lines.join('\n')) + '</textarea>' +
                '<div class="tl-foot"><button type="button" class="btn btn-sm" data-done="' + si + '">' + esc(L.done) + '</button></div>';
        } else {
            body = '<div class="tl-lines">' + s.lines.map(function (l, li) { return renderLine(si, li, l); }).join('') + '</div>' +
                '<div class="tl-foot"><button type="button" class="btn btn-ghost btn-sm" data-edit="' + si + '">' + esc(L.editText) + '</button>' +
                '<span class="tl-tip">' + esc(L.clickTip) + '</span></div>';
        }
        return '<section class="tl-card" data-sec="' + si + '">' +
            '<div class="tl-head">' +
            '<input class="tl-name' + (name ? '' : ' empty') + '" data-sec="' + si + '" value="' + esc(name) + '" list="tl-names" ' +
            'placeholder="' + esc(L.namePh) + '" aria-label="' + esc(L.namePh) + '" maxlength="29">' +
            '<div class="tl-tools">' +
            '<button type="button" class="tl-ic" data-up="' + si + '" title="' + esc(L.up) + '" aria-label="' + esc(L.up) + '"' + (si ? '' : ' disabled') + '>↑</button>' +
            '<button type="button" class="tl-ic" data-down="' + si + '" title="' + esc(L.down) + '" aria-label="' + esc(L.down) + '"' + (si < sections.length - 1 ? '' : ' disabled') + '>↓</button>' +
            '<button type="button" class="tl-ic" data-dup="' + si + '" title="' + esc(L.dup) + '" aria-label="' + esc(L.dup) + '">⧉</button>' +
            '<button type="button" class="tl-ic danger" data-del="' + si + '" title="' + esc(L.del) + '" aria-label="' + esc(L.del) + '">✕</button>' +
            '</div></div>' + body + '</section>';
    }
    // Linia w trybie akordów: każdy znak klikalny, akordy nad sylabami
    // (ten sam układ par akord+sylaba co u zespołu — akordy nie nachodzą).
    function renderLine(si, li, line) {
        var p = parseLine(line);
        var byPos = {};
        p.chords.forEach(function (c, ci) { (byPos[c.pos] = byPos[c.pos] || []).push(ci); });
        var html = '', i = 0, n = p.text.length;
        var ch = function (k) {
            var c = p.text.charAt(k);
            return '<span class="c' + (c === ' ' ? ' sp' : '') + '" data-pos="' + k + '">' + (c === ' ' ? ' ' : esc(c)) + '</span>';
        };
        var pair = function (ci, syl) {
            return '<span class="tl-pair"><button type="button" class="tl-ch" data-ci="' + ci + '">' +
                esc(p.chords[ci].name) + '</button><span class="tl-syl">' + (syl || '&#8203;') + '</span></span>';
        };
        while (i <= n) {
            var list = byPos[i];
            if (list) {
                // kilka akordów w jednym miejscu ([G][D/F#]tekst) — puste pary
                for (var j = 0; j < list.length - 1; j++) html += pair(list[j], '');
                // sylaba = znaki do spacji albo do następnego akordu
                var k = i, syl = '';
                while (k < n && p.text.charAt(k) !== ' ' && (k === i || !byPos[k])) { syl += ch(k); k++; }
                html += pair(list[list.length - 1], syl);
                if (k === i) {                // akord przed spacją albo na końcu
                    if (i === n) break;
                    html += ch(i);
                    k = i + 1;
                }
                i = k;
                continue;
            }
            if (i === n) break;
            html += ch(i);
            i++;
        }
        html += '<button type="button" class="tl-plus" data-pos="' + n + '" title="' + esc(L.addEnd) + '" aria-label="' + esc(L.addEnd) + '">+</button>';
        var chordOnly = !p.text.trim() && p.chords.length;
        return '<div class="tl-line' + (chordOnly ? ' only' : '') + (p.text.trim() || p.chords.length ? '' : ' blank') +
            '" data-sec="' + si + '" data-line="' + li + '">' + html + '</div>';
    }

    // ── Paleta (popover / dolny panel na telefonie) ──────────────────────
    function openPicker(si, li, pos, ci, anchor) {
        closePicker();
        var p = parseLine(sections[si].lines[li]);
        var cur = ci != null ? p.chords[ci].name : '';
        var word = ci != null ? '' : (p.text.slice(pos).split(' ')[0] || '');
        picker = { si: si, li: li, pos: ci != null ? p.chords[ci].pos : pos, ci: ci };
        var used = usedChords().filter(function (c) { return palette().indexOf(c) < 0; });
        var el = document.createElement('div');
        el.className = 'tl-picker';
        el.setAttribute('role', 'dialog');
        el.innerHTML =
            '<div class="tl-pk-head">' + esc(cur ? L.changeChord : L.addChord) +
            (word ? ' <b>„' + esc(word) + '”</b>' : '') +
            '<button type="button" class="tl-ic" data-pk="close" aria-label="' + esc(L.close) + '">✕</button></div>' +
            '<div class="tl-pk-lbl">' + esc(songKey() ? L.inKey.replace('%(key)s', shown((songKey().root) + (songKey().minor ? 'm' : ''))) : L.common) + '</div>' +
            '<div class="tl-pk-row">' + palette().map(function (c) {
                return '<button type="button" class="tl-pk-c' + (c === cur ? ' on' : '') + '" data-pick="' + esc(c) + '">' + esc(c) + '</button>';
            }).join('') + '</div>' +
            (used.length ? '<div class="tl-pk-lbl">' + esc(L.inSong) + '</div><div class="tl-pk-row">' + used.map(function (c) {
                return '<button type="button" class="tl-pk-c' + (c === cur ? ' on' : '') + '" data-pick="' + esc(c) + '">' + esc(c) + '</button>';
            }).join('') + '</div>' : '') +
            '<form class="tl-pk-form"><input id="tl-pk-in" value="' + esc(cur) + '" placeholder="' + esc(L.otherPh) + '" autocomplete="off" spellcheck="false">' +
            '<button type="submit" class="btn btn-sm">' + esc(cur ? L.change : L.insert) + '</button></form>' +
            '<div class="tl-pk-err" id="tl-pk-err" hidden>' + esc(L.badChord) + '</div>' +
            '<div class="tl-pk-foot">' +
            '<button type="button" class="btn btn-ghost btn-sm" data-pk="left" title="' + esc(L.moveLeft) + '">←</button>' +
            '<button type="button" class="btn btn-ghost btn-sm" data-pk="right" title="' + esc(L.moveRight) + '">→</button>' +
            '<span class="tl-pk-move">' + esc(L.move) + '</span>' +
            (cur ? '<button type="button" class="btn btn-danger btn-sm" data-pk="remove">' + esc(L.remove) + '</button>' : '') +
            '</div>';
        document.body.appendChild(el);
        if (window.matchMedia('(max-width: 700px)').matches) {
            el.classList.add('sheet');
        } else {
            var r = anchor.getBoundingClientRect();
            var left = Math.min(window.innerWidth - el.offsetWidth - 12, Math.max(12, r.left - 12));
            var top = r.bottom + 8;
            if (top + el.offsetHeight > window.innerHeight - 12) top = Math.max(12, r.top - el.offsetHeight - 8);
            el.style.left = left + 'px';
            el.style.top = top + 'px';
        }
        picker.el = el;
        if (!cur) {
            var first = el.querySelector('[data-pick]');
            if (first && !window.matchMedia('(max-width: 700px)').matches) first.focus();
        } else {
            $('tl-pk-in').select();
        }
        // przesunięcie akordu nie ma sensu, gdy go jeszcze nie ma
        if (!cur) el.querySelectorAll('[data-pk=left],[data-pk=right],.tl-pk-move').forEach(function (b) { b.hidden = true; });
    }
    function closePicker() {
        if (picker && picker.el) picker.el.remove();
        picker = null;
    }
    function applyChord(name) {
        if (!picker) return;
        name = (name || '').trim().replace(/^\[|\]$/g, '');
        if (!name) return;
        if (!CHORD_OK.test(name.replace(/♯/g, '#').replace(/♭/g, 'b'))) {
            $('tl-pk-err').hidden = false;
            return;
        }
        var s = sections[picker.si], p = parseLine(s.lines[picker.li]);
        if (picker.ci != null) {
            p.chords[picker.ci].name = name;
        } else {
            var at = p.chords.filter(function (c) { return c.pos === picker.pos; });
            if (at.length) at[at.length - 1].name = name;
            else {
                // dopisywanie na końcu linii samych akordów: odstęp między akordami
                if (picker.pos === p.text.length && p.chords.length && !p.text.trim()) {
                    p.text += ' ';
                    picker.pos = p.text.length;
                }
                p.chords.push({ pos: picker.pos, name: name });
            }
        }
        s.lines[picker.li] = buildLine(p);
        closePicker();
        commit();
        render();
    }
    function moveChord(dir) {
        var s = sections[picker.si], p = parseLine(s.lines[picker.li]), c = p.chords[picker.ci];
        var np = Math.max(0, Math.min(p.text.length, c.pos + dir));
        if (np === c.pos) return;
        c.pos = np;
        s.lines[picker.li] = buildLine(p);
        var keep = { si: picker.si, li: picker.li };
        commit();
        render();
        // zostaw paletę otwartą na przesuniętym akordzie
        var pp = parseLine(sections[keep.si].lines[keep.li]);
        var ci = pp.chords.findIndex(function (x) { return x.pos === np && x.name === c.name; });
        var a = root.querySelector('.tl-line[data-sec="' + keep.si + '"][data-line="' + keep.li + '"] .tl-ch[data-ci="' + ci + '"]');
        if (a) openPicker(keep.si, keep.li, np, ci, a);
    }
    function removeChord() {
        var s = sections[picker.si], p = parseLine(s.lines[picker.li]);
        p.chords.splice(picker.ci, 1);
        s.lines[picker.li] = buildLine(p).replace(/\s+$/, '');
        closePicker();
        commit();
        render();
    }

    // ── Wklejanie na start ───────────────────────────────────────────────
    var pasteSeq = 0;
    function takePaste(text) {
        if (!text.trim()) return;
        var my = ++pasteSeq;
        fetch('/api/songs/analyze', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text, notation: notationInput.value })
        }).then(function (r) { return r.json(); }).then(function (d) {
            if (my !== pasteSeq) return;
            var meta = d.meta || {};
            var t = $('f-title'), b = $('f-bpm');
            if (meta.title && t && !t.value) t.value = meta.title;
            if (meta.key && keyInput && !keyInput.value) keyInput.value = meta.key;
            if (meta.bpm && b && !b.value) b.value = meta.bpm;
            ta.value = d.converted || text;
            ta.dispatchEvent(new Event('input'));
            load();
            var notes = [];
            (d.fixes || []).forEach(function (f) { if (L.fix[f]) notes.push(L.fix[f]); });
            if (notes.length) flashNote(notes.join(' '));
        });
    }
    function flashNote(msg) {
        var n = document.createElement('div');
        n.className = 'tl-note';
        n.textContent = msg;
        root.insertBefore(n, root.firstChild);
        setTimeout(function () { n.remove(); }, 9000);
    }

    // ── Akcje ────────────────────────────────────────────────────────────
    function nextName(kind) {
        var base = L.names[kind];
        if (kind !== 'verse') return base;
        var n = sections.filter(function (s) { return s.label.toLowerCase().indexOf(base.toLowerCase()) === 0; }).length;
        return base + ' ' + (n + 1);
    }
    root.addEventListener('click', function (e) {
        var b = e.target.closest('button, .c');
        if (!b) return;
        var d = b.dataset;
        if (d.add) {
            sections.push({ label: nextName(d.add), lines: [] });
            editing[sections.length - 1] = true;
            commit(); render();
            var tx = root.querySelector('.tl-text[data-sec="' + (sections.length - 1) + '"]');
            if (tx) tx.focus();
            return;
        }
        var si;
        if (d.up != null) { si = +d.up; swap(si, si - 1); return; }
        if (d.down != null) { si = +d.down; swap(si, si + 1); return; }
        if (d.dup != null) {
            si = +d.dup;
            sections.splice(si + 1, 0, { label: sections[si].label, lines: sections[si].lines.slice() });
            commit(); render(); return;
        }
        if (d.del != null) {
            si = +d.del;
            var has = sections[si].lines.some(function (l) { return l.trim(); });
            if (has && !window.confirm(L.delConfirm.replace('%(name)s', sections[si].label || '…'))) return;
            sections.splice(si, 1);
            editing = {};
            commit(); render(); return;
        }
        if (d.edit != null) { editing[+d.edit] = true; render(); var t2 = root.querySelector('.tl-text[data-sec="' + d.edit + '"]'); if (t2) t2.focus(); return; }
        if (d.done != null) { delete editing[+d.done]; render(); return; }
        var line = b.closest('.tl-line');
        if (!line) return;
        si = +line.dataset.sec;
        var li = +line.dataset.line;
        if (b.classList.contains('tl-ch')) { openPicker(si, li, null, +d.ci, b); return; }
        if (b.classList.contains('tl-plus') || b.classList.contains('c')) { openPicker(si, li, +d.pos, null, b); }
    });
    function swap(a, b) {
        if (b < 0 || b >= sections.length) return;
        var t = sections[a]; sections[a] = sections[b]; sections[b] = t;
        editing = {};
        commit(); render();
    }
    root.addEventListener('input', function (e) {
        var t = e.target, si = +t.dataset.sec;
        if (t.classList.contains('tl-name')) {
            sections[si].label = t.value.replace(/\[|\]/g, '');
            t.classList.toggle('empty', !t.value.trim());
            commit();
        } else if (t.classList.contains('tl-text')) {
            sections[si].lines = t.value.replace(/\r/g, '').split('\n');
            // pusta linia w tekście części = nowa część (jak w trybie tekstowym)
            commit();
        }
    });
    root.addEventListener('focusout', function (e) {
        // po zakończeniu pisania przeliczamy podział (pusta linia → nowa część)
        if (e.target.classList.contains('tl-text') || e.target.classList.contains('tl-name')) {
            setTimeout(function () {
                if (root.contains(document.activeElement) && document.activeElement.matches('.tl-text, .tl-name')) return;
                var before = sections.length;
                sections = parseSong(ta.value);
                if (sections.length !== before) editing = {};
                render();
            }, 120);
        }
    });

    document.addEventListener('click', function (e) {
        if (!picker) return;
        var t = e.target;
        if (picker.el.contains(t)) {
            var b = t.closest('button');
            if (!b) return;
            if (b.dataset.pick) applyChord(b.dataset.pick);
            else if (b.dataset.pk === 'close') closePicker();
            else if (b.dataset.pk === 'remove') removeChord();
            else if (b.dataset.pk === 'left') moveChord(-1);
            else if (b.dataset.pk === 'right') moveChord(1);
            return;
        }
        if (!t.closest('.tl-ch, .c, .tl-plus')) closePicker();
    });
    document.addEventListener('submit', function (e) {
        if (picker && e.target.closest('.tl-pk-form')) {
            e.preventDefault();
            applyChord($('tl-pk-in').value);
        }
    });
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && picker) closePicker();
    });
    document.addEventListener('input', function (e) {
        if (e.target.id === 'tl-pk-in') $('tl-pk-err').hidden = true;
    });

    // ── Przełącznik Kafelki / Tekst ──────────────────────────────────────
    var editorBox = document.querySelector('.se-editor');
    function setMode(m) {
        try { localStorage.setItem('jonathan-song-editor', m); } catch (e) {}
        document.querySelectorAll('#mode-seg button').forEach(function (b) { b.classList.toggle('active', b.dataset.mode === m); });
        root.hidden = m !== 'tiles';
        editorBox.hidden = m === 'tiles';
        if (m === 'tiles') load(); else closePicker();
    }
    document.querySelectorAll('#mode-seg button').forEach(function (b) {
        b.addEventListener('click', function () { setMode(b.dataset.mode); });
    });
    // Problem z numerem linii → pokaż go w trybie tekstu (tam są numery)
    var issues = $('issues');
    if (issues) issues.addEventListener('click', function (e) {
        if (e.target.closest('li[data-line]') && !root.hidden) setMode('text');
    }, true);
    // Notacja/tonacja zmieniają nazwy w palecie — nic do przerysowania
    var saved = 'tiles';
    try { saved = localStorage.getItem('jonathan-song-editor') || 'tiles'; } catch (e) {}
    setMode(saved === 'text' ? 'text' : 'tiles');

    window.SongTiles = { parseSong: parseSong, serialize: serialize, parseLine: parseLine, buildLine: buildLine };
})();
