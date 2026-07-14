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
