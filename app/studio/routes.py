# Studio — port panelu sterowania z aplikacji desktop (control.html) 1:1.
# Ten blueprint odtwarza KONTRAKT API desktopowego app.py pod prefiksem
# /c/<church_id>/studio, żeby control_logic.js działał bez zmian logiki.
# Desktop: jedna baza = jedna wspólnota; tu każda trasa jest zawężona do
# wspólnoty i wymaga członkostwa (panel: prowadzący/admin) albo tokenu ekranu.
import json
import os
import random
import re
import string
import uuid
from functools import wraps
from io import BytesIO

import qrcode
from flask import (Blueprint, Response, abort, current_app, redirect,
                   render_template, request, send_file, send_from_directory,
                   url_for)

from app import db, socketio
from app.auth.routes import current_user
from app.live import state as live_state
from app.models import (BandPreset, Church, Membership, Profile, ScreenToken,
                        Song, SongPersonal, StudioSetlist)
from app.i18n import translate as _
from music_core.chords import (apply_transpose_to_single_chord,
                               convert_chords_over_lyrics,
                               detect_key_algorithm,
                               get_first_chord_from_chorus,
                               get_first_chord_of_song,
                               normalize_chord_to_international,
                               normalize_song_chords_to_international,
                               process_song, transpose_chord)
from music_core import TRANSITION_ENGINES

studio_bp = Blueprint('studio', __name__, url_prefix='/c/<church_id>')

ROLES = {'muzyk': 0, 'prowadzacy': 1, 'admin': 2}


# ── autoryzacja ──────────────────────────────────────────────────────────
def _member(church_id, min_role='muzyk'):
    user = current_user()
    if not user:
        return None
    m = Membership.query.filter_by(user_id=user.id, church_id=church_id,
                                   status='active').first()
    if not m or ROLES.get(m.role, 0) < ROLES[min_role]:
        return None
    return m


def _screen_ok(church_id):
    token = request.args.get('token') or request.headers.get('X-Screen-Token')
    if not token:
        return False
    t = ScreenToken.query.filter_by(token=token, church_id=church_id,
                                    revoked_at=None).first()
    return t is not None


def studio_auth(min_role='prowadzacy', allow_screen=False, allow_member=False):
    """Autoryzacja endpointów Studia:
    - min_role (prowadzący/admin) zawsze przechodzi;
    - allow_member: pozwala też zwykłemu muzykowi (członkowi wspólnoty) — do
      obsługi własnego profilu w widoku muzyka (zapisy) i odczytów;
    - allow_screen: pozwala anonimowemu tokenowi ekranu (rzutnik/TV) — TYLKO do
      ODCZYTU. Token ekranu jest półpubliczny (QR/wydruk), więc nigdy nie może
      modyfikować danych."""
    def deco(fn):
        @wraps(fn)
        def wrapper(church_id, *a, **kw):
            if _member(church_id, min_role):
                return fn(church_id, *a, **kw)
            if allow_member and _member(church_id, 'muzyk'):
                return fn(church_id, *a, **kw)
            if allow_screen and _screen_ok(church_id):
                return fn(church_id, *a, **kw)
            abort(403)
        return wrapper
    return deco


# ── ustawienia wspólnoty (odpowiednik desktopowego Settings) ─────────────
SETTINGS_DEFAULTS = {
    'font_family': 'Sen', 'bg_color': '#000000', 'text_color': '#ffffff',
    'chord_color': '#00e5ff', 'transition_engine': 'v4', 'language': 'pl',
    'chord_notation': 'international', 'minor_display': 'uppercase',
    'ccli_license': '',   # numer licencji CCLI wspólnoty (rynek USA)
    'ccli_notice': '1',   # notka copyright na rzutniku: '1' wł. / '0' wył.
}


def get_settings(church):
    s = dict(SETTINGS_DEFAULTS)
    s.update(church.settings or {})
    return s


def save_settings(church, updates):
    s = dict(church.settings or {})
    s.update(updates)
    church.settings = s
    db.session.commit()


# ── media per wspólnota (logo, tło, prezentacje, pady) ───────────────────
def media_dir(church_id, *parts):
    d = os.path.join(current_app.instance_path, 'uploads', church_id, *parts)
    os.makedirs(d, exist_ok=True)
    return d


def media_url(church_id, filename=''):
    base = f'/c/{church_id}/media'
    return f'{base}/{filename}' if filename else base


# Limity uploadów (ochrona przed zapełnieniem dysku / plikami-bombami).
IMAGE_MAX_BYTES = 8 * 1024 * 1024          # logo / tło: 8 MB
IMAGE_MAGICS = (b'\x89PNG\r\n', b'\xff\xd8\xff', b'GIF8', b'RIFF')  # png/jpg/gif/webp


def _read_image(f):
    """Wczytuje obraz z twardym limitem rozmiaru i weryfikacją sygnatury.
    Zwraca bajty albo None (za duży / to nie jest obraz)."""
    data = f.read(IMAGE_MAX_BYTES + 1)
    if len(data) > IMAGE_MAX_BYTES:
        return None
    if not any(data.startswith(m) for m in IMAGE_MAGICS):
        return None
    return data


@studio_bp.get('/media/<path:filename>')
def media(church_id, filename):
    # Zasoby wyświetlane na ekranach (logo/tło/slajdy) — URL zawiera
    # nieodgadywalny UUID wspólnoty; bez sesji, bo <img> na rzutniku
    # nie ma ciasteczek panelu.
    root = os.path.join(current_app.instance_path, 'uploads', church_id)
    full = os.path.normpath(os.path.join(root, filename))
    if not full.startswith(os.path.normpath(root)):
        abort(404)
    if filename == 'logo.png' and not os.path.exists(full):
        return send_from_directory(current_app.static_folder, 'logo.png')
    if not os.path.exists(full):
        abort(404)
    return send_from_directory(root, filename)


