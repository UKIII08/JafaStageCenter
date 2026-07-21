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
import html
import shutil
import uuid
import itertools
from collections import Counter
import random
import logging
import tempfile
import subprocess
from pathlib import Path
import webbrowser
import fitz  # PyMuPDF do cięcia prezentacji
try:
    import pythoncom
    import win32com.client
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# Import na poziomie modułu, żeby PyInstaller SPAKOWAŁ cryptography do .exe
# (przy leniwym imporcie potrafi go pominąć, przez co generowanie certyfikatu
# HTTPS pada, serwer schodzi na HTTP i telefon dostaje ERR_SSL_PROTOCOL_ERROR).
# BaseException — uszkodzony natywny backend cryptography potrafi rzucić panikę.
try:
    from cryptography import x509 as _crypto_x509
    from cryptography.x509.oid import NameOID as _crypto_NameOID, ExtendedKeyUsageOID as _crypto_EKUOID
    from cryptography.hazmat.primitives import hashes as _crypto_hashes, serialization as _crypto_serialization
    from cryptography.hazmat.primitives.asymmetric import rsa as _crypto_rsa
    HAS_CRYPTOGRAPHY = True
except BaseException:
    HAS_CRYPTOGRAPHY = False
# --- ENGINE IMPORTS ---
try:
    from AdvancedEngine import WorshipHybridEngineV2
except ImportError:
    print("Warning: AdvancedEngine.py not found.")
    WorshipHybridEngineV2 = None
try:
    from PivotEngine import WorshipPivotEngineV3
except ImportError:
    print("Warning: PivotEngine.py not found.")
    WorshipPivotEngineV3 = None
try:
    from ContextEngine import WorshipContextEngineV4
except ImportError:
    print("Warning: ContextEngine.py not found.")
    WorshipContextEngineV4 = None

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

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key_jafa')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

if getattr(sys, 'frozen', False):
    db_path = os.path.join(os.path.dirname(sys.executable), 'worship.db')
else:
    db_path = os.path.join(os.path.abspath("."), 'worship.db')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Katalog na dane zapisywalne (obok bazy) — tam trzymamy certyfikat HTTPS.
DATA_DIR = os.path.dirname(db_path) or os.path.abspath('.')

# HTTPS (opcjonalny). Potrzebny, żeby MIKROFON (stroik) działał na telefonach —
# iOS/Android udostępniają getUserMedia tylko w bezpiecznym kontekście (HTTPS).
# Włączany przełącznikiem w Ustawieniach (plik-marker) LUB zmienną JAFA_HTTPS=1.
# Domyślnie wyłączony — istniejące instalacje działają bez zmian (po HTTP).
HTTPS_FLAG_FILE = os.path.join(DATA_DIR, 'https.enabled')

# Port dla równoległego serwera HTTPS (główny HTTP zostaje ZAWSZE na :5000).
HTTPS_PORT = 5443

def https_requested():
    if os.environ.get('JAFA_HTTPS', '').strip().lower() in ('1', 'true', 'yes', 'on'):
        return True
    try:
        return os.path.exists(HTTPS_FLAG_FILE)
    except Exception:
        return False

HTTPS_ENABLED = https_requested()

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
    'current_index': -1,
    'is_blackout': False
}
LAST_SLIDE_DATA = {}
# Zegar/wiadomość mówcy — osobny kanał, żeby tik zegara NIE przebudowywał
# tego, co jest na rzutniku (prezentacja/Canva). Trafia tylko na scenę i
# prezentera, nie na ekrany poszczególnych muzyków (band_member).
CONF_TIMER_STATE = {'timer': '00:00', 'timer_color': 'white', 'message': ''}

SILENT_MD_STATE = {'active': False, 'current': None, 'history': []}

@socketio.on('connect')
def handle_connect():
    emit('sync_state_to_client', SERVER_STATE)
    if LAST_SLIDE_DATA:
        emit('update_slide', LAST_SLIDE_DATA)
    emit('timer_update', CONF_TIMER_STATE)
    if SILENT_MD_STATE.get('active'):
        emit('silent_md', SILENT_MD_STATE)

@socketio.on('silent_md')
def handle_silent_md(data):
    """Tryb Silent Music Director — relay akordów granych na pianinie
    (MIDI) do wszystkich ekranów zespołu (band_member + stage)."""
    global SILENT_MD_STATE
    SILENT_MD_STATE = {
        'active': bool(data.get('active')),
        'current': data.get('current'),
        'history': data.get('history', [])[-4:]
    }
    emit('silent_md', SILENT_MD_STATE, broadcast=True)

@socketio.on('request_current_slide')
def handle_request_slide():
    if LAST_SLIDE_DATA:
        emit('update_slide', LAST_SLIDE_DATA)

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
    # Link do nagrania/ćwiczenia (YouTube/Spotify/Drive) — synchronizowany z chmury
    link = db.Column(db.String(500), nullable=True, default='')

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    font_family = db.Column(db.String(50), default='Sen')
    bg_color = db.Column(db.String(20), default='#000000')
    text_color = db.Column(db.String(20), default='#ffffff')
    chord_color = db.Column(db.String(20), default='#00e5ff')
    transition_engine = db.Column(db.String(10), default='v4')
    # NEW FIELD: Language
    language = db.Column(db.String(5), default='pl')
    chord_notation = db.Column(db.String(15), default='international')
    minor_display = db.Column(db.String(10), default='uppercase')
    chords_standardized = db.Column(db.Boolean, default=False)
    # Synchronizacja z chmurą (web app) — apka pobiera piosenki/setlisty/profile
    # z konta prowadzącego, jeśli jest sieć; inaczej działa offline.
    cloud_enabled = db.Column(db.Boolean, default=False)
    cloud_url = db.Column(db.String(200), default='https://jonathanapp.com')
    cloud_email = db.Column(db.String(200), default='')
    cloud_password = db.Column(db.String(200), default='')
    cloud_church_id = db.Column(db.String(40), default='')
    cloud_last_sync = db.Column(db.String(40), default='')

class BandPreset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    show_chords = db.Column(db.Boolean, default=True)
    nashville_mode = db.Column(db.Boolean, default=False)
    chord_notation = db.Column(db.String(15), default='international')
    lowercase_minor = db.Column(db.Boolean, default=False)
    capo_fret = db.Column(db.Integer, default=0)
    beginner_mode = db.Column(db.Boolean, default=False)
    diagram_instrument = db.Column(db.String(10), default='guitar')
    font_size = db.Column(db.Integer, default=6)

class MusicianProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    instrument = db.Column(db.String(50), default='')
    color = db.Column(db.String(20), default='#6366f1')
    show_chords = db.Column(db.Boolean, default=True)
    chord_notation = db.Column(db.String(15), default='international')
    lowercase_minor = db.Column(db.Boolean, default=False)
    capo_fret = db.Column(db.Integer, default=0)
    beginner_mode = db.Column(db.Boolean, default=False)
    diagram_instrument = db.Column(db.String(10), default='guitar')
    font_size = db.Column(db.Integer, default=8)
    instrument_transpose = db.Column(db.Integer, default=0)
    theme = db.Column(db.String(10), default='dark')

class ProfileSongSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('musician_profile.id'), nullable=False)
    song_id = db.Column(db.Integer, nullable=False)
    capo_fret = db.Column(db.Integer, default=None, nullable=True)
    notes = db.Column(db.Text, default='{}')  # JSON: {"0": "note for section 0", "2": "bridge: palm mute"}

class SetlistHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), default='')
    date = db.Column(db.String(30), nullable=False)
    songs = db.Column(db.Text, nullable=False)  # JSON array of {id, title, key, bpm, transpose}
    share_code = db.Column(db.String(8), unique=True, nullable=True)

def get_notation():
    s = Settings.query.first()
    notation = s.chord_notation if s and s.chord_notation else 'international'
    minor = s.minor_display if s and s.minor_display else 'uppercase'
    return notation, minor

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
            if 'link' not in song_columns:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE song ADD COLUMN link VARCHAR(500) DEFAULT ''"))
                    conn.commit()

            # Check Settings table
            settings_columns = [col['name'] for col in inspector.get_columns('settings')]
            # stare bazy: "N/A" zapisane jako tonacja piosenek bez akordów
            try:
                with db.engine.begin() as conn:
                    conn.execute(text("UPDATE song SET key='' WHERE key IN ('N/A','-')"))
            except Exception: pass
            if 'transition_engine' not in settings_columns:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE settings ADD COLUMN transition_engine VARCHAR(10) DEFAULT 'v4'"))
                    conn.commit()
            
            # NEW: Check for language column
            if 'language' not in settings_columns:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE settings ADD COLUMN language VARCHAR(5) DEFAULT 'pl'"))
                    conn.commit()

            if 'chord_notation' not in settings_columns:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE settings ADD COLUMN chord_notation VARCHAR(15) DEFAULT 'international'"))
                    conn.commit()

            if 'minor_display' not in settings_columns:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE settings ADD COLUMN minor_display VARCHAR(10) DEFAULT 'uppercase'"))
                    conn.commit()

            # Kolumny synchronizacji z chmurą (dokładane do starych baz)
            _cloud_cols = [
                ("cloud_enabled", "BOOLEAN DEFAULT 0"),
                ("cloud_url", "VARCHAR(200) DEFAULT 'https://jonathanapp.com'"),
                ("cloud_email", "VARCHAR(200) DEFAULT ''"),
                ("cloud_password", "VARCHAR(200) DEFAULT ''"),
                ("cloud_church_id", "VARCHAR(40) DEFAULT ''"),
                ("cloud_last_sync", "VARCHAR(40) DEFAULT ''"),
            ]
            for _name, _ddl in _cloud_cols:
                if _name not in settings_columns:
                    with db.engine.connect() as conn:
                        conn.execute(text(f"ALTER TABLE settings ADD COLUMN {_name} {_ddl}"))
                        conn.commit()

            # Check if BandPreset table exists
            if 'band_preset' not in inspector.get_table_names():
                BandPreset.__table__.create(db.engine)
            else:
                bp_columns = [col['name'] for col in inspector.get_columns('band_preset')]
                if 'diagram_instrument' not in bp_columns:
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE band_preset ADD COLUMN diagram_instrument VARCHAR(10) DEFAULT 'guitar'"))
                        conn.commit()
                if 'chord_notation' not in bp_columns:
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE band_preset ADD COLUMN chord_notation VARCHAR(15) DEFAULT 'international'"))
                        conn.commit()
                if 'lowercase_minor' not in bp_columns:
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE band_preset ADD COLUMN lowercase_minor BOOLEAN DEFAULT 0"))
                        conn.commit()

            if 'chords_standardized' not in settings_columns:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE settings ADD COLUMN chords_standardized BOOLEAN DEFAULT 0"))
                    conn.commit()
                _migrate_songs_to_international()

            # Check MusicianProfile table
            if 'musician_profile' not in inspector.get_table_names():
                MusicianProfile.__table__.create(db.engine)

            # Check ProfileSongSettings table
            if 'profile_song_settings' not in inspector.get_table_names():
                ProfileSongSettings.__table__.create(db.engine)

            # Check SetlistHistory table
            if 'setlist_history' not in inspector.get_table_names():
                SetlistHistory.__table__.create(db.engine)
            else:
                sh_columns = [col['name'] for col in inspector.get_columns('setlist_history')]
                if 'share_code' not in sh_columns:
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE setlist_history ADD COLUMN share_code VARCHAR(8)"))
                        conn.commit()

        except Exception as e:
            # Silent fail for exe log
            pass

