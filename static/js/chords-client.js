// Klienckie przekształcenia akordów (port z aplikacji desktop, band_member):
// transpozycja pod capo z zachowaniem enharmonii + konwersja notacji
// międzynarodowa/polska + małe litery=moll + tryb początkującego.
(function (global) {
    var NOTES = ['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B'];
    var NOTES_SHARP = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
    var NOTES_FLAT = ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];
    var MAP = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'Fb':4,'E#':5,
        'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,
        'B':11,'Cb':11,'H':11,'B#':0,
        'Cis':1,'Dis':3,'Es':3,'Fis':6,'Gis':8,'As':8,'Ais':10,'His':0};
    var INT_TO_PL = {'C#':'Cis','Db':'Des','D#':'Dis','Eb':'Es','F#':'Fis',
        'Gb':'Ges','G#':'Gis','Ab':'As','A#':'Ais','Bb':'B','B':'H',
        'Cb':'H','E#':'F','Fb':'E','B#':'C'};
    var RE = /^([AaEe][Ss](?![uU])|[A-Ha-h][#b]?(?:is|IS|Is)?)(.*)$/;

    function parse(str) {
        var m = str.match(RE);
        return m ? { root: m[1], suffix: m[2] } : null;
    }
    function pitch(root) {
        var r = root.charAt(0).toUpperCase() + root.slice(1);
        return MAP[r] !== undefined ? MAP[r] : null;
    }
    function flavorTable(root) {
        var r = root.toLowerCase();
        if (r.indexOf('#') >= 0 || /is$/.test(r)) return NOTES_SHARP;
        if ((r.length > 1 && r.slice(1).indexOf('b') >= 0) || /es$/.test(r)
            || r === 'as' || r === 'es') return NOTES_FLAT;
        return NOTES;
    }
    function transpose(chord, semi) {
        if (chord.indexOf('/') >= 0) {
            var p = chord.split('/');
            return transpose(p[0], semi) + '/' + transpose(p.slice(1).join('/'), semi);
        }
        var p2 = parse(chord); if (!p2) return chord;
        var pc = pitch(p2.root); if (pc === null) return chord;
        return flavorTable(p2.root)[((pc + semi) % 12 + 12) % 12] + p2.suffix;
    }
    function convertNotation(chord, notation, lowercaseMinor) {
        if (chord.indexOf('/') >= 0) {
            var p = chord.split('/');
            return convertNotation(p[0], notation, lowercaseMinor) + '/'
                 + convertNotation(p.slice(1).join('/'), notation, lowercaseMinor);
        }
        var p2 = parse(chord); if (!p2) return chord;
        var root = p2.root.charAt(0).toUpperCase() + p2.root.slice(1);
        if (notation === 'polish') root = INT_TO_PL[root] || root;
        var suffix = p2.suffix;
        if (lowercaseMinor && /^m(?!aj)/i.test(suffix)) {
            root = root.charAt(0).toLowerCase() + root.slice(1);
            suffix = suffix.replace(/^m/i, '');
        }
        return root + suffix;
    }
    function simplify(chord) {
        if (chord.indexOf('/') >= 0) chord = chord.split('/')[0];
        var p = parse(chord); if (!p) return chord;
        return p.root + (/^m(?!aj)/i.test(p.suffix) ? 'm' : '');
    }

    // Przekształca wszystkie .chord w kontenerze wg preferencji profilu.
    global.applyChordPrefs = function (container, prefs) {
        prefs = prefs || {};
        if (prefs.show_chords === false) {
            container.querySelectorAll('.chord-pair .chord')
                .forEach(function (el) { el.remove(); });
            return;
        }
        var capo = parseInt(prefs.capo_default || 0, 10) || 0;
        container.querySelectorAll('.chord').forEach(function (el) {
            var raw = el.textContent.trim();
            var out = raw;
            if (capo > 0) out = transpose(out, -capo);
            if (prefs.beginner_mode) out = simplify(out);
            out = convertNotation(out, prefs.notation || 'international',
                                  !!prefs.lowercase_minor);
            if (out.indexOf('/') >= 0) {
                var parts = out.split('/');
                el.textContent = '';
                el.appendChild(document.createTextNode(parts[0]));
                var sl = document.createElement('span');
                sl.className = 'bass-slash'; sl.textContent = '/';
                el.appendChild(sl);
                var bn = document.createElement('span');
                bn.className = 'bass-note';
                bn.textContent = parts.slice(1).join('/');
                el.appendChild(bn);
            } else {
                el.textContent = out;
            }
        });
    };
    global.jafaChords = { transpose: transpose, convert: convertNotation,
                          simplify: simplify };
})(window);
