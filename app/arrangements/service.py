# Aranżacje — logika wspólna dla panelu (routes.py) i API studia (api.py).
# Forma = lista kafelków, obsada = lista ról (instrumentów, nie osób).
import hashlib
import os
import re
import secrets
import unicodedata
from datetime import datetime

from flask import current_app

import music_core as mc
from app import db
from app.i18n import instrument_label, translate as _
from app.models import (Arrangement, ArrangementCell, ArrangementRecording,
                        ArrangementRevision, Church, Profile)

MAX_TILES = 60
MAX_ROLES = 24
MAX_REPEAT = 8
ROLE_MAX_LEN = 60
LABEL_MAX_LEN = 40
NAME_MAX_LEN = 80
MAX_REVISIONS = 30            # starsze rewizje czyścimy, żeby baza nie puchła
# Dynamika kafelka: klucz w bazie -> etykieta (EN źródło, PL w i18n)
DYNAMICS = {
    '': '',
    'soft': 'Soft',
    'build': 'Build',
    'full': 'Full',
    'down': 'Break down',
    'band': 'Band only',
}
MEMO_MAX_BYTES = 8 * 1024 * 1024          # notatka głosowa z telefonu
RECORDING_MAX_BYTES = 40 * 1024 * 1024    # jeden plik z Reapera
# Sygnatury audio: MP3 (ID3 / ramka), MP4/M4A (ftyp), WebM/Matroska, Ogg, WAV
AUDIO_TYPES = (
    (b'ID3', 'mp3', 'audio/mpeg'),
    (b'\xff\xfb', 'mp3', 'audio/mpeg'),
    (b'\xff\xf3', 'mp3', 'audio/mpeg'),
    (b'\xff\xf2', 'mp3', 'audio/mpeg'),
    (b'\x1aE\xdf\xa3', 'webm', 'audio/webm'),
    (b'OggS', 'ogg', 'audio/ogg'),
    (b'RIFF', 'wav', 'audio/wav'),
    (b'fLaC', 'flac', 'audio/flac'),
)


# ── pliki prywatne (poza /media, które jest publiczne dla ekranów) ──────
def private_dir(church_id, *parts):
    d = os.path.join(current_app.instance_path, 'private', church_id, *parts)
    os.makedirs(d, exist_ok=True)
    return d


def arr_dir(arr):
    return private_dir(arr.church_id, 'arrangements', arr.id)


def sniff_audio(data):
    """(ext, mime) albo None — rozpoznanie po zawartości, nie po nazwie."""
    if len(data) > 12 and data[4:8] == b'ftyp':
        return 'm4a', 'audio/mp4'
    for magic, ext, mime in AUDIO_TYPES:
        if data.startswith(magic):
            return ext, mime
    return None


def read_audio(f, limit):
    """Czyta upload z twardym limitem; zwraca (bytes, ext, mime) albo None."""
    data = f.read(limit + 1)
    if not data or len(data) > limit:
        return None
    kind = sniff_audio(data)
    if not kind:
        return None
    return (data,) + kind


# ── kafelki ─────────────────────────────────────────────────────────────
def new_tile_id():
    return secrets.token_hex(4)


def song_sections(song):
    return mc.parse_song_sections(song.content or '')


def default_form(song):
    return [{'id': new_tile_id(), 'sec': i, 'label': s['label'][:LABEL_MAX_LEN],
             'repeat': 1, 'dyn': ''} for i, s in enumerate(song_sections(song))]


def clean_form(raw, n_sections):
    """Walidacja formy z przeglądarki/Reapera. Nieznane pola odpadają."""
    out, seen = [], set()
    for t in (raw or [])[:MAX_TILES]:
        if not isinstance(t, dict):
            continue
        tid = str(t.get('id') or '')
        if not re.fullmatch(r'[0-9a-f]{8}', tid) or tid in seen:
            tid = new_tile_id()
        seen.add(tid)
        sec = t.get('sec')
        try:
            sec = int(sec) if sec is not None and sec != '' else None
        except (TypeError, ValueError):
            sec = None
        if sec is not None and not (0 <= sec < n_sections):
            sec = None
        label = str(t.get('label') or '').strip()[:LABEL_MAX_LEN]
        if not label:
            continue
        try:
            repeat = max(1, min(MAX_REPEAT, int(t.get('repeat') or 1)))
        except (TypeError, ValueError):
            repeat = 1
        dyn = t.get('dyn') if t.get('dyn') in DYNAMICS else ''
        out.append({'id': tid, 'sec': sec, 'label': label,
                    'repeat': repeat, 'dyn': dyn})
    return out