def _migrate_songs_to_international():
    """One-time migration: convert all songs to international notation."""
    try:
        settings = Settings.query.first()
        old_notation = settings.chord_notation if settings else 'international'
        songs = Song.query.all()
        for song in songs:
            if song.content:
                song.content = normalize_song_chords_to_international(song.content, input_notation=old_notation)
            if song.key:
                song.key = normalize_chord_to_international(song.key, input_notation=old_notation)
        if settings:
            settings.chords_standardized = True
        db.session.commit()
    except Exception as e:
        print(f"MIGRATION ERROR: {e}")

# --- MAPPINGS ---
PITCH_CLASS_MAP = {
    'C': 0, 'C#': 1, 'DB': 1, 'D': 2, 'D#': 3, 'EB': 3, 'E': 4, 'FB': 4,
    'E#': 5, 'F': 5, 'F#': 6, 'GB': 6, 'G': 7, 'G#': 8, 'AB': 8,
    'A': 9, 'A#': 10, 'BB': 10, 'B': 11, 'CB': 11, 'H': 11, 'B#': 0
}
PITCH_CLASS_POLISH = {
    'CIS': 1, 'DIS': 3, 'FIS': 6, 'GIS': 8, 'AIS': 10,
    'ES': 3, 'AS': 8, 'HIS': 0
}
TRANSPOSE_LOOKUP = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
TRANSPOSE_LOOKUP_PL = ['C', 'Cis', 'D', 'Es', 'E', 'F', 'Fis', 'G', 'As', 'A', 'B', 'H']
# Pisownia wyniku transpozycji dziedziczy "smak" oryginału: akord z krzyżykiem
# transponuje się na krzyżyki (F#m +2 -> G#m, nie Abm), z bemolem na bemole
# (Bb +3 -> Db, nie C#). Nuty naturalne używają domyślnej mieszanej tabeli wyżej.
TRANSPOSE_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
TRANSPOSE_FLAT = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
TRANSPOSE_SHARP_PL = ['C', 'Cis', 'D', 'Dis', 'E', 'F', 'Fis', 'G', 'Gis', 'A', 'Ais', 'H']
TRANSPOSE_FLAT_PL = ['C', 'Des', 'D', 'Es', 'E', 'F', 'Ges', 'G', 'As', 'A', 'B', 'H']

def _accidental_flavor(root_str, notation='international'):
    """'sharp' / 'flat' / None (naturalna nuta) — na podstawie pisowni źródła."""
    r = root_str.strip()
    if '#' in r or r.lower().endswith('is'):
        return 'sharp'
    if len(r) > 1 and 'b' in r[1:].lower():
        return 'flat'
    lower = r.lower()
    if lower.endswith('es') or lower in ('as', 'es'):
        return 'flat'
    if notation == 'polish' and r.upper() == 'B':
        return 'flat'  # polskie B = Bb
    return None
CHORD_ROOT_RE = re.compile(r'^([AaEe][Ss](?![uU])|[A-Ha-h][#b]?(?:is|IS|Is)?)(.*)$')
VALID_CHORD_SUFFIX_RE = re.compile(r'^[majindugsMINDUGSAJ0-9#b()+\-/]*$')

def is_valid_chord(chord_str):
    if not chord_str or not chord_str.strip():
        return False
    chord_str = chord_str.strip().rstrip('-').rstrip()
    if '/' in chord_str:
        parts = chord_str.split('/', 1)
        return is_valid_chord(parts[0]) and (is_valid_chord(parts[1]) or parts[1].strip() == '')
    m = CHORD_ROOT_RE.match(chord_str)
    if not m:
        return False
    root = m.group(1)
    suffix = m.group(2)
    if not root or not root[0].upper() in 'ABCDEFGH':
        return False
    if suffix and not VALID_CHORD_SUFFIX_RE.match(suffix):
        return False
    return True

def clean_chord(chord_str):
    return chord_str.strip().rstrip('-').rstrip()

def _resolve_pitch_class(root_upper, notation='international'):
    if root_upper in PITCH_CLASS_POLISH:
        return PITCH_CLASS_POLISH[root_upper]
    if root_upper == 'B' and notation == 'polish':
        return 10
    if root_upper in PITCH_CLASS_MAP:
        return PITCH_CLASS_MAP[root_upper]
    return None

def normalize_chord_root(root_str, notation='international'):
    upper = root_str.upper()
    pc = _resolve_pitch_class(upper, notation)
    if pc is None:
        return root_str
    lookup = TRANSPOSE_LOOKUP_PL if notation == 'polish' else TRANSPOSE_LOOKUP
    return lookup[pc]

# --- IMPORT FORMATU "AKORDY NAD TEKSTEM" (Ultimate Guitar itp.) ---
# Wewnętrznym formatem aplikacji jest ChordPro ([C]tekst) - akord jest wtedy
# jednoznacznie przypięty do sylaby, co przeżywa zawijanie linii, zmianę
# czcionki i transpozycję. Ale użytkownicy kopiują piosenki z serwisów, gdzie
# akordy stoją W OSOBNEJ LINII nad tekstem, wyrównane spacjami. Ten konwerter
# skleja takie pary linii w ChordPro po pozycjach kolumnowych.
#
# Zasada bezpieczeństwa: konwersja jest KONSERWATYWNA. Linia jest uznana za
# linię akordów tylko, gdy WSZYSTKIE tokeny to poprawne akordy - a pojedyncza
# goła litera (np. "A" - po polsku spójnik!) nigdy. Fałszywy negatyw (nie
# skonwertował) jest tani; fałszywy pozytyw (zjadł linijkę tekstu) - kosztowny.

_STRICT_SINGLE_CHORD_RE = re.compile(
    r'^[A-Ha-h][#b]?(?:is|es)?'
    r'(?:m|maj7|maj9|m7b5|m7|m9|m11|dim7?|aug|sus[24]|add\d+|7sus4|6|7|9|11|13|\+|-)+'
    r'(?:/[A-Ha-h][#b]?(?:is|es)?)?$'
    r'|^[A-Ha-h][#b](?:/[A-Ha-h][#b]?)?$'
    r'|^[A-Ha-h][#b]?/[A-Ha-h][#b]?$'
)

def _is_chord_token(tok):
    return bool(CHORD_ROOT_RE.match(tok)) and is_valid_chord(tok)

def _is_chords_over_lyrics_line(line):
    """Czy linia wygląda JEDNOZNACZNIE na linię samych akordów?"""
    tokens = line.split()
    if not tokens:
        return False
    if any(not _is_chord_token(t) for t in tokens):
        return False
    if len(tokens) == 1:
        # pojedynczy token: tylko wyraźny akord (Am, F#, G7, C/E) -
        # goła litera ("A", "E") to po polsku często słowo piosenki
        return bool(_STRICT_SINGLE_CHORD_RE.match(tokens[0]))
    return True

_SECTION_HEADER_RE = re.compile(r'^\[([^\[\]]{1,40})\]$')

def convert_chords_over_lyrics(text):
    """Konwertuje format "akordy nad tekstem" na ChordPro.

    Zwraca (tekst, changed). Tekst już będący ChordPro przechodzi bez zmian
    (idempotentne) - można bezpiecznie wołać przy każdym zapisie.
    """
    if not text:
        return text, False
    lines = text.replace('\r', '').expandtabs(4).split('\n')
    out = []
    changed = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # nagłówek sekcji w stylu UG: [Intro], [Verse 1] -> zwykła etykieta
        m = _SECTION_HEADER_RE.match(stripped)
        if m and not _is_chord_token(m.group(1).strip()):
            out.append(m.group(1).strip())
            changed = True
            i += 1
            continue

        if _is_chords_over_lyrics_line(stripped):
            # pozycje akordów w linii (kolumna = indeks znaku)
            chords = [(mm.start(), mm.group(0)) for mm in re.finditer(r'\S+', line)]
            nxt = lines[i + 1] if i + 1 < len(lines) else ''
            nxt_stripped = nxt.strip()
            if nxt_stripped and not _is_chords_over_lyrics_line(nxt_stripped) \
                    and not _SECTION_HEADER_RE.match(nxt_stripped):
                # Akordy + tekst pod spodem -> sklej po kolumnach. Transkrypcje
                # "nad tekstem" są z konwencji wyrównane do SŁÓW, więc kolumnę
                # trafiającą w środek słowa przyciągamy do jego początku
                # (chyba że początek już zajęty innym akordem).
                merged = nxt
                positions = []
                tail = []      # akordy za końcem tekstu - doklejane na końcu
                taken = set()
                for col, ch in chords:
                    if col >= len(merged.rstrip()):
                        tail.append(ch)
                        continue
                    # kolumna na spacji -> początek następnego słowa
                    while col < len(merged) and merged[col] == ' ':
                        col += 1
                    # kolumna w środku słowa -> początek tego słowa
                    start = col
                    while start > 0 and merged[start - 1] != ' ':
                        start -= 1
                    if start not in taken:
                        col = start
                    taken.add(col)
                    positions.append((col, ch))
                for col, ch in sorted(positions, reverse=True):
                    merged = merged[:col] + '[' + ch + ']' + merged[col:]
                if tail:
                    merged = merged.rstrip() + ' ' + ' '.join('[' + ch + ']' for ch in tail)
                out.append(merged)
                changed = True
                i += 2
                continue
            else:
                # linia samych akordów bez tekstu (intro/instrumental)
                out.append(' '.join('[' + ch + ']' for _, ch in chords))
                changed = True
                i += 1
                continue

        out.append(line)
        i += 1
    return '\n'.join(out), changed

