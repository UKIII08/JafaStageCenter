"""music_core.chords — silnik muzyczny JafaStage.

Przeniesione 1:1 z aplikacji desktop (JafaStageCenter, gałęzie desktopowe)
— wspólna logika: walidacja i normalizacja akordów (z zachowaniem enharmonii),
transpozycja, konwerter formatu "akordy nad tekstem", detekcja tonacji
i renderowanie pieśni do HTML (pary akord+sylaba).

Czyste funkcje: zależności tylko re + html. Testy: tests/test_music_core.py.
"""
import html
import math
import re

# --- MAPPINGS ---
PITCH_CLASS_MAP = {
    'C': 0, 'C#': 1, 'DB': 1, 'D': 2, 'D#': 3, 'EB': 3, 'E': 4, 'FB': 4,
    'E#': 5, 'F': 5, 'F#': 6, 'GB': 6, 'G': 7, 'G#': 8, 'AB': 8,
    'A': 9, 'A#': 10, 'BB': 10, 'B': 11, 'CB': 11, 'H': 11, 'B#': 0
}
PITCH_CLASS_POLISH = {
    'CIS': 1, 'DIS': 3, 'FIS': 6, 'GIS': 8, 'AIS': 10,
    'ES': 3, 'AS': 8, 'HIS': 0
}
TRANSPOSE_LOOKUP = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
TRANSPOSE_LOOKUP_PL = ['C', 'Cis', 'D', 'Es', 'E', 'F', 'Fis', 'G', 'As', 'A', 'B', 'H']
# Pisownia wyniku transpozycji dziedziczy "smak" oryginału: akord z krzyżykiem
# transponuje się na krzyżyki (F#m +2 -> G#m, nie Abm), z bemolem na bemole
# (Bb +3 -> Db, nie C#). Nuty naturalne używają domyślnej mieszanej tabeli wyżej.
TRANSPOSE_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
TRANSPOSE_FLAT = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
TRANSPOSE_SHARP_PL = ['C', 'Cis', 'D', 'Dis', 'E', 'F', 'Fis', 'G', 'Gis', 'A', 'Ais', 'H']
TRANSPOSE_FLAT_PL = ['C', 'Des', 'D', 'Es', 'E', 'F', 'Ges', 'G', 'As', 'A', 'B', 'H']

def _accidental_flavor(root_str, notation='international'):
    """'sharp' / 'flat' / None (naturalna nuta) — na podstawie pisowni źródła."""
    r = root_str.strip()
    if '#' in r or r.lower().endswith('is'):
        return 'sharp'
    if len(r) > 1 and 'b' in r[1:].lower():
        return 'flat'
    lower = r.lower()
    if lower.endswith('es') or lower in ('as', 'es'):
        return 'flat'
    if notation == 'polish' and r.upper() == 'B':
        return 'flat'  # polskie B = Bb
    return None
CHORD_ROOT_RE = re.compile(r'^([AaEe][Ss](?![uU])|[A-Ha-h][#b]?(?:is|IS|Is)?)(.*)$')
VALID_CHORD_SUFFIX_RE = re.compile(r'^[majindugsMINDUGSAJ0-9#b()+\-/]*$')

def is_valid_chord(chord_str):
    if not chord_str or not chord_str.strip():
        return False
    chord_str = chord_str.strip().rstrip('-').rstrip()
    if '/' in chord_str:
        parts = chord_str.split('/', 1)
        return is_valid_chord(parts[0]) and (is_valid_chord(parts[1]) or parts[1].strip() == '')
    m = CHORD_ROOT_RE.match(chord_str)
    if not m:
        return False
    root = m.group(1)
    suffix = m.group(2)
    if not root or not root[0].upper() in 'ABCDEFGH':
        return False
    if suffix and not VALID_CHORD_SUFFIX_RE.match(suffix):
        return False
    return True

def clean_chord(chord_str):
    return chord_str.strip().rstrip('-').rstrip()

