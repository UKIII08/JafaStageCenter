import re
import random
import sys

class WorshipHybridEngineV21:
    """
    WorshipHybridEngine V23 - 'Gold Master & View Fix'
    ----------------------------------------------------
    1. [INHERIT] All V22 logic (Balance, Sus4 Fatigue, Diatonic Boost).
    2. [VIEW FIX] '/3' Notation Translator:
       Auto-converts 'C/3' -> 'C/E' and 'Gm/3' -> 'Gm/Bb' in final output.
    """
    def __init__(self):
        # --- 1. TEORIA ---
        self.INT_TO_NOTE_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        self.INT_TO_NOTE_FLAT  = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
        
        self.NOTE_TO_INT = {
            'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
            'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8,
            'A': 9, 'A#': 10, 'Bb': 10, 'B': 11, 'Cb': 11,
            'Fb': 4, 'E#': 5, 'B#': 0 
        }

        self.FLAT_KEYS_MAJOR = ['F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb', 'Cb']
        self.FLAT_KEYS_MINOR = ['Dm', 'Gm', 'Cm', 'Fm', 'Bbm', 'Ebm', 'Abm']
        
        self.INTERVALS = {
            'I': 0, 'i': 0, '1': 0,
            'bII': 1, 'ii': 2, 'II': 2,
            'bIII': 3, 'iii': 4, 'III': 4,
            'IV': 5, 'iv': 5,
            'bV': 6, 'V': 7, 'v': 7,
            'bVI': 8, 'vi': 9, 'VI': 9,
            'bVII': 10, 'vii': 11, 'VII': 11
        }

        self.MOD_TYPES = {
            'step':   [1, 2, 10, 11],
            'third':  [3, 4, 8, 9],
            'fifth':  [5, 7],
            'tritone':[6],
            'far':    [0]
        }

        # --- STRATEGIE ---
        self.PIVOT_TEMPLATES_MAJOR = {
            'step': [
                ['I', 'V|3', 'vi'],          # Walkdown (Priorytet)
                ['IV', 'V', 'I'], 
                ['IV', 'V/vi', 'vi'],
                ['iii7', 'vi7', 'ii7'],
            ],
            'third': [['I', 'V|3', 'vi'], ['vi', 'IV', 'V'], ['iii7', 'IV', 'V']],
            'fifth': [['ii7', 'V7sus4', 'I'], ['IV', 'V', 'I'], ['vi7', 'ii7', 'V7']],
            'tritone': [['bIImaj7', 'I', 'V'], ['IVm', 'bVII', 'I']],
            'far': [['vi', 'IV', 'V'], ['I', 'V|3', 'vi']]
        }
        
        self.PIVOT_TEMPLATES_MINOR = {
            'step': [['bVI', 'bVII', 'i'], ['iv7', 'V7', 'i'], ['bVI', 'bVII', 'Isus4']],
            'third': [['bVI', 'bVII', 'i'], ['i', 'V7', 'i'], ['i', 'bVII', 'bVI']],
            'fifth': [['ii7b5', 'V7', 'i'], ['bVI', 'bVII', 'V7']],
            'tritone': [['bII', 'V7', 'i']],
            'far': [['bVI', 'bVII', 'i']]
        }

        self.EXTENSIONS_CONFIG = {
            'major_stable': [('', 20), ('add9', 25), ('maj7', 15), ('sus2', 15)], 
            'major_tension': [('', 10), ('sus4', 20)], 
            'dominant': [('7', 20), ('7sus4', 30), ('13', 15)], 
            'minor': [('m7', 30), ('m9', 20), ('m11', 10)], 
            'dim': [('dim7', 10), ('m7b5', 20)] 
        }

    # --- TOOLS ---
    def _normalize_note(self, chord_str):
        if not chord_str: return 0
        match = re.match(r'^([A-G][#b]?)', chord_str, re.IGNORECASE)
        if match:
            root = match.group(1).capitalize()
            return self.NOTE_TO_INT.get(root, 0)
        return 0

    def _get_bass_note(self, chord_str):
        if '/' in chord_str:
            bass = chord_str.split('/')[1]
            # Obsługa sytuacji, gdyby bas był podany jako interwał (zabezpieczenie)
            if bass == '3': 
                 root = self._normalize_note(chord_str.split('/')[0])
                 is_minor = self._is_minor(chord_str.split('/')[0])
                 return (root + (3 if is_minor else 4)) % 12
            return self._normalize_note(bass)
        return self._normalize_note(chord_str)

    def _is_minor(self, text):
        if 'maj' in text: return False
        return bool(re.search(r'm($|\d|[^a-z])', text)) or bool(re.search(r'^[a-z]', text))

    def _get_note_name(self, note_val, context_key):
        clean_key = context_key.split('/')[0]
        use_flats = False
        if clean_key in self.FLAT_KEYS_MAJOR or clean_key in self.FLAT_KEYS_MINOR: use_flats = True
        raw_name = self.INT_TO_NOTE_FLAT[note_val % 12] if use_flats else self.INT_TO_NOTE_SHARP[note_val % 12]
        replacements = {'Fb': 'E', 'Cb': 'B', 'E#': 'F', 'B#': 'C'}
        return replacements.get(raw_name, raw_name)

    def _get_chord_root(self, func_str, key_root_val):
        clean_func = func_str.split('|')[0].split('/')[0]
        clean_func = re.sub(r'(sus4|add9|maj7|m7|7|9|13|11|#9|b9|V/|ii/)', '', clean_func)
        offset = 0
        if 'V/' in func_str: offset = 7 
        total_interval = self.INTERVALS.get(clean_func, 0) + offset
        return (key_root_val + total_interval) % 12

    # --- [NEW] VIEW HELPER: Tłumacz notacji /3 ---
    def _render_chord_name(self, chord_str, context_key):
        """
        Sprawdza, czy akord ma zapis '/3'. Jeśli tak, zamienia go na konkretną nutę
        (np. C/3 -> C/E, Gm/3 -> Gm/Bb). W przeciwnym razie zwraca akord bez zmian.
        """
        if '/3' not in chord_str:
            return chord_str
            
        root_str = chord_str.split('/')[0]
        root_val = self._normalize_note(root_str)
        is_minor = self._is_minor(root_str)
        
        # Tercja mała (3) dla molla, wielka (4) dla dura
        interval = 3 if is_minor else 4
        bass_val = (root_val + interval) % 12
        
        # Pobranie nazwy nuty basowej zgodnie z tonacją
        bass_name = self._get_note_name(bass_val, context_key)
        
        return f"{root_str}/{bass_name}"

    # --- CORE LOGIC ---
    def _create_chord_candidates(self, root_val, func, is_minor_context, target_key_str):
        root_name = self._get_note_name(root_val, target_key_str)
        candidates = []
        base_func = func.split('|')[0].split('/')[0]
        
        category = 'major_stable'
        if is_minor_context:
            if base_func in ['i', 'iv', 'v']: category = 'minor'
            elif base_func in ['ii', 'ii7b5']: category = 'dim'
            elif base_func in ['bIII', 'bVI', 'bVII']: category = 'major_stable'
            elif base_func in ['V', 'V7']: category = 'dominant'
        else:
            if base_func in ['ii', 'iii', 'vi']: category = 'minor'
            elif base_func in ['V']: category = 'dominant'
            elif base_func in ['vii']: category = 'dim'
            else: category = 'major_stable'
        if 'V/' in func or '7' in func and category != 'minor': category = 'dominant'

        extensions = self.EXTENSIONS_CONFIG.get(category, [('',0)])
        for ext, bonus in extensions:
            candidates.append({
                'name': f"{root_name}{ext}", 
                'score_bonus': bonus, 
                'func_type': category, 
                'root_val': root_val
            })

        if '|3' in func:
            slash_candidates = []
            interval = 3 if category in ['minor', 'dim'] else 4
            bass_val = (root_val + interval) % 12
            
            # Tutaj generujemy wewnętrzną nazwę. Jeśli użyjemy '/3', renderer na końcu to naprawi.
            # Jeśli użyjemy konkretnej nazwy, renderer tego nie dotknie.
            # Dla pewności używamy tutaj konkretnej nazwy (bo scoring może woleć konkrety),
            # ale renderer i tak będzie czuwał.
            bass_name = self._get_note_name(bass_val, target_key_str)
            
            for cand in candidates:
                slash_candidates.append({
                    'name': f"{cand['name']}/{bass_name}",
                    'score_bonus': cand['score_bonus'] + 50,
                    'func_type': category,
                    'root_val': root_val,
                    'is_slash': True,
                    'bass_val': bass_val
                })
            return slash_candidates 
        return candidates

    def _calculate_score(self, prev_chord_name, curr_cand, target_root_val):
        score = 0
        p_root = self._normalize_note(prev_chord_name)
        p_bass = self._get_bass_note(prev_chord_name)
        p_is_minor = self._is_minor(prev_chord_name)
        
        c_name = curr_cand['name']
        c_root = curr_cand['root_val']
        c_bass = curr_cand.get('bass_val', c_root)
        c_type = curr_cand['func_type']
        c_is_minor = (c_type == 'minor')

        # 1. Hand Comfort
        root_dist = abs(c_root - p_root)
        min_root_dist = min(root_dist, 12 - root_dist)
        if min_root_dist == 0 and 'sus' not in c_name and 'sus' not in prev_chord_name: score -= 50 
        elif min_root_dist <= 5: score += 20
        
        # 2. Bass Line Beauty
        bass_dist = abs(c_bass - p_bass)
        min_bass_dist = min(bass_dist, 12 - bass_dist)
        if min_bass_dist in [1, 2]: score += 65 
        elif min_bass_dist == 0 and min_root_dist > 0: score += 40 
        elif min_bass_dist == 5: score += 30

        # 3. Resolution & Sus Logic
        is_prev_dom = ('7' in prev_chord_name and 'maj' not in prev_chord_name)
        if is_prev_dom:
            move = (c_root - p_root) % 12
            if move == 5: score += 50 
            elif move == 9: score += 40 
            elif move == 2: score -= 20 

        # --- NEW IN V22: Sus4 Fatigue & Diatonic Balance ---
        if 'sus' in prev_chord_name and 'sus' in c_name:
            score -= 15 
        
        if min_root_dist in [1, 2]:
            score += 10

        score += curr_cand.get('score_bonus', 0)
        return score

    def _detect_modulation_type(self, diff):
        for name, values in self.MOD_TYPES.items():
            if diff in values: return name
        return 'far'

    def generate_full_progression(self, start_chord, start_key, end_chord, end_key):
        start_chord_clean = start_chord.replace('[','').replace(']','')
        start_key_clean = start_key.replace('[','').replace(']','')
        end_chord_clean = end_chord.replace('[','').replace(']','')
        end_key_clean = end_key.replace('[','').replace(']','')
        
        s_root = self._normalize_note(start_key_clean)
        e_root = self._normalize_note(end_key_clean)
        is_minor_target = bool(re.search(r'm', end_key_clean)) and 'maj' not in end_key_clean
        
        diff = (e_root - s_root) % 12
        mod_type = self._detect_modulation_type(diff)
        
        strategies = self.PIVOT_TEMPLATES_MINOR.get(mod_type, self.PIVOT_TEMPLATES_MINOR['far']) if is_minor_target \
                else self.PIVOT_TEMPLATES_MAJOR.get(mod_type, self.PIVOT_TEMPLATES_MAJOR['far'])
        
        best_bridges = []
        best_score = float('-inf')
        BEAM_WIDTH = 5 

        for strat in strategies:
            beam = [{'path': [], 'last_chord': start_chord_clean, 'score': 0}]
            for func in strat:
                new_beam = []
                for node in beam:
                    t_root = self._get_chord_root(func, e_root)
                    candidates = self._create_chord_candidates(t_root, func, is_minor_target, end_key_clean)
                    for cand in candidates:
                        step_score = self._calculate_score(node['last_chord'], cand, e_root)
                        new_node = {
                            'path': node['path'] + [cand['name']],
                            'last_chord': cand['name'],
                            'score': node['score'] + step_score
                        }
                        new_beam.append(new_node)
                new_beam.sort(key=lambda x: x['score'], reverse=True)
                beam = new_beam[:BEAM_WIDTH]
            
            if beam:
                for node in beam:
                    final_cand = {'name': end_chord_clean, 'root_val': self._normalize_note(end_chord_clean), 'func_type': 'major_stable'}
                    final_score_add = self._calculate_score(node['last_chord'], final_cand, e_root)
                    node['final_score'] = node['score'] + final_score_add
                beam.sort(key=lambda x: x['final_score'], reverse=True)
                if beam[0]['final_score'] > best_score:
                    best_score = beam[0]['final_score']
                    best_bridges = beam[0]['path']
        
        if best_bridges and best_bridges[-1] == end_chord_clean:
            best_bridges.pop()

        # --- [NEW] FINAL RENDER PASS: Tłumaczenie /3 na nuty ---
        final_path = []
        
        # Render start (tłumaczymy, bo input może być np C/3)
        final_path.append(f"[{self._render_chord_name(start_chord_clean, start_key_clean)}]")
        
        # Render bridge
        if best_bridges:
            for c in best_bridges:
                 final_path.append(f"[{self._render_chord_name(c, end_key_clean)}]")
        else:
             if start_chord_clean != end_chord_clean:
                 final_path.append("...")

        # Render end
        final_path.append(f"[{self._render_chord_name(end_chord_clean, end_key_clean)}]")

        return final_path



