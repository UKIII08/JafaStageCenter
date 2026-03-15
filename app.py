import sys
import os
import socket
import qrcode
import webbrowser
import json
import math
import threading  # Threading support
import webview    # Native window support
from threading import Timer
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, send_file, Response
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from sqlalchemy import text 
import re
import shutil
import itertools
from collections import Counter
import random
import logging
import tempfile
from pathlib import Path

# --- ENGINE IMPORTS ---
from Mingus_silnik import WorshipHybridEngineV1
try:
    from AdvancedEngine import WorshipHybridEngineV2
except ImportError:
    print("Warning: AdvancedEngine.py not found.")
    WorshipHybridEngineV2 = None

# --- 1. CONFIGURATION ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

app = Flask(__name__, 
            template_folder=resource_path('templates'), 
            static_folder=resource_path('static'))

# Disable default Flask logging to console
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app.config['SECRET_KEY'] = 'secret_key_change_in_prod'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

if getattr(sys, 'frozen', False):
    db_path = os.path.join(os.path.dirname(sys.executable), 'worship.db')
else:
    db_path = os.path.join(os.path.abspath("."), 'worship.db')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

socketio = SocketIO(app, async_mode='threading', cors_allowed_origins='*', logger=False, engineio_logger=False)

# --- 2. SHARED MEMORY ---
SERVER_STATE = {
    'setlist': [],
    'current_index': -1
}

@socketio.on('connect')
def handle_connect():
    emit('sync_state_to_client', SERVER_STATE)

@socketio.on('client_update_state')
def handle_client_update(data):
    global SERVER_STATE
    SERVER_STATE['setlist'] = data.get('setlist', [])
    SERVER_STATE['current_index'] = data.get('current_index', -1)
    emit('sync_state_to_client', SERVER_STATE, broadcast=True)

# --- 3. DATABASE MODELS ---
class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    key = db.Column(db.String(10), nullable=True, default='')
    bpm = db.Column(db.Integer, nullable=True, default=0)

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    font_family = db.Column(db.String(50), default='Sen')
    bg_color = db.Column(db.String(20), default='#000000')
    text_color = db.Column(db.String(20), default='#ffffff')
    chord_color = db.Column(db.String(20), default='#00e5ff')
    transition_engine = db.Column(db.String(10), default='v20')
    # NEW FIELD: Language
    language = db.Column(db.String(5), default='pl')

def init_settings():
    try:
        if not Settings.query.first():
            default = Settings()
            db.session.add(default)
            db.session.commit()
    except: pass

def check_db_schema():
    with app.app_context():
        try:
            inspector = db.inspect(db.engine)
            
            # Check Song table
            song_columns = [col['name'] for col in inspector.get_columns('song')]
            if 'key' not in song_columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE song ADD COLUMN key VARCHAR(10)'))
                    conn.commit()
            if 'bpm' not in song_columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE song ADD COLUMN bpm INTEGER DEFAULT 0'))
                    conn.commit()

            # Check Settings table
            settings_columns = [col['name'] for col in inspector.get_columns('settings')]
            if 'transition_engine' not in settings_columns:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE settings ADD COLUMN transition_engine VARCHAR(10) DEFAULT 'v20'"))
                    conn.commit()
            
            # NEW: Check for language column
            if 'language' not in settings_columns:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE settings ADD COLUMN language VARCHAR(5) DEFAULT 'pl'"))
                    conn.commit()

        except Exception as e:
            # Silent fail for exe log
            pass

# --- MAPPINGS ---
PITCH_CLASS_MAP = {
    'C': 0, 'C#': 1, 'DB': 1, 'D': 2, 'D#': 3, 'EB': 3, 'E': 4, 
    'F': 5, 'F#': 6, 'GB': 6, 'G': 7, 'G#': 8, 'AB': 8, 
    'A': 9, 'A#': 10, 'BB': 10, 'B': 11, 'CB': 11, 'H': 11 
}
TRANSPOSE_LOOKUP = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except: IP = '127.0.0.1'
    finally: s.close()
    return IP