def normalize_chord_to_international(chord_str, input_notation='international'):
    """Normalize a chord to international notation for storage."""
    if not chord_str or not chord_str.strip():
        return chord_str
    chord_str = clean_chord(chord_str)
    if '/' in chord_str:
        parts = chord_str.split('/')
        return '/'.join(normalize_chord_to_international(p, input_notation) for p in parts)
    if not is_valid_chord(chord_str):
        return chord_str
    m = CHORD_ROOT_RE.match(chord_str)
    if not m:
        return chord_str
    raw_root = m.group(1)
    suffix = m.group(2)
    is_minor_lowercase = raw_root[0].islower()
    upper = raw_root.upper()
    pc = _resolve_pitch_class(upper, input_notation)
    if pc is None:
        return chord_str
    # zachowaj pisownię źródła: G#m NIE zamienia się w Abm przy zapisie
    flavor = _accidental_flavor(raw_root, input_notation)
    if flavor == 'sharp':
        normalized_root = TRANSPOSE_SHARP[pc]
    elif flavor == 'flat':
        normalized_root = TRANSPOSE_FLAT[pc]
    else:
        normalized_root = TRANSPOSE_LOOKUP[pc]
    if is_minor_lowercase and not suffix.startswith('m'):
        suffix = 'm' + suffix
        normalized_root = normalized_root[0].upper() + normalized_root[1:]
    return normalized_root + suffix

def normalize_chord(chord_str, notation='international'):
    if not chord_str or not chord_str.strip():
        return chord_str
    chord_str = clean_chord(chord_str)
    if not is_valid_chord(chord_str):
        return chord_str
    m = CHORD_ROOT_RE.match(chord_str)
    if not m:
        return chord_str
    raw_root = m.group(1)
    suffix = m.group(2)
    is_minor_lowercase = raw_root[0].islower()
    normalized_root = normalize_chord_root(raw_root, notation)
    if is_minor_lowercase and not suffix.startswith('m'):
        suffix = 'm' + suffix
        normalized_root = normalized_root[0].upper() + normalized_root[1:]
    return normalized_root + suffix

def normalize_song_chords_to_international(content, input_notation='international'):
    """Normalize all chords in song content to international notation for storage."""
    def replace_chord(m):
        inner = m.group(1).strip()
        cleaned = clean_chord(inner)
        if '/' in cleaned:
            parts = cleaned.split('/', 1)
            if is_valid_chord(parts[0]):
                normalized_parts = [normalize_chord_to_international(p, input_notation) for p in cleaned.split('/')]
                return '[' + '/'.join(normalized_parts) + ']'
            return '[' + cleaned + ']'
        if not is_valid_chord(cleaned):
            return '[' + cleaned + ']'
        return '[' + normalize_chord_to_international(cleaned, input_notation) + ']'
    return re.sub(r'\[(.*?)\]', replace_chord, content)

def normalize_song_chords(content, notation='international'):
    def replace_chord(m):
        inner = m.group(1).strip()
        cleaned = clean_chord(inner)
        if '/' in cleaned:
            parts = cleaned.split('/', 1)
            if is_valid_chord(parts[0]):
                normalized_parts = [normalize_chord(p, notation) for p in cleaned.split('/')]
                return '[' + '/'.join(normalized_parts) + ']'
            return '[' + cleaned + ']'
        if not is_valid_chord(cleaned):
            return '[' + cleaned + ']'
        return '[' + normalize_chord(cleaned, notation) + ']'
    return re.sub(r'\[(.*?)\]', replace_chord, content)

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

    def save_lyrics_html(self, setlist_data):
        """Generuje tymczasowy HTML z samymi tekstami i otwiera go w przeglądarce"""
        try:
            with app.test_request_context(base_url='http://127.0.0.1:5000'):
                songs_to_print = []
                for item in setlist_data:
                    raw = item.get('content', '')
                    raw = re.sub(r'\[.*?\]', '', raw).strip()
                    paragraphs = re.split(r'\n\s*\n', raw)
                    html_blocks = []
                    for p in paragraphs:
                        if p.strip():
                            lines = p.strip().replace('\n', '<br>')
                            html_blocks.append(f'<div class="lyrics-block">{lines}</div>')
                    songs_to_print.append({'title': item.get('title', 'Bez tytułu'), 'html': ''.join(html_blocks)})

                static_path_obj = Path(app.static_folder)
                static_absolute_path = static_path_obj.as_uri()

                html_content = render_template('print_lyrics.html',
                                               songs=songs_to_print,
                                               static_root=static_absolute_path)

                fd, path = tempfile.mkstemp(suffix=".html", prefix="teksty_")
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
        self.index_to_note = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
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

    def _parse_chord(self, c):
        """Parse one chord token -> (pitch_class, is_major, bass_pc | None).

        Uses the app-wide CHORD_ROOT_RE so Polish notation (H, Cis, Es, B=Bb)
        parses identically to the transpose pipeline. 'm' in the suffix only
        counts as minor when it is not part of 'maj' (Cmaj7 is major)."""
        c = clean_chord(c)
        bass_pc = None
        if '/' in c:
            main, _, bass = c.partition('/')
            bm = CHORD_ROOT_RE.match(bass.strip())
            if bm:
                bass_pc = _resolve_pitch_class(bm.group(1).upper())
            c = main.strip()
        m = CHORD_ROOT_RE.match(c)
        if not m:
            return None
        pc = _resolve_pitch_class(m.group(1).upper())
        if pc is None:
            return None
        suffix = m.group(2)
        is_minor = m.group(1)[0].islower() or bool(re.search(r'(?<!di)m(?!aj)', suffix)) or 'dim' in suffix
        return pc, not is_minor, bass_pc

    def detect(self, text):
        chords_raw = self._extract_chords_from_text(text) if not isinstance(text, list) else text
        if not chords_raw: return "N/A"

        parsed = [self._parse_chord(c) for c in chords_raw]
        parsed = [p for p in parsed if p]
        if not parsed: return "N/A"

        first, last = parsed[0], parsed[-1]
        vec = [0.0]*12
        for pc, is_major, bass_pc in parsed:
            for n in self._get_chord_notes(pc, is_major):
                vec[n] += 1
            if bass_pc is not None:
                vec[bass_pc] += 0.5

        best_key, best_score = "N/A", -999.0
        for i in range(12):
            s = self._calculate_correlation(vec, self.major_profile[-i:] + self.major_profile[:-i])
            if last[1] and last[0]==i: s+=0.5
            if first[1] and first[0]==i: s+=0.6
            if s > best_score: best_score, best_key = s, self.index_to_note[i]

            s = self._calculate_correlation(vec, self.minor_profile[-i:] + self.minor_profile[:-i])
            if not last[1] and last[0]==i: s+=0.5
            if not first[1] and first[0]==i: s+=0.6
            if s > best_score: best_score, best_key = s, f"{self.index_to_note[i]}m"
        return best_key

key_detector = AdvancedKeyDetector()
def detect_key_algorithm(text): return key_detector.detect(text)

# --- TRANSPOSE & PARSING HELPERS ---
def transpose_chord(match, shift, notation='international'):
    full_chord = match.group(1)
    # NIE ruszaj tokenów, które nie są akordami ([Coda], [Bridge], [x2]…) —
    # inaczej transpozycja psuła etykiety sekcji ([Coda] +2 -> [Doda]).
    if not is_valid_chord(full_chord):
        return f"[{full_chord}]"
    polish = (notation == 'polish')
    def trans_part(part):
        if not part: return ""
        m = CHORD_ROOT_RE.match(part)
        if not m: return part
        root_str, suffix = m.group(1), m.group(2)
        is_lower = part[0].islower()
        pc = _resolve_pitch_class(root_str.upper(), notation)
        if pc is not None:
            flavor = _accidental_flavor(root_str, notation)
            # zachowaj styl pisowni źródła: "Fis" transponuje się na "Gis", nie "G#"
            spelled_pl = polish or root_str.lower().endswith(('is', 'es'))
            if flavor == 'sharp':
                lookup = TRANSPOSE_SHARP_PL if spelled_pl else TRANSPOSE_SHARP
            elif flavor == 'flat':
                lookup = TRANSPOSE_FLAT_PL if spelled_pl else TRANSPOSE_FLAT
            else:
                lookup = TRANSPOSE_LOOKUP_PL if polish else TRANSPOSE_LOOKUP
            new_root = lookup[(pc + shift) % 12]
            return f"{new_root.lower() if is_lower else new_root}{suffix}"
        return part

    if '/' in full_chord:
        parts = full_chord.split('/')
        return f"[{trans_part(parts[0])}/{trans_part(parts[1])}]" if len(parts)>=2 else f"[{trans_part(full_chord)}]"
    return f"[{trans_part(full_chord)}]"

def apply_transpose_to_single_chord(chord_str, shift, notation='international'):
    if shift == 0: return chord_str
    return re.sub(r'\[(.*?)\]', lambda m: transpose_chord(m, shift, notation), chord_str)

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

def _format_chord_for_display(chord_str, notation='international', minor_display='uppercase'):
    if not chord_str:
        return chord_str
    chord_str = clean_chord(chord_str)
    if '/' in chord_str:
        parts = chord_str.split('/')
        return '/'.join(_format_chord_for_display(p, notation, minor_display) for p in parts)
    if not is_valid_chord(chord_str):
        return chord_str
    m = CHORD_ROOT_RE.match(chord_str)
    if not m:
        return chord_str
    raw_root = m.group(1)
    suffix = m.group(2)
    normalized = normalize_chord_root(raw_root, notation)
    if minor_display == 'lowercase' and (suffix.startswith('m') and not suffix.startswith('maj')):
        normalized = normalized[0].lower() + normalized[1:]
        suffix = suffix[1:]
    return normalized + suffix

