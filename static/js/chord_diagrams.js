// Guitar Chord Diagram Database
// Format: [fret_start, [E,A,D,G,B,e]] where:
//   -1 = muted (X), 0 = open, 1-4 = finger on that fret (relative to fret_start)
// barres: [[from_string, to_string, fret]] (optional)

const CHORD_DB = {
    // ===== MAJOR =====
    'C':    { fret: 0, fingers: [-1,3,2,0,1,0], barres: [] },
    'D':    { fret: 0, fingers: [-1,-1,0,2,3,2], barres: [] },
    'E':    { fret: 0, fingers: [0,2,2,1,0,0], barres: [] },
    'F':    { fret: 1, fingers: [1,1,2,3,3,1], barres: [[1,6,1]] },
    'G':    { fret: 0, fingers: [3,2,0,0,0,3], barres: [] },
    'A':    { fret: 0, fingers: [-1,0,2,2,2,0], barres: [] },
    'B':    { fret: 2, fingers: [-1,1,1,2,3,4], barres: [[2,5,1]] },
    'Bb':   { fret: 1, fingers: [-1,1,1,2,3,4], barres: [[2,5,1]] },

    'C#':   { fret: 4, fingers: [-1,1,1,2,3,4], barres: [[2,5,1]] },
    'Db':   { fret: 4, fingers: [-1,1,1,2,3,4], barres: [[2,5,1]] },
    'Eb':   { fret: 6, fingers: [-1,1,1,2,3,4], barres: [[2,5,1]] },
    'F#':   { fret: 2, fingers: [1,1,2,3,3,1], barres: [[1,6,1]] },
    'Gb':   { fret: 2, fingers: [1,1,2,3,3,1], barres: [[1,6,1]] },
    'Ab':   { fret: 4, fingers: [1,1,2,3,3,1], barres: [[1,6,1]] },
    'G#':   { fret: 4, fingers: [1,1,2,3,3,1], barres: [[1,6,1]] },

    // ===== MINOR =====
    'Am':   { fret: 0, fingers: [-1,0,2,2,1,0], barres: [] },
    'Bm':   { fret: 2, fingers: [-1,1,1,2,3,2], barres: [[2,5,1]] },
    'Cm':   { fret: 3, fingers: [-1,1,1,2,3,2], barres: [[2,5,1]] },
    'Dm':   { fret: 0, fingers: [-1,-1,0,2,3,1], barres: [] },
    'Em':   { fret: 0, fingers: [0,2,2,0,0,0], barres: [] },
    'Fm':   { fret: 1, fingers: [1,1,2,3,3,1], barres: [[1,6,1]] },
    'Gm':   { fret: 3, fingers: [1,1,2,3,3,1], barres: [[1,6,1]] },

    'Bbm':  { fret: 1, fingers: [-1,1,1,2,3,2], barres: [[2,5,1]] },
    'C#m':  { fret: 4, fingers: [-1,1,1,2,3,2], barres: [[2,5,1]] },
    'Dbm':  { fret: 4, fingers: [-1,1,1,2,3,2], barres: [[2,5,1]] },
    'Ebm':  { fret: 6, fingers: [-1,1,1,2,3,2], barres: [[2,5,1]] },
    'D#m':  { fret: 6, fingers: [-1,1,1,2,3,2], barres: [[2,5,1]] },
    'F#m':  { fret: 2, fingers: [1,1,2,3,3,1], barres: [[1,6,1]] },
    'Gbm':  { fret: 2, fingers: [1,1,2,3,3,1], barres: [[1,6,1]] },
    'G#m':  { fret: 4, fingers: [1,1,2,3,3,1], barres: [[1,6,1]] },
    'Abm':  { fret: 4, fingers: [1,1,2,3,3,1], barres: [[1,6,1]] },

    // ===== 7th (dominant) =====
    'A7':   { fret: 0, fingers: [-1,0,2,0,2,0], barres: [] },
    'B7':   { fret: 0, fingers: [-1,2,1,2,0,2], barres: [] },
    'C7':   { fret: 0, fingers: [-1,3,2,3,1,0], barres: [] },
    'D7':   { fret: 0, fingers: [-1,-1,0,2,1,2], barres: [] },
    'E7':   { fret: 0, fingers: [0,2,0,1,0,0], barres: [] },
    'F7':   { fret: 1, fingers: [1,1,2,1,3,1], barres: [[1,6,1]] },
    'G7':   { fret: 0, fingers: [3,2,0,0,0,1], barres: [] },
    'Bb7':  { fret: 1, fingers: [-1,1,1,1,3,1], barres: [[2,5,1]] },

    // ===== MINOR 7th =====
    'Am7':  { fret: 0, fingers: [-1,0,2,0,1,0], barres: [] },
    'Bm7':  { fret: 2, fingers: [-1,1,1,1,2,1], barres: [[2,5,1]] },
    'Cm7':  { fret: 3, fingers: [-1,1,1,1,2,1], barres: [[2,5,1]] },
    'Dm7':  { fret: 0, fingers: [-1,-1,0,2,1,1], barres: [] },
    'Em7':  { fret: 0, fingers: [0,2,0,0,0,0], barres: [] },
    'F#m7': { fret: 2, fingers: [1,1,2,1,3,1], barres: [[1,6,1]] },
    'G#m7': { fret: 4, fingers: [1,1,2,1,3,1], barres: [[1,6,1]] },

    // ===== MAJOR 7th =====
    'Cmaj7':  { fret: 0, fingers: [-1,3,2,0,0,0], barres: [] },
    'Dmaj7':  { fret: 0, fingers: [-1,-1,0,2,2,2], barres: [] },
    'Emaj7':  { fret: 0, fingers: [0,2,1,1,0,0], barres: [] },
    'Fmaj7':  { fret: 0, fingers: [-1,-1,3,2,1,0], barres: [] },
    'Gmaj7':  { fret: 0, fingers: [3,2,0,0,0,2], barres: [] },
    'Amaj7':  { fret: 0, fingers: [-1,0,2,1,2,0], barres: [] },
    'Bbmaj7': { fret: 1, fingers: [-1,1,1,2,3,3], barres: [[2,5,1]] },

    // ===== sus2 =====
    'Asus2': { fret: 0, fingers: [-1,0,2,2,0,0], barres: [] },
    'Bsus2': { fret: 2, fingers: [-1,1,1,3,4,1], barres: [[2,5,1]] },
    'Csus2': { fret: 3, fingers: [-1,1,1,3,4,1], barres: [[2,5,1]] },
    'Dsus2': { fret: 0, fingers: [-1,-1,0,2,3,0], barres: [] },
    'Esus2': { fret: 0, fingers: [0,2,4,4,0,0], barres: [] },
    'Fsus2': { fret: 1, fingers: [-1,-1,1,1,2,1], barres: [[3,6,1]] },
    'Gsus2': { fret: 0, fingers: [3,0,0,0,3,3], barres: [] },

    // ===== sus4 =====
    'Asus4': { fret: 0, fingers: [-1,0,2,2,3,0], barres: [] },
    'Bsus4': { fret: 2, fingers: [-1,1,1,3,4,4], barres: [[2,5,1]] },
    'Csus4': { fret: 3, fingers: [-1,1,1,3,4,4], barres: [[2,5,1]] },
    'Dsus4': { fret: 0, fingers: [-1,-1,0,2,3,3], barres: [] },
    'Esus4': { fret: 0, fingers: [0,2,2,2,0,0], barres: [] },
    'Fsus4': { fret: 1, fingers: [1,1,2,3,4,1], barres: [[1,6,1]] },
    'Gsus4': { fret: 0, fingers: [3,2,0,0,1,3], barres: [] },

    // ===== add9 =====
    'Cadd9': { fret: 0, fingers: [-1,3,2,0,3,0], barres: [] },
    'Dadd9': { fret: 0, fingers: [-1,-1,0,2,3,0], barres: [] },
    'Eadd9': { fret: 0, fingers: [0,2,2,1,0,2], barres: [] },
    'Gadd9': { fret: 0, fingers: [3,2,0,2,0,3], barres: [] },
    'Aadd9': { fret: 0, fingers: [-1,0,2,4,2,0], barres: [] },
    'Fadd9': { fret: 0, fingers: [-1,-1,3,2,1,3], barres: [] },

    // ===== dim =====
    'Bdim':  { fret: 0, fingers: [-1,2,3,4,3,-1], barres: [] },
    'Cdim':  { fret: 0, fingers: [-1,3,4,2,4,-1], barres: [] },
    'Ddim':  { fret: 0, fingers: [-1,-1,0,1,3,1], barres: [] },
    'Edim':  { fret: 0, fingers: [0,1,2,0,2,0], barres: [] },
    'F#dim': { fret: 0, fingers: [-1,-1,4,2,1,2], barres: [] },
    'Gdim':  { fret: 0, fingers: [-1,-1,5,3,2,3], barres: [] },
    'Adim':  { fret: 0, fingers: [-1,0,1,2,1,-1], barres: [] },

    // ===== aug =====
    'Caug':  { fret: 0, fingers: [-1,3,2,1,1,0], barres: [] },
    'Daug':  { fret: 0, fingers: [-1,-1,0,3,3,2], barres: [] },
    'Eaug':  { fret: 0, fingers: [0,3,2,1,1,0], barres: [] },
    'Faug':  { fret: 0, fingers: [-1,-1,3,2,2,1], barres: [] },
    'Gaug':  { fret: 0, fingers: [3,2,1,0,0,3], barres: [] },
    'Aaug':  { fret: 0, fingers: [-1,0,3,2,2,1], barres: [] },

    // ===== Power chords (5) =====
    'C5':   { fret: 3, fingers: [-1,1,3,-1,-1,-1], barres: [] },
    'D5':   { fret: 5, fingers: [-1,1,3,-1,-1,-1], barres: [] },
    'E5':   { fret: 0, fingers: [0,2,2,-1,-1,-1], barres: [] },
    'F5':   { fret: 1, fingers: [1,3,3,-1,-1,-1], barres: [] },
    'G5':   { fret: 3, fingers: [1,3,3,-1,-1,-1], barres: [] },
    'A5':   { fret: 0, fingers: [-1,0,2,2,-1,-1], barres: [] },
    'B5':   { fret: 2, fingers: [-1,1,3,3,-1,-1], barres: [] },
};