# --- NOWA KLASA DO OBSŁUGI SYSTEMOWEGO ZAPISU ---
class JafaApi:
    def save_backup(self):
        """Generuje tekst bazy i otwiera systemowe okno zapisu"""
        with app.app_context():
            songs = Song.query.all()
            export_lines = []
            for song in songs:
                header = song.title
                if song.key: header += f" ({song.key})"
                if song.bpm and song.bpm > 0: header += f"-({song.bpm})"
                export_lines.append(header)
                export_lines.append(song.content.strip())
                export_lines.append("---")
            
            if export_lines and export_lines[-1] == "---": export_lines.pop()
            final_text = "\n".join(export_lines)

            # Otwórz okno dialogowe
            file_path = webview.windows[0].create_file_dialog(
                webview.SAVE_DIALOG, 
                directory='', 
                save_filename='kopia_bazy.txt',
                file_types=('Text Files (*.txt)', 'All files (*.*)')
            )

            if file_path:
                try:
                    # file_path może być listą lub stringiem zależnie od systemu
                    path = file_path if isinstance(file_path, str) else file_path[0]
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(final_text)
                    return {'status': 'ok', 'message': 'Zapisano pomyślnie!'}
                except Exception as e:
                    return {'status': 'error', 'message': str(e)}
            return {'status': 'cancelled'}

    def save_setlist_html(self, setlist_data):
        """Generuje tymczasowy HTML i otwiera go w przeglądarce"""
        try:
            with app.test_request_context(base_url='http://127.0.0.1:5000'):
                songs_to_print = []
                
                for item in setlist_data:
                    try: t_val = int(item.get('transpose', 0))
                    except: t_val = 0
                    
                    _, _, text_print = process_song(item.get('content', ''), t_val)
                    songs_to_print.append({'title': item.get('title', 'Bez tytułu'), 'html': text_print})
                
                # --- POPRAWKA: TWORZENIE POPRAWNEGO LINKU LOKALNEGO ---
                # Zamiast .replace(), używamy .as_uri(), co dodaje "file:///" i naprawia spacje
                static_path_obj = Path(app.static_folder)
                static_absolute_path = static_path_obj.as_uri()
                # Wynik wygląda teraz tak: file:///C:/Users/Jafa/static
                # ------------------------------------------------------

                html_content = render_template('print_view.html', 
                                               songs=songs_to_print, 
                                               static_root=static_absolute_path)

                fd, path = tempfile.mkstemp(suffix=".html", prefix="setlista_")
                
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                webbrowser.open('file://' + path)
                
                return {'status': 'ok', 'message': 'Otwarto w przeglądarce'}
                
        except Exception as e:
            print(f"BŁĄD API: {str(e)}")
            return {'status': 'error', 'message': str(e)}
# --- 4. KEY DETECTION LOGIC ---
class AdvancedKeyDetector:
    def __init__(self):
        self.note_map = {
            'c': 0, 'c#': 1, 'db': 1, 'd': 2, 'd#': 3, 'eb': 3,
            'e': 4, 'f': 5, 'f#': 6, 'gb': 6, 'g': 7, 'g#': 8, 'ab': 8,
            'a': 9, 'a#': 10, 'bb': 10, 'b': 11, 'h': 11, 'cb': 11
        }
        self.index_to_note = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        self.major_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
        self.minor_profile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

    def _get_chord_notes(self, root, is_major):
        return [root, (root + (4 if is_major else 3)) % 12, (root + 7) % 12]

    def _calculate_correlation(self, list1, list2):
        if not list1: return 0
        mean1, mean2 = sum(list1)/len(list1), sum(list2)/len(list2)
        num = sum((x - mean1) * (y - mean2) for x, y in zip(list1, list2))
        den = math.sqrt(sum((x - mean1)**2 for x in list1)) * math.sqrt(sum((y - mean2)**2 for y in list2))
        return num / den if den != 0 else 0

    def _extract_chords_from_text(self, text):
        return [c.strip() for c in re.findall(r'\[(.*?)\]', text) if c.strip()]

    def detect(self, text):
        chords_raw = self._extract_chords_from_text(text) if not isinstance(text, list) else text
        if not chords_raw: return "N/A"
        
        def parse(c):
             match = re.match(r'^([A-Ga-g][#b]?)(.*)$', c)
             if not match: return None
             root_lower = match.group(1).lower()
             if root_lower not in self.note_map: return None
             return self.note_map[root_lower], not (c[0].islower() or 'm' in match.group(2))

        first, last = parse(chords_raw[0]), parse(chords_raw[-1])
        vec = [0]*12
        for c in chords_raw:
            p = parse(c)
            if p: 
                for n in self._get_chord_notes(*p): vec[n] += 1
        
        best_key, best_score = "N/A", -999.0
        for i in range(12):
            s = self._calculate_correlation(vec, self.major_profile[-i:] + self.major_profile[:-i])
            if last and last[1] and last[0]==i: s+=0.5
            if first and first[1] and first[0]==i: s+=0.6
            if s > best_score: best_score, best_key = s, self.index_to_note[i]
            
            s = self._calculate_correlation(vec, self.minor_profile[-i:] + self.minor_profile[:-i])
            if last and not last[1] and last[0]==i: s+=0.5
            if first and not first[1] and first[0]==i: s+=0.6
            if s > best_score: best_score, best_key = s, f"{self.index_to_note[i]}m"
        return best_key