def process_song(text, transpose_amount=0, notation='international', minor_display='uppercase'):
    if not text: return "", "", ""
    text = text.strip()
    if transpose_amount != 0:
        text = re.sub(r'\[(.*?)\]', lambda m: transpose_chord(m, transpose_amount, 'international'), text)
    # HTML-escape treści tekstu (ochrona przed wstrzyknięciem HTML/JS z pieśni —
    # np. z importu lub z otwartego /send_text w sieci). Akordy w [] są usuwane.
    text_people = html.escape(re.sub(r'\[.*?\]', '', text).strip(), quote=False).replace('\n', '<br>')
    # PARY AKORD+SYLABA. Akord i sylaba, nad którą stoi, tworzą jeden
    # inline-block: akord zajmuje PRAWDZIWE miejsce w układzie (wiersz nad
    # sylabą), więc:
    #  - akordy nie mogą na siebie nachodzić (para po prostu się poszerza),
    #  - przy zawijaniu linii akord ZAWSZE wędruje razem ze swoją sylabą,
    #  - auto-dopasowanie rozmiaru (fitText) widzi pełną wysokość treści.
    # Zastępuje wcześniejsze zgadywanie szerokości w "ch", absolutne
    # pozycjonowanie i JS-owe rozsuwanie kolizji (fixChordOverlap).
    tokens = re.split(r'(\[.*?\])', text)

    def esc(s):
        return (html.escape(s, quote=False)
                .replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')
                .replace('  ', '&nbsp;&nbsp;'))

    def chord_inner_html(name):
        c = html.escape(name, quote=False)  # escapuj nazwę akordu
        if '/' in c:
            parts = c.split('/')
            c = (f"{parts[0]}<span class='bass-slash'>/</span>"
                 f"<span class='bass-note'>{'/'.join(parts[1:])}</span>")
        return c

    parts_out = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.startswith('[') and token.endswith(']'):
            name = token[1:-1].strip()
            if not name:
                i += 1
                continue
            # Sylaba pary: tekst za akordem do końca słowa (albo pusta, gdy
            # zaraz kolejny akord / koniec linii — para trzyma wtedy wysokość
            # przez CSS ::before z zero-width space).
            syl = ''
            if i + 1 < len(tokens) and not (tokens[i + 1].startswith('[') and tokens[i + 1].endswith(']')):
                m = re.match(r'[^\s]+', tokens[i + 1])
                if m:
                    syl = m.group(0)
                    tokens[i + 1] = tokens[i + 1][len(syl):]
            # Akord w środku słowa (Ła[G/B]ska): WORD JOINER przed parą
            # zabrania złamania linii wewnątrz słowa.
            if parts_out and not parts_out[-1].endswith('>') and parts_out[-1][-1:] and not parts_out[-1][-1:].isspace():
                parts_out.append('&#8288;')
            parts_out.append(
                f'<span class="chord-pair"><span class="chord">{chord_inner_html(name)}</span>'
                f'<span class="chord-syl">{esc(syl)}</span></span>')
        else:
            # escapuj tekst pieśni PRZED zamianą tab/spacji na &nbsp; (żeby nie
            # podwójnie escapować wstawianych encji)
            parts_out.append(esc(token))
        i += 1

    text_smart = ''.join(parts_out)
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
def home():
    return render_template('home.html')

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

@app.route('/band_member')
def band_member():
    presets = BandPreset.query.all()
    return render_template('band_member.html', presets=presets)

@app.route('/api/presets', methods=['GET'])
def get_presets():
    presets = BandPreset.query.all()
    return [{'id': p.id, 'name': p.name, 'show_chords': p.show_chords,
             'nashville_mode': p.nashville_mode,
             'chord_notation': p.chord_notation or ('nashville' if p.nashville_mode else 'international'),
             'lowercase_minor': p.lowercase_minor or False,
             'capo_fret': p.capo_fret,
             'beginner_mode': p.beginner_mode, 'diagram_instrument': p.diagram_instrument,
             'font_size': p.font_size} for p in presets]

@app.route('/api/presets', methods=['POST'])
def save_preset():
    data = request.json
    preset_id = data.get('id')
    if preset_id:
        p = BandPreset.query.get(preset_id)
        if not p:
            return {'error': 'not found'}, 404
    else:
        p = BandPreset()
        db.session.add(p)
    p.name = data.get('name', 'Preset')
    p.show_chords = data.get('show_chords', True)
    p.chord_notation = data.get('chord_notation', 'international')
    p.lowercase_minor = data.get('lowercase_minor', False)
    p.nashville_mode = (p.chord_notation == 'nashville')
    p.capo_fret = int(data.get('capo_fret', 0))
    p.beginner_mode = data.get('beginner_mode', False)
    p.diagram_instrument = data.get('diagram_instrument', 'guitar')
    p.font_size = int(data.get('font_size', 6))
    db.session.commit()
    return {'id': p.id, 'name': p.name}

@app.route('/api/presets/<int:pid>', methods=['DELETE'])
def delete_preset(pid):
    p = BandPreset.query.get(pid)
    if p:
        db.session.delete(p)
        db.session.commit()
    return {'status': 'ok'}

@app.route('/api/song/<int:song_id>/band')
def get_song_for_band(song_id):
    song = Song.query.get(song_id)
    if not song:
        return {'error': 'not found'}, 404
    import re
    raw = song.content or ''
    raw = re.sub(r'(\n\s*){2,}\n', '\n\n', raw)
    parts = re.split(r'\n\s*\n', raw)
    rendered = []
    for i, block in enumerate(parts):
        block = block.strip()
        if not block:
            continue
        lines = block.split('\n')
        label = f'Sekcja {i + 1}'
        content = block
        if lines and '[' not in lines[0] and len(lines[0]) < 30:
            label = lines[0].strip()
            content = '\n'.join(lines[1:]).strip()
        _, band_html, _ = process_song(content)
        rendered.append({
            'band_html': band_html,
            'raw_text': content,
            'label': label
        })
    key = song.key or ''
    if not key:
        key = detect_key(song.content)
    return {
        'id': song.id,
        'title': song.title,
        'key': key,
        'bpm': song.bpm or 0,
        'link': song.link or '',
        'sections': rendered
    }

@app.route('/api/setlist')
def get_setlist():
    return {'setlist': SERVER_STATE['setlist'], 'current_index': SERVER_STATE['current_index']}

@app.route('/api/current-slide')
def get_current_slide():
    return LAST_SLIDE_DATA if LAST_SLIDE_DATA else {'mode': 'none'}

# --- MUSICIAN PROFILES ---
@app.route('/api/profiles', methods=['GET'])
def get_profiles():
    profiles = MusicianProfile.query.all()
    return [{'id': p.id, 'name': p.name, 'instrument': p.instrument, 'color': p.color,
             'show_chords': p.show_chords, 'chord_notation': p.chord_notation,
             'lowercase_minor': p.lowercase_minor, 'capo_fret': p.capo_fret,
             'beginner_mode': p.beginner_mode, 'diagram_instrument': p.diagram_instrument,
             'font_size': p.font_size, 'instrument_transpose': p.instrument_transpose,
             'theme': p.theme} for p in profiles]

@app.route('/api/profiles', methods=['POST'])
def create_profile():
    data = request.json
    p = MusicianProfile()
    p.name = data.get('name', 'Muzyk')
    p.instrument = data.get('instrument', '')
    p.color = data.get('color', '#6366f1')
    db.session.add(p)
    db.session.commit()
    return {'id': p.id, 'name': p.name}

@app.route('/api/profiles/<int:pid>', methods=['GET'])
def get_profile(pid):
    p = MusicianProfile.query.get(pid)
    if not p:
        return {'error': 'not found'}, 404
    return {'id': p.id, 'name': p.name, 'instrument': p.instrument, 'color': p.color,
            'show_chords': p.show_chords, 'chord_notation': p.chord_notation,
            'lowercase_minor': p.lowercase_minor, 'capo_fret': p.capo_fret,
            'beginner_mode': p.beginner_mode, 'diagram_instrument': p.diagram_instrument,
            'font_size': p.font_size, 'instrument_transpose': p.instrument_transpose,
            'theme': p.theme}

@app.route('/api/profiles/<int:pid>', methods=['PUT'])
def update_profile(pid):
    p = MusicianProfile.query.get(pid)
    if not p:
        return {'error': 'not found'}, 404
    data = request.json
    for field in ['name', 'instrument', 'color', 'show_chords', 'chord_notation',
                  'lowercase_minor', 'beginner_mode', 'diagram_instrument', 'theme']:
        if field in data:
            setattr(p, field, data[field])
    for field in ['capo_fret', 'font_size', 'instrument_transpose']:
        if field in data:
            setattr(p, field, int(data[field]))
    db.session.commit()
    return {'status': 'ok', 'id': p.id}

@app.route('/api/profiles/<int:pid>', methods=['DELETE'])
def delete_profile(pid):
    p = MusicianProfile.query.get(pid)
    if p:
        ProfileSongSettings.query.filter_by(profile_id=pid).delete()
        db.session.delete(p)
        db.session.commit()
    return {'status': 'ok'}

# --- PER-SONG SETTINGS (capo + notes) ---
@app.route('/api/profiles/<int:pid>/song/<int:sid>', methods=['GET'])
def get_song_settings(pid, sid):
    s = ProfileSongSettings.query.filter_by(profile_id=pid, song_id=sid).first()
    if not s:
        return {'capo_fret': None, 'notes': {}}
    return {'capo_fret': s.capo_fret, 'notes': json.loads(s.notes or '{}')}

@app.route('/api/profiles/<int:pid>/song/<int:sid>', methods=['PUT'])
def update_song_settings(pid, sid):
    data = request.json
    s = ProfileSongSettings.query.filter_by(profile_id=pid, song_id=sid).first()
    if not s:
        s = ProfileSongSettings(profile_id=pid, song_id=sid)
        db.session.add(s)
    if 'capo_fret' in data:
        s.capo_fret = data['capo_fret']  # can be None to clear
    if 'notes' in data:
        s.notes = json.dumps(data['notes'])
    db.session.commit()
    return {'status': 'ok'}

# --- SETLIST HISTORY ---
@app.route('/api/setlist-history', methods=['GET'])
def get_setlist_history():
    items = SetlistHistory.query.order_by(SetlistHistory.id.desc()).all()
    return [{'id': h.id, 'name': h.name, 'date': h.date,
             'songs': json.loads(h.songs), 'song_count': len(json.loads(h.songs))} for h in items]

@app.route('/api/setlist-history', methods=['POST'])
def save_setlist_history():
    data = request.json
    h = SetlistHistory()
    h.name = data.get('name', '')
    h.date = data.get('date', '')
    h.songs = json.dumps(data.get('songs', []))
    db.session.add(h)
    db.session.commit()
    return {'id': h.id, 'status': 'ok'}

@app.route('/api/setlist-history/<int:hid>', methods=['GET'])
def get_setlist_history_item(hid):
    h = SetlistHistory.query.get(hid)
    if not h:
        return {'error': 'not found'}, 404
    return {'id': h.id, 'name': h.name, 'date': h.date, 'songs': json.loads(h.songs)}

@app.route('/api/setlist-history/<int:hid>', methods=['DELETE'])
def delete_setlist_history(hid):
    h = SetlistHistory.query.get(hid)
    if h:
        db.session.delete(h)
        db.session.commit()
    return {'status': 'ok'}

@app.route('/api/setlist-share', methods=['POST'])
def share_setlist():
    import string, random
    data = request.json
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    while SetlistHistory.query.filter_by(share_code=code).first():
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    h = SetlistHistory()
    h.name = data.get('name', '')
    h.date = data.get('date', '')
    h.songs = json.dumps(data.get('songs', []))
    h.share_code = code
    db.session.add(h)
    db.session.commit()
    return {'code': code, 'id': h.id}