function lookupChord(chordName) {
    if (CHORD_DB[chordName]) return CHORD_DB[chordName];
    // Try common aliases
    const aliases = {
        'H': 'B', 'Hm': 'Bm', 'H7': 'B7', 'Hm7': 'Bm7', 'Hmaj7': 'Bmaj7',
        'Hsus4': 'Bsus4', 'Hsus2': 'Bsus2', 'Hadd9': 'Badd9',
    };
    if (aliases[chordName] && CHORD_DB[aliases[chordName]]) return CHORD_DB[aliases[chordName]];
    return null;
}

function renderChordSVG(chordName, data) {
    const W = 120, H = 160;
    const LEFT = 30, TOP = 30;
    const SW = 70, SH = 100;  // string area
    const FRETS = 5;
    const STRINGS = 6;
    const fretH = SH / FRETS;
    const strW = SW / (STRINGS - 1);

    let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">`;

    // Background
    svg += `<rect x="0" y="0" width="${W}" height="${H}" rx="8" fill="#1a1a2e"/>`;

    // Title
    svg += `<text x="${W/2}" y="18" text-anchor="middle" font-size="14" font-weight="bold" fill="#00e5ff" font-family="Sen,sans-serif">${chordName}</text>`;

    // Fret number indicator
    if (data.fret > 0) {
        svg += `<text x="${LEFT-10}" y="${TOP+fretH/2+4}" text-anchor="middle" font-size="10" fill="#888" font-family="monospace">${data.fret}</text>`;
    }

    // Nut (thick line at top if fret 0)
    if (data.fret === 0) {
        svg += `<rect x="${LEFT-1}" y="${TOP-3}" width="${SW+2}" height="4" fill="#ddd" rx="1"/>`;
    }

    // Fret lines
    for (let i = 0; i <= FRETS; i++) {
        const y = TOP + i * fretH;
        svg += `<line x1="${LEFT}" y1="${y}" x2="${LEFT+SW}" y2="${y}" stroke="#555" stroke-width="1"/>`;
    }

    // String lines
    for (let i = 0; i < STRINGS; i++) {
        const x = LEFT + i * strW;
        svg += `<line x1="${x}" y1="${TOP}" x2="${x}" y2="${TOP+SH}" stroke="#666" stroke-width="1"/>`;
    }

    // Barres
    if (data.barres) {
        for (const barre of data.barres) {
            const [fromStr, toStr, fretPos] = barre;
            const x1 = LEFT + (fromStr - 1) * strW;
            const x2 = LEFT + (toStr - 1) * strW;
            const y = TOP + (fretPos - 0.5) * fretH;
            svg += `<line x1="${x1}" y1="${y}" x2="${x2}" y2="${y}" stroke="#fff" stroke-width="6" stroke-linecap="round"/>`;
        }
    }

    // Finger dots and muted/open indicators
    for (let i = 0; i < STRINGS; i++) {
        const x = LEFT + i * strW;
        const f = data.fingers[i];
        if (f === -1) {
            svg += `<text x="${x}" y="${TOP-8}" text-anchor="middle" font-size="10" fill="#f5365c" font-family="sans-serif">✕</text>`;
        } else if (f === 0) {
            svg += `<circle cx="${x}" cy="${TOP-10}" r="4" fill="none" stroke="#69f0ae" stroke-width="1.5"/>`;
        } else {
            const y = TOP + (f - 0.5) * fretH;
            svg += `<circle cx="${x}" cy="${y}" r="5.5" fill="#fff"/>`;
        }
    }

    svg += '</svg>';
    return svg;
}