def clean_roles(raw):
    out, seen = [], set()
    for r in (raw or [])[:MAX_ROLES]:
        r = re.sub(r'\s+', ' ', str(r or '')).strip()[:ROLE_MAX_LEN]
        if r and r.lower() not in seen:
            seen.add(r.lower())
            out.append(r)
    return out


def tiles_with_content(arr, song, transpose=0):
    """Kafelki z wyrenderowanymi akordami (widok ćwiczenia)."""
    sections = song_sections(song)
    by_label = {}
    for i, s in enumerate(sections):
        by_label.setdefault(s['label'].lower(), i)
    out = []
    for t in arr.form or []:
        sec = t.get('sec')
        # Tekst piosenki mógł się zmienić — gdy indeks już nie pasuje do
        # etykiety, szukamy sekcji po nazwie.
        if sec is None or sec >= len(sections) or \
                sections[sec]['label'].lower() != t['label'].lower():
            sec = by_label.get(t['label'].lower(), sec)
        html = ''
        if sec is not None and 0 <= sec < len(sections):
            _p, html, _x = mc.process_song(sections[sec]['content'],
                                           transpose_amount=transpose)
        out.append(dict(t, band_html=html,
                        span=(arr.markers or {}).get(t['id'])))
    return out


# ── aranżacje ───────────────────────────────────────────────────────────
def song_arrangements(song):
    return Arrangement.query.filter_by(song_id=song.id, church_id=song.church_id,
                                       deleted=False) \
        .order_by(Arrangement.is_main.desc(), Arrangement.created_at).all()


def ensure_main(song, user_id=None):
    main = Arrangement.query.filter_by(song_id=song.id, church_id=song.church_id,
                                       is_main=True, deleted=False).first()
    if main:
        return main
    main = Arrangement(church_id=song.church_id, song_id=song.id,
                       name=_('Main'), is_main=True, form=default_form(song),
                       roles=[], created_by=user_id, updated_by=user_id)
    db.session.add(main)
    db.session.commit()
    return main


def create_arrangement(song, name, user_id, copy_from=None):
    name = (name or '').strip()[:NAME_MAX_LEN] or _('New version')
    base = copy_from or ensure_main(song, user_id)
    arr = Arrangement(church_id=song.church_id, song_id=song.id, name=name,
                      is_main=False, form=[dict(t) for t in (base.form or [])],
                      roles=list(base.roles or []),
                      created_by=user_id, updated_by=user_id)
    db.session.add(arr)
    db.session.commit()
    return arr


def find_arrangement(song, name):
    """Po nazwie (bez wielkości liter/ogonków). Puste = Główna."""
    if not (name or '').strip():
        return ensure_main(song)
    want = fold(name)
    for a in song_arrangements(song):
        if fold(a.name) == want:
            return a
    return None


def snapshot(arr, what, user_id):
    db.session.add(ArrangementRevision(
        arrangement_id=arr.id, what=what, user_id=user_id,
        snapshot={'form': list(arr.form or []), 'roles': list(arr.roles or [])}))
    db.session.flush()
    old = ArrangementRevision.query.filter_by(arrangement_id=arr.id) \
        .order_by(ArrangementRevision.id.desc()).offset(MAX_REVISIONS).all()
    for r in old:
        db.session.delete(r)


def set_form(arr, form, user_id, what='form'):
    snapshot(arr, what, user_id)
    arr.form = form
    arr.updated_by = user_id
    arr.updated_at = datetime.utcnow()
    # Markery z nagrania wskazują na kafelki — usunięty kafelek nie ma czasu.
    ids = {t['id'] for t in form}
    if arr.markers:
        arr.markers = {k: v for k, v in arr.markers.items() if k in ids}