key_detector = AdvancedKeyDetector()
def detect_key_algorithm(text): return key_detector.detect(text)

# --- TRANSPOSE & PARSING HELPERS ---
def transpose_chord(match, shift):
    full_chord = match.group(1)
    def trans_part(part):
        if not part: return ""
        m = re.match(r'^([A-G][#b]?)(.*)$', part, re.IGNORECASE)
        if not m: return part
        root, suffix = m.group(1).upper(), m.group(2)
        is_lower = part[0].islower()
        if root in PITCH_CLASS_MAP:
            new_root = TRANSPOSE_LOOKUP[(PITCH_CLASS_MAP[root] + shift) % 12]
            return f"{new_root.lower() if is_lower else new_root}{suffix}"
        return part
    
    if '/' in full_chord:
        parts = full_chord.split('/')
        return f"[{trans_part(parts[0])}/{trans_part(parts[1])}]" if len(parts)>=2 else f"[{trans_part(full_chord)}]"
    return f"[{trans_part(full_chord)}]"

def apply_transpose_to_single_chord(chord_str, shift):
    if shift == 0: return chord_str
    return re.sub(r'\[(.*?)\]', lambda m: transpose_chord(m, shift), chord_str)

def get_first_chord_from_chorus(content):
    if not content: return None
    blocks = re.split(r'\n\s*\n', content)
    chorus_pattern = re.compile(r'^\[?(refren|chorus)', re.IGNORECASE)
    for block in blocks:
        lines = block.strip().splitlines()
        if not lines: continue
        if chorus_pattern.match(lines[0].strip()):
            chords = [c.strip() for c in re.findall(r'\[(.*?)\]', block) if c.strip()]
            if chords: return chords[0] 
    return get_first_chord_of_song(content)

def get_first_chord_of_song(content):
    if not content: return None
    chords = [c.strip() for c in re.findall(r'\[(.*?)\]', content) if c.strip()]
    return chords[0] if chords else None

