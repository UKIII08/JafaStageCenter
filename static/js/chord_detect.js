/* ============================================================
   CHORD DETECTION ENGINE — Silent Music Director
   Rozpoznaje akord z zestawu nut MIDI granych na pianinie.
   Odporny scorer: przewroty (slash), sus, septymy, add9, 6,
   brakująca kwinta, nuty przejściowe (melodia na górze).
   Czysta logika — testowalna bez hardware'u (Node + przeglądarka).
   ============================================================ */
(function (global) {
    'use strict';

    // Konwencja enharmoniczna spójna z resztą aplikacji
    var NOTE_NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B'];

    // Szablony akordów: interwały od prymy (półtony) + kara za złożoność
    // (mniejsza = prostszy, preferowany przy remisie).
    var TEMPLATES = [
        { q: 'maj',    ints: [0, 4, 7],           cx: 0.0 },
        { q: 'min',    ints: [0, 3, 7],           cx: 0.0 },
        { q: 'sus4',   ints: [0, 5, 7],           cx: 0.35 },
        { q: 'sus2',   ints: [0, 2, 7],           cx: 0.4 },
        { q: 'dim',    ints: [0, 3, 6],           cx: 0.5 },
        { q: 'aug',    ints: [0, 4, 8],           cx: 0.6 },
        { q: '5',      ints: [0, 7],              cx: 0.55 },
        { q: '7',      ints: [0, 4, 7, 10],       cx: 0.45 },
        { q: 'maj7',   ints: [0, 4, 7, 11],       cx: 0.5 },
        { q: 'm7',     ints: [0, 3, 7, 10],       cx: 0.5 },
        { q: 'm7b5',   ints: [0, 3, 6, 10],       cx: 0.75 },
        { q: 'dim7',   ints: [0, 3, 6, 9],        cx: 0.75 },
        { q: '6',      ints: [0, 4, 7, 9],        cx: 0.7 },
        { q: 'm6',     ints: [0, 3, 7, 9],        cx: 0.75 },
        { q: 'add9',   ints: [0, 4, 7, 2],        cx: 0.7 },
        { q: 'madd9',  ints: [0, 3, 7, 2],        cx: 0.75 },
        { q: '7sus4',  ints: [0, 5, 7, 10],       cx: 0.7 },
        { q: '9',      ints: [0, 4, 7, 10, 2],    cx: 0.9 },
        { q: 'maj9',   ints: [0, 4, 7, 11, 2],    cx: 0.95 },
        { q: 'm9',     ints: [0, 3, 7, 10, 2],    cx: 0.95 }
    ];

    // Waga składnika wg interwału — jak bardzo definiuje akord.
    function toneWeight(interval) {
        switch (interval) {
            case 0:  return 3.0;   // pryma
            case 3:  return 3.0;   // tercja mała
            case 4:  return 3.0;   // tercja wielka
            case 5:  return 2.6;   // kwarta (sus4 — definiująca)
            case 2:  return 2.4;   // sekunda (sus2 / 9)
            case 6:  return 1.6;   // kwinta zmniejszona
            case 8:  return 1.6;   // kwinta zwiększona
            case 7:  return 1.4;   // kwinta czysta (często pomijana)
            case 10: return 2.2;   // septyma mała
            case 11: return 2.2;   // septyma wielka
            case 9:  return 1.2;   // seksta / 13
            default: return 1.0;
        }
    }

    var EXTRA_PENALTY = 1.25;   // za każdą graną nutę nie należącą do akordu
    var SUFFIX = {
        maj: '', min: 'm', sus4: 'sus4', sus2: 'sus2', dim: 'dim', aug: 'aug',
        '5': '5', '7': '7', maj7: 'maj7', m7: 'm7', m7b5: 'm7b5', dim7: 'dim7',
        '6': '6', m6: 'm6', add9: 'add9', madd9: 'm(add9)', '7sus4': '7sus4',
        '9': '9', maj9: 'maj9', m9: 'm9'
    };

    function pc(n) { return ((n % 12) + 12) % 12; }

    /**
     * @param {number[]} midiNotes — numery MIDI aktualnie trzymanych nut
     * @returns {null | { name, root, quality, bass, notes, confidence }}
     */
    function detectChord(midiNotes) {
        if (!midiNotes || midiNotes.length === 0) return null;

        var sorted = midiNotes.slice().sort(function (a, b) { return a - b; });
        var bassPc = pc(sorted[0]);

        // Unikalne klasy wysokości
        var present = {};
        for (var i = 0; i < sorted.length; i++) present[pc(sorted[i])] = true;
        var pcs = Object.keys(present).map(Number);

        // Pojedyncza nuta — pokaż samą nazwę
        if (pcs.length === 1) {
            return { name: NOTE_NAMES[pcs[0]], root: pcs[0], quality: 'note', bass: pcs[0], notes: pcs, confidence: 1 };
        }

        var best = null;

        // Rozważamy TYLKO prymy faktycznie zagrane (obejmuje przewroty).
        for (var ri = 0; ri < pcs.length; ri++) {
            var root = pcs[ri];
            for (var ti = 0; ti < TEMPLATES.length; ti++) {
                var tpl = TEMPLATES[ti];
                var templatePcs = {};
                var score = 0;
                var t;
                // Punkty za składniki obecne / kara za brakujące
                for (t = 0; t < tpl.ints.length; t++) {
                    var tp = pc(root + tpl.ints[t]);
                    templatePcs[tp] = true;
                    var w = toneWeight(tpl.ints[t]);
                    if (present[tp]) score += w; else score -= w * 0.9;
                }
                // Kara za nuty grane, których szablon nie tłumaczy
                var extra = 0;
                for (var p = 0; p < pcs.length; p++) {
                    if (!templatePcs[pcs[p]]) extra++;
                }
                score -= extra * EXTRA_PENALTY;
                score -= tpl.cx;                       // preferuj proste
                // Premia gdy pryma jest w basie — rozstrzyga np. C6 (C w basie)
                // kontra Am7/C (te same nuty), zgodnie z intencją klawiszowca.
                if (root === bassPc) score += 1.4;

                if (!best || score > best.score) {
                    best = { score: score, root: root, quality: tpl.q };
                }
            }
        }

        if (!best) return null;

        var rootName = NOTE_NAMES[best.root];
        var suffix = SUFFIX[best.quality] !== undefined ? SUFFIX[best.quality] : best.quality;
        var name = rootName + suffix;
        // Slash tylko gdy bas ≠ pryma i bas jest realnie inny składnik
        if (bassPc !== best.root) {
            name += '/' + NOTE_NAMES[bassPc];
        }

        return {
            name: name,
            root: best.root,
            quality: best.quality,
            bass: bassPc,
            notes: pcs,
            confidence: best.score
        };
    }

    var api = { detectChord: detectChord, NOTE_NAMES: NOTE_NAMES, TEMPLATES: TEMPLATES };

    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    global.ChordDetect = api;
})(typeof window !== 'undefined' ? window : this);