def set_roles(arr, roles, user_id):
    snapshot(arr, 'roles', user_id)
    arr.roles = roles
    arr.updated_by = user_id
    arr.updated_at = datetime.utcnow()


def delete_arrangement(arr):
    arr.deleted = True
    remove_recordings(arr)
    for c in ArrangementCell.query.filter_by(arrangement_id=arr.id).all():
        _unlink(arr, c.memo)
        db.session.delete(c)


def _unlink(arr, filename):
    if not filename:
        return
    path = os.path.join(arr_dir(arr), filename)
    if os.path.exists(path):
        os.remove(path)


def remove_recordings(arr):
    for r in ArrangementRecording.query.filter_by(arrangement_id=arr.id).all():
        _unlink(arr, r.filename)
        db.session.delete(r)


def cells_map(arr):
    """{(tile_id, role): cell}"""
    return {(c.tile_id, c.role): c for c in
            ArrangementCell.query.filter_by(arrangement_id=arr.id).all()}


def recordings(arr):
    return ArrangementRecording.query.filter_by(arrangement_id=arr.id).all()


# ── obsada: podpowiedzi z instrumentów członków ─────────────────────────
def profile_instruments(profile):
    vals = list(profile.instruments or [])
    if not vals and profile.instrument:
        vals = [profile.instrument]
    return [v for v in vals if v and v != 'inny']


def instrument_suggestions(church_id):
    """Suma instrumentów wpisanych w profilach wspólnoty (etykiety w języku
    użytkownika), posortowana — lista do wyboru przy dodawaniu roli."""
    names = {}
    for p in Profile.query.filter_by(church_id=church_id, deleted=False).all():
        for v in profile_instruments(p):
            label = instrument_label(v)
            names.setdefault(fold(label), label)
    return sorted(names.values(), key=lambda s: s.lower())


def next_role_name(roles, base):
    """„Wokal" zajęty -> „Wokal 2", „Wokal 3"…"""
    taken = {fold(r) for r in roles}
    if fold(base) not in taken:
        return base
    n = 2
    while fold(f'{base} {n}') in taken:
        n += 1
    return f'{base} {n}'


def roles_for_profile(arr, profile):
    """Role tej aranżacji pasujące do instrumentów muzyka („Wokal 2" pasuje
    do instrumentu „wokal")."""
    if not profile:
        return []
    mine = {fold(instrument_label(v)) for v in profile_instruments(profile)} | \
        {fold(v) for v in profile_instruments(profile)}
    return [r for r in (arr.roles or [])
            if fold(re.sub(r'\s+\d+$', '', r)) in mine]


def my_role(arr, profile):
    """Zapamiętany wybór roli (prefs) albo pierwsza pasująca."""
    if not profile:
        return ''
    saved = ((profile.prefs or {}).get('arr_roles') or {}).get(arr.id)
    if saved and saved in (arr.roles or []):
        return saved
    match = roles_for_profile(arr, profile)
    return match[0] if match else ''


def remember_role(arr, profile, role):
    prefs = dict(profile.prefs or {})
    roles = dict(prefs.get('arr_roles') or {})
    roles[arr.id] = role
    prefs['arr_roles'] = roles
    profile.prefs = prefs


# ── dopasowanie nazw (markery i ślady z Reapera) ────────────────────────
def fold(s):
    s = str(s or '').replace('ł', 'l').replace('Ł', 'L')   # ł nie ma rozkładu NFKD
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore') \
        .decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


# Skróty i odpowiedniki nazw sekcji — wszystko sprowadzamy do jednego klucza.
SECTION_ALIASES = {
    'intro': ('intro', 'wstep'),
    'verse': ('verse', 'v', 'zwrotka', 'z', 'zw', 'strofa'),
    'chorus': ('chorus', 'ch', 'c', 'refren', 'r', 'ref'),
    'prechorus': ('pre chorus', 'prechorus', 'pre', 'pc', 'przedrefren'),
    'bridge': ('bridge', 'b', 'br', 'most', 'mostek'),
    'tag': ('tag',),
    'interlude': ('interlude', 'inter', 'przerywnik', 'interludium', 'solo'),
    'outro': ('outro', 'ending', 'end', 'zakonczenie', 'koniec', 'coda'),
}
_ALIAS = {a: k for k, vals in SECTION_ALIASES.items() for a in vals}