# ── strona Studia ────────────────────────────────────────────────────────
@studio_bp.get('/studio')
@studio_auth('prowadzacy')
def control(church_id):
    church = db.session.get(Church, church_id)
    songs = Song.query.filter_by(church_id=church_id, deleted=False) \
        .order_by(Song.title).all()
    settings = get_settings(church)
    has_bg = os.path.exists(os.path.join(media_dir(church_id),
                                         'background.png'))
    # Tryb "układam setlistę dla grania": ?granie=<id> — Zapisz setlistę
    # podepnie ją pod to granie, a istniejąca wczyta się na start.
    event_ctx = None
    eid = request.args.get('granie', type=int)
    if eid:
        from app.models import Event
        ev = Event.query.filter_by(id=eid, church_id=church_id,
                                   deleted=False).first()
        if ev:
            event_ctx = {'id': ev.id, 'name': ev.name,
                         'date': ev.date.strftime('%d.%m.%Y'),
                         'setlist_id': ev.setlist_id}
    return render_template('studio/control.html', songs=songs,
                           settings=settings, has_bg=has_bg,
                           church=church, event_ctx=event_ctx,
                           base=f'/c/{church_id}/studio',
                           media=media_url(church_id),
                           server_ip=request.host)


# ── piosenki (kontrakt desktopu: form POST + redirect) ───────────────────
def _back(church_id):
    return redirect(url_for('studio.control', church_id=church_id))


def _redirect_back(church_id):
    """Jak _back, ale honoruje bezpieczne (lokalne) pole `next` — dzięki temu
    ten sam endpoint (logo/kolory/tło) obsługuje zarówno Studio, jak i stronę
    Ustawień wspólnoty, wracając tam, skąd przyszedł."""
    from urllib.parse import urlparse
    nxt = request.form.get('next') or request.args.get('next')
    if (nxt and nxt.startswith('/') and not nxt.startswith('//')
            and not urlparse(nxt).netloc):
        return redirect(nxt)
    return redirect(url_for('studio.control', church_id=church_id))


@studio_bp.post('/studio/add_song')
@studio_auth('prowadzacy')
def add_song(church_id):
    title = request.form.get('title')
    content = request.form.get('content')
    key = request.form.get('key') or ''
    bpm = request.form.get('bpm')
    input_notation = request.form.get('input_notation', 'international')
    if content:
        content = normalize_song_chords_to_international(
            content, input_notation=input_notation)
    if key:
        key = normalize_chord_to_international(key,
                                               input_notation=input_notation)
    if not key and content:
        key = detect_key_algorithm(content)
    if title and content:
        try:
            bpm_val = int(bpm) if bpm else 0
        except ValueError:
            bpm_val = 0
        ccli = (request.form.get('ccli_number') or '').strip()[:20]
        author = (request.form.get('author') or '').strip()[:300]
        copyright_ = (request.form.get('copyright') or '').strip()[:300]
        existing = Song.query.filter_by(church_id=church_id, title=title,
                                        deleted=False).first()
        if existing:
            existing.content, existing.key, existing.bpm = content, key, bpm_val
            existing.ccli_number, existing.author = ccli, author
            existing.copyright = copyright_
        else:
            db.session.add(Song(church_id=church_id, title=title,
                                content=content, key=key, bpm=bpm_val,
                                ccli_number=ccli, author=author,
                                copyright=copyright_,
                                created_by=current_user().id))
        db.session.commit()
    return _back(church_id)


@studio_bp.post('/studio/edit_song/<sid>')
@studio_auth('prowadzacy')
def edit_song(church_id, sid):
    song = Song.query.filter_by(id=sid, church_id=church_id).first_or_404()
    song.title = request.form.get('title')
    content = request.form.get('content')
    input_notation = request.form.get('input_notation', 'international')
    if content:
        content = normalize_song_chords_to_international(
            content, input_notation=input_notation)
    song.content = content
    key = request.form.get('key')
    if key:
        key = normalize_chord_to_international(key,
                                               input_notation=input_notation)
    song.key = key
    bpm = request.form.get('bpm')
    try:
        song.bpm = int(bpm) if bpm else 0
    except ValueError:
        song.bpm = 0
    song.ccli_number = (request.form.get('ccli_number') or '').strip()[:20]
    song.author = (request.form.get('author') or '').strip()[:300]
    song.copyright = (request.form.get('copyright') or '').strip()[:300]
    db.session.commit()
    return _back(church_id)


@studio_bp.post('/studio/delete_song/<sid>')
@studio_auth('prowadzacy')
def delete_song(church_id, sid):
    song = Song.query.filter_by(id=sid, church_id=church_id).first_or_404()
    song.deleted = True   # tombstone pod sync (PLAN §2)
    db.session.commit()
    return _back(church_id)


@studio_bp.post('/studio/delete_demo_song')
@studio_auth('prowadzacy')
def delete_demo_song(church_id):
    s = Song.query.filter_by(church_id=church_id, title='Jedyny Krol',
                             deleted=False).first()
    clean = re.sub(r'\[[^\]]*\]', '', s.content or '') if s else ''
    if s and 'Jedyny Krol, ktory przyjal postac slugi' in clean:
        s.deleted = True
        db.session.commit()
        return {'status': 'ok', 'deleted': s.id}
    return {'status': 'skip'}