def _resolve_pitch_class(root_upper, notation='international'):
    if root_upper in PITCH_CLASS_POLISH:
        return PITCH_CLASS_POLISH[root_upper]
    if root_upper == 'B' and notation == 'polish':
        return 10
    if root_upper in PITCH_CLASS_MAP:
        return PITCH_CLASS_MAP[root_upper]
    return None

def normalize_chord_root(root_str, notation='international'):
    upper = root_str.upper()
    pc = _resolve_pitch_class(upper, notation)
    if pc is None:
        return root_str
    lookup = TRANSPOSE_LOOKUP_PL if notation == 'polish' else TRANSPOSE_LOOKUP
    return lookup[pc]

# --- IMPORT FORMATU "AKORDY NAD TEKSTEM" (Ultimate Guitar itp.) ---
# Wewnętrznym formatem aplikacji jest ChordPro ([C]tekst) - akord jest wtedy
# jednoznacznie przypięty do sylaby, co przeżywa zawijanie linii, zmianę
# czcionki i transpozycję. Ale użytkownicy kopiują piosenki z serwisów, gdzie
# akordy stoją W OSOBNEJ LINII nad tekstem, wyrównane spacjami. Ten konwerter
# skleja takie pary linii w ChordPro po pozycjach kolumnowych.
#
# Zasada bezpieczeństwa: konwersja jest KONSERWATYWNA. Linia jest uznana za
# linię akordów tylko, gdy WSZYSTKIE tokeny to poprawne akordy - a pojedyncza
# goła litera (np. "A" - po polsku spójnik!) nigdy. Fałszywy negatyw (nie
# skonwertował) jest tani; fałszywy pozytyw (zjadł linijkę tekstu) - kosztowny.

_STRICT_SINGLE_CHORD_RE = re.compile(
    r'^[A-Ha-h][#b]?(?:is|es)?'
    r'(?:m|maj7|maj9|m7b5|m7|m9|m11|dim7?|aug|sus[24]|add\d+|7sus4|6|7|9|11|13|\+|-)+'
    r'(?:/[A-Ha-h][#b]?(?:is|es)?)?$'
    r'|^[A-Ha-h][#b](?:/[A-Ha-h][#b]?)?$'
    r'|^[A-Ha-h][#b]?/[A-Ha-h][#b]?$'
)

def _is_chord_token(tok):
    return bool(CHORD_ROOT_RE.match(tok)) and is_valid_chord(tok)

def _is_chords_over_lyrics_line(line):
    """Czy linia wygląda JEDNOZNACZNIE na linię samych akordów?"""
    tokens = line.split()
    if not tokens:
        return False
    if any(not _is_chord_token(t) for t in tokens):
        return False
    if len(tokens) == 1:
        # pojedynczy token: tylko wyraźny akord (Am, F#, G7, C/E) -
        # goła litera ("A", "E") to po polsku często słowo piosenki
        return bool(_STRICT_SINGLE_CHORD_RE.match(tokens[0]))
    return True

_SECTION_HEADER_RE = re.compile(r'^\[([^\[\]]{1,40})\]$')

