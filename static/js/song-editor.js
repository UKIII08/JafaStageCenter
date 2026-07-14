// Edytor piosenki: walidacja akordów + sugestia tonacji na żywo (debounce)
// i jawny przycisk konwersji formatu "akordy nad tekstem".
(function () {
    var ta = document.getElementById('song-content');
    if (!ta) return;
    var status = document.getElementById('chord-status');
    var keyInput = document.getElementById('song-key');
    var timer = null;

    function analyze() {
        fetch('/api/songs/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: ta.value })
        }).then(function (r) { return r.json(); }).then(function (d) {
            if (!status) return;
            if (!d.total) { status.textContent = ''; return; }
            if (d.invalid.length) {
                status.style.color = '#f0a832';
                status.textContent = d.total + ' akordów — nierozpoznane: '
                    + d.invalid.join(', ');
            } else {
                status.style.color = '#2dce89';
                status.textContent = d.total + ' akordów — wszystkie poprawne';
            }
            if (keyInput && !keyInput.value && d.key) keyInput.placeholder = d.key;
        }).catch(function () {});
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
                ? 'Przekonwertowano — sprawdź wynik'
                : 'Nie wykryto akordów nad tekstem';
            setTimeout(function () {
                btn.textContent = 'Konwertuj akordy nad tekstem';
            }, 2500);
        });
    });
})();
