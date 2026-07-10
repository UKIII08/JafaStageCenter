import re
from PivotEngine import WorshipPivotEngineV3

class WorshipContextEngineV4(WorshipPivotEngineV3):
    """
    WorshipContextEngine V4 - 'Kontekstowy'
    ----------------------------------------
    Rozszerza V3 o analizę PEŁNEJ TREŚCI obu piosenek (nie tylko dwóch
    akordów i dwóch tonacji). Kontrakt wyjścia bez zmian:
    [start] + 3 takty + [lądowanie].

    Co dochodzi ponad V3:
    1. WSPÓLNY REPERTUAR: akordy, które realnie występują w obu piosenkach
       (po transpozycji!), dostają pierwszeństwo jako pivoty - zespół już je
       ma pod palcami i brzmią jak obie piosenki naraz.
    2. DOPASOWANIE STYLU: jeśli obie piosenki grają prostymi triadami,
       przejście nie wyskoczy z m7b5 i 13-tkami; jeśli są bogate w sus/add9,
       przejście może kolorować śmielej.
    3. POCZĄTEK PIOSENKI B: przejście unika wcześniejszego ogrania DRUGIEGO
       akordu B (żeby wejście B nie brzmiało jak powtórka pomostu).
    4. NUTA PEDAŁOWA: bonus dla ścieżek, przez które da się przetrzymać
       jeden wspólny dźwięk od startu do lądowania (pad/klawisz trzyma nutę
       - najgładszy trik przejściowy w worship).
    5. KONTUR BASU: bonus za bas idący konsekwentnie w jedną stronę.
    6. RÓŻNICA TEMP: przy dużym skoku BPM preferuje statyczne kolory
       (add9/sus2) zamiast dominant pchających do przodu.
    """

    _MIN_FAMILY = ('min', 'min7', 'dim', 'm7b5')
    _COLOR_QUALITIES = ('7sus4', 'min7', 'maj7', 'dom7', 'add9', 'sus2', 'sus4', 'm7b5')
    _FANCY_QUALITIES = ('7sus4', 'm7b5', 'maj7', 'min7', 'dom7')

    def _song_profile(self, content, shift=0):
        """Analiza treści piosenki -> repertuar akordów (po transpozycji),
        udział 'kolorów' i pierwsze akordy."""
        vocab = set()
        parsed_seq = []
        colored = total = 0
        for token in re.findall(r'\[([^\[\]]{1,12})\]', content or ''):
            p = self._parse(token)
            if not p:
                continue
            root = (p[0] + shift) % 12
            quality = p[1]
            total += 1
            if quality in self._COLOR_QUALITIES:
                colored += 1
            fam = 'min' if quality in self._MIN_FAMILY else 'maj'
            vocab.add((root, fam))
            if len(parsed_seq) < 3:
                parsed_seq.append((root, quality))
        return {
            'vocab': vocab,
            'color': (colored / total) if total else 0.35,
            'opening': parsed_seq,
        }

    def generate_full_progression(self, start_chord, start_key, end_chord, end_key,
                                  song_a_content=None, song_b_content=None,
                                  shift_a=0, shift_b=0, bpm_a=0, bpm_b=0):
        start_clean = (start_chord or '').replace('[', '').replace(']', '').strip()
        end_clean = (end_chord or '').replace('[', '').replace(']', '').strip()

        src_root, src_minor = self._key_info(start_key)
        tgt_root, tgt_minor = self._key_info(end_key)
        use_flats = self._use_flats(tgt_root, tgt_minor)

        start_p = self._parse(start_clean) or (src_root, 'min' if src_minor else 'maj', src_root)
        land_p = self._parse(end_clean) or (tgt_root, 'min' if tgt_minor else 'maj', tgt_root)
        start_node = self._as_node(start_p)
        land_node = self._as_node(land_p)

        cands = self._candidates(tgt_root, tgt_minor, land_p[0], land_p[1],
                                 src_root, src_minor, use_flats)

        # ---- KONTEKST OBU PIOSENEK ----
        prof_a = self._song_profile(song_a_content, shift_a)
        prof_b = self._song_profile(song_b_content, shift_b)
        avg_color = (prof_a['color'] + prof_b['color']) / 2
        # kara za "wymyślność" gdy obie piosenki grają prosto (skala 0..1)
        simplicity = max(0.0, 0.45 - avg_color) / 0.45
        big_tempo_gap = bool(bpm_a and bpm_b and abs(bpm_a - bpm_b) >= 15)
        # drugi akord piosenki B (nie ogrywać go w pomoście)
        b_second = prof_b['opening'][1] if len(prof_b['opening']) > 1 else None

        for c in cands:
            fam = 'min' if c['quality'] in self._MIN_FAMILY else 'maj'
            key_c = (c['root'], fam)
            in_a = key_c in prof_a['vocab']
            in_b = key_c in prof_b['vocab']
            if in_a and in_b:
                # realny wspólny repertuar - najlepszy pivot, jaki istnieje
                c['prior'][0] += 18
                c['prior'][1] += 8
            elif in_b:
                c['prior'][1] += 8
                c['prior'][2] += 6
            elif in_a:
                c['prior'][0] += 8
            if simplicity > 0:
                # obie piosenki grają prosto -> przejście też ma grać prosto
                # kary muszą przebić strukturalną premię akordów
                # 4-dźwiękowych w scoringu par (więcej wspólnych dźwięków)
                if c['quality'] in self._FANCY_QUALITIES:
                    p = int(28 * simplicity)
                    c['prior'] = [x - p for x in c['prior']]
                elif c['quality'] in ('add9', 'sus2'):
                    p = int(16 * simplicity)
                    c['prior'] = [x - p for x in c['prior']]
            if big_tempo_gap:
                if c['quality'] in ('add9', 'sus2', 'maj'):
                    c['prior'] = [x + 5 for x in c['prior']]
                elif c['quality'] == 'dom7':
                    c['prior'] = [x - 8 for x in c['prior']]
            if b_second is not None and c['root'] == b_second[0] and \
               ('min' if b_second[1] in self._MIN_FAMILY else 'maj') == fam:
                c['prior'][1] -= 10
                c['prior'][2] -= 16

        # pre-echo akordu lądowania (jak w V3)
        land_minor = land_p[1] in self._MIN_FAMILY
        for c in cands:
            if c['root'] == land_p[0] and \
               (c['quality'] in self._MIN_FAMILY) == land_minor:
                c['prior'][2] -= 60
                c['prior'][0] -= 25
                c['prior'][1] -= 10

        # ---- DP drugiego rzędu (jak V3) + bonusy CAŁOŚCIOWE ścieżki ----
        n = len(cands)
        NEG = float('-inf')
        start_minor = start_p[1] in self._MIN_FAMILY
        P = [[self._pair_score(cands[j], cands[k]) for k in range(n)]
             for j in range(n)]
        first = [self._pair_score(start_node, c) + c['prior'][0] for c in cands]
        closing = [self._pair_score(c, land_node) + c['prior'][2] for c in cands]
        best2 = [[NEG] * n for _ in range(n)]
        for j in range(n):
            fj = first[j]
            for k in range(n):
                s = fj + P[j][k] + cands[k]['prior'][1]
                if cands[k]['root'] == start_p[0] and \
                   (cands[k]['quality'] in self._MIN_FAMILY) == start_minor:
                    s -= 35
                best2[j][k] = s

        # nuty wspólne startu i lądowania - kandydatki na pedał
        pedal_pcs = start_node['tones'] & land_node['tones']
        start_bass, land_bass = start_p[2], land_p[2]

        best_total, best_path = NEG, (0, 0, 0)
        for j in range(n):
            b2j = best2[j]
            tj = cands[j]['tones']
            bj = cands[j]['bass']
            for k in range(n):
                base = b2j[k]
                Pk = P[k]
                tk = cands[k]['tones']
                bk = cands[k]['bass']
                # kierunek basu start->j->k (najkrótszą drogą, -6..+6)
                d1 = (bj - start_bass + 6) % 12 - 6
                d2 = (bk - bj + 6) % 12 - 6
                for l in range(n):
                    s = base + Pk[l] + closing[l]
                    if l == j:
                        s -= 40
                    cl = cands[l]
                    # PEDAŁ: jeden dźwięk gra przez całe przejście
                    if pedal_pcs and (pedal_pcs & tj & tk & cl['tones']):
                        s += 22
                    # KONTUR: bas konsekwentnie w jedną stronę do lądowania
                    d3 = (cl['bass'] - bk + 6) % 12 - 6
                    d4 = (land_bass - cl['bass'] + 6) % 12 - 6
                    dirs = [d for d in (d1, d2, d3, d4) if d != 0]
                    if len(dirs) >= 3 and (all(d > 0 for d in dirs) or all(d < 0 for d in dirs)):
                        s += 12
                    if s > best_total:
                        best_total, best_path = s, (j, k, l)
        bridge = [cands[i]['name'] for i in best_path]

        return [f"[{start_clean or self._spell(src_root, 'maj', src_root, use_flats)}]",
                *[f"[{c}]" for c in bridge],
                f"[{end_clean or self._spell(tgt_root, 'maj', tgt_root, use_flats)}]"]