@app.route('/api/setlist-share/<code>', methods=['GET'])
def get_shared_setlist(code):
    h = SetlistHistory.query.filter_by(share_code=code.upper()).first()
    if not h:
        return {'error': 'not found'}, 404
    return {'id': h.id, 'name': h.name, 'date': h.date, 'songs': json.loads(h.songs), 'code': h.share_code}

@app.route('/convert_song_format', methods=['POST'])
def route_convert_song_format():
    """Konwersja formatu "akordy nad tekstem" -> ChordPro. Wywoływana
    WYŁĄCZNIE jawnym przyciskiem w modalu dodawania/edycji - żadnej cichej
    auto-detekcji, użytkownik świadomie uruchamia konwersję i widzi wynik."""
    data = request.json or {}
    text = data.get('text', '')
    converted, changed = convert_chords_over_lyrics(text)
    return {'text': converted, 'changed': changed}

@app.route('/detect_key', methods=['POST'])
def route_detect_key():
    data = request.json
    text = data.get('text', '')
    transpose = int(data.get('transpose', 0))
    if transpose != 0:
        text = re.sub(r'\[(.*?)\]', lambda m: transpose_chord(m, transpose, 'international'), text)
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

    song_a_content = song_b_content = None
    song_a = song_b = None
    bpm_a = bpm_b = 0
    if id_start:
        song_a = Song.query.get(id_start)
        if song_a:
            key_start = song_a.key if song_a.key else "C"
            first_from_chorus = get_first_chord_from_chorus(song_a.content)
            start_chord_raw = first_from_chorus if first_from_chorus else (get_first_chord_of_song(song_a.content) or key_start)
            song_a_content = song_a.content
            bpm_a = song_a.bpm or 0

    if id_end:
        song_b = Song.query.get(id_end)
        if song_b:
            key_end = song_b.key if song_b.key else "C"
            first_chord = get_first_chord_of_song(song_b.content)
            end_chord_raw = first_chord if first_chord else key_end
            song_b_content = song_b.content
            bpm_b = song_b.bpm or 0

    if not id_start:
        start_chord_raw = data.get('start_chord', 'C')
        key_start = data.get('key_start', 'C')
    if not id_end:
        end_chord_raw = data.get('end_chord', 'C')
        key_end = data.get('key_end', 'C')

    # Przejście ma sens tylko między piosenkami Z akordami - inaczej silnik
    # lądowałby na "akordzie" będącym tonacją-zaślepką (np. dawne "N/A").
    if (id_start and song_a and not get_first_chord_of_song(song_a.content)) or \
       (id_end and song_b and not get_first_chord_of_song(song_b.content)):
        return {'status': 'skip', 'reason': 'no_chords'}

    if not start_chord_raw.startswith('['): start_to_trans = f"[{start_chord_raw}]"
    else: start_to_trans = start_chord_raw
    if not end_chord_raw.startswith('['): end_to_trans = f"[{end_chord_raw}]"
    else: end_to_trans = end_chord_raw

    real_start_chord = apply_transpose_to_single_chord(start_to_trans, trans_start, 'international')
    real_end_chord = apply_transpose_to_single_chord(end_to_trans, trans_end, 'international')
    real_key_start = apply_transpose_to_single_chord(f"[{key_start}]", trans_start, 'international')
    real_key_end = apply_transpose_to_single_chord(f"[{key_end}]", trans_end, 'international')

    settings = Settings.query.first()
    engine_choice = settings.transition_engine if settings else 'v4'
    if engine_choice not in ('v2', 'v3', 'v4'):
        engine_choice = 'v4'   # v1 wycofany, stare 'v20' -> domyślny V4

    # v1 wycofany; nieznane/stare wartości ('v1', 'v20') dostają domyślny V4
    if engine_choice == 'v2' and WorshipHybridEngineV2:
        engine = WorshipHybridEngineV2()
    elif engine_choice == 'v3' and WorshipPivotEngineV3:
        engine = WorshipPivotEngineV3()
    elif WorshipContextEngineV4:
        engine = WorshipContextEngineV4()
    else:
        engine = WorshipHybridEngineV2()

    if WorshipContextEngineV4 and isinstance(engine, WorshipContextEngineV4):
        # V4 dostaje pełny kontekst: treść obu piosenek (repertuar liczony
        # po transpozycji), oraz tempa - reszta silników zna tylko 4 akordy
        transition_chords = engine.generate_full_progression(
            real_start_chord, real_key_start, real_end_chord, real_key_end,
            song_a_content=song_a_content, song_b_content=song_b_content,
            shift_a=trans_start, shift_b=trans_end, bpm_a=bpm_a, bpm_b=bpm_b)
    else:
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
    input_notation = request.form.get('input_notation', 'international')
    if content:
        content = normalize_song_chords_to_international(content, input_notation=input_notation)
    if key:
        key = normalize_chord_to_international(key, input_notation=input_notation)
    if not key and content: key = detect_key_algorithm(content)
    if key in ('N/A', '-'): key = ''   # brak akordów = brak tonacji, nie literal "N/A"
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
    input_notation = request.form.get('input_notation', 'international')
    def save_or_update(song_title, song_content, song_key='', song_bpm=0):
        existing = Song.query.filter_by(title=song_title).first()
        song_content = normalize_song_chords_to_international(song_content, input_notation=input_notation)
        if song_key:
            song_key = normalize_chord_to_international(song_key, input_notation=input_notation)
        if not song_key: song_key = detect_key_algorithm(song_content)
        if song_key in ('N/A', '-'): song_key = ''
        if existing:
            existing.content = song_content
            existing.key = song_key
            existing.bpm = song_bpm
        else:
            db.session.add(Song(title=song_title, content=song_content, key=song_key, bpm=song_bpm))

    for file in files:
        if file and file.filename.endswith('.txt'):
            raw_data = file.read()
            try: content = raw_data.decode('utf-8-sig')  # -sig: zdejmij BOM z Notatnika
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
                            if key and not is_valid_chord(key):
                                title = f"{title} ({key})".strip(); key = ''
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
                    if key and not is_valid_chord(key):
                        title = f"{title} ({key})".strip(); key = ''
                    try: bpm = int(match.group(3)) if match.group(3) else 0
                    except: bpm = 0
                else:
                    title = raw_filename; key = ''; bpm = 0
                body = content.strip()
                if title and body: save_or_update(title, body, key, bpm)
    db.session.commit()
    return redirect(url_for('control'))


# ── Synchronizacja z chmurą (opcjonalna) ─────────────────────────────────
# Apka pobiera piosenki/setlisty/profile z web-owego konta prowadzącego, jeśli
# jest sieć. Przy braku sieci działa offline na lokalnej bazie (nic nie kasuje).
import cloud_sync


def _apply_cloud_songs(songs, input_notation='international'):
    """Upsert piosenek z chmury po tytule (nie usuwa lokalnych nadmiarowych).
    Wejście: lista dictów {title, content, key, bpm, link}."""
    added = updated = 0
    for s in songs:
        title = (s.get('title') or '').strip()
        body = s.get('content') or ''
        key = s.get('key') or ''
        bpm = s.get('bpm') or 0
        link = (s.get('link') or '').strip()
        if not title:
            continue
        content = normalize_song_chords_to_international(
            body, input_notation=input_notation)
        k = normalize_chord_to_international(
            key, input_notation=input_notation) if key else ''
        if not k:
            k = detect_key_algorithm(content)
        if k in ('N/A', '-'):
            k = ''
        existing = Song.query.filter_by(title=title).first()
        if existing:
            existing.content, existing.key, existing.bpm = content, k, bpm or 0
            existing.link = link
            updated += 1
        else:
            db.session.add(Song(title=title, content=content, key=k,
                                bpm=bpm or 0, link=link))
            added += 1
    return added, updated


def _apply_cloud_profiles(profiles):
    """Upsert profili muzyków po nazwie."""
    touched = 0
    str_f = ['instrument', 'color', 'chord_notation', 'diagram_instrument', 'theme']
    bool_f = ['show_chords', 'lowercase_minor', 'beginner_mode']
    int_f = ['capo_fret', 'font_size', 'instrument_transpose']
    for pdata in profiles or []:
        name = (pdata.get('name') or '').strip()
        if not name:
            continue
        p = MusicianProfile.query.filter_by(name=name).first()
        if not p:
            p = MusicianProfile(name=name)
            db.session.add(p)
        for f in str_f:
            if pdata.get(f) is not None:
                setattr(p, f, pdata[f])
        for f in bool_f:
            if pdata.get(f) is not None:
                setattr(p, f, bool(pdata[f]))
        for f in int_f:
            if pdata.get(f) is not None:
                try:
                    setattr(p, f, int(pdata[f]))
                except (TypeError, ValueError):
                    pass
        touched += 1
    return touched


def _apply_cloud_setlists(setlists):
    """Dokłada setlisty z chmury (po nazwie+dacie), nie duplikując."""
    added = 0
    for s in setlists or []:
        name = (s.get('name') or '').strip()
        date = s.get('date') or ''
        if not name or SetlistHistory.query.filter_by(name=name, date=date).first():
            continue
        h = SetlistHistory()
        h.name, h.date = name, date
        h.songs = json.dumps(s.get('songs', []))
        db.session.add(h)
        added += 1
    return added


def run_cloud_sync():
    """Pobiera dane z chmury do lokalnej bazy. Nigdy nie rzuca — przy braku
    sieci zwraca offline=True i aplikacja działa dalej na tym, co lokalne."""
    s = Settings.query.first()
    if not s or not s.cloud_enabled or not s.cloud_email or not s.cloud_password:
        return {'ok': False, 'configured': False,
                'message': 'Synchronizacja z chmurą jest wyłączona.'}
    try:
        opener, church_id = cloud_sync.connect(
            s.cloud_url, s.cloud_email, s.cloud_password)
    except cloud_sync.CloudUnavailable:
        return {'ok': False, 'offline': True,
                'message': 'Brak połączenia — pracuję offline na lokalnych danych.'}
    except cloud_sync.CloudAuthError as e:
        return {'ok': False, 'configured': True, 'message': str(e)}
    if s.cloud_church_id and len(s.cloud_church_id) == 36:
        church_id = s.cloud_church_id     # ręczny wybór (konto w kilku wspólnotach)
    try:
        songs = cloud_sync.fetch_songs(opener, s.cloud_url, church_id)
        profiles = cloud_sync.fetch_profiles(opener, s.cloud_url, church_id)
        setlists = cloud_sync.fetch_setlists(opener, s.cloud_url, church_id)
    except cloud_sync.CloudUnavailable:
        return {'ok': False, 'offline': True,
                'message': 'Połączenie przerwane — zostaję na lokalnych danych.'}
    c = {'songs_added': 0, 'songs_updated': 0, 'profiles': 0, 'setlists': 0}
    if songs is not None:
        c['songs_added'], c['songs_updated'] = _apply_cloud_songs(songs)
    if profiles is not None:
        c['profiles'] = _apply_cloud_profiles(profiles)
    if setlists is not None:
        c['setlists'] = _apply_cloud_setlists(setlists)
    from datetime import datetime as _dt
    s.cloud_church_id = church_id
    s.cloud_last_sync = _dt.now().strftime('%Y-%m-%d %H:%M')
    db.session.commit()
    return {'ok': True, 'church_id': church_id, 'last_sync': s.cloud_last_sync,
            'counts': c,
            'message': (f"Pobrano z chmury: +{c['songs_added']} nowych pieśni, "
                        f"{c['songs_updated']} zaktualizowanych, "
                        f"{c['profiles']} profili, +{c['setlists']} setlist.")}