// ===== PIANO CHORD DATABASE =====
// Format: array of MIDI-style note numbers (C=0, C#=1, ..., B=11) across 2 octaves
// Notes 0-11 = lower octave, 12-23 = upper octave
const PIANO_DB = {
    // Major
    'C':  [0, 4, 7],    'C#': [1, 5, 8],    'Db': [1, 5, 8],
    'D':  [2, 6, 9],    'Eb': [3, 7, 10],   'D#': [3, 7, 10],
    'E':  [4, 8, 11],   'F':  [5, 9, 12],   'F#': [6, 10, 13],
    'Gb': [6, 10, 13],  'G':  [7, 11, 14],  'Ab': [8, 12, 15],
    'G#': [8, 12, 15],  'A':  [9, 13, 16],  'Bb': [10, 14, 17],
    'A#': [10, 14, 17], 'B':  [11, 15, 18],

    // Minor
    'Cm':  [0, 3, 7],   'C#m': [1, 4, 8],   'Dbm': [1, 4, 8],
    'Dm':  [2, 5, 9],   'Ebm': [3, 6, 10],  'D#m': [3, 6, 10],
    'Em':  [4, 7, 11],  'Fm':  [5, 8, 12],  'F#m': [6, 9, 13],
    'Gbm': [6, 9, 13],  'Gm':  [7, 10, 14], 'Abm': [8, 11, 15],
    'G#m': [8, 11, 15], 'Am':  [9, 12, 16], 'Bbm': [10, 13, 17],
    'A#m': [10, 13, 17],'Bm':  [11, 14, 18],

    // 7th (dominant)
    'C7':  [0, 4, 7, 10],   'D7':  [2, 6, 9, 12],   'E7':  [4, 8, 11, 14],
    'F7':  [5, 9, 12, 15],  'G7':  [7, 11, 14, 17],  'A7':  [9, 13, 16, 19],
    'B7':  [11, 15, 18, 21],'Bb7': [10, 14, 17, 20],

    // Minor 7th
    'Am7': [9, 12, 16, 19], 'Bm7': [11, 14, 18, 21], 'Cm7': [0, 3, 7, 10],
    'Dm7': [2, 5, 9, 12],   'Em7': [4, 7, 11, 14],   'F#m7':[6, 9, 13, 16],
    'G#m7':[8, 11, 15, 18],

    // Major 7th
    'Cmaj7': [0, 4, 7, 11],  'Dmaj7': [2, 6, 9, 13],  'Emaj7': [4, 8, 11, 15],
    'Fmaj7': [5, 9, 12, 16], 'Gmaj7': [7, 11, 14, 18], 'Amaj7': [9, 13, 16, 20],
    'Bbmaj7':[10, 14, 17, 21],

    // sus2
    'Csus2': [0, 2, 7],  'Dsus2': [2, 4, 9],  'Esus2': [4, 6, 11],
    'Fsus2': [5, 7, 12], 'Gsus2': [7, 9, 14], 'Asus2': [9, 11, 16],
    'Bsus2': [11, 13, 18],

    // sus4
    'Csus4': [0, 5, 7],  'Dsus4': [2, 7, 9],  'Esus4': [4, 9, 11],
    'Fsus4': [5, 10, 12],'Gsus4': [7, 12, 14], 'Asus4': [9, 14, 16],
    'Bsus4': [11, 16, 18],

    // add9
    'Cadd9': [0, 4, 7, 14],  'Dadd9': [2, 6, 9, 16],  'Eadd9': [4, 8, 11, 18],
    'Gadd9': [7, 11, 14, 21], 'Aadd9': [9, 13, 16, 23], 'Fadd9': [5, 9, 12, 19],

    // dim
    'Bdim': [11, 14, 17], 'Cdim': [0, 3, 6],   'Ddim': [2, 5, 8],
    'Edim': [4, 7, 10],   'F#dim':[6, 9, 12],  'Gdim': [7, 10, 13],
    'Adim': [9, 12, 15],

    // aug
    'Caug': [0, 4, 8],  'Daug': [2, 6, 10],  'Eaug': [4, 8, 12],
    'Faug': [5, 9, 13], 'Gaug': [7, 11, 15], 'Aaug': [9, 13, 17],
};