try:
    from test1 import WorshipHybridEngineV21 as Engine
except ImportError:
    print("⚠️ Nie znaleziono pliku AdvancedEngine.py. Upewnij się, że klasa silnika jest dostępna.")
    sys.exit(1)

def run_tests():
    engine = Engine()
    
    print("="*60)
    print("🚀 ROZPOCZYNAM TESTY WORSHIP ENGINE V23")
    print("="*60)

    # --- ZESTAW 1: TESTY SLASH CHORDS (/3) ---
    # Sprawdzamy, czy silnik zamienia '/3' na konkretne nuty (np. /E, /B)
    slash_tests = [
        ("C", "C/3"), ("G", "G/3"), ("D", "D/3"), ("A", "A/3"), ("E", "E/3"),
        ("B", "B/3"), ("F", "F/3"), ("Bb", "Bb/3"), ("Eb", "Eb/3"), ("Ab", "Ab/3"),
        ("Am", "Am/3"), ("Em", "Em/3"), ("Bm", "Bm/3"), ("F#m", "F#m/3"), ("Dm", "Dm/3"),
        ("Gm", "Gm/3"), ("C/3", "F"), ("G/3", "C"), ("D/3", "G"), ("A/3", "D")
    ]

    print(f"\n📂 [TEST 1] SLASH LOGIC CHECK ({len(slash_tests)} przypadków)")
    print("Oczekiwany rezultat: Brak '[X/3]' w wynikach, zamiast tego np. '[X/E]'")
    print("-" * 60)

    for start, end in slash_tests:
        # Zakładamy, że tonacja startowa to start, a końcowa to end (dla uproszczenia testu)
        s_key = start.split('/')[0]
        e_key = end.split('/')[0]
        
        result = engine.generate_full_progression(
            f"[{start}]", f"[{s_key}]", 
            f"[{end}]", f"[{e_key}]"
        )
        path_str = " -> ".join(result)
        
        # Weryfikacja czy slash został przetłumaczony
        status = "✅ OK" if "/3" not in path_str else "❌ BŁĄD (Widoczne /3)"
        print(f"{start.ljust(5)} -> {end.ljust(5)} : {path_str} \t{status}")

    # --- ZESTAW 2: TESTY NORMALNE (STABILNOŚĆ) ---
    # 50 losowych, klasycznych przejść, żeby sprawdzić balans i harmonię
    normal_tests = [
        # C Major & Friends
        ("C", "G"), ("G", "Am"), ("Am", "F"), ("F", "C"), ("C", "Dm"),
        ("Dm", "G"), ("G", "C"), ("C", "Em"), ("Em", "Am"), ("F", "G"),
        # G Major & Friends
        ("G", "D"), ("D", "Em"), ("Em", "C"), ("C", "D"), ("D", "G"),
        ("G", "Em"), ("Em", "Bm"), ("Bm", "C"), ("Am", "D"), ("D", "C"),
        # D Major & Friends
        ("D", "A"), ("A", "Bm"), ("Bm", "G"), ("G", "A"), ("A", "D"),
        ("D", "F#m"), ("F#m", "G"), ("Bm", "A"), ("A", "Em"), ("Em", "A"),
        # E Major & A Major
        ("E", "A"), ("A", "E"), ("E", "B"), ("B", "C#m"), ("C#m", "A"),
        ("A", "F#m"), ("F#m", "D"), ("B", "E"), ("E", "G#m"), ("F#m", "B"),
        # Flat Keys (F, Bb, Eb)
        ("F", "Bb"), ("Bb", "F"), ("F", "Dm"), ("Dm", "Bb"), ("Bb", "Gm"),
        ("Gm", "C"), ("C", "F"), ("Bb", "Eb"), ("Eb", "Cm"), ("Cm", "Ab")
    ]

    print(f"\n📂 [TEST 2] STABILITY & HARMONY CHECK ({len(normal_tests)} przypadków)")
    print("Oczekiwany rezultat: Płynne przejścia, brak monotonii sus4, poprawne basy.")
    print("-" * 60)

    for i, (start, end) in enumerate(normal_tests):
        result = engine.generate_full_progression(
            f"[{start}]", f"[{start}]", 
            f"[{end}]", f"[{end}]"
        )
        path_str = " -> ".join(result)
        print(f"{str(i+1).zfill(2)}. {start} -> {end}: {path_str}")

if __name__ == "__main__":
    run_tests()