@studio_bp.post('/studio/import_songs')
@studio_auth('prowadzacy')
def import_songs(church_id):
    files = request.files.getlist('import_files')
    input_notation = request.form.get('input_notation', 'international')

    def save_or_update(song_title, song_content, song_key='', song_bpm=0):
        song_content = normalize_song_chords_to_international(
            song_content, input_notation=input_notation)
        if song_key:
            song_key = normalize_chord_to_international(
                song_key, input_notation=input_notation)
        if not song_key:
            song_key = detect_key_algorithm(song_content)
        existing = Song.query.filter_by(church_id=church_id,
                                        title=song_title,
                                        deleted=False).first()
        if existing:
            existing.content, existing.key, existing.bpm = \
                song_content, song_key, song_bpm
        else:
            db.session.add(Song(church_id=church_id, title=song_title,
                                content=song_content, key=song_key,
                                bpm=song_bpm, created_by=current_user().id))

    def parse_header(raw):
        m = re.match(r'^(.*?)(?:\s*\(([^)]+)\))?(?:-\((\d+)\))?$', raw)
        if m:
            t = m.group(1).strip()
            k = m.group(2).strip() if m.group(2) else ''
            try:
                b = int(m.group(3)) if m.group(3) else 0
            except ValueError:
                b = 0
            return t, k, b
        return raw, '', 0

    for file in files:
        if not (file and file.filename.endswith('.txt')):
            continue
        raw_data = file.read()
        try:
            content = raw_data.decode('utf-8')
        except UnicodeDecodeError:
            content = raw_data.decode('cp1250', errors='ignore')
        content = content.replace('\r', '')
        if '---' in content:
            for chunk in content.split('---'):
                chunk = chunk.strip()
                if not chunk:
                    continue
                lines = chunk.splitlines()
                title, key, bpm = parse_header(lines[0].strip())
                body = '\n'.join(lines[1:]).strip()
                if title and body:
                    save_or_update(title, body, key, bpm)
        else:
            title, key, bpm = parse_header(
                os.path.splitext(file.filename)[0])
            if title and content.strip():
                save_or_update(title, content.strip(), key, bpm)
    db.session.commit()
    return _back(church_id)


@studio_bp.get('/studio/export_songs')
@studio_auth('prowadzacy')
def export_songs(church_id):
    songs = Song.query.filter_by(church_id=church_id, deleted=False) \
        .order_by(Song.title).all()
    lines = []
    for song in songs:
        header = song.title
        if song.key:
            header += f' ({song.key})'
        if song.bpm:
            header += f'-({song.bpm})'
        lines += [header, (song.content or '').strip(), '---']
    if lines and lines[-1] == '---':
        lines.pop()
    return Response('\n'.join(lines), mimetype='text/plain', headers={
        'Content-disposition': 'attachment; filename=baza_piosenek.txt'})


@studio_bp.post('/studio/convert_song_format')
@studio_auth('prowadzacy')
def convert_song_format(church_id):
    data = request.json or {}
    converted, changed = convert_chords_over_lyrics(data.get('text', ''))
    return {'text': converted, 'changed': changed}


@studio_bp.post('/studio/detect_key')
@studio_auth('prowadzacy')
def detect_key_route(church_id):
    data = request.json
    text = data.get('text', '')
    transpose = int(data.get('transpose', 0))
    if transpose != 0:
        text = re.sub(r'\[(.*?)\]',
                      lambda m: transpose_chord(m, transpose, 'international'),
                      text)
    detected = detect_key_algorithm(text)
    pad_note = detected.replace('m', '') if detected != 'N/A' else 'N/A'
    return {'key': detected, 'pad': pad_note}


# ── przejścia muzyczne ───────────────────────────────────────────────────
@studio_bp.post('/studio/generate_transition')
@studio_auth('prowadzacy')
def generate_transition(church_id):
    data = request.json
    id_start, id_end = data.get('id_start'), data.get('id_end')
    trans_start = int(data.get('transpose_start', 0))
    trans_end = int(data.get('transpose_end', 0))

    key_start = key_end = 'C'
    start_chord_raw = end_chord_raw = 'C'
    song_a = song_b = None
    bpm_a = bpm_b = 0

    if id_start:
        song_a = Song.query.filter_by(id=id_start,
                                      church_id=church_id).first()
        if song_a:
            key_start = song_a.key or 'C'
            first = get_first_chord_from_chorus(song_a.content)
            start_chord_raw = first or (get_first_chord_of_song(song_a.content)
                                        or key_start)
            bpm_a = song_a.bpm or 0
    if id_end:
        song_b = Song.query.filter_by(id=id_end, church_id=church_id).first()
        if song_b:
            key_end = song_b.key or 'C'
            end_chord_raw = get_first_chord_of_song(song_b.content) or key_end
            bpm_b = song_b.bpm or 0
    if not id_start:
        start_chord_raw = data.get('start_chord', 'C')
        key_start = data.get('key_start', 'C')
    if not id_end:
        end_chord_raw = data.get('end_chord', 'C')
        key_end = data.get('key_end', 'C')

    if (id_start and song_a and not get_first_chord_of_song(song_a.content)) \
            or (id_end and song_b
                and not get_first_chord_of_song(song_b.content)):
        return {'status': 'skip', 'reason': 'no_chords'}

    def wrap(c):
        return c if c.startswith('[') else f'[{c}]'

    real_start = apply_transpose_to_single_chord(wrap(start_chord_raw),
                                                 trans_start, 'international')
    real_end = apply_transpose_to_single_chord(wrap(end_chord_raw),
                                               trans_end, 'international')
    real_key_start = apply_transpose_to_single_chord(f'[{key_start}]',
                                                     trans_start,
                                                     'international')
    real_key_end = apply_transpose_to_single_chord(f'[{key_end}]',
                                                   trans_end, 'international')

    church = db.session.get(Church, church_id)
    engine_choice = get_settings(church)['transition_engine']
    if engine_choice not in TRANSITION_ENGINES:
        engine_choice = 'v4'   # v1 wycofany, stare 'v20' -> domyślny V4
    engine = TRANSITION_ENGINES[engine_choice]()

    if engine_choice == 'v4':
        # V4 dostaje pełny kontekst: treść obu piosenek i tempa — reszta
        # silników zna tylko 4 akordy
        chords = engine.generate_full_progression(
            real_start, real_key_start, real_end, real_key_end,
            song_a_content=song_a.content if song_a else None,
            song_b_content=song_b.content if song_b else None,
            shift_a=trans_start, shift_b=trans_end, bpm_a=bpm_a, bpm_b=bpm_b)
    else:
        chords = engine.generate_full_progression(
            real_start, real_key_start, real_end, real_key_end)
    return {'status': 'ok', 'transition': ' '.join(chords),
            'chords_list': chords, 'debug_start': real_start,
            'debug_end': real_end, 'engine_used': engine_choice}


