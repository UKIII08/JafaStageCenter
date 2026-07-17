# Pokój LIVE (M2): sesja na żywo per wspólnota, panel prowadzącego,
# widok muzyka, ekrany tokenowe (rzutnik/TV). Sterowanie = REST (proste,
# testowalne), dystrybucja do urządzeń = Socket.IO (room per wspólnota).
import base64
import io
import secrets
from datetime import datetime

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, abort, jsonify)

import music_core as mc
from app import db, socketio
from app.auth.routes import current_user, login_required
from app.live import state as live_state
from app.models import (Church, Song, Setlist, LiveSession, ScreenToken,
                        Profile)
from app.panel.routes import require_membership, get_membership
from app.i18n import translate as _

live_bp = Blueprint('live', __name__)

# Konwencja z desktopu: 12 plików tonacją durową z krzyżykiem (C.mp3 … B.mp3).
PAD_KEYS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


@live_bp.get('/pads/<key>.mp3')
def global_pad(key):
    """Wspólne pady (jeden zestaw, który wgrywa deweloper na serwer) —
    nie per-wspólnota, żeby dysk się nie zapełniał uploadami. Trzymane na
    trwałym wolumenie uploads (instance/uploads/_shared/pads/), a jeśli tam
    nic nie ma, fallback do wersji dołączonej do repo (static/pads/)."""
    import os
    from flask import current_app, send_from_directory
    if key not in PAD_KEYS:
        abort(404)
    fname = f'{key}.mp3'
    shared = os.path.join(current_app.instance_path, 'uploads', '_shared',
                          'pads')
    if os.path.exists(os.path.join(shared, fname)):
        return send_from_directory(shared, fname)
    bundled = os.path.join(current_app.static_folder, 'pads')
    if os.path.exists(os.path.join(bundled, fname)):
        return send_from_directory(bundled, fname)
    abort(404)


def _qr_svg(data):
    import qrcode
    import qrcode.image.svg
    img = qrcode.make(data, image_factory=qrcode.image.svg.SvgPathImage)
    buf = io.BytesIO()
    img.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def _active_session(church_id):
    return LiveSession.query.filter_by(
        church_id=church_id, ended_at=None).first()


# Po tylu minutach od ostatniego slajdu przestajemy uznawać sesję za "na żywo"
# (prowadzący zwykle po prostu zamyka Studio, bez formalnego kończenia).
_LIVE_FRESH_MINUTES = 90


def _studio_is_live(church_id):
    """Czy w Studiu (port desktopu) trwa realne LIVE. Warunki (wszystkie):
    (1) ostatni slajd to realna treść (nie logo/pusto/blackout),
    (2) setlista nie jest pusta,
    (3) slajd jest świeży (< _LIVE_FRESH_MINUTES temu).
    Bez tego dashboard pokazywałby 'na żywo' bez końca (last_slide siedzi w
    Redisie godzinami), a po opróżnieniu setlisty wciąż 'trwa'."""
    last = live_state.studio_get(church_id, 'last_slide')
    if not last or last.get('mode') in (None, 'none', 'logo'):
        return False
    if last.get('is_blackout'):
        return False
    ss = live_state.studio_get(church_id, 'server_state') or {}
    if not ss.get('setlist'):
        return False
    at = live_state.studio_get(church_id, 'last_slide_at')
    if at:
        from datetime import datetime, timedelta
        try:
            when = datetime.fromisoformat(at)
            if datetime.utcnow() - when > timedelta(minutes=_LIVE_FRESH_MINUTES):
                return False
        except (ValueError, TypeError):
            pass
    return True


def _setlist_rows(church_id, sl):
    songs_by_id = {s.id: s for s in Song.query.filter_by(
        church_id=church_id, deleted=False).all()}
    rows = []
    for item in (sl.items or []):
        song = songs_by_id.get(item.get('song_id'))
        if song:
            rows.append({'song': song,
                         'transpose': int(item.get('transpose', 0)),
                         'sections': mc.parse_song_sections(song.content)})
    return rows


def _emit(church_id, event, payload):
    socketio.emit(event, payload, to=f'live:{church_id}')


def _render_slide(church_id, rows, song_idx, section_idx):
    row = rows[song_idx]
    section = row['sections'][section_idx]
    people, band, _ = mc.process_song(section['content'],
                                      transpose_amount=row['transpose'])
    key = row['song'].key
    if key and row['transpose']:
        key = mc.apply_transpose_to_single_chord(
            f'[{key}]', row['transpose']).strip('[]')
    # następna sekcja (dla ekranów zespołu)
    next_band = ''
    if section_idx + 1 < len(row['sections']):
        nxt = row['sections'][section_idx + 1]
        _, next_band, _ = mc.process_song(nxt['content'],
                                          transpose_amount=row['transpose'])
    elif song_idx + 1 < len(rows):
        nrow = rows[song_idx + 1]
        if nrow['sections']:
            _, next_band, _ = mc.process_song(
                nrow['sections'][0]['content'],
                transpose_amount=nrow['transpose'])
    return {
        'type': 'section',
        'song_idx': song_idx, 'section_idx': section_idx,
        'song_title': row['song'].title,
        'section_label': section['label'],
        'key': key, 'bpm': row['song'].bpm or 0,
        'people_html': people, 'band_html': band,
        'next_band_html': next_band,
        'blackout': False, 'logo': False,
    }