function lookupPianoChord(chordName) {
    if (PIANO_DB[chordName]) return PIANO_DB[chordName];
    const aliases = {
        'H': 'B', 'Hm': 'Bm', 'H7': 'B7', 'Hm7': 'Bm7', 'Hmaj7': 'Bmaj7',
        'Hsus4': 'Bsus4', 'Hsus2': 'Bsus2', 'Hadd9': 'Badd9',
    };
    if (aliases[chordName] && PIANO_DB[aliases[chordName]]) return PIANO_DB[aliases[chordName]];
    // Auto-generate from chord theory if not in DB
    return generatePianoChord(chordName);
}

function generatePianoChord(chordName) {
    const NOTE_TO_PITCH = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11,'H':11};
    const m = chordName.match(/^([A-H][#b]?)(.*)$/);
    if (!m) return null;
    let root = m[1];
    if (root === 'H') root = 'B';
    const pc = NOTE_TO_PITCH[root];
    if (pc === undefined) return null;
    const suffix = m[2].toLowerCase();

    let intervals;
    if (suffix === '' || suffix === 'maj') intervals = [0, 4, 7];
    else if (suffix === 'm' || suffix === 'min') intervals = [0, 3, 7];
    else if (suffix === '7') intervals = [0, 4, 7, 10];
    else if (suffix === 'm7' || suffix === 'min7') intervals = [0, 3, 7, 10];
    else if (suffix === 'maj7') intervals = [0, 4, 7, 11];
    else if (suffix === 'dim') intervals = [0, 3, 6];
    else if (suffix === 'aug') intervals = [0, 4, 8];
    else if (suffix === 'sus2') intervals = [0, 2, 7];
    else if (suffix === 'sus4') intervals = [0, 5, 7];
    else if (suffix === 'add9') intervals = [0, 4, 7, 14];
    else if (suffix === '9') intervals = [0, 4, 7, 10, 14];
    else if (suffix === 'm9') intervals = [0, 3, 7, 10, 14];
    else if (suffix === '6') intervals = [0, 4, 7, 9];
    else if (suffix === 'm6') intervals = [0, 3, 7, 9];
    else if (suffix === 'dim7') intervals = [0, 3, 6, 9];
    else if (suffix === '7sus4') intervals = [0, 5, 7, 10];
    else if (suffix === '11') intervals = [0, 4, 7, 10, 14, 17];
    else return null;

    return intervals.map(i => pc + i);
}

function renderPianoSVG(chordName, notes) {
    const W = 200, H = 120;
    const TOP = 28;
    const KW = 13, KH = 65;
    const BKW = 9, BKH = 40;
    const NUM_WHITES = 14; // 2 octaves
    const pianoW = NUM_WHITES * KW;
    const LEFT = (W - pianoW) / 2;

    // Map white keys: C=0, D=1, E=2, F=3, G=4, A=5, B=6 (per octave)
    const WHITE_NOTE = [0, 2, 4, 5, 7, 9, 11]; // semitone values
    const BLACK_POSITIONS = [0.65, 1.75, 3.6, 4.7, 5.75]; // x positions relative to white keys
    const BLACK_NOTE = [1, 3, 6, 8, 10]; // semitone values

    // Normalize notes to 0-23 range
    const activeNotes = new Set(notes.map(n => ((n % 24) + 24) % 24));

    let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">`;
    svg += `<rect x="0" y="0" width="${W}" height="${H}" rx="8" fill="#1a1a2e"/>`;
    svg += `<text x="${W/2}" y="18" text-anchor="middle" font-size="13" font-weight="bold" fill="#ff9800" font-family="Sen,sans-serif">${chordName}</text>`;

    // Draw white keys
    for (let oct = 0; oct < 2; oct++) {
        for (let i = 0; i < 7; i++) {
            const idx = oct * 7 + i;
            const x = LEFT + idx * KW;
            const semitone = oct * 12 + WHITE_NOTE[i];
            const active = activeNotes.has(semitone);
            svg += `<rect x="${x}" y="${TOP}" width="${KW-1}" height="${KH}" rx="2" fill="${active ? '#ff9800' : '#f5f5f5'}" stroke="#333" stroke-width="0.5"/>`;
            if (active) {
                svg += `<rect x="${x}" y="${TOP + KH - 14}" width="${KW-1}" height="12" rx="1" fill="#e65100" opacity="0.6"/>`;
            }
        }
    }

    // Draw black keys
    for (let oct = 0; oct < 2; oct++) {
        for (let i = 0; i < 5; i++) {
            const x = LEFT + (oct * 7 + BLACK_POSITIONS[i]) * KW;
            const semitone = oct * 12 + BLACK_NOTE[i];
            const active = activeNotes.has(semitone);
            svg += `<rect x="${x}" y="${TOP}" width="${BKW}" height="${BKH}" rx="1.5" fill="${active ? '#ff9800' : '#222'}" stroke="#000" stroke-width="0.5"/>`;
            if (active) {
                svg += `<rect x="${x+1}" y="${TOP + BKH - 10}" width="${BKW-2}" height="8" rx="1" fill="#ffcc02" opacity="0.7"/>`;
            }
        }
    }

    svg += '</svg>';
    return svg;
}
