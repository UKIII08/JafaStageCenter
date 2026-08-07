import re

class WorshipPivotEngineV3:
    """
    WorshipPivotEngine V3 - 'Pivot & Voice-Leading'
    ------------------------------------------------
    Kontrakt jak w V2: wejście = ostatni akord piosenki A + jej tonacja oraz
    pierwszy akord piosenki B + jej tonacja; wyjście = 5 tokenów
    [start] [t2] [t3] [t4] [lądowanie], czyli 4 takty + downbeat piosenki B.

    Co robi inaczej niż V1/V2:
    1. PIVOT: pierwszy takt pomostu preferuje akord WSPÓLNY obu tonacji
       (diatoniczny i tu, i tu) - ucho zespołu nie słyszy szwu.
    2. CEL = AKORD, nie tonacja: ostatni takt pomostu to akord dojściowy do
       KONKRETNEGO akordu lądowania (V7sus4/x, IV/x, bVII/x, bas krokiem),
       a nie kadencja na tonikę tonacji (V2 dla piosenki zaczynającej się od
       vi budował V7sus4->I i doklejał vi).
    3. VOICE-LEADING: scoring liczy wspólne dźwięki i sumę przesunięć
       składników akordu (nie tylko odległość prym), plus linię basu krokiem.
    4. PEŁNE PRZESZUKIWANIE: pula ~30 kandydatów na takt, dynamiczne
       programowanie po wszystkich parach (bez wąskiego beamu po szablonach).
    """

    NOTE_TO_INT = {
        'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
        'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8,
        'A': 9, 'A#': 10, 'Bb': 10, 'B': 11, 'Cb': 11,
        'Fb': 4, 'E#': 5, 'B#': 0, 'H': 11,
    }
    SHARP_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    FLAT_NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
    FLAT_MAJOR_KEYS = {5, 10, 3, 8, 1, 6}   # F Bb Eb Ab Db Gb
    FLAT_MINOR_KEYS = {2, 7, 0, 5, 10, 3}   # d g c f bb eb

    # interwały składników względem prymy
    QUALITY_TONES = {
        'maj':   (0, 4, 7),
        'min':   (0, 3, 7),
        'dim':   (0, 3, 6),
        'sus4':  (0, 5, 7),
        'sus2':  (0, 2, 7),
        'dom7':  (0, 4, 7, 10),
        '7sus4': (0, 5, 7, 10),
        'min7':  (0, 3, 7, 10),
        'maj7':  (0, 4, 7, 11),
        'add9':  (0, 2, 4, 7),
        'm7b5':  (0, 3, 6, 10),
    }

    # --- PARSOWANIE ---

    def _parse(self, chord_str):
        """-> (root_pc, quality, bass_pc) ; None gdy nie da się sparsować."""
        s = (chord_str or '').replace('[', '').replace(']', '').strip()
        if not s:
            return None
        bass_pc = None
        if '/' in s:
            s, _, bass = s.partition('/')
            m = re.match(r'^([A-Ga-g][#b]?)', bass.strip())
            if m:
                bass_pc = self.NOTE_TO_INT.get(m.group(1).capitalize())
        m = re.match(r'^([A-Ga-g][#b]?)(.*)$', s.strip())
        if not m:
            return None
        root = self.NOTE_TO_INT.get(m.group(1).capitalize())
        if root is None:
            return None
        suffix = m.group(2)
        low = suffix.lower()
        if 'maj7' in low:
            quality = 'maj7'
        elif '7sus' in low:
            quality = '7sus4'
        elif 'sus4' in low or (low.startswith('sus') and '2' not in low):
            quality = 'sus4'
        elif 'sus2' in low:
            quality = 'sus2'
        elif 'dim' in low or 'm7b5' in low or low.startswith('0'):
            quality = 'dim'
        elif re.match(r'^m(?!aj)', suffix) or (m.group(1)[0].islower() and 'maj' not in low):
            quality = 'min7' if '7' in low else 'min'
        elif '7' in low or '9' in low or '13' in low:
            quality = 'dom7'
        elif 'add9' in low:
            quality = 'add9'
        else:
            quality = 'maj'
        if bass_pc is None:
            bass_pc = root
        return (root, quality, bass_pc)

    def _tones(self, root, quality):
        return frozenset((root + i) % 12 for i in self.QUALITY_TONES.get(quality, (0, 4, 7)))

    def _name(self, pc, use_flats):
        return (self.FLAT_NAMES if use_flats else self.SHARP_NAMES)[pc % 12]

    def _spell(self, root, quality, bass, use_flats):
        root_name = self._name(root, use_flats)
        suffix = {
            'maj': '', 'min': 'm', 'dim': 'dim', 'sus4': 'sus4', 'sus2': 'sus2',
            'dom7': '7', '7sus4': '7sus4', 'min7': 'm7', 'maj7': 'maj7',
            'add9': 'add9', 'm7b5': 'm7b5',
        }[quality]
        if bass != root:
            return f"{root_name}{suffix}/{self._name(bass, use_flats)}"
        return f"{root_name}{suffix}"

    # --- TONACJE ---

    def _key_info(self, key_str):
        p = self._parse(key_str)
        if not p:
            return (0, False)
        root, quality, _ = p
        return (root, quality in ('min', 'min7', 'dim'))

    def _diatonic(self, key_root, is_minor):
        """Zbiór (pc, 'maj'/'min'/'dim') triad diatonicznych tonacji."""
        if is_minor:
            # moll naturalny + durowa dominanta (harmoniczna) - praktyka worship
            degrees = [(0, 'min'), (2, 'dim'), (3, 'maj'), (5, 'min'),
                       (7, 'min'), (7, 'maj'), (8, 'maj'), (10, 'maj')]
        else:
            degrees = [(0, 'maj'), (2, 'min'), (4, 'min'), (5, 'maj'),
                       (7, 'maj'), (9, 'min'), (11, 'dim')]
        return {((key_root + iv) % 12, q) for iv, q in degrees}

    def _use_flats(self, key_root, is_minor):
        return key_root in (self.FLAT_MINOR_KEYS if is_minor else self.FLAT_MAJOR_KEYS)

    # --- KANDYDACI ---

    def _candidates(self, key_root, is_minor, land_root, land_quality,
                    src_root, src_minor, use_flats):
        """Pula kandydatów na takty pomostu, z bonusami pozycyjnymi.

        Zwraca listę słowników:
          {'root','quality','bass','tones','name','prior':[b1,b2,b3]}
        prior[i] = bonus za użycie w takcie i pomostu (0=pivot, 2=dojście).
        """
        target_dia = self._diatonic(key_root, is_minor)
        source_dia = self._diatonic(src_root, src_minor)
        pool = {}

        def add(root, quality, bass=None, prior=(0, 0, 0)):
            bass = root if bass is None else bass % 12
            k = (root % 12, quality, bass)
            if k in pool:
                pool[k]['prior'] = [max(a, b) for a, b in zip(pool[k]['prior'], prior)]
                return
            pool[k] = {
                'root': root % 12, 'quality': quality, 'bass': bass,
                'tones': self._tones(root, quality),
                'name': self._spell(root % 12, quality, bass, use_flats),
                'prior': list(prior),
            }

        # 1. Diatonika tonacji docelowej, z worshipowymi kolorami
        for pc, q in target_dia:
            deg = (pc - key_root) % 12
            pivot = (pc, q) in source_dia
            base = 14 if pivot else 0          # akord wspólny: bonus w takcie 1
            if q == 'maj':
                add(pc, 'maj', prior=(base + 6, 8, 4))
                add(pc, 'add9', prior=(base + 4, 8, 2))
                if deg in (0, 5):              # I oraz IV: łagodne kolory
                    add(pc, 'sus2', prior=(base, 4, 0))
                if deg == 7:                   # V: zawieszenia dojściowe
                    add(pc, 'sus4', prior=(0, 6, 10))
                    add(pc, '7sus4', prior=(0, 4, 12))
                # przewroty tercjowe dla linii basu (I/3, IV/3, V/3)
                add(pc, 'maj', bass=pc + 4, prior=(base, 10, 8))
            elif q == 'min':
                add(pc, 'min', prior=(base + 4, 6, 2))
                add(pc, 'min7', prior=(base + 6, 8, 4))
            elif q == 'dim':
                add(pc, 'm7b5', prior=(0, 2, 0))

        # 2. Pożyczone, worshipowo bezpieczne (tylko cel durowy)
        if not is_minor:
            add((key_root + 10) % 12, 'maj', prior=(2, 8, 6))    # bVII
            add((key_root + 5) % 12, 'min', prior=(0, 4, 2))     # iv
        # 3. Akordy WSPÓLNE spoza diatoniki celu (najlepszy pivot: takt 1)
        for pc, q in source_dia - target_dia:
            if q == 'dim':
                continue
            add(pc, q, prior=(10, 0, 0))

        # 4. Dojście do KONKRETNEGO akordu lądowania (takt 3 pomostu)
        land_dom = (land_root + 7) % 12
        add(land_dom, '7sus4', prior=(0, 0, 22))                 # V7sus4/x
        add(land_dom, 'sus4', prior=(0, 0, 16))
        add(land_dom, 'dom7' if land_quality in ('min', 'min7') else 'maj',
            prior=(0, 0, 14))                                    # V/x (V7 gdy cel moll)
        add((land_root + 5) % 12, 'maj', prior=(0, 0, 12))       # IV/x (plagalne)
        add((land_root + 10) % 12, 'maj', prior=(0, 0, 10))      # bVII/x
        add(land_dom, 'maj', bass=land_dom + 4, prior=(0, 0, 14))  # V/3 - bas półtonem w cel

        return list(pool.values())

    # --- SCORING PARY ---

    def _pair_score(self, prev, curr):
        """Jakość przejścia prev->curr: wspólne dźwięki, przesunięcia, bas."""
        score = 0
        common = len(prev['tones'] & curr['tones'])
        score += common * 12
        # suma minimalnych przesunięć dla dźwięków nowych
        for t in curr['tones'] - prev['tones']:
            score -= min(min(abs(t - p), 12 - abs(t - p)) for p in prev['tones']) * 3
        # linia basu
        bd = abs(curr['bass'] - prev['bass'])
        bd = min(bd, 12 - bd)
        if bd in (1, 2):
            score += 30                        # bas krokiem - złoto
        elif bd in (5, 7):
            score += 16                        # kwarta/kwinta
        elif bd == 0:
            score += 4 if curr['root'] != prev['root'] else -30
        elif bd == 6:
            score -= 22                        # tryton w basie
        # ruch prym kwartowo/kwintowo (silne funkcyjnie)
        rd = (curr['root'] - prev['root']) % 12
        if rd in (5, 7):
            score += 8
        # dokładnie ten sam akord obok siebie - nudno
        if prev['root'] == curr['root'] and prev['quality'] == curr['quality']:
            score -= 45
        # dwa zawieszenia z rzędu meczą
        if 'sus' in prev['quality'] and 'sus' in curr['quality']:
            score -= 14
        return score

    def _as_node(self, parsed):
        root, quality, bass = parsed
        return {'root': root, 'quality': quality, 'bass': bass,
                'tones': self._tones(root, quality)}

    # --- GŁÓWNE API (kontrakt jak V1/V2) ---

    def generate_full_progression(self, start_chord, start_key, end_chord, end_key):
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
        # nie zaczynaj pomostu od akordu lądowania (pre-echo psuje przyjazd)
        # ani nie kończ nim; porównanie po rodzinie (Gm7 ~ Gm)
        land_minor = land_p[1] in ('min', 'min7', 'dim', 'm7b5')
        for c in cands:
            if c['root'] == land_p[0] and \
               (c['quality'] in ('min', 'min7', 'dim', 'm7b5')) == land_minor:
                c['prior'][2] -= 60
                c['prior'][0] -= 25
                c['prior'][1] -= 10

        # DP DRUGIEGO RZĘDU po 3 taktach pomostu: stan = (akord taktu i-1,
        # akord taktu i), z karą za powrót do akordu sprzed dwóch taktów
        # (schemat X-Y-X brzmi jak zacięta płyta).
        n = len(cands)
        NEG = float('-inf')
        start_minor = start_p[1] in ('min', 'min7', 'dim', 'm7b5')
        # prekomputacja macierzy par (DP robi n^3 odczytów, ale tylko n^2
        # unikalnych par - bez tego kliknięcie kafelka czekałoby ~100 ms)
        P = [[self._pair_score(cands[j], cands[k]) for k in range(n)]
             for j in range(n)]
        first = [self._pair_score(start_node, c) + c['prior'][0] for c in cands]
        closing = [self._pair_score(c, land_node) + c['prior'][2] for c in cands]
        # takt 2: stan (j = takt1, k = takt2); echo akordu startowego w
        # takcie 2 to schemat START-Y-START - ta sama zacięta płyta
        best2 = [[NEG] * n for _ in range(n)]
        for j in range(n):
            fj = first[j]
            for k in range(n):
                s = fj + P[j][k] + cands[k]['prior'][1]
                if cands[k]['root'] == start_p[0] and \
                   (cands[k]['quality'] in ('min', 'min7', 'dim', 'm7b5')) == start_minor:
                    s -= 35
                best2[j][k] = s
        # takt 3 + domknięcie na akord lądowania
        best_total, best_path = NEG, (0, 0, 0)
        for j in range(n):
            b2j = best2[j]
            for k in range(n):
                base = b2j[k]
                Pk = P[k]
                for l in range(n):
                    s = base + Pk[l] + closing[l]
                    if l == j:
                        s -= 40                # X-Y-X: powrót po dwóch taktach
                    if s > best_total:
                        best_total, best_path = s, (j, k, l)
        bridge = [cands[i]['name'] for i in best_path]

        return [f"[{start_clean or self._spell(src_root, 'maj', src_root, use_flats)}]",
                *[f"[{c}]" for c in bridge],
                f"[{end_clean or self._spell(tgt_root, 'maj', tgt_root, use_flats)}]"]