def process_song(text, transpose_amount=0):
    if not text: return "", "", ""
    text = text.strip()
    if transpose_amount != 0:
        text = re.sub(r'\[(.*?)\]', lambda m: transpose_chord(m, transpose_amount), text)
    text_people = re.sub(r'\[.*?\]', '', text).strip().replace('\n', '<br>')
    tokens = re.split(r'(\[.*?\])', text)
    text_smart = ""

    def has_text_anywhere_on_line(idx, all_tokens):
        for k in range(idx - 1, -1, -1):
            t = all_tokens[k]
            if t.startswith('[') and t.endswith(']'): continue
            if '\n' in t: break
            if t.strip(): return True
        for k in range(idx + 1, len(all_tokens)):
            t = all_tokens[k]
            if t.startswith('[') and t.endswith(']'): continue
            if '\n' in t:
                return bool(t.split('\n')[0].strip())
            if t.strip(): return True
        return False

    def get_text_info_until_next_chord(idx, all_tokens):
        text_len = 0
        has_next_chord = False
        for k in range(idx + 1, len(all_tokens)):
            t = all_tokens[k]
            if t.startswith('[') and t.endswith(']'):
                has_next_chord = True
                break 
            if '\n' in t:
                line_end_text = t.split('\n')[0].rstrip()
                text_len += len(line_end_text)
                break
            text_len += len(t)
        return text_len, has_next_chord

    for i, token in enumerate(tokens):
        if token.startswith('[') and token.endswith(']'):
            chord_content = token[1:-1]
            if '/' in chord_content:
                parts = chord_content.split('/')
                root_part = parts[0]
                bass_part = "/".join(parts[1:])
                chord_content = f"{root_part}<span class='bass-slash'>/</span><span class='bass-note'>{bass_part}</span>"
            
            if not has_text_anywhere_on_line(i, tokens):
                text_smart += f'<span class="chord-wrapper" style="width:auto; display:inline-block; margin-right:0.5em;"><span class="chord" style="position:static; font-size:1em;">{chord_content}</span>&nbsp;</span>'
            else:
                clean_chord = re.sub(r"<[^>]+>", "", chord_content)
                ch_width = (len(clean_chord) * 1.2) + 1.2
                
                text_len, has_next_chord = get_text_info_until_next_chord(i, tokens)
                
                needs_width_expansion = False
                missing_width = 0

                # Dodajemy ratunkową szerokość tylko gdy to absolutnie konieczne:
                if text_len == 0:
                    needs_width_expansion = True
                    missing_width = ch_width
                elif has_next_chord and text_len < ch_width:
                    needs_width_expansion = True
                    missing_width = ch_width - text_len

                if needs_width_expansion:
                    text_smart += f'<span class="chord-wrapper" style="display:inline-block; width:{missing_width}ch; height:0px; position:relative;"><span class="chord">{chord_content}</span></span>'
                else:
                    # WRACAMY DO TWOJEGO ORYGINAŁU - zero ingerencji w style dla akordów wewnątrz słów!
                    text_smart += f'<span class="chord-wrapper"><span class="chord">{chord_content}</span></span>'
        else:
            # Zamienia taby i wielokrotne spacje na twarde spacje, żeby HTML ich nie zjadał
            safe_token = token.replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;').replace('  ', '&nbsp;&nbsp;')
            text_smart += safe_token
            
    text_band = text_smart.replace('\n', '<br>')
    blocks = re.split(r'\n\s*\n', text_smart)
    html_blocks = []
    
    for block in blocks:
        if block.strip():
            block_clean = block.strip().replace('\n', '<br>')
            html_blocks.append(f'<div class="print-block">{block_clean}</div>')
            
    text_print = "".join(html_blocks)
    return text_people, text_band, text_print

# --- 6. ROUTING ---
@app.route('/')
@app.route('/control')
def control():
    songs = Song.query.all()
    settings = Settings.query.first()
    bg_path = os.path.join(app.static_folder, 'background.png')
    has_bg = os.path.exists(bg_path)
    return render_template('control.html', songs=songs, server_ip=get_local_ip(), settings=settings, has_bg=has_bg)

@app.route('/projector')
def projector():
    settings = Settings.query.first()
    bg_path = os.path.join(app.static_folder, 'background.png')
    has_bg = os.path.exists(bg_path)
    return render_template('projector.html', settings=settings, has_bg=has_bg)

@app.route('/stage')
def stage(): return render_template('stage.html')

@app.route('/detect_key', methods=['POST'])
def route_detect_key():
    data = request.json
    text = data.get('text', '')
    transpose = int(data.get('transpose', 0))
    if transpose != 0:
        text = re.sub(r'\[(.*?)\]', lambda m: transpose_chord(m, transpose), text)
    detected = detect_key_algorithm(text)
    pad_note = detected.replace('m', '') if detected != "N/A" else "N/A"
    return {'key': detected, 'pad': pad_note}