# ── Cykl życia sesji ──
@live_bp.post('/c/<church_id>/live/start/<setlist_id>')
@require_membership('prowadzacy')
def live_start(church_id, setlist_id, membership):
    if _active_session(church_id):
        flash(_('A live session is already running — joined it.'))
        return redirect(url_for('live.leader', church_id=church_id))
    sl = Setlist.query.filter_by(id=setlist_id, church_id=church_id,
                                 deleted=False).first()
    if not sl:
        abort(404)
    session_obj = LiveSession(church_id=church_id, setlist_id=sl.id,
                              started_by=current_user().id)
    db.session.add(session_obj)
    db.session.commit()
    live_state.set_state(church_id, {'type': 'idle', 'blackout': False,
                                     'logo': True,
                                     'setlist_id': sl.id})
    _emit(church_id, 'session_started', {'setlist': sl.name})
    return redirect(url_for('live.leader', church_id=church_id))


@live_bp.post('/c/<church_id>/live/end')
@require_membership('prowadzacy')
def live_end(church_id, membership):
    session_obj = _active_session(church_id)
    if session_obj:
        session_obj.ended_at = datetime.utcnow()
        db.session.commit()
    live_state.clear_state(church_id)
    _emit(church_id, 'session_ended', {})
    flash(_('Live session ended.'))
    return redirect(url_for('panel.church_home', church_id=church_id))


# ── Panel prowadzącego = Studio (port panelu desktop) ──
@live_bp.get('/c/<church_id>/live')
@require_membership('prowadzacy')
def leader(church_id, membership):
    return redirect(url_for('studio.control', church_id=church_id))


# ── Sterowanie slajdami (REST od prowadzącego) ──
@live_bp.post('/c/<church_id>/live/slide')
@require_membership('prowadzacy')
def slide(church_id, membership):
    session_obj = _active_session(church_id)
    if not session_obj:
        return jsonify({'error': 'no_session'}), 409
    sl = db.session.get(Setlist, session_obj.setlist_id)
    rows = _setlist_rows(church_id, sl)
    data = request.json or {}
    try:
        song_idx = int(data.get('song_idx'))
        section_idx = int(data.get('section_idx'))
        payload = _render_slide(church_id, rows, song_idx, section_idx)
    except (TypeError, ValueError, IndexError):
        return jsonify({'error': 'bad_index'}), 400
    live_state.set_state(church_id, payload)
    _emit(church_id, 'update_slide', payload)
    return jsonify({'status': 'ok'})


@live_bp.post('/c/<church_id>/live/transition')
@require_membership('prowadzacy')
def transition(church_id, membership):
    """Przejście akordowe między piosenką song_idx a song_idx+1."""
    session_obj = _active_session(church_id)
    if not session_obj:
        return jsonify({'error': 'no_session'}), 409
    sl = db.session.get(Setlist, session_obj.setlist_id)
    rows = _setlist_rows(church_id, sl)
    try:
        i = int((request.json or {}).get('song_idx'))
        row_a, row_b = rows[i], rows[i + 1]
    except (TypeError, ValueError, IndexError):
        return jsonify({'error': 'bad_index'}), 400
    a, b = row_a['song'], row_b['song']
    start = (mc.get_first_chord_from_chorus(a.content)
             or mc.get_first_chord_of_song(a.content) or a.key)
    end = mc.get_first_chord_of_song(b.content) or b.key
    if not start or not end:
        return jsonify({'error': 'no_chords'}), 409
    t_a, t_b = row_a['transpose'], row_b['transpose']
    start = mc.apply_transpose_to_single_chord(f'[{start}]', t_a)
    end = mc.apply_transpose_to_single_chord(f'[{end}]', t_b)
    key_a = mc.apply_transpose_to_single_chord(f'[{a.key or "C"}]', t_a)
    key_b = mc.apply_transpose_to_single_chord(f'[{b.key or "C"}]', t_b)
    church = db.session.get(Church, church_id)
    engine_key = (church.settings or {}).get('transition_engine', 'v4')
    engine_cls = mc.TRANSITION_ENGINES.get(engine_key,
                                           mc.TRANSITION_ENGINES['v4'])
    engine = engine_cls()
    if engine_key == 'v4':
        chords = engine.generate_full_progression(
            start, key_a, end, key_b,
            song_a_content=a.content, song_b_content=b.content,
            shift_a=t_a, shift_b=t_b, bpm_a=a.bpm or 0, bpm_b=b.bpm or 0)
    else:
        chords = engine.generate_full_progression(start, key_a, end, key_b)
    _, band, _ = mc.process_song(' '.join(chords))
    payload = {
        'type': 'transition', 'song_idx': i,
        'song_title': f'Przejście: {a.title} → {b.title}',
        'section_label': 'PRZEJŚCIE',
        'key': key_b.strip('[]'), 'bpm': b.bpm or 0,
        'people_html': '', 'band_html': band, 'next_band_html': '',
        'blackout': False, 'logo': False,
        'chords': ' '.join(chords),
    }
    live_state.set_state(church_id, payload)
    _emit(church_id, 'update_slide', payload)
    return jsonify({'status': 'ok', 'chords': chords})