# ── ustawienia ───────────────────────────────────────────────────────────
@studio_bp.post('/studio/update_settings')
@studio_auth('prowadzacy')
def update_settings(church_id):
    church = db.session.get(Church, church_id)
    updates = {k: request.form.get(k) for k in SETTINGS_DEFAULTS
               if request.form.get(k) is not None}
    save_settings(church, updates)
    s = get_settings(church)
    socketio.emit('apply_settings', {
        'font_family': s['font_family'], 'bg_color': s['bg_color'],
        'text_color': s['text_color'], 'chord_color': s['chord_color'],
        'lang': s['language'], 'chord_notation': s['chord_notation'],
        'minor_display': s['minor_display'],
    }, room=f'live:{church_id}')
    socketio.emit('settings_changed', room=f'live:{church_id}')
    return _redirect_back(church_id)


@studio_bp.post('/studio/reset_settings')
@studio_auth('prowadzacy')
def reset_settings(church_id):
    church = db.session.get(Church, church_id)
    save_settings(church, dict(SETTINGS_DEFAULTS))
    bg = os.path.join(media_dir(church_id), 'background.png')
    if os.path.exists(bg):
        os.remove(bg)
    socketio.emit('apply_settings',
                  {'font_family': 'Sen', 'bg_color': '#000000',
                   'text_color': '#ffffff'}, room=f'live:{church_id}')
    socketio.emit('refresh_background', {'has_bg': False},
                  room=f'live:{church_id}')
    return _redirect_back(church_id)


# ── media: logo / tło / prezentacje ──────────────────────────────────────
@studio_bp.post('/studio/upload_logo')
@studio_auth('prowadzacy')
def upload_logo(church_id):
    f = request.files.get('logo_file')
    if f and f.filename:
        data = _read_image(f)
        if not data:
            return {'status': 'error',
                    'message': _('Upload a PNG/JPG image up to 8 MB.')}, 400
        with open(os.path.join(media_dir(church_id), 'logo.png'), 'wb') as out:
            out.write(data)
        socketio.emit('refresh_logo', room=f'live:{church_id}')
    return _redirect_back(church_id)


@studio_bp.post('/studio/upload_background')
@studio_auth('prowadzacy')
def upload_background(church_id):
    f = request.files.get('bg_file')
    if f and f.filename:
        data = _read_image(f)
        if not data:
            return {'status': 'error',
                    'message': _('Upload a PNG/JPG image up to 8 MB.')}, 400
        with open(os.path.join(media_dir(church_id), 'background.png'), 'wb') as out:
            out.write(data)
        socketio.emit('refresh_background', {'has_bg': True},
                      room=f'live:{church_id}')
    return _redirect_back(church_id)


@studio_bp.post('/studio/delete_background')
@studio_auth('prowadzacy')
def delete_background(church_id):
    bg = os.path.join(media_dir(church_id), 'background.png')
    if os.path.exists(bg):
        os.remove(bg)
        socketio.emit('refresh_background', {'has_bg': False},
                      room=f'live:{church_id}')
    return _redirect_back(church_id)


# Prezentacje PDF są celowo dostępne TYLKO w aplikacji desktop — renderowanie
# PDF→PNG po stronie serwera zjadałoby miejsce i CPU. W wersji online do
# prezentacji służy Canva (embed, bez przechowywania plików).


@studio_bp.post('/studio/open_canva')
@studio_auth('prowadzacy')
def open_canva(church_id):
    # W desktopie otwierało okno przeglądarki na tym samym komputerze;
    # w wersji online JS panelu sam otwiera nową kartę z tym adresem.
    data = request.json or {}
    url = data.get('url', '')
    if url and '/edit' in url:
        url = url.replace('/edit', '/view')
    return {'status': 'ok', 'url': url}


# ── LIVE: stan i rozsyłanie (protokół desktopu, per wspólnota) ───────────
def _default_server_state():
    return {'setlist': [], 'current_index': -1, 'is_blackout': False}