@app.route('/generate_transition', methods=['POST'])
def route_generate_transition():
    data = request.json
    id_start = data.get('id_start')
    id_end = data.get('id_end')
    trans_start = int(data.get('transpose_start', 0))
    trans_end = int(data.get('transpose_end', 0))

    key_start = "C"
    key_end = "C"
    start_chord_raw = "C"
    end_chord_raw = "C" 

    if id_start:
        song_a = Song.query.get(id_start)
        if song_a:
            key_start = song_a.key if song_a.key else "C"
            first_from_chorus = get_first_chord_from_chorus(song_a.content)
            start_chord_raw = first_from_chorus if first_from_chorus else (get_first_chord_of_song(song_a.content) or key_start)

    if id_end:
        song_b = Song.query.get(id_end)
        if song_b:
            key_end = song_b.key if song_b.key else "C"
            first_chord = get_first_chord_of_song(song_b.content)
            end_chord_raw = first_chord if first_chord else key_end

    if not id_start:
        start_chord_raw = data.get('start_chord', 'C')
        key_start = data.get('key_start', 'C')
    if not id_end:
        end_chord_raw = data.get('end_chord', 'C')
        key_end = data.get('key_end', 'C')

    if not start_chord_raw.startswith('['): start_to_trans = f"[{start_chord_raw}]"
    else: start_to_trans = start_chord_raw
    if not end_chord_raw.startswith('['): end_to_trans = f"[{end_chord_raw}]"
    else: end_to_trans = end_chord_raw

    real_start_chord = apply_transpose_to_single_chord(start_to_trans, trans_start)
    real_end_chord = apply_transpose_to_single_chord(end_to_trans, trans_end)
    real_key_start = apply_transpose_to_single_chord(f"[{key_start}]", trans_start)
    real_key_end = apply_transpose_to_single_chord(f"[{key_end}]", trans_end)

    settings = Settings.query.first()
    engine_choice = settings.transition_engine if settings else 'v2'

    if engine_choice == 'v1': 
        engine = WorshipHybridEngineV1()
    else: 
        if WorshipHybridEngineV2:
            engine = WorshipHybridEngineV2() 
        else:
            engine = WorshipHybridEngineV1()

    transition_chords = engine.generate_full_progression(real_start_chord, real_key_start, real_end_chord, real_key_end)
    return {
        'status': 'ok', 'transition': " ".join(transition_chords), 'chords_list': transition_chords,
        'debug_start': real_start_chord, 'debug_end': real_end_chord, 'engine_used': engine_choice
    }

@app.route('/add_song', methods=['POST'])
def add_song():
    title = request.form.get('title')
    content = request.form.get('content')
    key = request.form.get('key') or ''
    bpm = request.form.get('bpm')
    if not key and content: key = detect_key_algorithm(content)
    if title and content:
        try: bpm_val = int(bpm) if bpm else 0
        except ValueError: bpm_val = 0
        existing = Song.query.filter_by(title=title).first()
        if existing: 
            existing.content = content
            existing.key = key
            existing.bpm = bpm_val
        else: 
            db.session.add(Song(title=title, content=content, key=key, bpm=bpm_val))
        db.session.commit()
    return redirect(url_for('control'))

