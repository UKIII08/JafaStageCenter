# Testy music_core — przeniesione scenariusze z sesji rozwojowych desktopu
# (enharmonia, ochrona nie-akordów, pary akord+sylaba, konwerter UG, silniki).
import re

import music_core as mc


def T(chord, shift, notation='international'):
    return re.sub(r'\[(.*?)\]',
                  lambda m: mc.transpose_chord(m, shift, notation), chord)


# ── Transpozycja: enharmonia dziedziczy pisownię źródła ──
def test_transpose_flavor():
    assert T('[F#m]', 2) == '[G#m]'        # nie Abm
    assert T('[Bb]', 3) == '[Db]'          # nie C#
    assert T('[Eb]', -1) == '[D]'
    assert T('[D/F#]', 2) == '[E/G#]'
    assert T('[fis]', 2) == '[gis]'        # pisownia "is" zachowana
    assert T('[a]', 2) == '[b]'            # małe litery = moll


def test_transpose_skips_non_chords():
    for tok in ('[Coda]', '[Bridge]', '[Intro]', '[x2]', '[Refren]'):
        assert T(tok, 2) == tok


def test_transpose_roundtrip():
    c = '[Bb]'
    for _ in range(12):
        c = T(c, 1)
    assert c == '[Bb]'


# ── Normalizacja przy zapisie ──
def test_normalize_preserves_flavor():
    n = mc.normalize_chord_to_international
    assert n('G#m') == 'G#m'               # nie Abm
    assert n('Cis', input_notation='polish') == 'C#'
    assert n('B', input_notation='polish') == 'Bb'
    assert n('H', input_notation='polish') == 'B'
    assert n('fis', input_notation='polish') == 'F#m'


# ── Renderowanie: pary akord+sylaba ──
def test_process_song_chord_pairs():
    _, band, _ = mc.process_song('Ła[G/B]ska [C]Pana\n[D]\n[C][G]')
    assert 'chord-pair' in band
    assert 'chord-syl' in band
    assert "bass-note" in band             # slash chord ma bas
    # tekst "people" bez akordów
    people, _, _ = mc.process_song('[C]Alleluja [G]amen')
    assert '[' not in people and 'Alleluja' in people


def test_process_song_escapes_html():
    _, band, _ = mc.process_song('<script>alert(1)</script> [C]tekst')
    assert '<script>' not in band


# ── Konwerter "akordy nad tekstem" ──
UG = """[Verse 1]
Am        C
Cudowny Bóg
G          F                    Am   C
Odrzucił Król majestat swój"""


def test_convert_chords_over_lyrics():
    out, changed = mc.convert_chords_over_lyrics(UG)
    assert changed
    assert '[Am]Cudowny [C]Bóg' in out
    assert 'Verse 1' in out and '[Verse 1]' not in out
    # idempotencja
    out2, ch2 = mc.convert_chords_over_lyrics(out)
    assert out2 == out and not ch2


def test_convert_false_positive_traps():
    for line, expected in [('A ja idę', False), ('A', False),
                           ('Amen', False), ('Am C G F', True),
                           ('C/E', True), ('Am', True)]:
        from music_core.chords import _is_chords_over_lyrics_line
        assert _is_chords_over_lyrics_line(line) == expected, line


# ── Detekcja tonacji ──
def test_key_detection():
    assert mc.detect_key_algorithm('[Am] x [G] y [F] z [E7] w') == 'Am'
    assert mc.detect_key_algorithm('bez akordów wcale') in ('N/A', '')


# ── Silniki przejść ──
def test_engines_contract():
    for key, cls in mc.TRANSITION_ENGINES.items():
        eng = cls()
        out = eng.generate_full_progression('[G]', '[G]', '[Am]', '[C]')
        assert out[0] == '[G]' and out[-1] == '[Am]', key
        assert len(out) == 5, key


def test_engine_v4_context():
    eng = mc.TRANSITION_ENGINES['v4']()
    out = eng.generate_full_progression(
        '[G]', '[G]', '[Am7]', '[C]',
        song_a_content='[G]a [C]b [D]c [Em]d', song_b_content='[Am7]x [F]y')
    assert len(out) == 5 and out[-1] == '[Am7]'


# ── Wpisywanie akordów: symbole, polskie bemole, 6/9, N.C. ────────────────
def test_canon_chord_symbols():
    assert mc.canon_chord('F♯m') == 'F#m'
    assert mc.canon_chord('B♭') == 'Bb'
    assert mc.canon_chord('C△7') == 'Cmaj7'
    assert mc.canon_chord('B°') == 'Bdim'
    assert mc.canon_chord('Bø') == 'Bm7b5'
    for ch in ('F♯m', 'C△7', 'Bø', 'N.C.', 'C6/9', 'Des', 'Ges', 'Ces', 'fis'):
        assert mc.is_valid_chord(mc.canon_chord(ch)), ch


def test_six_nine_is_not_a_bass_note():
    from music_core.chords import bass_split
    assert bass_split('C6/9') == ('C6/9', None)
    assert list(bass_split('G/B')) == ['G', 'B']
    assert T('[C6/9]', 2) == '[D6/9]'


def test_polish_flats_normalize():
    out = mc.normalize_song_chords_to_international('[Des]a [Ges]b [H]c [B]d [fis]e', 'polish')
    assert out == '[Db]a [Gb]b [B]c [Bb]d [F#m]e'


def test_chord_only_line_can_wrap():
    html = mc.process_song('[G] [D] [Em] [C] [G] [D] [Em] [C]')[1]
    assert '⁠' not in html          # brak WORD JOINER = linia może się złamać
    assert '</span> <span' in html       # zwykła spacja między parami


def test_tidy_song_text():
    text, changes = mc.tidy_song_text('[Refren]\n[[G]]Ala [] ma   \n\n\n\nkota')
    assert text == 'Refren\n[G]Ala  ma\n\nkota'
    assert changes


def test_analyze_song_reports_lines():
    r = mc.analyze_song('Zwrotka\n[G]Ala [Xyz]ma\n[C kota\n\n[Refren]\n[[D]]x')
    kinds = {(i['kind'], i['line']) for i in r['issues']}
    assert ('unclosed', 3) in kinds
    assert ('label_brackets', 5) in kinds
    assert ('double_brackets', 6) in kinds
    assert r['invalid'] == [{'chord': 'Xyz', 'lines': [2]}]


def test_analyze_song_notation_and_above_lyrics():
    r = mc.analyze_song('[H]a [Fis]b [e]c', 'international')
    assert r['notation_hint'] and r['notation_hint']['notation'] == 'polish'
    assert mc.analyze_song('[H]a [Fis]b', 'polish')['notation_hint'] is None
    r = mc.analyze_song('Zwrotka\nG       D\nAla ma kota')
    assert r['above_lyrics'] == [2]
