import re

class WorshipHybridEngineV1:
    """
    WorshipHybridEngine V1
    -----------------------
   
    """
    def __init__(self):
        # --- 1. TEORIA I MAPY ---
        self.INT_TO_NOTE_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        self.INT_TO_NOTE_FLAT  = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
        
        self.NOTE_TO_INT = {
            'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
            'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8,
            'A': 9, 'A#': 10, 'Bb': 10, 'B': 11, 'Cb': 11,
            'Fb': 4, 'E#': 5, 'B#': 0 
        }

        self.FLAT_KEYS_MAJOR = ['F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb', 'Cb', 'Fb']
        self.FLAT_KEYS_MINOR = ['Dm', 'Gm', 'Cm', 'Fm', 'Bbm', 'Ebm', 'Abm']

        self.INTERVALS = {
            'I': 0, 'i': 0, '1': 0,
            'bII': 1, 'ii': 2, 'II': 2, '2': 2,
            'bIII': 3, 'iii': 4, 'III': 4, '3': 4, 'b3': 3,
            'IV': 5, 'iv': 5, '4': 5,
            'bV': 6, 'V': 7, 'v': 7, '5': 7,
            'bVI': 8, 'vi': 9, 'VI': 9, '6': 9,
            'bVII': 10, 'vii': 11, 'VII': 11, '7': 11, 'b7': 10
        }

        self.MOD_TYPES = {
            'step':   [1, 2, 10, 11],
            'third':  [3, 4, 8, 9],
            'fifth':  [5, 7],
            'tritone':[6],
            'far':    [0]
        }

        # --- STRATEGIE (Zaktualizowane o Slash Chords |3) ---
        self.PIVOT_TEMPLATES_MAJOR = {
            'step': [
                ['bVII', 'IV|3', 'Vsus4'],   # Np. Bb -> F/A -> Gsus4 -> C
                ['IV', 'V|3', 'vi'],         # Step up bass: F -> G/B -> Am
                ['IV', 'V', 'V7'],          
                ['ii', 'V|3', 'I']           # Dm -> G/B -> C (Nice bass resolution)
            ],
            'third': [
                ['vi', 'IV', 'V'],
                ['iii', 'I|3', 'IV'],        # Mediant + Bass drop
                ['I', 'bVI', 'bVII|3']       # Epic: C -> Ab -> Bb/D -> ...
            ],
            'fifth': [
                ['ii', 'Isus4', 'V'],      
                ['IV', 'V/V', 'V'],        
                ['bVII', 'IV', 'Isus4']
            ],
            'tritone': [
                ['bII', 'V', 'I'],         
                ['IV', 'bII', 'Isus4']
            ],
            'far': [
                ['IV', 'V', 'Isus4'],
                ['vi', 'IV', 'V|3'],         # Slash chord finish
                ['bVII', 'IV', 'V']
            ]
        }

        self.PIVOT_TEMPLATES_MINOR = {
            'step': [
                ['bVI', 'bVII', 'V7'],    
                ['iv', 'V7', 'i'],        
                ['bVI', 'bVII|3', 'i']       # F -> G/B -> Am (Bass ascent)
            ],
            'third': [
                ['bVI', 'bVII', 'i'],     
                ['i', 'V7', 'i'],         
                ['bIII', 'iv', 'V7']      
            ],
            'fifth': [
                ['i', 'bIII', 'iv'],      
                ['bIII', 'bVI', 'iv'],
                ['bVI', 'bVII', 'V7#9']   
            ],
            'tritone': [
                ['bII', 'V7', 'i']        
            ],
            'far': [
                ['bVI', 'bVII', 'i'],     
                ['iv', 'bVII', 'V7']      
            ]
        }

        self.EXTENSIONS_CONFIG = {
            'major_stable': [('', 0), ('add9', 20), ('maj7', 5), ('sus2', 10), ('6', 5)],
            'major_tension': [('', 0), ('sus4', 20), ('7', 15)],
            'minor': [('m', 0), ('m7', 20), ('m9', 10), ('m11', 5)]
        }

    # --- 2. NARZĘDZIA ---

    def _normalize_note(self, chord_str):
        if not chord_str: return 0
        match = re.match(r'^([A-G][#b]?)', chord_str, re.IGNORECASE)
        if match:
            root = match.group(1).capitalize()
            return self.NOTE_TO_INT.get(root, 0)
        return 0

    def _is_minor(self, text):
        if 'maj' in text: return False
        return bool(re.search(r'm($|\d|[^a-z])', text)) or bool(re.search(r'^[a-z]', text))

    def _get_note_name(self, note_val, context_key):
        """
        Zwraca nazwę nuty z uwzględnieniem Enharmonic Fix (Fb->E).
        """
        clean_key = context_key.split('/')[0]
        use_flats = False
        
        # Determine strict notation first
        if clean_key in self.FLAT_KEYS_MAJOR or clean_key in self.FLAT_KEYS_MINOR: use_flats = True
        elif 'b' in clean_key: use_flats = True
        elif clean_key == 'F': use_flats = True
        
        raw_name = self.INT_TO_NOTE_FLAT[note_val % 12] if use_flats else self.INT_TO_NOTE_SHARP[note_val % 12]
        
        # --- FIX ENHARMONIA ---
        # Zamieniamy "teoretycznie poprawne" ale "praktycznie niewygodne" nazwy
        enharmonic_replacements = {
            'Fb': 'E',
            'Cb': 'B',
            'E#': 'F',
            'B#': 'C'
        }
        return enharmonic_replacements.get(raw_name, raw_name)

    def _get_chord_root(self, func_str, key_root_val):
        clean_func = func_str.split('|')[0]
        parts = clean_func.split('/')
        total_interval = 0
        for part in parts:
            part_clean = part.replace('sus4','').replace('add9','').replace('maj7','').replace('m7','').replace('7','').replace('#9','')
            if part_clean in self.INTERVALS:
                total_interval += self.INTERVALS[part_clean]
        return (key_root_val + total_interval) % 12

    def _find_function_for_chord(self, chord_clean, key_clean):
        c_root = self._normalize_note(chord_clean)
        k_root = self._normalize_note(key_clean)
        interval = (c_root - k_root) % 12
        for func, val in self.INTERVALS.items():
            if val == interval:
                if func in ['I', 'ii', 'iii', 'IV', 'V', 'vi', 'bVII', 'i', 'iv', 'v']:
                    return func
        return 'I'

    def _detect_modulation_type(self, diff):
        for name, values in self.MOD_TYPES.items():
            if diff in values:
                return name
        return 'far'

    def _create_chord_candidates(self, root_val, func, is_minor_context, target_key_str):
        root_name = self._get_note_name(root_val, target_key_str)
        candidates = []
        func_base_full = func.split('|')[0]
        func_primary = func_base_full.split('/')[0]
        
        category = 'major_stable'
        if self._is_minor(func_primary) or func_primary in ['ii', 'iii', 'vi']:
            category = 'minor'
            if is_minor_context and func_primary == 'v': category = 'major_tension'
        
        if func_primary in ['V', 'bVII', 'bII']: category = 'major_tension'
        if func_primary in ['I', 'IV', 'bVI', 'bIII']: category = 'major_stable'
            
        extensions = self.EXTENSIONS_CONFIG.get(category, [('',0)])
        for ext, bonus in extensions:
            name = f"{root_name}{ext}"
            
            local_bonus = bonus
            if is_minor_context and category == 'major_tension':
                if ext == '7': local_bonus += 30
                if ext == 'sus4': local_bonus -= 10 
            
            candidates.append({'name': name, 'score_bonus': local_bonus})

        # Obsługa slash chords (bass lines)
        if '|3' in func:
            is_minor_chord = (category == 'minor')
            # Dla molla tercja mała (3), dla dura tercja wielka (4)
            interval = 3 if is_minor_chord else 4
            bass_val = (root_val + interval) % 12
            bass_name = self._get_note_name(bass_val, target_key_str)
            
            slash_candidates = []
            for cand in candidates:
                 base_part = cand['name']
                 # Bardzo duży bonus za użycie sugerowanego slash chorda
                 slash_candidates.append({'name': f"{base_part}/{bass_name}", 'score_bonus': cand['score_bonus'] + 40})
            candidates.extend(slash_candidates)

        return candidates

    def _get_bridge_strategies(self, diff, end_func, is_minor_target):
        mod_type = self._detect_modulation_type(diff)
        if is_minor_target:
            strategies = self.PIVOT_TEMPLATES_MINOR.get(mod_type, self.PIVOT_TEMPLATES_MINOR['far'])
        else:
            strategies = self.PIVOT_TEMPLATES_MAJOR.get(mod_type, self.PIVOT_TEMPLATES_MAJOR['far'])
        return strategies

    # --- 4. SCORING (Zmieniony) ---

    def _calculate_score(self, prev_chord, curr_cand, target_root_val):
        score = 0
        p_root = self._normalize_note(prev_chord)
        c_root = self._normalize_note(curr_cand['name'])
        
        # 1. Distance logic (Movement fluidity)
        interval = abs(c_root - p_root)
        dist = min(interval, 12 - interval)

        if dist == 0: score -= 10
        elif dist in [1, 2]: score += 30
        elif dist in [3, 4]: score += 10
        elif dist in [5, 7]: score += 20
        else: score -= 20

        # 2. Bonus from generation
        score += curr_cand.get('score_bonus', 0)
        
        # 3. Penalize repetition
        if prev_chord == curr_cand['name']: score -= 40 

        # 4. CLASH AVOIDANCE (New logic)
        # Jeśli akord to 'sus4' i jest o 1 półton od TARGET ROOT -> Kara.
        # Np. Esus4 (root E) -> Eb (root Eb). Dist = 1.
        dist_to_target = abs(c_root - target_root_val)
        min_dist_target = min(dist_to_target, 12 - dist_to_target)
        
        if 'sus4' in curr_cand['name'] and min_dist_target == 1:
            score -= 50 # Unikamy "gryzących się" dominant zawieszonych chromatycznie blisko celu

        return score

    # --- 5. GŁÓWNA LOGIKA ---

    def generate_full_progression(self, start_chord, start_key, end_chord, end_key):
        start_chord_clean = start_chord.replace('[','').replace(']','')
        start_key_clean = start_key.replace('[','').replace(']','')
        end_chord_clean = end_chord.replace('[','').replace(']','')
        end_key_clean = end_key.replace('[','').replace(']','')
        
        end_func = self._find_function_for_chord(end_chord_clean, end_key_clean)
        s_root = self._normalize_note(start_key_clean)
        e_root = self._normalize_note(end_key_clean)
        is_minor_target = bool(re.search(r'm($|\d|[^a-z])', end_key_clean)) and 'maj' not in end_key_clean
        
        diff = (e_root - s_root) % 12
        strategies = self._get_bridge_strategies(diff, end_func, is_minor_target)
        
        best_bridges = []
        best_score = float('-inf')
        
        for strat in strategies:
            beam = [{'path': [], 'last_chord': start_chord_clean, 'score': 0}]
            
            for func in strat:
                new_beam = []
                func_for_root = re.sub(r'(sus4|add9|maj7|m7|7|#9)', '', func)
                
                t_root = self._get_chord_root(func_for_root, e_root)
                candidates = self._create_chord_candidates(t_root, func, is_minor_target, end_key_clean)
                
                # Hints handling
                if 'sus4' in func:
                    for c in candidates:
                        if 'sus4' in c['name']: c['score_bonus'] += 50
                elif 'add9' in func:
                    for c in candidates:
                        if 'add9' in c['name']: c['score_bonus'] += 50
                elif '7' in func and 'maj7' not in func:
                    for c in candidates:
                        if '7' in c['name'] and 'maj' not in c['name']: c['score_bonus'] += 50
                
                for node in beam:
                    for cand in candidates:
                        # Pass e_root to calculate score for Clash Check
                        step_score = self._calculate_score(node['last_chord'], cand, e_root)
                        
                        new_node = {
                            'path': node['path'] + [cand['name']],
                            'last_chord': cand['name'],
                            'score': node['score'] + step_score
                        }
                        new_beam.append(new_node)
            
                new_beam.sort(key=lambda x: x['score'], reverse=True)
                beam = new_beam[:3]
            
            if beam:
                for node in beam:
                    # Final connection scoring
                    final_cand = {'name': end_chord_clean, 'score_bonus': 0}
                    final_connection_score = self._calculate_score(node['last_chord'], final_cand, e_root)
                    
                    last = node['last_chord']
                    if '7' in last and 'maj' not in last: final_connection_score += 40
                    elif 'sus4' in last: final_connection_score += 35
                        
                    node['final_score'] = node['score'] + final_connection_score
                
                beam.sort(key=lambda x: x['final_score'], reverse=True)
                winner = beam[0]
                
                if winner['final_score'] > best_score:
                    best_score = winner['final_score']
                    best_bridges = winner['path']
        
        bridges_formatted = [f"[{c}]" for c in best_bridges]
        if not bridges_formatted:
             bridges_formatted = [f"[{start_key_clean}]", "[N/A]", f"[{end_key_clean}]"]

        return [
            f"[{start_chord_clean}]",
            *bridges_formatted
        ]

    def generate_transition(self, start_chord, start_key, end_key):
        end_chord = end_key
        is_min = bool(re.search(r'm($|\d|[^a-z])', end_key)) and 'maj' not in end_key
        if is_min and not (bool(re.search(r'm($|\d|[^a-z])', end_chord))): 
            end_chord += 'm'
        return self.generate_full_progression(start_chord, start_key, end_chord, end_key)