@app.route('/import_songs', methods=['POST'])
def import_songs():
    files = request.files.getlist('import_files')
    def save_or_update(song_title, song_content, song_key='', song_bpm=0):
        existing = Song.query.filter_by(title=song_title).first()
        if not song_key: song_key = detect_key_algorithm(song_content) 
        if existing: 
            existing.content = song_content
            existing.key = song_key
            existing.bpm = song_bpm
        else: 
            db.session.add(Song(title=song_title, content=song_content, key=song_key, bpm=song_bpm))

    for file in files:
        if file and file.filename.endswith('.txt'):
            raw_data = file.read()
            try: content = raw_data.decode('utf-8')
            except: content = raw_data.decode('cp1250', errors='ignore')
            content=content.replace('\r','')
            if '---' in content:
                chunks = content.split('---')
                for chunk in chunks:
                    chunk = chunk.strip()
                    if not chunk: continue
                    lines = chunk.splitlines()
                    if len(lines) >= 1:
                        raw_title_line = lines[0].strip()
                        match = re.match(r'^(.*?)(?:\s*\(([^)]+)\))?(?:-\((\d+)\))?$', raw_title_line)
                        if match:
                            title = match.group(1).strip()
                            key = match.group(2).strip() if match.group(2) else ''
                            try: bpm = int(match.group(3)) if match.group(3) else 0
                            except: bpm = 0
                        else:
                            title = raw_title_line; key = ''; bpm = 0
                        body = '\n'.join(lines[1:]).strip()
                        if title and body: save_or_update(title, body, key, bpm)
            else:
                raw_filename = os.path.splitext(file.filename)[0]
                match = re.match(r'^(.*?)(?:\s*\(([^)]+)\))?(?:-\((\d+)\))?$', raw_filename)
                if match:
                    title = match.group(1).strip()
                    key = match.group(2).strip() if match.group(2) else ''
                    try: bpm = int(match.group(3)) if match.group(3) else 0
                    except: bpm = 0
                else:
                    title = raw_filename; key = ''; bpm = 0
                body = content.strip()
                if title and body: save_or_update(title, body, key, bpm)
    db.session.commit()
    return redirect(url_for('control'))

@app.route('/edit_song/<int:id>', methods=['POST'])
def edit_song(id):
    song = Song.query.get_or_404(id)
    song.title = request.form.get('title')
    song.content = request.form.get('content')
    song.key = request.form.get('key')
    bpm = request.form.get('bpm')
    try: song.bpm = int(bpm) if bpm else 0
    except ValueError: song.bpm = 0
    db.session.commit()
    return redirect(url_for('control'))

@app.route('/delete_song/<int:id>', methods=['POST'])
def delete_song(id):
    db.session.delete(Song.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('control'))

@app.route('/update_settings', methods=['POST'])
def update_settings():
    settings = Settings.query.first()
    settings.font_family = request.form.get('font_family')
    settings.bg_color = request.form.get('bg_color')
    settings.text_color = request.form.get('text_color')
    settings.chord_color = request.form.get('chord_color')
    settings.transition_engine = request.form.get('transition_engine')
    # NOWE: Zapis języka
    settings.language = request.form.get('language')
    
    db.session.commit()
    socketio.emit('apply_settings', {'font_family': settings.font_family, 'bg_color': settings.bg_color, 'text_color': settings.text_color})
    return redirect(url_for('control'))

@app.route('/reset_settings', methods=['POST'])
def reset_settings():
    settings = Settings.query.first()
    settings.font_family = 'Sen'; settings.bg_color = '#000000'; settings.text_color = '#ffffff'; settings.chord_color = '#00e5ff'; settings.transition_engine = 'v20'
    settings.language = 'pl' # Reset języka
    db.session.commit()
    bg_path = os.path.join(app.static_folder, 'background.png')
    if os.path.exists(bg_path):
        try: os.remove(bg_path)
        except Exception as e: pass
    socketio.emit('apply_settings', {'font_family': 'Sen', 'bg_color': '#000000', 'text_color': '#ffffff'})
    socketio.emit('refresh_background', {'has_bg': False})
    return redirect(url_for('control'))

@app.route('/upload_logo', methods=['POST'])
def upload_logo():
    if 'logo_file' in request.files:
        file = request.files['logo_file']
        if file.filename != '':
            file.save(os.path.join(app.static_folder, 'logo.png'))
            socketio.emit('refresh_logo')
    return redirect(url_for('control'))

@app.route('/upload_background', methods=['POST'])
def upload_background():
    f = request.files.get('bg_file')
    if f and f.filename:
        f.save(os.path.join(app.static_folder, 'background.png'))
        socketio.emit('refresh_background', {'has_bg': True})
    return redirect(url_for('control'))

