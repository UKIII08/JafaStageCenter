# API dla skryptu Reapera („Jonathan: wyślij próbę").
# Autoryzacja: jeden token studia na wspólnotę (Authorization: Bearer jst_…),
# generowany przez admina w Ustawieniach — tylko komputer, który go ma,
# może wysyłać nagrania. Całe dopasowanie (piosenka, wersja, kafelki, role)
# liczy serwer w /plan, a skrypt tylko pokazuje wynik i wysyła pliki.
import os
import secrets
from datetime import datetime
from functools import wraps

from flask import Blueprint, abort, g, jsonify, request

from app import db, limiter
from app.models import Arrangement, ArrangementRecording, Song
from app.arrangements import service as svc

studio_api_bp = Blueprint('studio_api', __name__, url_prefix='/api/studio')

MAX_REGIONS = 40
MAX_MARKERS = 60
MAX_TRACKS = 32


def token_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        auth = request.headers.get('Authorization', '')
        token = auth[7:].strip() if auth.lower().startswith('bearer ') else ''
        church = svc.church_for_token(token)
        if not church:
            return jsonify({'error': 'bad_token'}), 401
        g.church = church
        s = dict(church.settings or {})
        s['studio_token_used'] = datetime.utcnow().isoformat(timespec='seconds')
        church.settings = s
        db.session.commit()
        return fn(*a, **kw)
    return wrapper


def _songs():
    return Song.query.filter_by(church_id=g.church.id, deleted=False).all()


def _split_region(name):
    """„Oceany | Akustyczna" -> ('Oceany', 'Akustyczna')."""
    title, _sep, version = (name or '').partition('|')
    return title.strip(), version.strip()


def _find_song(title, songs):
    want = svc.fold(title)
    if not want:
        return None
    exact = [s for s in songs if svc.fold(s.title) == want]
    if exact:
        return exact[0]
    loose = [s for s in songs if svc.fold(s.title).startswith(want)
             or want.startswith(svc.fold(s.title))]
    return loose[0] if len(loose) == 1 else None


def _clean_markers(raw, region_len=None):
    out = []
    for m in (raw or [])[:MAX_MARKERS]:
        try:
            start, end = float(m.get('start')), float(m.get('end'))
        except (TypeError, ValueError, AttributeError):
            continue
        name = str(m.get('name') or '').strip()[:svc.LABEL_MAX_LEN]
        if name and 0 <= start < end:
            out.append({'name': name, 'start': start, 'end': end})
    return sorted(out, key=lambda m: m['start'])


def _clean_tracks(raw):
    return svc.clean_roles([str(t) for t in (raw or [])[:MAX_TRACKS]])


def _plan_region(region, songs):
    title, version = _split_region(region.get('name'))
    markers = _clean_markers(region.get('markers'))
    tracks = _clean_tracks(region.get('tracks'))
    out = {'region': region.get('name', ''), 'title': title,
           'version': version, 'ok': False}
    song = _find_song(title, songs)
    if not song:
        out['error'] = 'song_not_found'
        return out
    out['song_id'] = song.id
    out['song_title'] = song.title
    arr = svc.find_arrangement(song, version) if version else \
        Arrangement.query.filter_by(song_id=song.id, is_main=True,
                                    deleted=False).first()
    form = arr.form if arr else svc.default_form(song)
    roles = arr.roles if arr else []
    out['arrangement'] = arr.name if arr else (version or 'Main')
    out['arrangement_id'] = arr.id if arr else None
    out['create'] = arr is None
    spans, matched = svc.match_markers(form, markers)
    out['markers'] = len(markers)
    out['tiles'] = len(form)
    out['tiles_matched'] = len(spans)
    out['form_differs'] = bool(markers) and not matched
    out['tracks'] = [{'track': t, 'role': svc.match_role(roles, t)}
                     for t in tracks]
    out['missing_roles'] = [t['track'] for t in out['tracks'] if not t['role']]
    out['ok'] = True
    return out


@studio_api_bp.get('/ping')
@token_required
def ping():
    return jsonify({'church': g.church.name})


