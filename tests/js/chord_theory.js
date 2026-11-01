// Teoria akordów vs. diagramy (static/js/chord_diagrams.js). Uruchamia go
// tests/test_chord_diagrams_js.py. Wynik: JSON z listą błędnych dźwięków.
// Użycie: node tests/js/chord_theory.js <repo>
const fs = require('fs');
const path = require('path');
const repo = process.argv[2];
const src = fs.readFileSync(path.join(repo, 'static/js/chord_diagrams.js'), 'utf8');
const F = new Function(src + ';return {lookupPianoChord, lookupChord, simplifyDiagramChord};')();

const PC = { C: 0, 'C#': 1, Db: 1, D: 2, 'D#': 3, Eb: 3, E: 4, F: 5, 'F#': 6, Gb: 6, G: 7, 'G#': 8, Ab: 8, A: 9, 'A#': 10, Bb: 10, B: 11, H: 11 };
const NN = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'B', 'H'];

// teoria: sufiks -> [wymagane interwały, opcjonalne interwały]
const T = {
    '': [[0, 4, 7]], 'm': [[0, 3, 7]], '7': [[0, 4, 10], [7]], 'm7': [[0, 3, 10], [7]],
    'maj7': [[0, 4, 11], [7]], 'M7': [[0, 4, 11], [7]], 'maj': [[0, 4, 7]],
    '6': [[0, 4, 9], [7]], 'm6': [[0, 3, 9], [7]],
    '9': [[0, 4, 10, 2], [7]], 'm9': [[0, 3, 10, 2], [7]], 'maj9': [[0, 4, 11, 2], [7]],
    'add9': [[0, 4, 2], [7]], 'madd9': [[0, 3, 2], [7]], 'add2': [[0, 4, 2], [7]], 'madd2': [[0, 3, 2], [7]],
    'sus2': [[0, 2, 7]], 'sus4': [[0, 5, 7]], 'sus': [[0, 5, 7]],
    '7sus4': [[0, 5, 10], [7]], '7sus2': [[0, 2, 10], [7]], '7sus': [[0, 5, 10], [7]],
    'dim': [[0, 3, 6]], 'dim7': [[0, 3, 6, 9]], 'm7b5': [[0, 3, 6, 10]], 'm7-5': [[0, 3, 6, 10]],
    'aug': [[0, 4, 8]], '+': [[0, 4, 8]], '5': [[0, 7]],
    '11': [[0, 10, 5], [2, 4, 7]], 'm11': [[0, 3, 10, 5], [2, 7]], '13': [[0, 4, 10, 9], [2, 5, 7]],
    'add11': [[0, 4, 5], [7]], 'add4': [[0, 4, 5], [7]], 'madd11': [[0, 3, 5], [7]],
    '7b9': [[0, 4, 10, 1], [7]], '7#9': [[0, 4, 10, 3], [7]], '7b5': [[0, 4, 6, 10]], '7#5': [[0, 4, 8, 10]], '7+5': [[0, 4, 8, 10]],
    'mmaj7': [[0, 3, 11], [7]], 'm(maj7)': [[0, 3, 11], [7]], '69': [[0, 4, 9, 2], [7]], '6/9': [[0, 4, 9, 2], [7]],
    '7+': [[0, 4, 11], [7]], '7maj': [[0, 4, 11], [7]], '-': [[0, 3, 7]], 'm7maj': [[0, 3, 11], [7]],
    '4': [[0, 5, 7]], '2': [[0, 2, 7], [4]],
};
const ROOTS = ['C', 'C#', 'Db', 'D', 'D#', 'Eb', 'E', 'F', 'F#', 'Gb', 'G', 'G#', 'Ab', 'A', 'A#', 'Bb', 'B', 'H'];
const TUNING = [4, 9, 2, 7, 11, 4];
const OPEN_MIDI = [40, 45, 50, 55, 59, 64];

function parse(name) {
    const m = name.match(/^([A-H][#b]?)(.*?)(?:\/([A-H][#b]?))?$/);
    if (!m) return null;
    return { root: m[1], suffix: m[2], bass: m[3] || null };
}
function names(pcs) { return [...pcs].map(p => NN[p]).join(' '); }

function check(name) {
    const p = parse(name);
    if (!p || !(p.suffix in T)) return { skip: true };
    const r = PC[p.root];
    const [req, opt = []] = T[p.suffix];
    const need = new Set(req.map(i => (r + i) % 12));
    const ok = new Set([...need, ...opt.map(i => (r + i) % 12)]);
    if (p.bass) { ok.add(PC[p.bass]); }
    const probs = [];
    // pianino
    const pn = F.lookupPianoChord(name);
    if (!pn) probs.push('piano: brak');
    else {
        const s = new Set(pn.map(n => ((n % 12) + 12) % 12));
        const extra = [...s].filter(x => !ok.has(x)), miss = [...need].filter(x => !s.has(x));
        if (extra.length || miss.length) probs.push(`piano: ${names(s)}` + (extra.length ? ` | obce: ${names(extra)}` : '') + (miss.length ? ` | brak: ${names(miss)}` : ''));
        if (p.bass) {
            const low = ((Math.min(...pn) % 12) + 12) % 12;
            if (low !== PC[p.bass]) probs.push(`piano: najniższy ${NN[low]}, bas ${p.bass}`);
        }
    }
    // gitara (to, co pokazuje widok: uproszczony akord)
    const shown = F.simplifyDiagramChord(name);
    const g = F.lookupChord(shown);
    if (!g) probs.push(`gitara: brak (pokazuje ${shown})`);
    else {
        const midi = [];
        g.fingers.forEach((f, i) => {
            if (f < 0) return;
            const abs = g.fret > 0 ? (f === 0 ? 0 : f + g.fret - 1) : f;
            midi.push(OPEN_MIDI[i] + abs);
        });
        const s = new Set(midi.map(x => x % 12));
        const mainOnly = shown.split('/')[0] !== name.replace('6/9', '69').split('/')[0];
        const extra = [...s].filter(x => !ok.has(x));
        const miss = mainOnly ? [] : [...need].filter(x => !s.has(x) && x !== (r + 7) % 12);
        if (extra.length || miss.length) probs.push(`gitara(${shown}, próg ${g.fret}, ${JSON.stringify(g.fingers)}): ${names(s)}` + (extra.length ? ` | obce: ${names(extra)}` : '') + (miss.length ? ` | brak: ${names(miss)}` : ''));
        const low = Math.min(...midi) % 12;
        if (!p.bass && low !== r && !mainOnly) probs.push(`gitara(${shown}): najniższa nuta ${NN[low]}, nie pryma`);
        if (mainOnly) probs.push(`gitara: uproszczony do ${shown}`);
    }
    return { probs };
}

const list = [];
for (const r of ROOTS) for (const s of Object.keys(T)) list.push(r + s);
for (const r of ['A', 'C', 'D', 'E', 'G', 'H', 'F#', 'Bb']) for (const b of ['C#', 'E', 'G', 'F#', 'H', 'D']) list.push(r + '/' + b);
const errors = [];
let total = 0;
for (const c of list) {
    const res = check(c);
    if (res.skip) continue;
    total++;
    const real = res.probs.filter(x => !x.startsWith('gitara: uproszczony') && !x.includes('nie pryma'));
    if (real.length) errors.push(c + ': ' + real.join(' || '));
}
console.log(JSON.stringify({ total, errors }));
