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
    var formTimer = null;
    function saveForm() {
        status('form-status', 'saving');
        clearTimeout(formTimer);
        formTimer = setTimeout(function () {
            post(BASE + '/form', { form: A.form }).then(function (d) {
                A.form = d.form; status('form-status', 'saved'); renderGrid();
            }).catch(function () { status('form-status', 'error'); });
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

            var dyn = el('select', 'dyn' + (t.dyn ? ' set' : ''));
            dyn.setAttribute('aria-label', L.noDyn);
            var o0 = el('option', '', L.noDyn + '…'); o0.value = ''; dyn.appendChild(o0);
            Object.keys(L.dyn).forEach(function (k) {
                var o = el('option', '', L.dyn[k]); o.value = k;
                if (t.dyn === k) o.selected = true;
                dyn.appendChild(o);
            });
            dyn.onchange = function () { t.dyn = dyn.value; dyn.classList.toggle('set', !!t.dyn); saveForm(); renderGrid(); };
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
            A.roles = d.roles; renderRoles(); renderGrid(); status('roles-status', 'saved');
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

    function renderGrid() {
        var wrap = $('grid-wrap');
        wrap.innerHTML = '';
        var table = el('table', 'pgrid');
        var thead = el('thead'), hr = el('tr');
        hr.appendChild(el('th'));
        A.form.forEach(function (t) {
            var th = el('th');
            th.style.setProperty('--c', 'var(--sec-' + ({ intro: 'intro', outro: 'intro', tag: 'intro', verse: 'verse',
                prechorus: 'pre', chorus: 'chorus', bridge: 'bridge' }[secType(t.label)] || 'other') + ')');
            th.appendChild(el('i'));
            th.appendChild(document.createTextNode(t.label + (t.repeat > 1 ? ' ×' + t.repeat : '')));
            hr.appendChild(th);
        });
        thead.appendChild(hr); table.appendChild(thead);
        var tbody = el('tbody');
        if (!A.roles.length || !A.form.length) {
            var tr0 = el('tr', 'empty-row'), td0 = el('td', '', A.form.length ? L.noRoles : L.noTiles);
            td0.colSpan = A.form.length + 1; tr0.appendChild(td0); tbody.appendChild(tr0);
        }
        A.roles.forEach(function (r) {
            if (!A.form.length) return;
            var tr = el('tr');
            tr.appendChild(el('th', r === A.myRole ? 'mine' : '', r));
            A.form.forEach(function (t) {
                var td = el('td'), c = A.cells[cellKey(t.id, r)] || {};
                var b = el('button', 'pcell' + ((c.note || c.memo) ? ' filled' : ''));
                b.type = 'button';
                if (c.note) { b.appendChild(el('span', 'pnote' + (monoPref() ? ' mono' : ''), c.note)); }
                if (c.memo) {
                    var m = el('span', 'pmemo');
                    m.innerHTML = '<svg viewBox="0 0 24 24"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0 0 14 0M12 17v4"/></svg>';
                    m.appendChild(document.createTextNode(c.memo_by || '♪'));
                    b.appendChild(m);
                }
                if (!c.note && !c.memo) b.appendChild(el('span', 'plus', '+'));
                b.onclick = function () { openCell(t, r); };
                td.appendChild(b); tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        wrap.appendChild(table);
    }

    // ── MODAL KOMÓRKI + nagrywanie ──
    var cur = null, noteTimer = null;
    function openCell(t, r) {
        cur = { tile: t.id, role: r };
        var c = A.cells[cellKey(t.id, r)] || {};
        $('cell-eyebrow').textContent = r;
        $('cell-title').textContent = t.label + (t.repeat > 1 ? ' ×' + t.repeat : '') + (t.dyn ? ' · ' + L.dyn[t.dyn] : '');
        $('cell-note').value = c.note || '';
        $('cell-mono').checked = monoPref();
        $('cell-note').classList.toggle('mono', monoPref());
        status('cell-status', '');
        showMemo(c);
        resetRec();
        $('cell-modal').hidden = false;
        setTimeout(function () { if (!('ontouchstart' in window)) $('cell-note').focus(); }, 30);
    }
    function closeCell() {
        if (rec && rec.state === 'recording') return;     // najpierw stop
        flushNote();
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
    function saveNote() {
        if (!cur) return;
        var key = cellKey(cur.tile, cur.role), note = $('cell-note').value;
        status('cell-status', 'saving');
        post(BASE + '/cell', { tile: cur.tile, role: cur.role, note: note }).then(function () {
            A.cells[key] = Object.assign({}, A.cells[key] || {}, { note: note });
            status('cell-status', 'saved');
        }).catch(function () { status('cell-status', 'error'); });
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
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
            alert(L.noMic); return;
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
                        .catch(function (err) { alert(err.message || L.error); resetRec(); showMemo(A.cells[cellKey(target.tile, target.role)] || {}); });
                };
                rec.start(1000);
                recStart = Date.now();
                b.classList.add('on');
                $('rec-label').textContent = L.stop;
                $('rec-sub').hidden = true;
                $('rec-time').textContent = '0:00';
                recTick = setInterval(function () { $('rec-time').textContent = fmtTime((Date.now() - recStart) / 1000); }, 250);
            })
            .catch(function () { alert(L.noMic); });
    };

    renderForm();
    renderRoles();
    renderGrid();
})();