@app.route('/api/cloud/config', methods=['GET', 'POST'])
def cloud_config():
    s = Settings.query.first()
    if request.method == 'POST':
        data = request.json or {}
        s.cloud_enabled = bool(data.get('enabled'))
        s.cloud_url = (data.get('url') or 'https://jonathanapp.com').strip()
        s.cloud_email = (data.get('email') or '').strip()
        if data.get('password'):     # nie nadpisuj pustym (hasło maskowane w GET)
            s.cloud_password = data['password']
        s.cloud_church_id = (data.get('church_id') or '').strip()
        db.session.commit()
        return {'status': 'ok'}
    return {'enabled': bool(s.cloud_enabled),
            'url': s.cloud_url or 'https://jonathanapp.com',
            'email': s.cloud_email or '', 'has_password': bool(s.cloud_password),
            'church_id': s.cloud_church_id or '', 'last_sync': s.cloud_last_sync or ''}


@app.route('/api/cloud/sync', methods=['POST'])
def cloud_sync_now():
    return run_cloud_sync()


@app.route('/edit_song/<int:id>', methods=['POST'])
def edit_song(id):
    song = Song.query.get_or_404(id)
    song.title = request.form.get('title')
    song.content = request.form.get('content')
    input_notation = request.form.get('input_notation', 'international')
    if song.content:
        song.content = normalize_song_chords_to_international(song.content, input_notation=input_notation)
    song.key = request.form.get('key')
    if song.key:
        song.key = normalize_chord_to_international(song.key, input_notation=input_notation)
    bpm = request.form.get('bpm')
    try: song.bpm = int(bpm) if bpm else 0
    except ValueError: song.bpm = 0
    db.session.commit()
    return redirect(url_for('control'))

@app.route('/delete_demo_song', methods=['POST'])
def delete_demo_song():
    """Usuwa WYŁĄCZNIE piosenkę demo samouczka (weryfikacja po treści),
    żeby sprzątanie po onboardingu nie mogło trafić w piosenkę użytkownika."""
    s = Song.query.filter_by(title='Jedyny Krol').first()
    # fraza w treści demo jest poprzecinana akordami ([G]przyjal...) - zdejmij
    # nawiasy przed porównaniem
    clean = re.sub(r'\[[^\]]*\]', '', s.content or '') if s else ''
    if s and 'Jedyny Krol, ktory przyjal postac slugi' in clean:
        deleted_id = s.id
        db.session.delete(s)
        db.session.commit()
        return {'status': 'ok', 'deleted': deleted_id}
    return {'status': 'skip'}

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
    settings.language = request.form.get('language')
    settings.chord_notation = request.form.get('chord_notation', 'international')
    settings.minor_display = request.form.get('minor_display', 'uppercase')

    db.session.commit()
    socketio.emit('apply_settings', {'font_family': settings.font_family, 'bg_color': settings.bg_color, 'text_color': settings.text_color, 'lang': settings.language, 'chord_notation': settings.chord_notation, 'minor_display': settings.minor_display})
    socketio.emit('settings_changed')
    return redirect(url_for('control'))

@socketio.on('set_language')
def handle_set_language(data):
    emit('apply_settings', {'lang': data.get('lang', 'pl')}, broadcast=True)

@app.route('/reset_settings', methods=['POST'])
def reset_settings():
    settings = Settings.query.first()
    settings.font_family = 'Sen'; settings.bg_color = '#000000'; settings.text_color = '#ffffff'; settings.chord_color = '#00e5ff'; settings.transition_engine = 'v4'
    settings.language = 'pl'
    settings.chord_notation = 'international'
    settings.minor_display = 'uppercase'
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

# ── Ekran powitalny: odliczanie + ogłoszenia ze zdjęciami (tylko offline) ──
_ANNOUNCE_IMG_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}

def _announce_dir():
    d = os.path.join(app.static_folder, 'announcements')
    os.makedirs(d, exist_ok=True)
    return d

def _announce_config_path():
    return os.path.join(_announce_dir(), 'config.json')

@app.route('/announcements/upload_image', methods=['POST'])
def announce_upload_image():
    f = request.files.get('image')
    if not f or not f.filename:
        return {'status': 'error', 'message': 'Brak pliku.'}, 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in _ANNOUNCE_IMG_EXT:
        return {'status': 'error', 'message': 'Dozwolone: PNG/JPG/GIF/WebP.'}, 400
    name = uuid.uuid4().hex[:12] + ext
    f.save(os.path.join(_announce_dir(), name))
    return {'status': 'ok', 'filename': name,
            'url': '/static/announcements/' + name}