def section_key(label):
    """„Zwrotka 2" -> ('verse', '2'); „R" -> ('chorus', ''); „Pieśń" -> ('piesn','')."""
    f = fold(label)
    m = re.match(r'^(.*?)\s*(\d+)?$', f)
    base, num = (m.group(1) or '').strip(), (m.group(2) or '')
    if not base and num:
        base, num = num, ''
    return _ALIAS.get(base, base), num


def match_markers(form, markers):
    """Dopasowuje markery Reapera (po kolei) do kafelków formy.
    markers: [{'name', 'start', 'end'}] posortowane po czasie.
    Zwraca (spans {tile_id: [start, end]}, ok: bool) — ok = każdy marker
    znalazł swój kafelek w tej samej kolejności."""
    spans, ti = {}, 0
    for mk in markers:
        want = section_key(mk['name'])
        found = None
        while ti < len(form):
            got = section_key(form[ti]['label'])
            ti += 1
            if got[0] == want[0] and (not want[1] or not got[1]
                                      or got[1] == want[1]):
                found = form[ti - 1]
                break
        if not found:
            return spans, False
        spans[found['id']] = [round(mk['start'], 3), round(mk['end'], 3)]
    return spans, len(spans) == len(form)


def form_from_markers(song, markers, old_form=None):
    """Nowa forma wg markerów: etykiety z Reapera, sekcje dobrane po nazwie,
    id kafelków odzyskane z dotychczasowej formy (komórki nie przepadają)."""
    sections = song_sections(song)
    sec_by_key = {}
    for i, s in enumerate(sections):
        sec_by_key.setdefault(section_key(s['label']), i)
        sec_by_key.setdefault((section_key(s['label'])[0], ''), i)
    reuse = list(old_form or [])
    form, spans = [], {}
    for mk in markers:
        k = section_key(mk['name'])
        tile = None
        for j, t in enumerate(reuse):
            if section_key(t['label']) == k or (
                    section_key(t['label'])[0] == k[0] and not k[1]):
                tile = dict(reuse.pop(j))
                break
        if tile is None:
            tile = {'id': new_tile_id(), 'dyn': ''}
        # Każde powtórzenie to w Reaperze osobny marker — stare „×2"
        # odziedziczone po kafelku zawyżałoby formę.
        tile['repeat'] = 1
        tile['label'] = str(mk['name']).strip()[:LABEL_MAX_LEN] or tile.get('label', '?')
        tile['sec'] = sec_by_key.get(k, sec_by_key.get((k[0], '')))
        form.append(tile)
        spans[tile['id']] = [round(mk['start'], 3), round(mk['end'], 3)]
    return form, spans


def match_role(roles, track_name):
    """Nazwa śladu (bez „J:") -> rola obsady albo None."""
    want = fold(track_name)
    for r in roles:
        if fold(r) == want:
            return r
    return None


# ── token studia (jeden komputer z Reaperem na wspólnotę) ───────────────
TOKEN_PREFIX = 'jst_'


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def new_studio_token(church):
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    s = dict(church.settings or {})
    s['studio_token_hash'] = _hash(token)
    s['studio_token_created'] = datetime.utcnow().isoformat(timespec='seconds')
    s.pop('studio_token_used', None)
    church.settings = s
    return token


def revoke_studio_token(church):
    s = dict(church.settings or {})
    for k in ('studio_token_hash', 'studio_token_created', 'studio_token_used'):
        s.pop(k, None)
    church.settings = s


def church_for_token(token):
    """Kościół, do którego należy token studia (stałoczasowe porównanie)."""
    if not token or not token.startswith(TOKEN_PREFIX):
        return None
    h = _hash(token)
    for church in Church.query.all():
        stored = (church.settings or {}).get('studio_token_hash')
        if stored and secrets.compare_digest(stored, h):
            return church
    return None
