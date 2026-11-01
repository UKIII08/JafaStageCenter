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