@studio_bp.post('/studio/send_text')
@studio_auth('prowadzacy')
def send_text(church_id):
    data = request.json
    room = f'live:{church_id}'
    server_state = live_state.studio_get(church_id, 'server_state',
                                         _default_server_state())
    state_updated = False
    if 'current_index' in data:
        server_state['current_index'] = data.get('current_index')
        state_updated = True
    if 'setlist' in data:
        server_state['setlist'] = data.get('setlist')
        state_updated = True
    if state_updated:
        socketio.emit('sync_state_to_client', server_state, room=room)

    def set_slide(slide):
        from datetime import datetime
        live_state.studio_set(church_id, 'last_slide', slide)
        # Znacznik świeżości — dashboard uznaje LIVE tylko, gdy slajd jest świeży
        # (prowadzący, który zamknął przeglądarkę, nie zostaje "na żywo" na dobę).
        live_state.studio_set(church_id, 'last_slide_at',
                              datetime.utcnow().isoformat())
        socketio.emit('update_slide', slide, room=room)

    if data.get('logo') is True:
        server_state['is_blackout'] = False
        live_state.studio_set(church_id, 'server_state', server_state)
        set_slide({'mode': 'logo'})
        return {'status': 'ok'}
    if data.get('mode') in ['conference', 'canva', 'presentation']:
        data['is_blackout'] = bool(data.get('blackout',
                                            data.get('is_blackout', False)))
        server_state['is_blackout'] = data['is_blackout']
        live_state.studio_set(church_id, 'server_state', server_state)
        set_slide(data)
        return {'status': 'ok'}
    if data.get('mode') == 'note':
        # Spontaniczny tekst na ekran (bez akordów/CCLI) — np. „wyciszmy się".
        # Escapujemy i zamieniamy nowe linie na <br>, limit chroni ekran/pamięć.
        from markupsafe import escape
        raw = (data.get('text') or '')[:2000]
        is_blackout = bool(data.get('blackout', False))
        server_state['is_blackout'] = is_blackout
        live_state.studio_set(church_id, 'server_state', server_state)
        html = '<br>'.join(str(escape(ln)) for ln in raw.split('\n'))
        set_slide({'mode': 'note', 'html': html, 'text': raw,
                   'is_blackout': is_blackout})
        return {'status': 'ok'}
    if not data or 'text' not in data:
        if state_updated:
            live_state.studio_set(church_id, 'server_state', server_state)
            return {'status': 'ok'}
        return {'status': 'error', 'reason': 'missing text'}, 400

    raw_text = data.get('text', '')
    is_blackout = data.get('blackout', False)
    server_state['is_blackout'] = is_blackout
    live_state.studio_set(church_id, 'server_state', server_state)

    shift = int(data.get('transpose', 0))
    next_shift = int(data.get('next_transpose', shift))
    church = db.session.get(Church, church_id)
    s = get_settings(church)

    people_html, band_html, _ = process_song(raw_text, shift)
    _, band_next_html, _ = process_song(data.get('next_text', ''), next_shift)

    # CCLI: notka copyright na rzutniku + log uzycia (raz na dzien)
    copyright_line = ''
    title = (data.get('song_title') or '').strip()
    if title:
        song_row = Song.query.filter_by(church_id=church_id, title=title,
                                        deleted=False).first()
        if song_row:
            _log_song_usage(church_id, song_row.id)   # log zawsze (raport)
            if s.get('ccli_notice', '1') == '1':
                copyright_line = build_copyright_line(
                    song_row, s.get('ccli_license', ''))

    set_slide({
        'copyright_line': copyright_line,
        'mode': 'worship', 'people': people_html, 'band': band_html,
        'band_next': band_next_html, 'raw_text': raw_text,
        'raw_next': data.get('next_text', ''),
        'current_key': data.get('key', 'N/A'),
        'current_bpm': data.get('bpm', 0),
        'song_title': data.get('song_title', ''),
        'is_blackout': is_blackout, 'lang': s['language'],
        'notation': s['chord_notation'],
        'minor_display': s['minor_display'], 'transpose': shift,
    })
    return {'status': 'ok'}


@studio_bp.post('/studio/conf_timer')
@studio_auth('prowadzacy')
def conf_timer(church_id):
    data = request.json or {}
    timer_state = {'timer': data.get('timer', '00:00'),
                   'timer_color': data.get('timer_color', 'white'),
                   'message': data.get('message', '')}
    live_state.studio_set(church_id, 'conf_timer', timer_state)
    socketio.emit('timer_update', timer_state, room=f'live:{church_id}')
    return {'status': 'ok'}


@studio_bp.get('/studio/api/setlist')
@studio_auth('prowadzacy', allow_screen=True, allow_member=True)
def api_setlist(church_id):
    st = live_state.studio_get(church_id, 'server_state',
                               _default_server_state())
    return {'setlist': st['setlist'], 'current_index': st['current_index']}


@studio_bp.get('/studio/api/current-slide')
@studio_auth('prowadzacy', allow_screen=True, allow_member=True)
def api_current_slide(church_id):
    return live_state.studio_get(church_id, 'last_slide') or {'mode': 'none'}


# ── piosenka dla widoku zespołu ──────────────────────────────────────────
@studio_bp.get('/studio/api/song/<sid>/band')
@studio_auth('prowadzacy', allow_screen=True, allow_member=True)
def api_song_band(church_id, sid):
    song = Song.query.filter_by(id=sid, church_id=church_id,
                                deleted=False).first()
    if not song:
        return {'error': 'not found'}, 404
    raw = re.sub(r'(\n\s*){2,}\n', '\n\n', song.content or '')
    rendered = []
    for i, block in enumerate(re.split(r'\n\s*\n', raw)):
        block = block.strip()
        if not block:
            continue
        lines = block.split('\n')
        label, content = f'Sekcja {i + 1}', block
        if lines and '[' not in lines[0] and len(lines[0]) < 30:
            label = lines[0].strip()
            content = '\n'.join(lines[1:]).strip()
        _, band_html, _ = process_song(content)
        rendered.append({'band_html': band_html, 'raw_text': content,
                         'label': label})
    key = song.key or detect_key_algorithm(song.content)
    return {'id': song.id, 'title': song.title, 'key': key,
            'bpm': song.bpm or 0, 'sections': rendered}


# ── presety zespołu ──────────────────────────────────────────────────────
def _preset_json(p):
    return {'id': p.id, 'name': p.name, 'show_chords': p.show_chords,
            'nashville_mode': p.nashville_mode,
            'chord_notation': p.chord_notation
            or ('nashville' if p.nashville_mode else 'international'),
            'lowercase_minor': p.lowercase_minor or False,
            'capo_fret': p.capo_fret, 'beginner_mode': p.beginner_mode,
            'diagram_instrument': p.diagram_instrument,
            'font_size': p.font_size}


