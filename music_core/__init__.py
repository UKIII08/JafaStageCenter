"""music_core — wspólny silnik muzyczny JafaStage (web + desktop od M5).

Źródło prawdy dla: akordów, transpozycji, notacji, detekcji tonacji,
renderowania pieśni i silników przejść między piosenkami.
"""
from music_core.chords import (
    is_valid_chord, clean_chord,
    normalize_chord_to_international, normalize_song_chords_to_international,
    transpose_chord, apply_transpose_to_single_chord,
    convert_chords_over_lyrics,
    detect_key_algorithm,
    get_first_chord_of_song, get_first_chord_from_chorus,
    process_song, parse_song_sections,
)
from music_core.engine_v2 import WorshipHybridEngineV2
from music_core.engine_v3 import WorshipPivotEngineV3
from music_core.engine_v4 import WorshipContextEngineV4

TRANSITION_ENGINES = {
    'v2': WorshipHybridEngineV2,
    'v3': WorshipPivotEngineV3,
    'v4': WorshipContextEngineV4,
}
