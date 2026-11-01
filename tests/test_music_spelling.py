# Pisownia akordów po transpozycji (serwer i telefon), przejścia, tryb
# początkującego. Akordy piszą się znakami tonacji docelowej, nie każdy osobno.
import json
import re
import shutil
import subprocess

import pytest

from music_core import chords as mc
from music_core.engine_v4 import WorshipContextEngineV4

NODE = shutil.which('node')
SHARPS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FLATS = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']


def shown(song, n, **kw):
    html = mc.process_song(song, n, **kw)[1]
    return re.findall(r'class="chord">([^<]*)', html)


def mixed(chords):
    roots = [re.match(r'[A-G][#b]?', c).group(0) for c in chords]
    return any('#' in r for r in roots) and any(len(r) > 1 and r[1] == 'b' for r in roots)


def test_real_song_up_a_semitone_reads_in_one_key():
    # „Jedyny Król" (a-moll) o pół tonu w górę = b-moll: Gb i Db, nie F# i C#
    got = shown('[Am][G][F][Dm][Fmaj7][C]', 1, key='Am')
    assert got == ['Bbm', 'Ab', 'Gb', 'Ebm', 'Gbmaj7', 'Db']


def test_borrowed_chords_keep_flats_in_sharp_keys():
    assert shown('[G][Bb][Eb][D][C]', 2, key='G') == ['A', 'C', 'F', 'E', 'D']
    assert shown('[D][Bb][C][A]', 0 + 7, key='D') == ['A', 'F', 'G', 'E']


def test_leading_tone_in_minor_is_sharp():
    assert shown('[Am][E7][G#dim]', 3, key='Am') == ['Cm', 'G7', 'Bdim']
    assert shown('[Bm][F#7]', -1, key='Bm') == ['Bbm', 'F7']


@pytest.mark.parametrize('tonic', range(12))
@pytest.mark.parametrize('minor', [False, True])
def test_every_key_every_shift_is_consistent(tonic, minor):
    names = FLATS if tonic in (1, 3, 5, 8, 10) else SHARPS
    q = 'm' if minor else ''
    song = ''.join(f'[{names[(tonic + i) % 12]}{s}]' for i, s in
                   [(0, q), (7, ''), (5, q), (9 if not minor else 8, 'm' if not minor else '')])
    for n in range(-6, 7):
        out = shown(song, n)
        assert not mixed(out), (song, n, out)
        src = re.findall(r'\[([^\]]+)\]', song)
        for a, b in zip(src, out):
            assert (mc._chord_pc(a)[0] + n) % 12 == mc._chord_pc(b)[0]


def test_shown_key_uses_key_signature_names():
    t = mc.apply_transpose_to_single_chord
    assert [t(f'[{k}]', n).strip('[]') for k, n in
            [('C', 1), ('E', -1), ('Gm', 3), ('Am', 1), ('D', 4), ('Em', -1)]] == \
        ['Db', 'Eb', 'Bbm', 'Bbm', 'F#', 'Ebm']


def test_transition_is_spelled_in_target_key():
    out = WorshipContextEngineV4().generate_full_progression('C', 'C', 'F#', 'F#')
    out = out[:1] + [mc.respell_in_key(c, 'F#') for c in out[1:]]
    assert not any('b' in c.strip('[]')[1:2] for c in out[1:])


def js(expr_list):
    code = ("global.window=global;require('./static/js/chords-client.js');"
            "console.log(JSON.stringify(%s));" % expr_list)
    return json.loads(subprocess.run([NODE, '-e', code], capture_output=True, text=True,
                                     check=True).stdout)


@pytest.mark.skipif(not NODE, reason='node not installed')
def test_capo_on_phone_spells_shapes_in_one_key():
    # Bb z kapodastrem na 1. progu = chwyty z A-dur: E/G#, nie E/Ab
    out = js("['Bb','Gm','Eb','F/A','Cm7'].map(c=>jafaChords.transpose(c,-1,'Bb'))")
    assert out == ['A', 'F#m', 'D', 'E/G#', 'Bm7']


@pytest.mark.skipif(not NODE, reason='node not installed')
def test_phone_and_server_agree():
    chords = [r + s for r in SHARPS + ['Db', 'Eb', 'Gb', 'Ab', 'Bb'] for s in ('', 'm', '7', '/E')]
    out = js("(%s).map(c=>[-5,-2,1,3,6].map(n=>jafaChords.transpose(c,n,c.split('/')[0])))"
             % json.dumps(chords))
    for c, row in zip(chords, out):
        for n, got in zip([-5, -2, 1, 3, 6], row):
            assert mc.apply_transpose_to_single_chord(f'[{c}]', n, key=c.split('/')[0]) == f'[{got}]'


@pytest.mark.skipif(not NODE, reason='node not installed')
def test_beginner_mode_keeps_minor_third():
    assert js("['Cdim','Bm7b5','F#dim7','Am7','Gsus4','Caug'].map(jafaChords.simplify)") == \
        ['Cm', 'Bm', 'F#m', 'Am', 'G', 'C']