@app.route('/announcements', methods=['GET'])
def announce_get():
    try:
        with open(_announce_config_path(), 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except (FileNotFoundError, ValueError):
        return {'start_time': '', 'heading': '', 'items': []}

@app.route('/announcements', methods=['POST'])
def announce_save():
    data = request.json or {}
    items = []
    for it in (data.get('items') or [])[:20]:
        text = (it.get('text') or '').strip()[:300]
        image = (it.get('image') or '').strip()[:200]
        if text or image:
            items.append({'text': text, 'image': image})
    cfg = {'start_time': (data.get('start_time') or '')[:5],
           'heading': (data.get('heading') or '').strip()[:120],
           'items': items}
    with open(_announce_config_path(), 'w', encoding='utf-8') as fh:
        json.dump(cfg, fh, ensure_ascii=False)
    # Sprzątanie: usuń pliki obrazków, do których nie ma już odwołania.
    used = {it['image'].rsplit('/', 1)[-1] for it in items if it.get('image')}
    for fn in os.listdir(_announce_dir()):
        if fn != 'config.json' and fn not in used:
            try:
                os.remove(os.path.join(_announce_dir(), fn))
            except OSError:
                pass
    return {'status': 'ok'}

@app.route('/print_setlist', methods=['POST'])
def print_setlist():
    data = request.json
    songs_to_print = []
    for item in data:
        _, _, text_print = process_song(item['content'], int(item['transpose']))
        songs_to_print.append({'title': item['title'], 'html': text_print})
    return render_template('print_view.html', songs=songs_to_print, static_root='/static')

@app.route('/print_lyrics', methods=['POST'])
def print_lyrics():
    data = request.json
    songs_to_print = []
    for item in data:
        raw = item['content']
        raw = re.sub(r'\[.*?\]', '', raw).strip()
        paragraphs = re.split(r'\n\s*\n', raw)
        html_blocks = []
        for p in paragraphs:
            if p.strip():
                lines = html.escape(p.strip(), quote=False).replace('\n', '<br>')
                html_blocks.append(f'<div class="lyrics-block">{lines}</div>')
        songs_to_print.append({'title': item['title'], 'html': ''.join(html_blocks)})
    return render_template('print_lyrics.html', songs=songs_to_print, static_root='/static')

@app.route('/qr_setlist')
def qr_setlist():
    data = request.args.get('data', '')
    if not data:
        return 'No data', 400
    qr = qrcode.QRCode(version=None, box_size=6, border=3, error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(data); qr.make(fit=True)
    img_io = BytesIO()
    try:
        qr.make_image(fill_color="black", back_color="white").save(img_io, 'PNG')
        img_io.seek(0)
        return send_file(img_io, mimetype='image/png')
    except Exception:
        from qrcode.image.svg import SvgPathImage
        svg_img = qr.make_image(image_factory=SvgPathImage)
        svg_io = BytesIO()
        svg_img.save(svg_io)
        svg_io.seek(0)
        return send_file(svg_io, mimetype='image/svg+xml')

@app.route('/qr_code/<path:subpath>')
def qr_code(subpath):
    ip = get_local_ip()
    # ZAWSZE http:5000 — ten port działa bez względu na ustawienia HTTPS, więc
    # zeskanowany QR nigdy nie trafi w pustkę. Stroik (jedyna funkcja wymagająca
    # HTTPS) sam prowadzi na https:5443 przez /mic_help.
    url = f"http://{ip}:5000/{subpath}"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url); qr.make(fit=True)
    img_io = BytesIO()
    try:
        qr.make_image(fill_color="black", back_color="white").save(img_io, 'PNG')
        img_io.seek(0)
        return send_file(img_io, mimetype='image/png')
    except Exception:
        from qrcode.image.svg import SvgPathImage
        factory = SvgPathImage
        svg_img = qr.make_image(image_factory=factory)
        svg_io = BytesIO()
        svg_img.save(svg_io)
        svg_io.seek(0)
        return send_file(svg_io, mimetype='image/svg+xml')

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

    global LAST_SLIDE_DATA
    if data.get('logo') is True:
        SERVER_STATE['is_blackout'] = False
        LAST_SLIDE_DATA = {'mode': 'logo'}
        socketio.emit('update_slide', LAST_SLIDE_DATA)
        return {'status': 'ok'}
    if data.get('mode') in ['conference', 'canva', 'presentation', 'countdown']:
        # Ujednolić flagę blackoutu: widoki czytają 'is_blackout', a klient
        # wysyła 'blackout'. Bez tego blackout nie gasił projektora w prezentacji.
        data['is_blackout'] = bool(data.get('blackout', data.get('is_blackout', False)))
        SERVER_STATE['is_blackout'] = data['is_blackout']
        LAST_SLIDE_DATA = data
        socketio.emit('update_slide', data)
        return {'status': 'ok'}
    if not data or 'text' not in data:
        return {'status': 'error', 'reason': 'missing text'}, 400
    raw_text = data.get('text', '')
    is_blackout = data.get('blackout', False)
    SERVER_STATE['is_blackout'] = is_blackout

    shift = int(data.get('transpose', 0))
    next_shift = int(data.get('next_transpose', shift))
    passed_key = data.get('key', 'N/A')
    passed_bpm = data.get('bpm', 0)

    settings = Settings.query.first()
    lang = settings.language if settings else 'pl'
    notation = settings.chord_notation if settings else 'international'
    minor_display = settings.minor_display if settings else 'uppercase'

    people_html, band_html, _ = process_song(raw_text, shift)
    _, band_next_html, _ = process_song(data.get('next_text', ''), next_shift)

    LAST_SLIDE_DATA = {
        'mode': 'worship',
        'people': people_html,
        'band': band_html,
        'band_next': band_next_html,
        'raw_text': raw_text,
        'raw_next': data.get('next_text', ''),
        'current_key': passed_key,
        'current_bpm': passed_bpm,
        'song_title': data.get('song_title', ''),
        'is_blackout': is_blackout,
        'lang': lang,
        'notation': notation,
        'minor_display': minor_display,
        'transpose': shift
    }
    socketio.emit('update_slide', LAST_SLIDE_DATA)
    return {'status': 'ok'}

@app.route('/conf_timer', methods=['POST'])
def conf_timer():
    """Zegar/wiadomość mówcy — osobny, lekki kanał. NIE dotyka rzutnika ani
    LAST_SLIDE_DATA, więc uruchomienie/tik zegara nie gasi prezentacji.
    Odbierają go tylko scena (ZESPÓŁ) i prezenter — nie band_member."""
    global CONF_TIMER_STATE
    data = request.json or {}
    CONF_TIMER_STATE = {
        'timer': data.get('timer', '00:00'),
        'timer_color': data.get('timer_color', 'white'),
        'message': data.get('message', '')
    }
    socketio.emit('timer_update', CONF_TIMER_STATE)
    return {'status': 'ok'}

@app.route('/https_status', methods=['GET'])
def https_status():
    """enabled = przełącznik ustawiony; active = serwer FAKTYCZNIE po HTTPS w tej sesji;
    can_https = czy w ogóle da się wygenerować certyfikat (cryptography lub openssl)."""
    return {
        'enabled': os.path.exists(HTTPS_FLAG_FILE),
        'active': HTTPS_ACTIVE,
        'can_https': bool(HAS_CRYPTOGRAPHY or shutil.which('openssl')),
    }

@app.route('/toggle_https', methods=['POST'])
def toggle_https():
    """Włącza/wyłącza tryb HTTPS (mikrofon/stroik na telefonie). Wymaga
    restartu aplikacji, żeby serwer wystartował na właściwym protokole."""
    data = request.get_json(silent=True) or {}
    want = bool(data.get('enabled'))
    try:
        if want:
            with open(HTTPS_FLAG_FILE, 'w') as f:
                f.write('1')
        elif os.path.exists(HTTPS_FLAG_FILE):
            os.remove(HTTPS_FLAG_FILE)
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
    return {
        'status': 'ok',
        'enabled': want,
        'restart_required': (want != HTTPS_ENABLED),
        'can_https': bool(HAS_CRYPTOGRAPHY or shutil.which('openssl')),
    }

@app.route('/ca.crt')
def ca_certificate():
    """Certyfikat lokalnego CA do JEDNORAZOWEJ instalacji na telefonie.
    Po zainstalowaniu i zaufaniu (iPhone: Ustawienia → Profil → Zainstaluj,
    potem Ogólne → Informacje → Ustawienia zaufania certyfikatów) połączenie
    HTTPS jest w pełni zaufane i mikrofon (stroik) działa bez ostrzeżeń."""
    if not os.path.exists(CA_CERT_FILE):
        try:
            ensure_https_cert()
        except Exception:
            return ('Certyfikat nie został jeszcze wygenerowany. Włącz HTTPS w '
                    'Ustawieniach i uruchom aplikację ponownie.'), 404
    return send_file(CA_CERT_FILE, mimetype='application/x-x509-ca-cert',
                     as_attachment=True, download_name='JafaStageCenter-CA.crt')

@app.route('/mic_help')
def mic_help():
    """Instrukcja (PL/EN) jak uruchomić mikrofon/stroik na telefonie + test na żywo."""
    ip = get_local_ip()
    return render_template('mic_help.html',
                           ip=ip,
                           https_url=f'https://{ip}:{HTTPS_PORT}',
                           https_active=HTTPS_ACTIVE,
                           https_enabled=https_requested(),
                           can_https=bool(HAS_CRYPTOGRAPHY or shutil.which('openssl')))

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
@app.route('/open_canva', methods=['POST'])
def route_open_canva():
    data = request.json
    url = data.get('url', '')
    if url:
        # Jeśli wkleisz link edycji, program zamieni go na link 'view', żeby od razu zrzucić interfejs edytora
        if '/edit' in url:
            url = url.replace('/edit', '/view')
        webbrowser.open(url)
    return {'status': 'ok'}

@app.route('/presenter')
def presenter():
    """Nowy, dedykowany widok dla mówcy (Presenter View)"""
    return render_template('presenter.html')

@app.route('/upload_presentation', methods=['POST'])
def upload_presentation():
    """Odbiera plik PDF lub PPTX, konwertuje do PDF (jeśli trzeba), tnie na slajdy (PNG) i zapisuje w folderze static"""
    file = request.files.get('pres_file')
    if not file:
        return {'status': 'error', 'message': 'Brak pliku.'}
        
    filename = file.filename.lower()
    if not (filename.endswith('.pdf') or filename.endswith('.pptx') or filename.endswith('.ppt')):
        return {'status': 'error', 'message': 'Proszę wgrać plik PDF lub PowerPoint (.pptx).'}

    base_dir = os.path.join(app.static_folder, 'presentation')
    os.makedirs(base_dir, exist_ok=True)

    # Każda prezentacja trafia do własnego podfolderu (unikalne id), więc
    # wgranie kolejnego PDF NIE kasuje poprzednich — można je przełączać.
    pres_id = uuid.uuid4().hex[:8]
    save_dir = os.path.join(base_dir, pres_id)
    os.makedirs(save_dir, exist_ok=True)

    display_name = os.path.splitext(os.path.basename(file.filename))[0]

    # Zapisujemy wgrany plik tymczasowo z jego oryginalnym rozszerzeniem
    ext = os.path.splitext(filename)[1]
    temp_input_path = os.path.join(save_dir, 'uploaded_file' + ext)
    file.save(temp_input_path)

    pdf_path = os.path.join(save_dir, 'temp.pdf')

    try:
        # 1. KONWERSJA Z POWERPOINTA DO PDF (JEŚLI POTRZEBA)
        if ext in ['.pptx', '.ppt']:
            abs_input = os.path.abspath(temp_input_path)
            abs_pdf = os.path.abspath(pdf_path)
            converted = False

            # 1a. Windows + MS Office (najwierniejsza konwersja) — jeśli dostępne.
            if HAS_WIN32:
                try:
                    pythoncom.CoInitialize()
                    powerpoint = win32com.client.Dispatch("PowerPoint.Application")
                    presentation = powerpoint.Presentations.Open(abs_input, WithWindow=False)
                    presentation.SaveAs(abs_pdf, 32)  # 32 = format PDF w MS Office
                    presentation.Close()
                    pythoncom.CoUninitialize()
                    converted = os.path.exists(abs_pdf)
                except Exception as e:
                    logging.warning(f"Konwersja PPTX przez MS Office nie powiodła się: {e}")
                    converted = False

            # 1b. LibreOffice (Linux/Mac/Windows, bez MS Office) — uniwersalny fallback.
            if not converted:
                soffice = shutil.which('soffice') or shutil.which('libreoffice')
                if not soffice:
                    return {'status': 'error', 'message': 'Nie można przekonwertować PowerPointa (brak LibreOffice / MS Office). Najprościej: w PowerPoint zapisz jako PDF i wgraj plik PDF.'}
                subprocess.run(
                    [soffice, '--headless', '--convert-to', 'pdf', '--outdir', save_dir, abs_input],
                    check=True, timeout=180,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                # LibreOffice zapisuje jako <nazwa_wejścia>.pdf w outdir.
                produced = os.path.join(save_dir, os.path.splitext(os.path.basename(temp_input_path))[0] + '.pdf')
                if os.path.exists(produced) and produced != pdf_path:
                    os.rename(produced, pdf_path)
                if not os.path.exists(pdf_path):
                    return {'status': 'error', 'message': 'Nie udało się przekonwertować pliku PowerPoint. Najprościej: zapisz go jako PDF i wgraj PDF.'}
        else:
            # Jeśli to był od razu PDF, po prostu zmieniamy mu nazwę
            os.rename(temp_input_path, pdf_path)

        # 2. CIĘCIE PDF-A NA OBRAZKI (SLAJDY)
        doc = fitz.open(pdf_path)
        slide_urls = []
        
        for i in range(len(doc)):
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=150) # Rozdzielczość 150 dpi jest idealna i szybka
            img_name = f"slide_{i}.png"
            pix.save(os.path.join(save_dir, img_name))

            slide_urls.append(f"/static/presentation/{pres_id}/{img_name}?v={random.randint(1,10000)}")

        doc.close()

        # Opcjonalnie usuwamy tymczasowy plik PDF/PPTX żeby nie zaśmiecać dysku
        try: os.remove(pdf_path)
        except: pass

        payload = {'id': pres_id, 'name': display_name, 'slides': slide_urls}
        socketio.emit('presentation_ready', payload)
        return {'status': 'ok', **payload}

    except Exception as e:
        return {'status': 'error', 'message': f'Błąd przetwarzania: {str(e)}'}


@app.route('/delete_presentation', methods=['POST'])
def delete_presentation():
    """Usuwa pojedynczą wgraną prezentację (jej podfolder ze slajdami)."""
    data = request.get_json(silent=True) or {}
    pres_id = data.get('id', '')
    # Zabezpieczenie przed wyjściem poza katalog prezentacji
    if not pres_id or '/' in pres_id or '\\' in pres_id or '..' in pres_id:
        return {'status': 'error', 'message': 'Nieprawidłowe id.'}
    target = os.path.join(app.static_folder, 'presentation', pres_id)
    if os.path.isdir(target):
        shutil.rmtree(target, ignore_errors=True)
    return {'status': 'ok'}
# --- HTTPS: lokalne CA + certyfikat serwera ---
# Model jak w mkcert: raz generujemy własne CA ("JafaStageCenter Local CA"),
# a certyfikat serwera jest nim PODPISANY. Telefon, na którym zainstaluje się
# i zaufa CA (jednorazowo, przez /mic_help → /ca.crt), widzi połączenie jako
# w pełni zaufane (kłódka, bez ostrzeżeń) — a wtedy iOS/Android na pewno
# pozwalają na mikrofon. Bez instalacji CA nadal działa ścieżka "zaakceptuj
# ostrzeżenie w Safari". Certyfikat serwera regenerujemy automatycznie, gdy
# zmieni się IP w sieci (inne Wi-Fi) albo zbliża się koniec ważności.
CA_CERT_FILE = os.path.join(DATA_DIR, 'jafa_ca.pem')
CA_KEY_FILE = os.path.join(DATA_DIR, 'jafa_ca_key.pem')
TLS_CERT_FILE = os.path.join(DATA_DIR, 'jafa_cert.pem')
TLS_KEY_FILE = os.path.join(DATA_DIR, 'jafa_key.pem')
CERT_META_FILE = os.path.join(DATA_DIR, 'jafa_cert_meta.json')

def _cert_is_current(ip):
    """True, gdy certyfikat serwera istnieje, obejmuje bieżące IP i nie wygasa
    w ciągu 30 dni. Metadane (IP, ważność) trzymamy w JSON obok certyfikatu,
    żeby nie parsować X.509 (cryptography może być niedostępne)."""
    try:
        needed = (TLS_CERT_FILE, TLS_KEY_FILE, CA_CERT_FILE, CA_KEY_FILE, CERT_META_FILE)
        if not all(os.path.exists(p) for p in needed):
            return False
        import datetime
        with open(CERT_META_FILE) as f:
            meta = json.load(f)
        expires = datetime.datetime.fromisoformat(meta.get('expires', '1970-01-01T00:00:00'))
        if expires - datetime.datetime.utcnow() < datetime.timedelta(days=30):
            return False
        return ip in meta.get('ips', [])
    except Exception:
        return False

def _san_ips(ip):
    ips = ['127.0.0.1']
    if ip and ip not in ips:
        ips.append(ip)
    return ips

# iOS odrzuca certyfikaty serwera ważne dłużej niż 825 dni.
LEAF_DAYS = 820

def _generate_certs_cryptography(ip):
    """Generuje CA (jeśli brak) i podpisany nim certyfikat serwera. Zwraca listę IP w SAN."""
    import datetime, ipaddress
    x509 = _crypto_x509
    now = datetime.datetime.utcnow()

    if os.path.exists(CA_CERT_FILE) and os.path.exists(CA_KEY_FILE):
        with open(CA_KEY_FILE, 'rb') as f:
            ca_key = _crypto_serialization.load_pem_private_key(f.read(), password=None)
        with open(CA_CERT_FILE, 'rb') as f:
            ca_cert = x509.load_pem_x509_certificate(f.read())
    else:
        ca_key = _crypto_rsa.generate_private_key(public_exponent=65537, key_size=2048)
        ca_name = x509.Name([x509.NameAttribute(_crypto_NameOID.COMMON_NAME, u'JafaStageCenter Local CA')])
        ca_cert = (x509.CertificateBuilder()
                   .subject_name(ca_name).issuer_name(ca_name)
                   .public_key(ca_key.public_key())
                   .serial_number(x509.random_serial_number())
                   .not_valid_before(now - datetime.timedelta(days=1))
                   .not_valid_after(now + datetime.timedelta(days=3650))
                   .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
                   .add_extension(x509.KeyUsage(digital_signature=False, content_commitment=False,
                                                key_encipherment=False, data_encipherment=False,
                                                key_agreement=False, key_cert_sign=True, crl_sign=True,
                                                encipher_only=False, decipher_only=False), critical=True)
                   .sign(ca_key, _crypto_hashes.SHA256()))
        with open(CA_KEY_FILE, 'wb') as f:
            f.write(ca_key.private_bytes(_crypto_serialization.Encoding.PEM,
                                         _crypto_serialization.PrivateFormat.TraditionalOpenSSL,
                                         _crypto_serialization.NoEncryption()))
        with open(CA_CERT_FILE, 'wb') as f:
            f.write(ca_cert.public_bytes(_crypto_serialization.Encoding.PEM))

    key = _crypto_rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ips = _san_ips(ip)
    sans = [x509.DNSName('localhost')] + [x509.IPAddress(ipaddress.ip_address(a)) for a in ips]
    cert = (x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(_crypto_NameOID.COMMON_NAME, u'JafaStageCenter')]))
            .issuer_name(ca_cert.subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=LEAF_DAYS))
            .add_extension(x509.SubjectAlternativeName(sans), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.ExtendedKeyUsage([_crypto_EKUOID.SERVER_AUTH]), critical=False)
            .sign(ca_key, _crypto_hashes.SHA256()))
    with open(TLS_KEY_FILE, 'wb') as f:
        f.write(key.private_bytes(_crypto_serialization.Encoding.PEM,
                                  _crypto_serialization.PrivateFormat.TraditionalOpenSSL,
                                  _crypto_serialization.NoEncryption()))
    # Pełny łańcuch (serwer + CA), żeby klient zawsze mógł go zweryfikować.
    with open(TLS_CERT_FILE, 'wb') as f:
        f.write(cert.public_bytes(_crypto_serialization.Encoding.PEM))
        f.write(ca_cert.public_bytes(_crypto_serialization.Encoding.PEM))
    return ips

