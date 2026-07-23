// Edytor piosenki: walidacja formatu + akordów + sugestia tonacji na żywo
// (debounce) i jawny przycisk konwersji formatu "akordy nad tekstem".
// Teksty statusu przez window.SONG_EDITOR_I18N (patrz songs/form.html).
(function () {
    var ta = document.getElementById('song-content');
    if (!ta) return;
    var status = document.getElementById('chord-status');
    var keyInput = document.getElementById('song-key');
    var timer = null;
    var I18N = window.SONG_EDITOR_I18N || {};

    function t(key, fallback) {
        return (I18N[key] != null) ? I18N[key] : fallback;
    }

    // Ile "sekcji" (linia-etykieta bez akordów w nawiasach) — czysto po stronie
    // klienta, żeby dać natychmiastowy sygnał zanim odpowie serwer.
    function countSections(text) {
        var lines = text.split('\n');
        var n = 0;
        for (var i = 0; i < lines.length; i++) {
            var ln = lines[i].trim();
            if (!ln) continue;
            // Etykieta sekcji = linia bez [akordów], krótka, nie wygląda jak tekst.
            if (ln.indexOf('[') === -1 && ln.length <= 40
                && !/[.!?,;:]/.test(ln)) {
                var prev = i > 0 ? lines[i - 1].trim() : '';
                if (prev === '' || i === 0) n++;
            }
        }
        return n;
    }

    function hasUnclosedBracket(text) {
        // Nawias otwierający bez zamykającego przed następnym '[' lub końcem linii.
        var lines = text.split('\n');
        for (var i = 0; i < lines.length; i++) {
            var opens = 0;
            var s = lines[i];
            for (var j = 0; j < s.length; j++) {
                if (s[j] === '[') opens++;
                else if (s[j] === ']') opens--;
                if (opens < 0) opens = 0;
            }
            if (opens > 0) return true;
        }
        return false;
    }

    function localChordCount(text) {
        var m = text.match(/\[[^\]\n]+\]/g);
        return m ? m.length : 0;
    }

    function render(d) {
        if (!status) return;
        var text = ta.value;
        if (!text.trim()) { status.textContent = ''; status.className = 'song-status'; return; }

        // 1) Błąd twardy: niezamknięty nawias.
        if (hasUnclosedBracket(text)) {
            status.className = 'song-status is-warn';
            status.textContent = t('unclosed', 'Unclosed bracket.');
            return;
        }

        // Liczba akordów: serwer, a jeśli nie odpowiedział — licz lokalnie,
        // żeby nigdy nie twierdzić "brak akordów", gdy nawiasy są w tekście.
        var total = d ? d.total : localChordCount(text);
        var invalid = (d && d.invalid) ? d.invalid : [];
        var sections = countSections(text);

        // 2) Brak akordów w ogóle.
        if (!total) {
            status.className = 'song-status is-hint';
            status.textContent = t('noChords', 'No chords yet.');
            return;
        }

        // 3) Podsumowanie: liczba akordów + sekcji + status rozpoznania.
        var parts = [];
        parts.push(total + ' ' + t('chords', 'chords'));
        if (sections) parts.push(sections + ' ' + t('sections', 'sections'));
        if (invalid.length) {
            status.className = 'song-status is-warn';
            parts.push(t('notRecognized', 'not recognized') + ': ' + invalid.join(', '));
        } else {
            status.className = 'song-status is-ok';
            parts.push(t('allValid', 'all recognized'));
        }
        status.textContent = parts.join(' · ');
        if (d && keyInput && !keyInput.value && d.key) keyInput.placeholder = d.key;
    }

    function analyze() {
        // Natychmiastowy render lokalny (nawias/brak akordów), potem serwer.
        render(null);
        fetch('/api/songs/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: ta.value })
        }).then(function (r) { return r.json(); })
          .then(function (d) { render(d); })
          .catch(function () {});
    }

    ta.addEventListener('input', function () {
        clearTimeout(timer);
        timer = setTimeout(analyze, 400);
    });
    if (ta.value.trim()) analyze();

    var btn = document.getElementById('convert-format-btn');
    if (btn) btn.addEventListener('click', function () {
        fetch('/api/songs/convert-format', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: ta.value })
        }).then(function (r) { return r.json(); }).then(function (d) {
            if (d.changed) { ta.value = d.text; analyze(); }
            btn.textContent = d.changed
                ? t('converted', 'Converted — check the result')
                : t('convertNone', 'No chords-above-lyrics detected');
            setTimeout(function () {
                btn.textContent = t('convertBtn', 'Convert chords-above-lyrics');
            }, 2500);
        });
    });
})();