@studio_api_bp.get('/catalog')
@token_required
def catalog():
    songs = []
    for s in sorted(_songs(), key=lambda s: s.title.lower()):
        arrs = Arrangement.query.filter_by(song_id=s.id, deleted=False).all()
        songs.append({'id': s.id, 'title': s.title, 'arrangements': [
            {'id': a.id, 'name': a.name, 'is_main': bool(a.is_main),
             'tiles': [t['label'] for t in (a.form or [])],
             'roles': a.roles or []} for a in arrs]})
    return jsonify({'church': g.church.name, 'songs': songs})


@studio_api_bp.post('/plan')
@token_required
def plan():
    """Na sucho: co się stanie po wysłaniu (do okna potwierdzenia)."""
    regions = (request.json or {}).get('regions') or []
    songs = _songs()
    return jsonify({'church': g.church.name,
                    'regions': [_plan_region(r, songs)
                                for r in regions[:MAX_REGIONS]]})


@studio_api_bp.post('/commit')
@token_required
@limiter.limit('120/hour')
def commit():
    """Przygotowuje wersję pod nowe nagranie: tworzy ją w razie potrzeby,
    dopisuje brakujące role, ustawia formę/markery wg Reapera i kasuje stare
    pliki (nagranie się NADPISUJE). Pliki idą potem osobno do /file."""
    data = request.json or {}
    song = Song.query.filter_by(id=str(data.get('song_id')),
                                church_id=g.church.id, deleted=False).first()
    if not song:
        abort(404)
    version = str(data.get('version') or '').strip()
    arr = svc.find_arrangement(song, version) if version else svc.ensure_main(song)
    if not arr:
        arr = svc.create_arrangement(song, version, None)
    markers = _clean_markers(data.get('markers'))
    tracks = _clean_tracks(data.get('tracks'))

    roles = list(arr.roles or [])
    for t in tracks:
        if not svc.match_role(roles, t):
            roles.append(t)
    if roles != (arr.roles or []):
        svc.set_roles(arr, svc.clean_roles(roles), None)

    if markers:
        spans, matched = svc.match_markers(arr.form or [], markers)
        if not matched:
            # Nagranie to wersja „gotowa" — forma idzie za Reaperem.
            form, spans = svc.form_from_markers(song, markers, arr.form)
            svc.set_form(arr, form, None, what='reaper')
        arr.markers = spans
    else:
        arr.markers = {}
    try:
        arr.duration = max(0.0, float(data.get('duration') or 0)) or None
    except (TypeError, ValueError):
        arr.duration = None
    svc.remove_recordings(arr)
    arr.recorded_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'status': 'ok', 'arrangement_id': arr.id,
                    'arrangement': arr.name,
                    'roles': {t: svc.match_role(arr.roles or [], t)
                              for t in tracks}})


@studio_api_bp.post('/arrangements/<arr_id>/file')
@token_required
@limiter.limit('2000/hour')
def upload_file(arr_id):
    arr = Arrangement.query.filter_by(id=arr_id, church_id=g.church.id,
                                      deleted=False).first()
    if not arr:
        abort(404)
    kind = request.form.get('kind', '')
    role = request.form.get('role', '').strip()
    if kind not in ('mix', 'loud', 'minus'):
        abort(400)
    if kind == 'mix':
        role = ''
    elif role not in (arr.roles or []):
        abort(400)
    f = request.files.get('file')
    got = svc.read_audio(f, svc.RECORDING_MAX_BYTES) if f else None
    if not got:
        return jsonify({'error': 'bad_audio'}), 400
    blob, ext, _mime = got
    for old in ArrangementRecording.query.filter_by(
            arrangement_id=arr.id, kind=kind, role=role).all():
        svc._unlink(arr, old.filename)
        db.session.delete(old)
    name = f'{kind}-{secrets.token_hex(6)}.{ext}'
    with open(os.path.join(svc.arr_dir(arr), name), 'wb') as out:
        out.write(blob)
    db.session.add(ArrangementRecording(arrangement_id=arr.id, kind=kind,
                                        role=role, filename=name,
                                        size=len(blob)))
    db.session.commit()
    return jsonify({'status': 'ok'})