def convert_chords_over_lyrics(text):
    """Konwertuje format "akordy nad tekstem" na ChordPro.

    Zwraca (tekst, changed). Tekst już będący ChordPro przechodzi bez zmian
    (idempotentne) - można bezpiecznie wołać przy każdym zapisie.
    """
    if not text:
        return text, False
    lines = text.replace('\r', '').expandtabs(4).split('\n')
    out = []
    changed = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # nagłówek sekcji w stylu UG: [Intro], [Verse 1] -> zwykła etykieta
        m = _SECTION_HEADER_RE.match(stripped)
        if m and not _is_chord_token(m.group(1).strip()):
            out.append(m.group(1).strip())
            changed = True
            i += 1
            continue

        if _is_chords_over_lyrics_line(stripped):
            # pozycje akordów w linii (kolumna = indeks znaku)
            chords = [(mm.start(), mm.group(0)) for mm in re.finditer(r'\S+', line)]
            nxt = lines[i + 1] if i + 1 < len(lines) else ''
            nxt_stripped = nxt.strip()
            if nxt_stripped and not _is_chords_over_lyrics_line(nxt_stripped) \
                    and not _SECTION_HEADER_RE.match(nxt_stripped):
                # Akordy + tekst pod spodem -> sklej po kolumnach. Transkrypcje
                # "nad tekstem" są z konwencji wyrównane do SŁÓW, więc kolumnę
                # trafiającą w środek słowa przyciągamy do jego początku
                # (chyba że początek już zajęty innym akordem).
                merged = nxt
                positions = []
                tail = []      # akordy za końcem tekstu - doklejane na końcu
                taken = set()
                for col, ch in chords:
                    if col >= len(merged.rstrip()):
                        tail.append(ch)
                        continue
                    # kolumna na spacji -> początek następnego słowa
                    while col < len(merged) and merged[col] == ' ':
                        col += 1
                    # kolumna w środku słowa -> początek tego słowa
                    start = col
                    while start > 0 and merged[start - 1] != ' ':
                        start -= 1
                    if start not in taken:
                        col = start
                    taken.add(col)
                    positions.append((col, ch))
                for col, ch in sorted(positions, reverse=True):
                    merged = merged[:col] + '[' + ch + ']' + merged[col:]
                if tail:
                    merged = merged.rstrip() + ' ' + ' '.join('[' + ch + ']' for ch in tail)
                out.append(merged)
                changed = True
                i += 2
                continue
            else:
                # linia samych akordów bez tekstu (intro/instrumental)
                out.append(' '.join('[' + ch + ']' for _, ch in chords))
                changed = True
                i += 1
                continue

        out.append(line)
        i += 1
    return '\n'.join(out), changed

def normalize_chord_to_international(chord_str, input_notation='international'):
    """Normalize a chord to international notation for storage."""
    if not chord_str or not chord_str.strip():
        return chord_str
    chord_str = clean_chord(chord_str)
    if '/' in chord_str:
        parts = chord_str.split('/')
        return '/'.join(normalize_chord_to_international(p, input_notation) for p in parts)
    if not is_valid_chord(chord_str):
        return chord_str
    m = CHORD_ROOT_RE.match(chord_str)
    if not m:
        return chord_str
    raw_root = m.group(1)
    suffix = m.group(2)
    is_minor_lowercase = raw_root[0].islower()
    upper = raw_root.upper()
    pc = _resolve_pitch_class(upper, input_notation)
    if pc is None:
        return chord_str
    # zachowaj pisownię źródła: G#m NIE zamienia się w Abm przy zapisie
    flavor = _accidental_flavor(raw_root, input_notation)
    if flavor == 'sharp':
        normalized_root = TRANSPOSE_SHARP[pc]
    elif flavor == 'flat':
        normalized_root = TRANSPOSE_FLAT[pc]
    else:
        normalized_root = TRANSPOSE_LOOKUP[pc]
    if is_minor_lowercase and not suffix.startswith('m'):
        suffix = 'm' + suffix
        normalized_root = normalized_root[0].upper() + normalized_root[1:]
    return normalized_root + suffix

def normalize_chord(chord_str, notation='international'):
    if not chord_str or not chord_str.strip():
        return chord_str
    chord_str = clean_chord(chord_str)
    if not is_valid_chord(chord_str):
        return chord_str
    m = CHORD_ROOT_RE.match(chord_str)
    if not m:
        return chord_str
    raw_root = m.group(1)
    suffix = m.group(2)
    is_minor_lowercase = raw_root[0].islower()
    normalized_root = normalize_chord_root(raw_root, notation)
    if is_minor_lowercase and not suffix.startswith('m'):
        suffix = 'm' + suffix
        normalized_root = normalized_root[0].upper() + normalized_root[1:]
    return normalized_root + suffix

