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