@studio_bp.get('/studio/api/presets')
@studio_auth('prowadzacy', allow_screen=True, allow_member=True)
def get_presets(church_id):
    return [_preset_json(p) for p in
            BandPreset.query.filter_by(church_id=church_id).all()]


@studio_bp.post('/studio/api/presets')
@studio_auth('prowadzacy', allow_member=True)
def save_preset(church_id):
    data = request.json
    if data.get('id'):
        p = BandPreset.query.filter_by(id=data['id'],
                                       church_id=church_id).first()
        if not p:
            return {'error': 'not found'}, 404
    else:
        p = BandPreset(church_id=church_id)
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


@studio_bp.delete('/studio/api/presets/<int:pid>')
@studio_auth('prowadzacy', allow_member=True)
def delete_preset(church_id, pid):
    p = BandPreset.query.filter_by(id=pid, church_id=church_id).first()
    if p:
        db.session.delete(p)
        db.session.commit()
    return {'status': 'ok'}


# ── profile muzyków (mapowane na Profile.prefs) ──────────────────────────
PROFILE_PREF_FIELDS = ['show_chords', 'chord_notation', 'lowercase_minor',
                       'capo_fret', 'beginner_mode', 'diagram_instrument',
                       'font_size', 'instrument_transpose', 'theme']
PROFILE_PREF_DEFAULTS = {'show_chords': True,
                         'chord_notation': 'international',
                         'lowercase_minor': False, 'capo_fret': 0,
                         'beginner_mode': False,
                         'diagram_instrument': 'guitar', 'font_size': 8,
                         'instrument_transpose': 0, 'theme': 'dark'}


def _profile_json(p):
    prefs = dict(PROFILE_PREF_DEFAULTS)
    prefs.update(p.prefs or {})
    out = {'id': p.id, 'name': p.name, 'instrument': p.instrument or '',
           'color': p.color or '#6366f1'}
    out.update({k: prefs[k] for k in PROFILE_PREF_FIELDS})
    return out


@studio_bp.get('/studio/api/profiles')
@studio_auth('prowadzacy', allow_screen=True, allow_member=True)
def get_profiles(church_id):
    return [_profile_json(p) for p in
            Profile.query.filter_by(church_id=church_id, deleted=False).all()]


@studio_bp.post('/studio/api/profiles')
@studio_auth('prowadzacy', allow_member=True)
def create_profile(church_id):
    data = request.json
    user = current_user()
    p = Profile(church_id=church_id, name=data.get('name', 'Muzyk'),
                instrument=data.get('instrument', ''),
                color=data.get('color', '#6366f1'),
                user_id=user.id if user else None,
                prefs=dict(PROFILE_PREF_DEFAULTS))
    db.session.add(p)
    db.session.commit()
    return {'id': p.id, 'name': p.name}


@studio_bp.get('/studio/api/profiles/<pid>')
@studio_auth('prowadzacy', allow_screen=True, allow_member=True)
def get_profile(church_id, pid):
    p = Profile.query.filter_by(id=pid, church_id=church_id,
                                deleted=False).first()
    if not p:
        return {'error': 'not found'}, 404
    return _profile_json(p)


@studio_bp.put('/studio/api/profiles/<pid>')
@studio_auth('prowadzacy', allow_member=True)
def update_profile(church_id, pid):
    p = Profile.query.filter_by(id=pid, church_id=church_id,
                                deleted=False).first()
    if not p:
        return {'error': 'not found'}, 404
    data = request.json
    for field in ['name', 'instrument', 'color']:
        if field in data:
            setattr(p, field, data[field])
    prefs = dict(PROFILE_PREF_DEFAULTS)
    prefs.update(p.prefs or {})
    for field in PROFILE_PREF_FIELDS:
        if field in data:
            if field in ('capo_fret', 'font_size', 'instrument_transpose'):
                prefs[field] = int(data[field])
            else:
                prefs[field] = data[field]
    p.prefs = prefs
    db.session.commit()
    return {'status': 'ok', 'id': p.id}


@studio_bp.delete('/studio/api/profiles/<pid>')
@studio_auth('prowadzacy', allow_member=True)
def delete_profile(church_id, pid):
    p = Profile.query.filter_by(id=pid, church_id=church_id).first()
    if p:
        SongPersonal.query.filter_by(profile_id=pid).delete()
        p.deleted = True
        db.session.commit()
    return {'status': 'ok'}


@studio_bp.get('/studio/api/profiles/<pid>/song/<sid>')
@studio_auth('prowadzacy', allow_screen=True, allow_member=True)
def get_song_settings(church_id, pid, sid):
    profile = Profile.query.filter_by(id=pid, church_id=church_id).first()
    if not profile:
        return {'error': 'not found'}, 404
    s = SongPersonal.query.filter_by(profile_id=pid, song_id=sid).first()
    if not s:
        return {'capo_fret': None, 'notes': {}}
    return {'capo_fret': s.capo_fret,
            'notes': json.loads(s.section_notes or '{}')}


@studio_bp.put('/studio/api/profiles/<pid>/song/<sid>')
@studio_auth('prowadzacy', allow_member=True)
def update_song_settings(church_id, pid, sid):
    profile = Profile.query.filter_by(id=pid, church_id=church_id).first()
    song = Song.query.filter_by(id=sid, church_id=church_id).first()
    if not profile or not song:
        return {'error': 'not found'}, 404
    data = request.json
    s = SongPersonal.query.filter_by(profile_id=pid, song_id=sid).first()
    if not s:
        s = SongPersonal(profile_id=pid, song_id=sid)
        db.session.add(s)
    if 'capo_fret' in data:
        s.capo_fret = data['capo_fret']
    if 'notes' in data:
        s.section_notes = json.dumps(data['notes'])
    db.session.commit()
    return {'status': 'ok'}