def normalize_song_chords_to_international(content, input_notation='international'):
    """Normalize all chords in song content to international notation for storage."""
    def replace_chord(m):
        inner = m.group(1).strip()
        cleaned = clean_chord(inner)
        if '/' in cleaned:
            parts = cleaned.split('/', 1)
            if is_valid_chord(parts[0]):
                normalized_parts = [normalize_chord_to_international(p, input_notation) for p in cleaned.split('/')]
                return '[' + '/'.join(normalized_parts) + ']'
            return '[' + cleaned + ']'
        if not is_valid_chord(cleaned):
            return '[' + cleaned + ']'
        return '[' + normalize_chord_to_international(cleaned, input_notation) + ']'
    return re.sub(r'\[(.*?)\]', replace_chord, content)

def normalize_song_chords(content, notation='international'):
    def replace_chord(m):
        inner = m.group(1).strip()
        cleaned = clean_chord(inner)
        if '/' in cleaned:
            parts = cleaned.split('/', 1)
            if is_valid_chord(parts[0]):
                normalized_parts = [normalize_chord(p, notation) for p in cleaned.split('/')]
                return '[' + '/'.join(normalized_parts) + ']'
            return '[' + cleaned + ']'
        if not is_valid_chord(cleaned):
            return '[' + cleaned + ']'
        return '[' + normalize_chord(cleaned, notation) + ']'
    return re.sub(r'\[(.*?)\]', replace_chord, content)


class AdvancedKeyDetector:
    def __init__(self):
        self.note_map = {
            'c': 0, 'c#': 1, 'db': 1, 'd': 2, 'd#': 3, 'eb': 3,
            'e': 4, 'f': 5, 'f#': 6, 'gb': 6, 'g': 7, 'g#': 8, 'ab': 8,
            'a': 9, 'a#': 10, 'bb': 10, 'b': 11, 'h': 11, 'cb': 11
        }
        self.index_to_note = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
        self.major_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
        self.minor_profile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

    def _get_chord_notes(self, root, is_major):
        return [root, (root + (4 if is_major else 3)) % 12, (root + 7) % 12]

    def _calculate_correlation(self, list1, list2):
        if not list1: return 0
        mean1, mean2 = sum(list1)/len(list1), sum(list2)/len(list2)
        num = sum((x - mean1) * (y - mean2) for x, y in zip(list1, list2))
        den = math.sqrt(sum((x - mean1)**2 for x in list1)) * math.sqrt(sum((y - mean2)**2 for y in list2))
        return num / den if den != 0 else 0

    def _extract_chords_from_text(self, text):
        return [c.strip() for c in re.findall(r'\[(.*?)\]', text) if c.strip()]

    def _parse_chord(self, c):
        """Parse one chord token -> (pitch_class, is_major, bass_pc | None).

        Uses the app-wide CHORD_ROOT_RE so Polish notation (H, Cis, Es, B=Bb)
        parses identically to the transpose pipeline. 'm' in the suffix only
        counts as minor when it is not part of 'maj' (Cmaj7 is major)."""
        c = clean_chord(c)
        bass_pc = None
        if '/' in c:
            main, _, bass = c.partition('/')
            bm = CHORD_ROOT_RE.match(bass.strip())
            if bm:
                bass_pc = _resolve_pitch_class(bm.group(1).upper())
            c = main.strip()
        m = CHORD_ROOT_RE.match(c)
        if not m:
            return None
        pc = _resolve_pitch_class(m.group(1).upper())
        if pc is None:
            return None
        suffix = m.group(2)
        is_minor = m.group(1)[0].islower() or bool(re.search(r'(?<!di)m(?!aj)', suffix)) or 'dim' in suffix
        return pc, not is_minor, bass_pc

    def detect(self, text):
        chords_raw = self._extract_chords_from_text(text) if not isinstance(text, list) else text
        if not chords_raw: return "N/A"

        parsed = [self._parse_chord(c) for c in chords_raw]
        parsed = [p for p in parsed if p]
        if not parsed: return "N/A"

        first, last = parsed[0], parsed[-1]
        vec = [0.0]*12
        for pc, is_major, bass_pc in parsed:
            for n in self._get_chord_notes(pc, is_major):
                vec[n] += 1
            if bass_pc is not None:
                vec[bass_pc] += 0.5

        best_key, best_score = "N/A", -999.0
        for i in range(12):
            s = self._calculate_correlation(vec, self.major_profile[-i:] + self.major_profile[:-i])
            if last[1] and last[0]==i: s+=0.5
            if first[1] and first[0]==i: s+=0.6
            if s > best_score: best_score, best_key = s, self.index_to_note[i]

            s = self._calculate_correlation(vec, self.minor_profile[-i:] + self.minor_profile[:-i])
            if not last[1] and last[0]==i: s+=0.5
            if not first[1] and first[0]==i: s+=0.6
            if s > best_score: best_score, best_key = s, f"{self.index_to_note[i]}m"
        return best_key