@live_bp.post('/c/<church_id>/live/blackout')
@require_membership('prowadzacy')
def blackout(church_id, membership):
    st = live_state.get_state(church_id) or {'type': 'idle'}
    st['blackout'] = not st.get('blackout')
    st['logo'] = False
    live_state.set_state(church_id, st)
    _emit(church_id, 'update_slide', st)
    return jsonify({'blackout': st['blackout']})


@live_bp.post('/c/<church_id>/live/logo')
@require_membership('prowadzacy')
def logo(church_id, membership):
    st = live_state.get_state(church_id) or {'type': 'idle'}
    st['logo'] = not st.get('logo')
    st['blackout'] = False
    live_state.set_state(church_id, st)
    _emit(church_id, 'update_slide', st)
    return jsonify({'logo': st['logo']})


@live_bp.get('/api/live/current/<church_id>')
def api_current(church_id):
    """Snapshot stanu dla spóźnionych (muzyk po zalogowaniu / ekran po tokenie)."""
    token = request.args.get('token', '')
    if not get_membership(church_id):
        st_ok = ScreenToken.query.filter_by(
            church_id=church_id, token=token, revoked_at=None).first()
        if not st_ok:
            abort(403)
    active = (_active_session(church_id) is not None
              or _studio_is_live(church_id))
    return jsonify({'active': active,
                    'state': live_state.get_state(church_id)})


def _studio_screen_ctx(church_id, token=None):
    from app.studio.routes import get_settings, media_url
    church = db.session.get(Church, church_id)
    return {'base': f'/c/{church_id}/studio',
            'media': media_url(church_id),
            'church_id': church_id,
            'screen_token': token,
            'settings': get_settings(church)}


# ── Widok muzyka (port band_member.html z desktopu) ──
@live_bp.get('/c/<church_id>/live/band')
@require_membership('muzyk')
def band(church_id, membership):
    # Zalogowany członek nie wybiera profilu — wchodzi od razu w swój
    # (ten powiązany z kontem). Jeśli go brak (stare konto), tworzymy.
    user = current_user()
    profile = Profile.query.filter_by(
        church_id=church_id, user_id=user.id, deleted=False).first()
    if not profile:
        profile = Profile(church_id=church_id, user_id=user.id,
                          name=user.display_name)
        db.session.add(profile)
        db.session.commit()
    ctx = _studio_screen_ctx(church_id)
    ctx['my_profile_id'] = profile.id
    return render_template('studio/band_member.html', **ctx)


# ── Ekrany (rzutnik / TV sceny / telefon zespołu) ──
@live_bp.get('/screen/<token>')
def screen(token):
    st = ScreenToken.query.filter_by(token=token, revoked_at=None).first()
    if not st:
        abort(404)
    template = {'projector': 'studio/projector.html',
                'stage': 'studio/stage.html',
                'band': 'studio/band_member.html'}.get(
        st.type, 'studio/projector.html')
    return render_template(template,
                           **_studio_screen_ctx(st.church_id, token))


@live_bp.route('/c/<church_id>/screens', methods=['GET', 'POST'])
@require_membership('admin')
def screens(church_id, membership):
    if request.method == 'POST':
        stype = request.form.get('type')
        if stype not in ('projector', 'stage', 'band'):
            stype = 'projector'
        db.session.add(ScreenToken(
            church_id=church_id, token=secrets.token_urlsafe(24),
            type=stype, name=(request.form.get('name') or '').strip()[:120]))
        db.session.commit()
        return redirect(url_for('live.screens', church_id=church_id))
    tokens = ScreenToken.query.filter_by(church_id=church_id,
                                         revoked_at=None).all()
    items = [{'t': t, 'url': url_for('live.screen', token=t.token,
                                     _external=True)} for t in tokens]
    for it in items:
        it['qr'] = _qr_svg(it['url'])
    return render_template('live/screens.html', items=items,
                           church=db.session.get(Church, church_id),
                           membership=membership, user=current_user())


@live_bp.post('/c/<church_id>/screens/<int:sid>/revoke')
@require_membership('admin')
def screen_revoke(church_id, sid, membership):
    st = ScreenToken.query.filter_by(id=sid, church_id=church_id).first()
    if st:
        st.revoked_at = datetime.utcnow()
        db.session.commit()
    return redirect(url_for('live.screens', church_id=church_id))