# ── historia setlist + udostępnianie ─────────────────────────────────────
@studio_bp.get('/studio/api/setlist-history')
@studio_auth('prowadzacy')
def get_setlist_history(church_id):
    items = StudioSetlist.query.filter_by(church_id=church_id) \
        .order_by(StudioSetlist.id.desc()).all()
    return [{'id': h.id, 'name': h.name, 'date': h.date,
             'songs': json.loads(h.songs),
             'song_count': len(json.loads(h.songs))} for h in items]


@studio_bp.post('/studio/api/setlist-history')
@studio_auth('prowadzacy')
def save_setlist_history(church_id):
    data = request.json
    h = StudioSetlist(church_id=church_id, name=data.get('name', ''),
                      date=data.get('date', ''),
                      songs=json.dumps(data.get('songs', [])))
    db.session.add(h)
    db.session.flush()
    # Zapis w trybie grania (?granie=): setlista od razu podpięta
    # pod wydarzenie — muzycy widzą ją w Graniu do ćwiczenia.
    event_id = data.get('event_id')
    attached = False
    if event_id:
        from app.models import Event
        ev = Event.query.filter_by(id=event_id, church_id=church_id,
                                   deleted=False).first()
        if ev:
            ev.setlist_id = h.id
            attached = True
    db.session.commit()
    return {'id': h.id, 'status': 'ok', 'attached_event': attached}


@studio_bp.get('/studio/api/setlist-history/<int:hid>')
@studio_auth('prowadzacy')
def get_setlist_history_item(church_id, hid):
    h = StudioSetlist.query.filter_by(id=hid, church_id=church_id).first()
    if not h:
        return {'error': 'not found'}, 404
    return {'id': h.id, 'name': h.name, 'date': h.date,
            'songs': json.loads(h.songs)}


@studio_bp.delete('/studio/api/setlist-history/<int:hid>')
@studio_auth('prowadzacy')
def delete_setlist_history(church_id, hid):
    h = StudioSetlist.query.filter_by(id=hid, church_id=church_id).first()
    if h:
        db.session.delete(h)
        db.session.commit()
    return {'status': 'ok'}


@studio_bp.post('/studio/api/setlist-share')
@studio_auth('prowadzacy')
def share_setlist(church_id):
    data = request.json
    code = ''.join(random.choices(string.ascii_uppercase + string.digits,
                                  k=6))
    while StudioSetlist.query.filter_by(share_code=code).first():
        code = ''.join(random.choices(string.ascii_uppercase + string.digits,
                                      k=6))
    h = StudioSetlist(church_id=church_id, name=data.get('name', ''),
                      date=data.get('date', ''),
                      songs=json.dumps(data.get('songs', [])),
                      share_code=code)
    db.session.add(h)
    db.session.commit()
    return {'code': code, 'id': h.id}


@studio_bp.get('/studio/api/setlist-share/<code>')
@studio_auth('prowadzacy')
def get_shared_setlist(church_id, code):
    h = StudioSetlist.query.filter_by(church_id=church_id,
                                      share_code=code.upper()).first()
    if not h:
        return {'error': 'not found'}, 404
    return {'id': h.id, 'name': h.name, 'date': h.date,
            'songs': json.loads(h.songs), 'code': h.share_code}


# ── druk ─────────────────────────────────────────────────────────────────
@studio_bp.post('/studio/print_setlist')
@studio_auth('prowadzacy')
def print_setlist(church_id):
    data = request.json
    songs_to_print = []
    for item in data:
        _, _, text_print = process_song(item['content'],
                                        int(item['transpose']))
        songs_to_print.append({'title': item['title'], 'html': text_print})
    return render_template('studio/print_view.html', songs=songs_to_print,
                           static_root='/static')


@studio_bp.post('/studio/print_lyrics')
@studio_auth('prowadzacy')
def print_lyrics(church_id):
    import html as html_mod
    data = request.json
    songs_to_print = []
    for item in data:
        raw = re.sub(r'\[.*?\]', '', item['content']).strip()
        blocks = []
        for p in re.split(r'\n\s*\n', raw):
            if p.strip():
                lines = html_mod.escape(p.strip(),
                                        quote=False).replace('\n', '<br>')
                blocks.append(f'<div class="lyrics-block">{lines}</div>')
        songs_to_print.append({'title': item['title'],
                               'html': ''.join(blocks)})
    return render_template('studio/print_lyrics.html', songs=songs_to_print,
                           static_root='/static')


# ── kody QR (adresy publiczne zamiast IP z sieci lokalnej) ───────────────
def _default_screen_url(church_id, screen_type):
    """Stały token 'domyślnego' ekranu danego typu — tworzony przy pierwszym
    użyciu QR, wielokrotnego użytku, odwoływalny w zakładce Ekrany."""
    import secrets
    t = ScreenToken.query.filter_by(church_id=church_id, type=screen_type,
                                    name='Studio QR',
                                    revoked_at=None).first()
    if not t:
        t = ScreenToken(church_id=church_id, type=screen_type,
                        name='Studio QR', token=secrets.token_urlsafe(32)[:43])
        db.session.add(t)
        db.session.commit()
    return url_for('live.screen', token=t.token, _external=True)


def screen_target_url(church_id, subpath):
    if subpath == 'control':
        return url_for('studio.control', church_id=church_id,
                       _external=True)
    if subpath == 'projector':
        return _default_screen_url(church_id, 'projector')
    if subpath == 'stage':
        return _default_screen_url(church_id, 'stage')
    if subpath == 'band_member':
        return _default_screen_url(church_id, 'band')
    return url_for('studio.control', church_id=church_id, _external=True)


