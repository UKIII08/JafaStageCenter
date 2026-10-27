# Diagnostyka wyświetlania na zestawie trudnych piosenek (tests/song_corpus.py).
# Każda piosenka idzie ścieżką zapisu (prepare_song) i wyświetlania
# (parse_song_sections + process_song); sprawdzamy, że nic nie ginie
# i akordy stoją nad właściwymi sylabami.
import html
import re

import pytest

import music_core as mc
from tests.song_corpus import SONGS


def _chords(src):
    return [c.strip() for c in re.findall(r'\[([^\[\]]*)\]', src) if c.strip()]


def _plain(s):
    s = s.replace(' ', ' ').replace('⁠', '').replace('&nbsp;', ' ')
    return re.sub(r'\s+', ' ', s).strip()


def _band_parts(band):
    chords = [re.sub(r'<[^>]+>', '', html.unescape(c)) for c in re.findall(
        r'<span class="chord">(.*?)</span><span class="chord-syl">', band)]
    syls = [html.unescape(s) for s in re.findall(r'<span class="chord-syl">(.*?)</span>', band)]
    text = re.sub(r'<span class="chord">.*?</span><span class="chord-syl">', '', band)
    text = re.sub(r'<[^>]+>', '', text.replace('<br>', '\n'))
    return chords, syls, html.unescape(text)


@pytest.mark.parametrize('name', sorted(SONGS))
def test_song_survives_save_and_display(name):
    raw, notation = SONGS[name]
    saved = mc.prepare_song(raw, notation)['content']
    # zapis jest stały — ponowny zapis niczego nie zmienia
    assert mc.prepare_song(saved)['content'] == saved
    # bez niewidocznych znaków i końców linii z Windowsa
    assert not re.search('[\r​﻿⁠­]', saved)
    sections = mc.parse_song_sections(saved)
    assert _chords('\n'.join(s['content'] for s in sections)) == _chords(saved)
    for sec in sections:
        people, band, _ = mc.process_song(sec['content'])
        chords, syls, text = _band_parts(band)
        # każdy akord jest, w tej samej kolejności
        assert chords == [mc.canon_chord(c) for c in _chords(sec['content'])]
        # tekst piosenki nic nie traci
        src_text = re.sub(r'\[[^\[\]]*\]', '', sec['content'])
        # (porównanie bez znaczników — tekst z „<b>” w piosence jest escapowany)
        assert _plain(re.sub(r'<[^>]+>', '', text)) == _plain(re.sub(r'<[^>]+>', '', src_text))
        # akord stoi nad pierwszym fragmentem tekstu za nim
        for m, syl in zip(re.finditer(r'\[[^\[\]]*\]([^\[\n]*)', sec['content']), syls):
            assert _plain(syl) == _plain(re.match(r'\S*', m.group(1)).group(0))
        # HTML z tekstu jest bezpieczny, na rzutnik nie trafiają akordy
        assert '<script' not in band and '<script' not in people
        assert not any('[' + c + ']' in people for c in _chords(sec['content']))


def test_label_separated_by_blank_line_keeps_its_section():
    saved = mc.prepare_song(SONGS['many_blank_lines'][0])['content']
    assert [s['label'] for s in mc.parse_song_sections(saved)] == ['Zwrotka', 'Refren']


def test_pasted_chordpro_is_converted_with_meta():
    prep = mc.prepare_song(SONGS['chordpro_directives'][0])
    assert 'chordpro' in prep['changes'] and prep['meta']['title'] == 'Testowa'
    assert '{' not in prep['content']
    assert [s['label'] for s in mc.parse_song_sections(prep['content'])] == ['Verse', 'Chorus']


def test_capo_line_is_flagged():
    kinds = [i['kind'] for i in mc.analyze_song(SONGS['capo_comment'][0])['issues']]
    assert 'capo_line' in kinds


def test_sections_match_studio_rule():
    # samodzielna nazwa części na końcu = osobna część z tą nazwą (jak w Studiu)
    secs = mc.parse_song_sections(mc.prepare_song(SONGS['single_line_sections'][0])['content'])
    assert secs[-1] == {'label': 'Outro', 'content': ''}


def test_continuation_label_is_a_section_name():
    # „Refren (cd.)" powstaje przy dzieleniu długiej części na slajdy
    for label in ('Refren (cd.)', 'Zwrotka 2 (cd.)', 'Chorus (cont.)'):
        assert mc.is_section_label(label)
    assert not mc.is_section_label('Ala (cd.)')