def _generate_certs_openssl(ip, ossl):
    """To samo co wyżej, ale przez openssl CLI (fallback, gdy brak cryptography)."""
    if not (os.path.exists(CA_CERT_FILE) and os.path.exists(CA_KEY_FILE)):
        subprocess.run([ossl, 'req', '-x509', '-newkey', 'rsa:2048',
                        '-keyout', CA_KEY_FILE, '-out', CA_CERT_FILE, '-days', '3650', '-nodes',
                        '-subj', '/CN=JafaStageCenter Local CA',
                        '-addext', 'basicConstraints=critical,CA:TRUE,pathlen:0',
                        '-addext', 'keyUsage=critical,keyCertSign,cRLSign'],
                       check=True, timeout=60,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ips = _san_ips(ip)
    san = 'subjectAltName=DNS:localhost,' + ','.join('IP:' + a for a in ips)
    with tempfile.TemporaryDirectory() as tmp:
        csr = os.path.join(tmp, 'server.csr')
        ext = os.path.join(tmp, 'server.ext')
        with open(ext, 'w') as f:
            f.write(san + '\nbasicConstraints=critical,CA:FALSE\nextendedKeyUsage=serverAuth\n')
        subprocess.run([ossl, 'req', '-new', '-newkey', 'rsa:2048', '-nodes',
                        '-keyout', TLS_KEY_FILE, '-out', csr, '-subj', '/CN=JafaStageCenter'],
                       check=True, timeout=60,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([ossl, 'x509', '-req', '-in', csr, '-CA', CA_CERT_FILE, '-CAkey', CA_KEY_FILE,
                        '-CAcreateserial', '-days', str(LEAF_DAYS), '-out', TLS_CERT_FILE,
                        '-extfile', ext],
                       check=True, timeout=60,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with open(CA_CERT_FILE, 'rb') as f:
        ca_pem = f.read()
    with open(TLS_CERT_FILE, 'ab') as f:
        f.write(ca_pem)
    return ips

def ensure_https_cert():
    """Zwraca (cert_path, key_path). Dba o to, żeby certyfikat obejmował
    bieżące IP (regeneruje po zmianie sieci) i był podpisany lokalnym CA."""
    ip = get_local_ip()
    if _cert_is_current(ip):
        return TLS_CERT_FILE, TLS_KEY_FILE

    import datetime
    ips = None
    if HAS_CRYPTOGRAPHY:
        try:
            ips = _generate_certs_cryptography(ip)
        except BaseException as e:
            logging.warning(f"Certyfikat przez cryptography nie powiódł się ({e}); próbuję openssl.")
    if ips is None:
        ossl = shutil.which('openssl')
        if ossl:
            ips = _generate_certs_openssl(ip, ossl)
    if ips is None:
        raise RuntimeError('Brak cryptography i openssl — nie można wygenerować certyfikatu HTTPS.')

    meta = {'ips': ips,
            'expires': (datetime.datetime.utcnow() + datetime.timedelta(days=LEAF_DAYS)).isoformat()}
    with open(CERT_META_FILE, 'w') as f:
        json.dump(meta, f)
    return TLS_CERT_FILE, TLS_KEY_FILE

# Czy HTTPS FAKTYCZNIE działa (True dopiero po udanym certyfikacie).
HTTPS_ACTIVE = False

# ARCHITEKTURA DWUPORTOWA: główny serwer mówi ZAWSZE po HTTP na :5000 — każdy
# stary link, QR i zakładka działa bez względu na ustawienia (koniec z pustą,
# wiecznie ładującą się stroną po włączeniu HTTPS). HTTPS (potrzebny tylko do
# mikrofonu/stroika na telefonie) chodzi RÓWNOLEGLE na :5443 z tą samą apką.

# --- SERVER START THREAD ---
def start_server():
    global HTTPS_ACTIVE
    if HTTPS_ENABLED:
        try:
            ssl_ctx = ensure_https_cert()
            from werkzeug.serving import make_server
            https_srv = make_server('0.0.0.0', HTTPS_PORT, app, threaded=True, ssl_context=ssl_ctx)
            threading.Thread(target=https_srv.serve_forever, daemon=True).start()
            HTTPS_ACTIVE = True
            logging.info(f"HTTPS aktywny na porcie {HTTPS_PORT} — stroik na telefonie może użyć mikrofonu.")
        except Exception as e:
            HTTPS_ACTIVE = False
            logging.warning(f"Nie udało się włączyć HTTPS ({e}) — stroik na telefonie nie zadziała.")
    # Główny serwer — ZAWSZE zwykły HTTP na :5000.
    socketio.run(app, host='0.0.0.0', port=5000, use_reloader=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        check_db_schema()
        init_settings()

    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()

    # Przy starcie: jeśli synchronizacja włączona i jest sieć — dociągnij dane
    # z chmury (best-effort, w tle, nie blokuje uruchomienia; offline = cisza).
    def _startup_cloud_sync():
        try:
            with app.app_context():
                res = run_cloud_sync()
                if res.get('ok'):
                    logging.info('Cloud sync: %s', res.get('message'))
        except Exception as _e:
            logging.info('Cloud sync pominięty: %s', _e)
    threading.Thread(target=_startup_cloud_sync, daemon=True).start()

    # WAŻNE: Dodajemy js_api=JafaApi()
    api = JafaApi()
    
    # --- ZMIANA DLA LOADING SCREEN ---
    # 1. Ustalamy ścieżkę do pliku loading.html
    # Używamy resource_path, aby działało też po kompilacji do .exe
    loading_screen_path = resource_path(os.path.join('templates', 'loading.html'))
    
    # 2. Konwertujemy ścieżkę na format URL (file://). NIE dodajemy query stringa —
    #    na Windows psuje to adres file:// (ERR_FILE_NOT_FOUND). Okno desktopowe
    #    łączy się zawsze po http://127.0.0.1:5000 (HTTPS dla telefonów działa
    #    równolegle na :5443), więc nie potrzebuje żadnych wyjątków certyfikatów.
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