@app.route('/delete_background', methods=['POST'])
def delete_background():
    bg_path = os.path.join(app.static_folder, 'background.png')
    if os.path.exists(bg_path):
        os.remove(bg_path)
        socketio.emit('refresh_background', {'has_bg': False})
    return redirect(url_for('control'))

@app.route('/print_setlist', methods=['POST'])
def print_setlist():
    data = request.json 
    songs_to_print = []
    for item in data:
        _, _, text_print = process_song(item['content'], int(item['transpose']))
        songs_to_print.append({'title': item['title'], 'html': text_print})
    return render_template('print_view.html', songs=songs_to_print)

@app.route('/qr_code/<path:subpath>')
def qr_code(subpath):
    ip = get_local_ip()
    url = f"http://{ip}:5000/{subpath}"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url); qr.make(fit=True)
    img_io = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route('/send_text', methods=['POST'])
def send_text():
    data = request.json
    global SERVER_STATE
    state_updated = False
    if 'current_index' in data:
        SERVER_STATE['current_index'] = data.get('current_index')
        state_updated = True
    if 'setlist' in data:
        SERVER_STATE['setlist'] = data.get('setlist')
        state_updated = True
    if state_updated: socketio.emit('sync_state_to_client', SERVER_STATE)

    if data.get('logo') is True:
        socketio.emit('update_slide', {'mode': 'logo'})
        return {'status': 'ok'}
    if data.get('mode') == 'conference':
        socketio.emit('update_slide', data) 
        return {'status': 'ok'}
    raw_text = data.get('text', '')
    if not raw_text:
        socketio.emit('update_slide', {'mode': 'blackout'})
        return {'status': 'ok'}
    
    shift = int(data.get('transpose', 0))
    next_shift = int(data.get('next_transpose', shift)) # Łapiemy nową transpozycję z JS
    passed_key = data.get('key', 'N/A')
    passed_bpm = data.get('bpm', 0)
    
    people_html, band_html, _ = process_song(raw_text, shift)
    _, band_next_html, _ = process_song(data.get('next_text', ''), next_shift) # Zmieniamy używany shift
    
    socketio.emit('update_slide', {
        'mode': 'worship', 
        'people': people_html, 
        'band': band_html, 
        'band_next': band_next_html,
        'current_key': passed_key,
        'current_bpm': passed_bpm
    })
    return {'status': 'ok'}

@app.route('/export_songs', methods=['GET'])
def export_songs():
    songs = Song.query.all()
    export_lines = []
    for song in songs:
        header = song.title
        if song.key: header += f" ({song.key})"
        if song.bpm and song.bpm > 0: header += f"-({song.bpm})"
        export_lines.append(header)
        export_lines.append(song.content.strip())
        export_lines.append("---")
    if export_lines and export_lines[-1] == "---": export_lines.pop()
    final_text = "\n".join(export_lines)
    return Response(final_text, mimetype="text/plain", headers={"Content-disposition": "attachment; filename=baza_piosenek.txt"})

# --- SERVER START THREAD ---
def start_server():
    socketio.run(app, host='0.0.0.0', port=5000, use_reloader=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        check_db_schema()
        init_settings()

    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()

    # WAŻNE: Dodajemy js_api=JafaApi()
    api = JafaApi()
    
    # --- ZMIANA DLA LOADING SCREEN ---
    # 1. Ustalamy ścieżkę do pliku loading.html
    # Używamy resource_path, aby działało też po kompilacji do .exe
    loading_screen_path = resource_path(os.path.join('templates', 'loading.html'))
    
    # 2. Konwertujemy ścieżkę na format URL (file://)
    loading_url = f'file://{os.path.abspath(loading_screen_path)}'

    # 3. Otwieramy okno startując od pliku lokalnego
    webview.create_window(
        'JafaStageCenter Control',       
        loading_url,  # <--- ZMIANA: Zamiast http://127.0.0.1:5000/control dajemy loading_url
        resizable=True,
        min_size=(800, 600),
        frameless=False,  
        easy_drag=True,
        maximized=True,
        background_color='#000000', # Warto ustawić czarne tło, żeby nie mignęło na biało
        js_api=api
    )

    webview.start()
    sys.exit()
