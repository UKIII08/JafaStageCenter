# Diagramy akordów (static/js/chord_diagrams.js) liczone w Node.
# A7 = septyma mała (G); Amaj7, A7maj i A7+ = septyma wielka (G#).
import json
import shutil
import subprocess

import pytest

NODE = shutil.which('node')
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def piano(chords):
    js = ("const fs=require('fs');"
          "const f=new Function(fs.readFileSync('static/js/chord_diagrams.js','utf8')"
          "+';return {lookupPianoChord};')();"
          "console.log(JSON.stringify(%s.map(c=>f.lookupPianoChord(c))));" % json.dumps(chords))
    out = subprocess.run([NODE, '-e', js], capture_output=True, text=True, check=True).stdout
    return [[NAMES[n % 12] for n in notes] for notes in json.loads(out)]


@pytest.mark.skipif(not NODE, reason='node not installed')
def test_seventh_chords():
    a7, amaj7, a7maj, a7plus, a7plus5, am7 = piano(['A7', 'Amaj7', 'A7maj', 'A7+', 'A7+5', 'Am7'])
    assert a7 == ['A', 'C#', 'E', 'G']
    assert amaj7 == a7maj == a7plus == ['A', 'C#', 'E', 'G#']
    assert 'F' in a7plus5 and 'G' in a7plus5          # +5 to wciąż podwyższona kwinta
    assert am7 == ['A', 'C', 'E', 'G']


@pytest.mark.skipif(not NODE, reason='node not installed')
def test_every_chord_type_against_theory():
    """Każdy rodzaj akordu od każdego dźwięku: pianino i gitara nie grają
    obcych dźwięków (tests/js/chord_theory.js liczy teorię niezależnie)."""
    out = subprocess.run([NODE, 'tests/js/chord_theory.js', '.'], capture_output=True,
                         text=True, check=True).stdout
    res = json.loads(out)
    assert res['total'] > 900
    assert res['errors'] == []


@pytest.mark.skipif(not NODE, reason='node not installed')
def test_songbook_spellings():
    g2, c4, cplus, cminus, cm7, c69, e_gis = piano(['G2', 'C4', 'C+', 'C-', 'CM7', 'C6/9', 'E/gis'])
    assert g2 == ['G', 'B', 'D', 'A']                  # G2 = Gadd2
    assert c4 == ['C', 'F', 'G']                       # C4 = Csus4
    assert cplus == ['C', 'E', 'G#']                   # C+ = Caug
    assert cminus == ['C', 'D#', 'G']                  # C- = Cm
    assert cm7 == ['C', 'E', 'G', 'B']                 # CM7 = Cmaj7, nie Cm7
    assert sorted(c69) == sorted(['C', 'E', 'G', 'A', 'D'])
    assert e_gis[0] == 'G#'                            # polski bas na dole
