# Zestaw piosenek testowych do sprawdzania wyświetlania akordów.
# Teksty są wymyślone na potrzeby testów — każda piosenka celowo zawiera
# przypadki, które w praktyce psuły albo mogłyby psuć wyświetlanie.
# Klucz: nazwa przypadku → (treść, notacja wpisu).

SONGS = {
    'basic': ("""Zwrotka 1
[G]Idę przez [D]pola o [Em]świcie
[C]światło [G]prowadzi mnie [D]dalej

Refren
[C]Śpiewam [G]głośno [D]dziś
[Em]Ty [C]jesteś [D]blisko""", 'international'),

    'mid_word': ("""Zwrotka
Ła[G/B]ska Two[C]ja jest wiel[D]ka
Prze[Em]baczenie [C]da[D]rem""", 'international'),

    'adjacent_chords': ("""Refren
[G][D/F#]Razem [Em][C]idziemy
[Am7][D]dalej[G]""", 'international'),

    'chord_only_intro': ("""Intro
[G]  [D]  [Em]  [C]

Przejście
[G] [D/F#] [Em] [C] [G] [D/F#] [Em] [C] [Am7] [D] [G] [C]""", 'international'),

    'extended_chords': ("""Bridge
[Cmaj7]Niebo [Dsus4]nad [D]nami [Em7]świeci
[Am7b5]Cicho [B7#9]i [Ebdim]głośno [F#m7b5]razem
[Gadd9]Jasno [Asus2]i [C6/9]pięknie [Bb13]dalej
[E+]Wyżej [G7sus4]i [Dm9]wyżej""", 'international'),

    'polish_input': ("""Zwrotka
[e]Idę [H]dalej [Fis]przez [B]most
[a]Cicho [Es]i [As]mocno [Cis]dziś
[fis]Wiatr [Gis]i [d]deszcz""", 'polish'),

    'unicode_symbols': ("""Zwrotka
[F♯m]Jasno [B♭]i [C△7]ciepło [B°]dziś
[Bø]Cisza [E♭maj7]nad [A♭]wodą""", 'international'),

    'nc_and_repeat': ("""Koniec
[G]Amen [D]amen [N.C.]amen (x2)
||: [C]Alle[G]luja :||""", 'international'),

    'long_line': ("""Zwrotka
[G]To jest bardzo długa linia tekstu, która na telefonie [D]na pewno się zawinie do kolejnego [Em]wiersza i musi zachować akordy nad [C]właściwymi sylabami bez nachodzenia""", 'international'),

    'long_word': ("""Zwrotka
[G]Konstantynopolitańczykowianeczka [D]najdłuższe [Em]słowo""", 'international'),

    'punctuation': ("""Zwrotka
[G], to jest [D]„cytat” i [Em](nawias) [C]— myślnik.
Pytanie[G]? [D]Tak!""", 'international'),

    'html_like': ("""Zwrotka
[G]Tekst z <b>tagiem</b> i [D]& znakiem
[Em]Skrypt <script>alert(1)</script> [C]koniec""", 'international'),

    'crlf_windows': ("Zwrotka 1\r\n[G]Linia z [D]Windowsa\r\n[Em]druga [C]linia\r\n\r\nRefren\r\n[C]Refren [G]tutaj\r\n", 'international'),

    'nbsp_and_tabs': ("Zwrotka\n[G] Tekst z twardą [D]spacją\n[Em]\tTab [C]tutaj\n  [G]Wcięta [D]linia", 'international'),

    'zero_width': ("Zwrotka\n[G]Tekst​z​niewidocznymi [D]znakami﻿", 'international'),

    'chords_over_lyrics': ("""Zwrotka 1
G        D         Em
Idę przez pola o świcie
C           G
Światło prowadzi mnie

Refren
C      G      D
Śpiewam głośno dziś""", 'international'),

    'labels_variety': ("""Verse 1
[G]English [D]label

Chorus x2
[C]Repeat [G]this

Pre-Chorus:
[Am]Before [D]chorus

[Bridge]
[Em]Bracket [C]label

(Refren)
[G]Paren [D]label

Zakończenie
[G]Koniec""", 'international'),

    'label_looks_like_text': ("""Alleluja
[G]Alle[D]luja [Em]amen

Amen
[C]Amen [G]amen""", 'international'),

    'no_labels': ("""[G]Pierwsza [D]linia bez etykiety
[Em]druga [C]linia

[G]Druga [D]sekcja bez etykiety""", 'international'),

    'single_line_sections': ("""Intro
[G] [D]

[Em]Jedna linia sekcji

Outro""", 'international'),

    'many_blank_lines': ("""Zwrotka


[G]Po wielu [D]pustych


Refren



[C]Refren [G]tu""", 'international'),

    'trailing_spaces': ("Zwrotka   \n[G]Tekst [D]ze spacjami   \n\n   \nRefren\n[C]Dalej   ", 'international'),

    'chordpro_directives': ("""{title: Testowa}
{key: G}
{start_of_verse}
[G]Zwrotka [D]chordpro
{end_of_verse}
{start_of_chorus}
[C]Refren [G]chordpro
{end_of_chorus}""", 'international'),

    'capo_comment': ("""Capo 2
Zwrotka
[G]Z kapo [D]na drugim""", 'international'),

    'bracket_errors': ("""Zwrotka
[G]Dobry [D]akord
[[Em]]podwójny [Xyz]zły
[]pusty [C]ok""", 'international'),

    'sharps_flats_mix': ("""Zwrotka
[F#]Krzyżyk [Gb]bemol [A#m]krzyżyk [Bbm]bemol
[Db/F]Bas [C#/E#]dziwny [Cb]rzadki [E#]rzadki""", 'international'),

    'emoji_and_diacritics': ("""Zwrotka 🙏
[G]Zażółć [D]gęślą [Em]jaźń 🎵
[C]Ąę [G]Óź ż""", 'international'),

    'chord_after_space': ("""Zwrotka
Tekst [G] przed spacją [D] i po
[Em] Zaczyna od spacji""", 'international'),

    'chord_end_of_line': ("""Zwrotka
Linia kończy się akordem [G]
Druga też [D]
[Em]""", 'international'),

    'big_song': ("\n\n".join(
        f"Zwrotka {i}\n[G]Linia {i} [D]pierwsza [Em]tutaj [C]dziś\n[Am]Linia {i} [D]druga [G]tutaj" for i in range(1, 13)), 'international'),
}