key_detector = AdvancedKeyDetector()
def detect_key_algorithm(text): return key_detector.detect(text)


def transpose_chord(match, shift, notation='international'):
    full_chord = match.group(1)
    # NIE ruszaj tokenów, które nie są akordami ([Coda], [Bridge], [x2]…) —
    # inaczej transpozycja psuła etykiety sekcji ([Coda] +2 -> [Doda]).
    if not is_valid_chord(full_chord):
        return f"[{full_chord}]"
    polish = (notation == 'polish')
    def trans_part(part):
        if not part: return ""
        m = CHORD_ROOT_RE.match(part)
        if not m: return part
        root_str, suffix = m.group(1), m.group(2)
        is_lower = part[0].islower()
        pc = _resolve_pitch_class(root_str.upper(), notation)
        if pc is not None:
            flavor = _accidental_flavor(root_str, notation)
            # zachowaj styl pisowni źródła: "Fis" transponuje się na "Gis", nie "G#"
            spelled_pl = polish or root_str.lower().endswith(('is', 'es'))
            if flavor == 'sharp':
                lookup = TRANSPOSE_SHARP_PL if spelled_pl else TRANSPOSE_SHARP
            elif flavor == 'flat':
                lookup = TRANSPOSE_FLAT_PL if spelled_pl else TRANSPOSE_FLAT
            else:
                lookup = TRANSPOSE_LOOKUP_PL if polish else TRANSPOSE_LOOKUP
            new_root = lookup[(pc + shift) % 12]
            return f"{new_root.lower() if is_lower else new_root}{suffix}"
        return part

    if '/' in full_chord:
        parts = full_chord.split('/')
        return f"[{trans_part(parts[0])}/{trans_part(parts[1])}]" if len(parts)>=2 else f"[{trans_part(full_chord)}]"
    return f"[{trans_part(full_chord)}]"

def apply_transpose_to_single_chord(chord_str, shift, notation='international'):
    if shift == 0: return chord_str
    return re.sub(r'\[(.*?)\]', lambda m: transpose_chord(m, shift, notation), chord_str)

def get_first_chord_from_chorus(content):
    if not content: return None
    blocks = re.split(r'\n\s*\n', content)
    chorus_pattern = re.compile(r'^\[?(refren|chorus)', re.IGNORECASE)
    for block in blocks:
        lines = block.strip().splitlines()
        if not lines: continue
        if chorus_pattern.match(lines[0].strip()):
            chords = [c.strip() for c in re.findall(r'\[(.*?)\]', block) if c.strip()]
            if chords: return chords[0] 
    return get_first_chord_of_song(content)

def get_first_chord_of_song(content):
    if not content: return None
    chords = [c.strip() for c in re.findall(r'\[(.*?)\]', content) if c.strip()]
    return chords[0] if chords else None


def _format_chord_for_display(chord_str, notation='international', minor_display='uppercase'):
    if not chord_str:
        return chord_str
    chord_str = clean_chord(chord_str)
    if '/' in chord_str:
        parts = chord_str.split('/')
        return '/'.join(_format_chord_for_display(p, notation, minor_display) for p in parts)
    if not is_valid_chord(chord_str):
        return chord_str
    m = CHORD_ROOT_RE.match(chord_str)
    if not m:
        return chord_str
    raw_root = m.group(1)
    suffix = m.group(2)
    normalized = normalize_chord_root(raw_root, notation)
    if minor_display == 'lowercase' and (suffix.startswith('m') and not suffix.startswith('maj')):
        normalized = normalized[0].lower() + normalized[1:]
        suffix = suffix[1:]
    return normalized + suffix

