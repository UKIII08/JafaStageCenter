/* Edytor aranżacji: forma (kafelki), obsada (role), siatka partii,
   notatki i nagrania pomysłów z telefonu. Dane startowe: window.ARR. */
(function () {
    'use strict';
    var A = window.ARR, L = A.L;
    var BASE = '/c/' + A.church + '/arrangements/' + A.id;

    // ── narzędzia ──
    function $(id) { return document.getElementById(id); }
    function el(tag, cls, text) {
        var e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text != null) e.textContent = text;
        return e;
    }
    function post(url, body) {
        return fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(body) })
            .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
    }
    function status(id, state) {
        var s = $(id); if (!s) return;
        s.classList.toggle('err', state === 'error');
        s.textContent = state === 'saving' ? L.saving : state === 'error' ? L.error : state === 'saved' ? L.saved : '';
        if (state === 'saved') setTimeout(function () { if (s.textContent === L.saved) s.textContent = ''; }, 1800);
    }
    function tileId() {
        var b = new Uint8Array(4); (window.crypto || window.msCrypto).getRandomValues(b);
        return Array.prototype.map.call(b, function (x) { return ('0' + x.toString(16)).slice(-2); }).join('');
    }
    function fmtTime(s) { s = Math.max(0, Math.round(s)); return Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2); }

    // Typ sekcji (kolor kafelka) — lustrzane do service.section_key
    var ALIAS = {
        intro: ['intro', 'wstep'], verse: ['verse', 'v', 'zwrotka', 'z', 'zw', 'strofa'],
        chorus: ['chorus', 'ch', 'c', 'refren', 'r', 'ref'],
        prechorus: ['pre chorus', 'prechorus', 'pre', 'pc', 'przedrefren'],
        bridge: ['bridge', 'b', 'br', 'most', 'mostek'], tag: ['tag'],
        outro: ['outro', 'ending', 'end', 'zakonczenie', 'koniec', 'coda']
    };
    var ALIAS_MAP = {};
    Object.keys(ALIAS).forEach(function (k) { ALIAS[k].forEach(function (a) { ALIAS_MAP[a] = k; }); });
    function fold(s) {
        return String(s || '').normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/ł/g, 'l').replace(/Ł/g, 'l')
            .toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
    }
    function secType(label) {
        var base = fold(label).replace(/\s*\d+$/, '').trim();
        return ALIAS_MAP[base] || 'other';
    }

    // ── FORMA ──
    var formTimer = null, saving = 0;
    function saveForm() {
        status('form-status', 'saving');
        clearTimeout(formTimer);
        formTimer = setTimeout(function () {
            formTimer = null; saving++;
            fetch(BASE + '/form', { method: 'POST', headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ form: A.form, base: A.rev }) })
                .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, code: r.status, d: d }; }); })
                .then(function (res) {
                    if (res.code === 409) {          // ktoś zmienił formę w międzyczasie
                        applyState(res.d); notice(L.conflict); status('form-status', '');
                    } else if (!res.ok) {
                        throw new Error(res.code);
                    } else {
                        A.form = res.d.form; A.rev = res.d.rev; status('form-status', 'saved'); renderGrid();
                    }
                })
                .catch(function () { status('form-status', 'error'); })
                .then(function () { saving--; });
        }, 450);
    }

    function renderForm() {
        var strip = $('form-strip');
        strip.innerHTML = '';
        if (!A.form.length) { strip.appendChild(el('span', 'empty', L.noTiles)); }
        A.form.forEach(function (t, i) {
            var tile = el('div', 'ftile');
            tile.dataset.id = t.id;
            tile.dataset.type = secType(t.label);

            var top = el('div', 'ftile-top');
            top.appendChild(el('span', 'ftile-n', String(i + 1)));
            var lab = el('input', 'ftile-label');
            lab.value = t.label; lab.maxLength = 40; lab.setAttribute('aria-label', t.label);
            lab.addEventListener('change', function () {
                var v = lab.value.trim();
                if (!v) { lab.value = t.label; return; }
                t.label = v; tile.dataset.type = secType(v); saveForm();
            });
            lab.addEventListener('keydown', function (e) { if (e.key === 'Enter') lab.blur(); });
            top.appendChild(lab);
            var x = el('button', 'ftile-x', '✕');
            x.type = 'button'; x.title = L.remove;
            x.onclick = function () { A.form.splice(A.form.indexOf(t), 1); renderForm(); saveForm(); };
            top.appendChild(x);
            tile.appendChild(top);

            var ctrl = el('div', 'ftile-ctrl');
            var rep = el('span', 'rep' + (t.repeat > 1 ? ' multi' : ''));
            rep.title = L.repeat;
            var minus = el('button', '', '−'); minus.type = 'button';
            var val = el('b', '', '×' + t.repeat);
            var plus = el('button', '', '+'); plus.type = 'button';
            minus.onclick = function () { if (t.repeat > 1) { t.repeat--; renderForm(); saveForm(); } };
            plus.onclick = function () { if (t.repeat < 8) { t.repeat++; renderForm(); saveForm(); } };
            rep.appendChild(minus); rep.appendChild(val); rep.appendChild(plus);
            ctrl.appendChild(rep);

            var opts = [{ value: '', text: L.noDynNone, short: L.noDyn }].concat(
                Object.keys(L.dyn).map(function (k) { return { value: k, text: L.dyn[k] }; }));
            var dyn = Pick.create({
                cls: 'sm dyn-pick' + (t.dyn ? ' set' : ''), options: opts, value: t.dyn || '', title: L.noDyn,
                onChange: function (v) { t.dyn = v; dyn.classList.toggle('set', !!v); saveForm(); renderGrid(); }
            });
            ctrl.appendChild(dyn);
            tile.appendChild(ctrl);

            var span = A.markers[t.id];
            if (span) tile.appendChild(el('span', 'ftile-time', fmtTime(span[0]) + ' – ' + fmtTime(span[1])));
            strip.appendChild(tile);
        });
    }

    if (window.Sortable) {
        Sortable.create($('form-strip'), {
            animation: 160, filter: 'input,select,button', preventOnFilter: false,
            draggable: '.ftile', delay: 120, delayOnTouchOnly: true,
            onEnd: function () {
                var byId = {};
                A.form.forEach(function (t) { byId[t.id] = t; });
                A.form = Array.prototype.map.call($('form-strip').querySelectorAll('.ftile'),
                    function (n) { return byId[n.dataset.id]; });
                renderForm(); saveForm();
            }
        });
    }

    function addTile(sec, label) {
        A.form.push({ id: tileId(), sec: sec, label: label, repeat: 1, dyn: '' });
        renderForm(); saveForm();
        $('add-tile-pop').open = false;
    }
    A.sections.forEach(function (s) {
        var b = el('button', '', s.label); b.type = 'button';
        b.onclick = function () { addTile(s.idx, s.label); };
        $('palette').appendChild(b);
    });
    $('custom-tile-add').onclick = function () {
        var v = $('custom-tile').value.trim();
        if (v) { addTile(null, v); $('custom-tile').value = ''; }
    };
    $('custom-tile').addEventListener('keydown', function (e) {
        if (e.key === 'Enter') { e.preventDefault(); $('custom-tile-add').click(); }
    });

    // ── OBSADA ──
    function rolesCall(body) {
        status('roles-status', 'saving');
        return post(BASE + '/roles', body).then(function (d) {
            A.roles = d.roles; if (d.rev) A.rev = d.rev; renderRoles(); renderGrid(); status('roles-status', 'saved');
        }).catch(function () { status('roles-status', 'error'); });
    }
    function renderRoles() {
        var box = $('role-chips');
        box.innerHTML = '';
        if (!A.roles.length) box.appendChild(el('span', 'empty', L.noRoles));
        A.roles.forEach(function (r) {
            var c = el('span', 'role-chip' + (r === A.myRole ? ' mine' : ''));
            c.dataset.role = r;
            c.appendChild(el('span', '', r));
            if (r === A.myRole) c.appendChild(el('span', 'me-tag', L.me));
            var x = el('button', '', '✕'); x.type = 'button'; x.title = L.remove;
            x.onclick = function () { if (confirm(L.removeRole)) rolesCall({ remove: r }); };
            c.appendChild(x);
            box.appendChild(c);
        });
        var sug = $('role-suggest');
        sug.innerHTML = '';
        A.suggestions.forEach(function (s) {
            var b = el('button', '', '+ ' + s); b.type = 'button';
            b.onclick = function () { rolesCall({ add: s }); };
            sug.appendChild(b);
        });
    }
    if (window.Sortable) {
        Sortable.create($('role-chips'), {
            animation: 160, filter: 'button', preventOnFilter: false, draggable: '.role-chip',
            delay: 120, delayOnTouchOnly: true,
            onEnd: function () {
                var order = Array.prototype.map.call($('role-chips').querySelectorAll('.role-chip'),
                    function (n) { return n.dataset.role; });
                rolesCall({ roles: order });
            }
        });
    }
    $('role-custom-add').onclick = function () {
        var v = $('role-custom').value.trim();
        if (v) { rolesCall({ add: v }); $('role-custom').value = ''; }
    };
    $('role-custom').addEventListener('keydown', function (e) {
        if (e.key === 'Enter') { e.preventDefault(); $('role-custom-add').click(); }
    });

    // ── SIATKA PARTII ──
    function cellKey(t, r) { return t + '|' + r; }
    function monoPref() { try { return localStorage.getItem('jonathan-tab-font') === '1'; } catch (e) { return false; } }

    // Kolor toru wg rodzaju instrumentu (jak w DAW: każdy instrument swój)
    var FAMILY = [
        ['vocal', /wokal|vocal|voice|spiew|chor|choir|lead|sopran|alt|tenor/],
        ['guitar', /gitar|guitar|elektr|akust|electric|acoustic|ukulele/],
        ['bass', /bas|bass/],
        ['keys', /klaw|keys|keyboard|piano|pianin|organ|organy|synth|pad/],
        ['drums', /perk|drum|bebn|cajon|percus|kongi|conga/],
        ['strings', /skrzyp|violin|wiolonc|cello|altowk|smycz|string/],
        ['winds', /flet|flute|sax|trab|trumpet|klarnet|clarinet|puzon/]
    ];
    function family(role) {
        var f = fold(role);
        for (var i = 0; i < FAMILY.length; i++) if (FAMILY[i][1].test(f)) return FAMILY[i][0];
        return 'other';
    }
    function secColor(label) {
        return 'var(--sec-' + ({ intro: 'intro', outro: 'intro', tag: 'intro', verse: 'verse',
            prechorus: 'pre', chorus: 'chorus', bridge: 'bridge' }[secType(label)] || 'other') + ')';
    }
    var narrow = window.matchMedia('(max-width: 760px)');

    // OŚ CZASU: klipy części u góry, tor na każdą rolę; w kratce notatka,
    // riff (mini-tabulatura) i nagranie pomysłu. Na telefonie: część po
    // części, pod nią wpisy wszystkich instrumentów.
    function renderGrid() {
        var wrap = $('grid-wrap');
        wrap.innerHTML = '';
        if (!A.roles.length || !A.form.length) {
            wrap.appendChild(el('div', 'tl-empty', A.form.length ? L.noRoles : L.noTiles));
            return;
        }
        if (narrow.matches) { renderStack(wrap); return; }
        var daw = el('div', 'daw');
        daw.style.setProperty('--n', A.form.length);
        // linijka: klipy części (szerokość wg powtórzeń)
        var cols = A.form.map(function (t) { return 'minmax(' + (150 + 40 * Math.min(t.repeat - 1, 3)) + 'px, ' + t.repeat + 'fr)'; });
        daw.style.gridTemplateColumns = '150px ' + cols.join(' ');
        daw.appendChild(el('div', 'daw-corner'));
        A.form.forEach(function (t) {
            var clip = el('div', 'daw-sec');
            clip.style.setProperty('--c', secColor(t.label));
            clip.appendChild(el('b', '', t.label));
            if (t.repeat > 1) clip.appendChild(el('span', 'daw-rep', '×' + t.repeat));
            if (t.dyn) clip.appendChild(el('span', 'daw-dyn', L.dyn[t.dyn]));
            daw.appendChild(clip);
        });
        A.roles.forEach(function (r) {
            var head = el('div', 'daw-lane fam-' + family(r) + (r === A.myRole ? ' mine' : ''));
            head.appendChild(el('i'));
            head.appendChild(el('span', '', r));
            if (r === A.myRole) head.appendChild(el('em', '', L.me));
            daw.appendChild(head);
            A.form.forEach(function (t) { daw.appendChild(cellButton(t, r)); });
        });
        wrap.appendChild(daw);
    }
    function renderStack(wrap) {
        A.form.forEach(function (t) {
            var sec = el('section', 'stk');
            var h = el('div', 'stk-head');
            h.style.setProperty('--c', secColor(t.label));
            h.appendChild(el('b', '', t.label + (t.repeat > 1 ? ' ×' + t.repeat : '')));
            if (t.dyn) h.appendChild(el('span', 'daw-dyn', L.dyn[t.dyn]));
            sec.appendChild(h);
            A.roles.forEach(function (r) {
                var row = el('div', 'stk-row fam-' + family(r));
                var lab = el('div', 'stk-role' + (r === A.myRole ? ' mine' : ''));
                lab.appendChild(el('i')); lab.appendChild(el('span', '', r));
                row.appendChild(lab);
                row.appendChild(cellButton(t, r));
                sec.appendChild(row);
            });
            wrap.appendChild(sec);
        });
    }
    function cellButton(t, r) {
        var c = A.cells[cellKey(t.id, r)] || {};
        var staff = c.riff && c.riff.kind === 'staff' && window.JStaff && JStaff.hasNotes(c.riff);
        var riff = !staff && c.riff && window.JRiff && JRiff.hasNotes(c.riff);
        var filled = c.note || c.memo || riff || staff;
        var b = el('button', 'daw-cell fam-' + family(r) + (filled ? ' filled' : ''));
        b.type = 'button';
        b.setAttribute('aria-label', r + ' · ' + t.label);
        if (c.note) b.appendChild(el('span', 'pnote' + (monoPref() ? ' mono' : ''), c.note));
        if (riff) {
            var pre = el('pre', 'daw-tab', JRiff.ascii(c.riff, 16));
            b.appendChild(pre);
        }
        if (staff) {
            var mini = el('span', 'daw-staff');
            b.appendChild(mini);
            JStaff.render(mini, c.riff, { width: 300, compact: true });
        }
        if (c.memo || riff || staff) {
            var chips = el('span', 'daw-chips');
            if (riff) chips.appendChild(el('span', 'chip riff', '🎸 ' + L.riff));
            if (staff) chips.appendChild(el('span', 'chip riff', '🎼 ' + L.notes));
            if (c.memo) {
                var m = el('span', 'chip memo');
                m.innerHTML = '<svg viewBox="0 0 24 24"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0 0 14 0M12 17v4"/></svg>';
                m.appendChild(document.createTextNode(c.memo_by || '♪'));
                chips.appendChild(m);
            }
            b.appendChild(chips);
        }
        if (!filled) b.appendChild(el('span', 'plus', '+'));
        b.onclick = function () { openCell(t, r); };
        return b;
    }
    narrow.addEventListener ? narrow.addEventListener('change', function () { renderGrid(); }) : narrow.addListener(renderGrid);

    // ── MODAL KOMÓRKI + nagrywanie ──
    var cur = null, noteTimer = null;
    function openCell(t, r) {
        cur = { tile: t.id, role: r, v: (A.cells[cellKey(t.id, r)] || {}).v || '' };
        $('cell-conflict').hidden = true;
        var c = A.cells[cellKey(t.id, r)] || {};
        $('cell-eyebrow').textContent = r;
        $('cell-title').textContent = t.label + (t.repeat > 1 ? ' ×' + t.repeat : '') + (t.dyn ? ' · ' + L.dyn[t.dyn] : '');
        $('cell-note').value = c.note || '';
        $('cell-mono').checked = monoPref();
        $('cell-note').classList.toggle('mono', monoPref());
        status('cell-status', '');
        showMemo(c);
        resetRec();
        // najpierw pokaż okno — edytor nut mierzy dostępną szerokość
        $('cell-modal').hidden = false;
        openRiff(c.riff);
        setTimeout(function () { if (!('ontouchstart' in window)) $('cell-note').focus(); }, 30);
    }
    // ── Riff (tabulatura) w komórce ──
    var riffEd = null, riffTimer = null, musicKind = 'tab';
    // Gitary i bas piszą tabulaturę, reszta (wokale, klawisze, smyczki,
    // dęte) nuty — ale każdy może przełączyć.
    function defaultKind(role) { return /^(guitar|bass)$/.test(family(role)) ? 'tab' : 'staff'; }
    function openRiff(riff) {
        var staff = riff && riff.kind === 'staff';
        var has = staff ? JStaff.hasNotes(riff) : !!(riff && JRiff.hasNotes(riff));
        // na dużym ekranie sekcja jest rozwinięta (jest na nią miejsce)
        $('riff-box').open = has || window.matchMedia('(min-width: 1001px)').matches;
        if (has) {
            musicKind = staff ? 'staff' : 'tab';
            mountMusic(riff);
        } else {
            showMusicChooser();
        }
    }
    // Pusta kratka: najpierw wybór (riff albo nuty), edytor dopiero potem —
    // komuś, kto chce tylko dopisać notatkę, nie pokazujemy 18 przycisków.
    function showMusicChooser() {
        if (riffEd) { riffEd.destroy(); riffEd = null; }
        musicKind = null;
        $('music-kind').hidden = true;
        var def = defaultKind(cur.role);
        var box = $('riff-editor');
        box.innerHTML = '<div class="music-choose">' +
            '<button type="button" class="btn' + (def === 'tab' ? '' : ' btn-ghost') + '" data-choose="tab">🎸 ' + L.chooseTab + '</button>' +
            '<button type="button" class="btn' + (def === 'staff' ? '' : ' btn-ghost') + '" data-choose="staff">🎼 ' + L.chooseStaff + '</button>' +
            '</div>';
        box.querySelectorAll('[data-choose]').forEach(function (b) {
            b.addEventListener('click', function () {
                musicKind = b.dataset.choose;
                mountMusic(null);
            });
        });
    }
    function mountMusic(data) {
        if (riffEd) riffEd.destroy();
        $('music-kind').hidden = false;
        document.querySelectorAll('#music-kind button').forEach(function (b) { b.classList.toggle('active', b.dataset.kind === musicKind); });
        var onChange = function (r) {
            status('cell-status', 'saving');
            clearTimeout(riffTimer);
            riffTimer = setTimeout(function () { riffTimer = null; saveRiff(r); }, 700);
        };
        var fam = family(cur.role);
        riffEd = musicKind === 'staff'
            ? JStaff.mount($('riff-editor'), data, { bpm: A.bpm, L: L.st, onChange: onChange,
                clef: fam === 'bass' ? 'bass' : 'treble' })
            : JRiff.mount($('riff-editor'), data && data.cols ? data : (fam === 'bass' ? { inst: 'bass', cols: [] } : null),
                { bpm: A.bpm, L: L.rf, onChange: onChange });
    }
    document.querySelectorAll('#music-kind button').forEach(function (b) {
        b.addEventListener('click', function () {
            if (b.dataset.kind === musicKind || !cur) return;
            var c = A.cells[cellKey(cur.tile, cur.role)] || {};
            var has = c.riff && (c.riff.kind === 'staff' ? JStaff.hasNotes(c.riff) : JRiff.hasNotes(c.riff));
            if (has && !confirm(L.switchKind)) return;
            flushRiff();
            musicKind = b.dataset.kind;
            if (has) saveRiff(null);
            mountMusic(null);
        });
    });
    function saveRiff(r) {
        if (!cur) return;
        var key = cellKey(cur.tile, cur.role);
        cellPost({ riff: r }, function (d) {
            A.cells[key] = Object.assign({}, A.cells[key] || {}, { riff: d.riff, v: d.v });
        }, { riff: r });
    }
    function flushRiff() {
        if (!riffTimer || !riffEd) return;
        clearTimeout(riffTimer); riffTimer = null; saveRiff(riffEd.get());
    }
    function closeCell() {
        if (rec && rec.state === 'recording') return;     // najpierw stop
        flushNote();
        flushRiff();
        if (window.JRiff) JRiff.stop();
        if (window.JStaff) JStaff.stop();
        $('cell-modal').hidden = true;
        var a = $('memo-audio'); a.pause();
        cur = null;
        renderGrid();
    }
    function showMemo(c) {
        var has = !!c.memo;
        $('memo-existing').hidden = !has;
        if (has) {
            $('memo-audio').src = c.memo;
            $('memo-by').textContent = c.memo_by ? L.by + ': ' + c.memo_by : '';
        } else { $('memo-audio').removeAttribute('src'); }
        $('rec-label').textContent = has ? L.rerec : L.rec;
    }
    function flushNote() {
        if (!noteTimer) return;
        clearTimeout(noteTimer); noteTimer = null; saveNote();
    }
    // Zapis kratki z numerem wersji. 409 = ktoś inny zmienił kratkę w tym
    // czasie: pokazujemy jego wersję i dajemy przywrócić własną.
    var mine = null;
    function cellPost(fields, ok, myVersion) {
        if (!cur) return;
        var target = cur, key = cellKey(cur.tile, cur.role);
        fetch(BASE + '/cell', { method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(Object.assign({ tile: target.tile, role: target.role, base: target.v }, fields)) })
            .then(function (r) { return r.json().then(function (d) { return { code: r.status, d: d }; }); })
            .then(function (res) {
                if (res.code === 409 && res.d.conflict) {
                    var theirs = res.d.cell || {};
                    A.cells[key] = theirs;
                    target.v = theirs.v || '';
                    mine = Object.assign(mine || {}, myVersion);
                    if (cur === target) {
                        $('cell-note').value = theirs.note || '';
                        openRiff(theirs.riff);
                        $('cell-conflict-text').textContent = L.cellConflict.replace('%(name)s', theirs.by || '?');
                        $('cell-conflict').hidden = false;
                    }
                    status('cell-status', '');
                    return;
                }
                if (res.code >= 400) throw new Error(res.code);
                target.v = res.d.v || '';
                ok(res.d);
                status('cell-status', 'saved');
            })
            .catch(function () { status('cell-status', 'error'); });
    }
    $('cell-conflict-mine').onclick = function () {
        if (!cur || !mine) return;
        if (mine.note !== undefined) { $('cell-note').value = mine.note; saveNote(); }
        if (mine.riff !== undefined) { openRiff(mine.riff); saveRiff(mine.riff); }
        mine = null;
        $('cell-conflict').hidden = true;
    };
    function saveNote() {
        if (!cur) return;
        var key = cellKey(cur.tile, cur.role), note = $('cell-note').value;
        status('cell-status', 'saving');
        cellPost({ note: note }, function (d) {
            A.cells[key] = Object.assign({}, A.cells[key] || {}, { note: note, v: d.v });
        }, { note: note });
    }
    $('cell-note').addEventListener('input', function () {
        status('cell-status', 'saving');
        clearTimeout(noteTimer);
        noteTimer = setTimeout(function () { noteTimer = null; saveNote(); }, 600);
    });
    $('cell-mono').onchange = function () {
        try { localStorage.setItem('jonathan-tab-font', this.checked ? '1' : '0'); } catch (e) {}
        $('cell-note').classList.toggle('mono', this.checked);
    };
    $('cell-close').onclick = closeCell;
    $('cell-modal').addEventListener('click', function (e) { if (e.target === this) closeCell(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !$('cell-modal').hidden) closeCell(); });
    $('memo-delete').onclick = function () {
        if (!cur || !confirm(L.delMemo)) return;
        var key = cellKey(cur.tile, cur.role);
        post(BASE + '/memo/delete', { tile: cur.tile, role: cur.role }).then(function () {
            A.cells[key] = Object.assign({}, A.cells[key] || {}, { memo: '', memo_by: '' });
            showMemo(A.cells[key]);
        });
    };

    var rec = null, chunks = [], recStart = 0, recTick = null, stream = null;
    function pickMime() {
        var opts = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/webm', 'audio/ogg;codecs=opus'];
        if (!window.MediaRecorder || !MediaRecorder.isTypeSupported) return '';
        for (var i = 0; i < opts.length; i++) if (MediaRecorder.isTypeSupported(opts[i])) return opts[i];
        return '';
    }
    function resetRec() {
        var b = $('rec-btn');
        b.classList.remove('on'); b.disabled = false;
        $('rec-time').textContent = '';
        $('rec-sub').hidden = false;
    }
    function stopStream() { if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; } }
    $('rec-btn').onclick = function () {
        var b = this;
        if (rec && rec.state === 'recording') { rec.stop(); return; }
        var mineNow = cur && A.cells[cellKey(cur.tile, cur.role)];
        if (mineNow && mineNow.memo && mineNow.memo_by && mineNow.memo_by !== A.me &&
                !confirm(L.replaceOther.replace('%(name)s', mineNow.memo_by))) return;
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
            window.panelNotice(L.noMic, 'error'); return;
        }
        navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: true } })
            .then(function (s) {
                stream = s; chunks = [];
                var mime = pickMime();
                rec = mime ? new MediaRecorder(s, { mimeType: mime, audioBitsPerSecond: 96000 }) : new MediaRecorder(s);
                var target = cur;
                rec.ondataavailable = function (e) { if (e.data && e.data.size) chunks.push(e.data); };
                rec.onstop = function () {
                    clearInterval(recTick); stopStream();
                    b.classList.remove('on'); b.disabled = true;
                    $('rec-label').textContent = L.uploading;
                    var blob = new Blob(chunks, { type: rec.mimeType || mime || 'audio/webm' });
                    var fd = new FormData();
                    fd.append('tile', target.tile); fd.append('role', target.role);
                    fd.append('audio', blob, 'memo');
                    fetch(BASE + '/memo', { method: 'POST', body: fd })
                        .then(function (r) { return r.json().then(function (d) { if (!r.ok) throw new Error(d.error || r.status); return d; }); })
                        .then(function (d) {
                            var key = cellKey(target.tile, target.role);
                            A.cells[key] = Object.assign({}, A.cells[key] || {}, { memo: d.memo, memo_by: d.memo_by });
                            if (cur && cur.tile === target.tile && cur.role === target.role) showMemo(A.cells[key]);
                            resetRec();
                        })
                        .catch(function (err) { window.panelNotice(err.message || L.error, 'error'); resetRec(); showMemo(A.cells[cellKey(target.tile, target.role)] || {}); });
                };
                rec.start(1000);
                recStart = Date.now();
                b.classList.add('on');
                $('rec-label').textContent = L.stop;
                $('rec-sub').hidden = true;
                $('rec-time').textContent = '0:00';
                recTick = setInterval(function () { $('rec-time').textContent = fmtTime((Date.now() - recStart) / 1000); }, 250);
            })
            .catch(function () { window.panelNotice(L.noMic, 'error'); });
    };

    // ── Kilka osób naraz: odświeżanie stanu i baner ze zmianami ──
    var noticeTimer = null;
    function notice(text) {
        var n = $('arr-notice');
        if (!n) return;
        n.textContent = text; n.hidden = false;
        clearTimeout(noticeTimer);
        noticeTimer = setTimeout(function () { n.hidden = true; }, 6000);
    }
    function applyState(s) {
        A.rev = s.rev; A.form = s.form; A.roles = s.roles; A.markers = s.markers || {}; A.cells = s.cells || {};
        renderForm(); renderRoles();
        if ($('cell-modal').hidden) renderGrid();
    }
    function refresh() {
        if (document.hidden || formTimer || saving) return;
        fetch(BASE + '/state').then(function (r) { return r.ok ? r.json() : null; }).then(function (s) {
            if (!s || formTimer || saving) return;
            if (s.rev !== A.rev) {
                applyState(s);
                notice(L.updatedBy + (s.updated_by ? ' ' + s.updated_by : '') + '.');
            } else if (JSON.stringify(s.cells) !== JSON.stringify(A.cells)) {
                A.cells = s.cells;
                if ($('cell-modal').hidden) renderGrid();
            }
        }).catch(function () {});
    }
    setInterval(refresh, 15000);
    window.addEventListener('focus', refresh);
    document.addEventListener('visibilitychange', function () { if (!document.hidden) refresh(); });

    renderForm();
    renderRoles();
    renderGrid();
})();