def _qr_png(url, box_size=10, border=4):
    qr = qrcode.QRCode(version=None, box_size=box_size, border=border,
                       error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(url)
    qr.make(fit=True)
    img_io = BytesIO()
    try:
        qr.make_image(fill_color='black',
                      back_color='white').save(img_io, 'PNG')
        mimetype = 'image/png'
    except Exception:
        from qrcode.image.svg import SvgPathImage
        img_io = BytesIO()
        qr.make_image(image_factory=SvgPathImage).save(img_io)
        mimetype = 'image/svg+xml'
    img_io.seek(0)
    return send_file(img_io, mimetype=mimetype)


@studio_bp.get('/studio/qr_code/<path:subpath>')
@studio_auth('prowadzacy')
def qr_code(church_id, subpath):
    return _qr_png(screen_target_url(church_id, subpath))


@studio_bp.get('/studio/qr_setlist')
@studio_auth('prowadzacy')
def qr_setlist(church_id):
    data = request.args.get('data', '')
    if not data:
        return 'No data', 400
    return _qr_png(data, box_size=6, border=3)


@studio_bp.get('/studio/screen_url/<path:subpath>')
@studio_auth('prowadzacy')
def screen_url(church_id, subpath):
    return {'url': screen_target_url(church_id, subpath)}


@studio_bp.get('/studio/presenter')
@studio_auth('prowadzacy')
def presenter(church_id):
    """Widok mówcy (Presenter View) — port presenter.html z desktopu."""
    church = db.session.get(Church, church_id)
    return render_template('studio/presenter.html',
                           base=f'/c/{church_id}/studio',
                           media=media_url(church_id),
                           church_id=church_id, screen_token=None,
                           settings=get_settings(church))


# ── Pady atmosfery ───────────────────────────────────────────────────────
# Wspólny zestaw padów (jeden na całą platformę, wgrywany przez dewelopera na
# serwer) serwuje live.global_pad z /pads/<key>.mp3 — bez uploadu per-wspólnota,
# żeby dysk się nie zapełniał. Zob. app/live/routes.py.


@studio_bp.get('/studio/api/song/<sid>/team-prefs')
@studio_auth('prowadzacy')
def song_team_prefs(church_id, sid):
    """Preferowane tonacje zespołu dla piosenki — do układania setlisty
    ("Wiktoria (wokal) woli Dm" -> ustawiasz transpozycję pod wokal)."""
    song = Song.query.filter_by(id=sid, church_id=church_id,
                                deleted=False).first()
    if not song:
        return {'error': 'not found'}, 404
    rows = db.session.query(SongPersonal, Profile) \
        .join(Profile, Profile.id == SongPersonal.profile_id) \
        .filter(SongPersonal.song_id == sid,
                Profile.church_id == church_id,
                Profile.deleted.is_(False)) \
        .all()
    prefs = []
    for sp, prof in rows:
        if sp.preferred_key or sp.preferred_transpose:
            prefs.append({'name': prof.name,
                          'instrument': prof.instrument or '',
                          'key': sp.preferred_key or '',
                          'transpose': sp.preferred_transpose or 0})
    return {'song_key': song.key or '', 'prefs': prefs}


# ── CCLI: log użyć + raport (rynek USA) ──────────────────────────────────
def _log_song_usage(church_id, song_id):
    from datetime import date as _date

    from app.models import SongUsage
    today = _date.today()
    exists = SongUsage.query.filter_by(church_id=church_id, song_id=song_id,
                                       used_on=today).first()
    if not exists:
        db.session.add(SongUsage(church_id=church_id, song_id=song_id,
                                 used_on=today))
        db.session.commit()


def build_copyright_line(song, license_number):
    """Notka wymagana warunkami licencji CCLI przy projekcji tekstu:
    tytuł, autorzy, © właściciel praw, numer licencji WSPÓLNOTY."""
    parts = [f'"{song.title}"']
    if song.author:
        parts.append(f'words and music by {song.author}')
    if song.copyright:
        parts.append(f'© {song.copyright}')
    if not (song.author or song.copyright):
        return ''
    line = ', '.join(parts) + '. Used By Permission.'
    if license_number:
        line += f' CCLI License #{license_number}'
    return line


@studio_bp.get('/studio/ccli-report')
@studio_auth('prowadzacy')
def ccli_report(church_id):
    from datetime import date as _date, timedelta

    from app.models import SongUsage
    church = db.session.get(Church, church_id)
    try:
        d_to = _date.fromisoformat(request.args.get('to', ''))
    except ValueError:
        d_to = _date.today()
    try:
        d_from = _date.fromisoformat(request.args.get('from', ''))
    except ValueError:
        d_from = d_to - timedelta(days=182)   # domyślnie ~6 miesięcy

    rows = db.session.query(Song, db.func.count(SongUsage.id)) \
        .join(SongUsage, SongUsage.song_id == Song.id) \
        .filter(SongUsage.church_id == church_id,
                SongUsage.used_on >= d_from,
                SongUsage.used_on <= d_to) \
        .group_by(Song.id) \
        .order_by(db.func.count(SongUsage.id).desc()) \
        .all()
    items = [{'song': s, 'count': c} for s, c in rows]

    if request.args.get('format') == 'csv':
        import csv
        import io as _io
        buf = _io.StringIO()
        w = csv.writer(buf)
        w.writerow(['Song Title', 'CCLI Song Number', 'Author',
                    'Times Used'])
        for it in items:
            w.writerow([it['song'].title, it['song'].ccli_number or '',
                        it['song'].author or '', it['count']])
        return Response(
            buf.getvalue(), mimetype='text/csv',
            headers={'Content-disposition':
                     f'attachment; filename=ccli_report_{d_from}_{d_to}.csv'})

    from app.panel.routes import get_membership
    return render_template('studio/ccli_report.html', items=items,
                           d_from=d_from, d_to=d_to, church=church,
                           settings=get_settings(church),
                           membership=get_membership(church_id),
                           user=current_user())