def process_song(text, transpose_amount=0, notation='international', minor_display='uppercase'):
    if not text: return "", "", ""
    text = text.strip()
    if transpose_amount != 0:
        text = re.sub(r'\[(.*?)\]', lambda m: transpose_chord(m, transpose_amount, 'international'), text)
    # HTML-escape treści tekstu (ochrona przed wstrzyknięciem HTML/JS z pieśni —
    # np. z importu lub z otwartego /send_text w sieci). Akordy w [] są usuwane.
    text_people = html.escape(re.sub(r'\[.*?\]', '', text).strip(), quote=False).replace('\n', '<br>')
    # PARY AKORD+SYLABA. Akord i sylaba, nad którą stoi, tworzą jeden
    # inline-block: akord zajmuje PRAWDZIWE miejsce w układzie (wiersz nad
    # sylabą), więc:
    #  - akordy nie mogą na siebie nachodzić (para po prostu się poszerza),
    #  - przy zawijaniu linii akord ZAWSZE wędruje razem ze swoją sylabą,
    #  - auto-dopasowanie rozmiaru (fitText) widzi pełną wysokość treści.
    # Zastępuje wcześniejsze zgadywanie szerokości w "ch", absolutne
    # pozycjonowanie i JS-owe rozsuwanie kolizji (fixChordOverlap).
    tokens = re.split(r'(\[.*?\])', text)

    def esc(s):
        return (html.escape(s, quote=False)
                .replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')
                .replace('  ', '&nbsp;&nbsp;'))

    def chord_inner_html(name):
        c = html.escape(name, quote=False)  # escapuj nazwę akordu
        if '/' in c:
            parts = c.split('/')
            c = (f"{parts[0]}<span class='bass-slash'>/</span>"
                 f"<span class='bass-note'>{'/'.join(parts[1:])}</span>")
        return c

    parts_out = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.startswith('[') and token.endswith(']'):
            name = token[1:-1].strip()
            if not name:
                i += 1
                continue
            # Sylaba pary: tekst za akordem do końca słowa (albo pusta, gdy
            # zaraz kolejny akord / koniec linii — para trzyma wtedy wysokość
            # przez CSS ::before z zero-width space).
            syl = ''
            if i + 1 < len(tokens) and not (tokens[i + 1].startswith('[') and tokens[i + 1].endswith(']')):
                m = re.match(r'[^\s]+', tokens[i + 1])
                if m:
                    syl = m.group(0)
                    tokens[i + 1] = tokens[i + 1][len(syl):]
            # Akord w środku słowa (Ła[G/B]ska): WORD JOINER przed parą
            # zabrania złamania linii wewnątrz słowa.
            if parts_out and not parts_out[-1].endswith('>') and parts_out[-1][-1:] and not parts_out[-1][-1:].isspace():
                parts_out.append('&#8288;')
            parts_out.append(
                f'<span class="chord-pair"><span class="chord">{chord_inner_html(name)}</span>'
                f'<span class="chord-syl">{esc(syl)}</span></span>')
        else:
            # escapuj tekst pieśni PRZED zamianą tab/spacji na &nbsp; (żeby nie
            # podwójnie escapować wstawianych encji)
            parts_out.append(esc(token))
        i += 1

    text_smart = ''.join(parts_out)
    text_band = text_smart.replace('\n', '<br>')
    blocks = re.split(r'\n\s*\n', text_smart)
    html_blocks = []
    
    for block in blocks:
        if block.strip():
            block_clean = block.strip().replace('\n', '<br>')
            html_blocks.append(f'<div class="print-block">{block_clean}</div>')
            
    text_print = "".join(html_blocks)
    return text_people, text_band, text_print

# --- 6. ROUTING ---
