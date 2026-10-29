# Aranżacje w panelu: forma (kafelki), obsada (role), komórki rola × kafelek
# z notatką i nagraniem z telefonu, historia zmian, odtwarzanie nagrań z prób.
# Edytować może każdy członek zespołu (decyzja zespołu) — dlatego jest
# historia z „Przywróć" zamiast blokad. Usuwanie wersji: prowadzący/admin.
import os
import secrets

from flask import (Blueprint, abort, current_app, flash, jsonify, redirect,
                   render_template, request, send_from_directory, session,
                   url_for)

from app import db
from app.auth.routes import current_user
from app.i18n import translate as _
from app.models import (Arrangement, ArrangementCell, ArrangementRevision,
                        Church, Profile, Song, User)
from app.panel.routes import require_membership
from app.arrangements import service as svc

arr_bp = Blueprint('arr', __name__)


def _song(church_id, song_id):
    song = Song.query.filter_by(id=song_id, church_id=church_id,
                                deleted=False).first()
    if not song:
        abort(404)
    return song


def _arr(church_id, arr_id):
    arr = Arrangement.query.filter_by(id=arr_id, church_id=church_id,
                                      deleted=False).first()
    if not arr:
        abort(404)
    return arr


def _my_profile(church_id):
    return Profile.query.filter_by(church_id=church_id,
                                   user_id=current_user().id,
                                   deleted=False).first()


def _names(church_id, user_ids):
    """user_id -> imię z profilu wspólnoty (fallback: nazwa konta)."""
    ids = {u for u in user_ids if u}
    if not ids:
        return {}
    out = {p.user_id: p.name for p in Profile.query.filter(
        Profile.church_id == church_id, Profile.user_id.in_(ids)).all()}
    for u in User.query.filter(User.id.in_(ids - set(out))).all():
        out[u.id] = u.display_name
    return out


def audio_url(arr, filename):
    return url_for('arr.audio', church_id=arr.church_id, arr_id=arr.id,
                   filename=filename)


def cells_payload(arr):
    cells = svc.cells_map(arr)
    names = _names(arr.church_id, [c.memo_by for c in cells.values()] +
                   [c.updated_by for c in cells.values()])
    return {f'{t}|{r}': {'note': c.note or '',
                         'riff': c.riff or None,
                         'memo': audio_url(arr, c.memo) if c.memo else '',
                         'memo_by': names.get(c.memo_by, ''),
                         'by': names.get(c.updated_by, ''),
                         'v': _cell_version(c)}
            for (t, r), c in cells.items()}


def _cell_version(c):
    return c.updated_at.isoformat() if c and c.updated_at else ''


def recordings_payload(arr):
    out = {'mix': '', 'loud': {}, 'minus': {}}
    for r in svc.recordings(arr):
        url = audio_url(arr, r.filename)
        if r.kind == 'mix':
            out['mix'] = url
        elif r.kind in ('loud', 'minus'):
            out[r.kind][r.role] = url
    return out


# ── strony ──────────────────────────────────────────────────────────────
@arr_bp.get('/c/<church_id>/songs/<song_id>/arrangement')
@require_membership('muzyk')
def song_main(church_id, song_id, membership):
    song = _song(church_id, song_id)
    arr = svc.ensure_main(song, current_user().id)
    return redirect(url_for('arr.edit', church_id=church_id, arr_id=arr.id))


@arr_bp.get('/c/<church_id>/arrangements/<arr_id>')
@require_membership('muzyk')
def edit(church_id, arr_id, membership):
    arr = _arr(church_id, arr_id)
    song = _song(church_id, arr.song_id)
    sections = [{'idx': i, 'label': s['label']}
                for i, s in enumerate(svc.song_sections(song))]
    revs = ArrangementRevision.query.filter_by(arrangement_id=arr.id) \
        .order_by(ArrangementRevision.id.desc()).limit(12).all()
    names = _names(church_id, [r.user_id for r in revs] + [arr.updated_by])
    history = [{'id': r.id, 'what': r.what, 'when': r.created_at,
                'who': names.get(r.user_id, '?'),
                'tiles': len((r.snapshot or {}).get('form') or []),
                'roles': len((r.snapshot or {}).get('roles') or [])}
               for r in revs]
    profile = _my_profile(church_id)
    return render_template(
        'arrangements/edit.html', song=song, arr=arr,
        arrangements=svc.song_arrangements(song), sections=sections,
        suggestions=svc.instrument_suggestions(church_id),
        cells=cells_payload(arr), rec=recordings_payload(arr),
        dynamics=svc.DYNAMICS, history=history,
        updated_by=names.get(arr.updated_by, ''),
        my_role=svc.my_role(arr, profile), rev=rev(arr),
        me_name=_names(church_id, [current_user().id]).get(current_user().id, ''),
        church=db.session.get(Church, church_id),
        membership=membership, user=current_user())


@arr_bp.post('/c/<church_id>/songs/<song_id>/arrangements')
@require_membership('muzyk')
def create(church_id, song_id, membership):
    song = _song(church_id, song_id)
    name = request.form.get('name', '')
    if svc.find_arrangement(song, name) and name.strip():
        flash(_('A version with this name already exists.'))
        return redirect(url_for('arr.song_main', church_id=church_id,
                                song_id=song_id))
    src = None
    if request.form.get('copy_from'):
        src = _arr(church_id, request.form['copy_from'])
    arr = svc.create_arrangement(song, name, current_user().id, copy_from=src)
    return redirect(url_for('arr.edit', church_id=church_id, arr_id=arr.id))


@arr_bp.post('/c/<church_id>/arrangements/<arr_id>/rename')
@require_membership('muzyk')
def rename(church_id, arr_id, membership):
    arr = _arr(church_id, arr_id)
    name = (request.form.get('name') or '').strip()[:svc.NAME_MAX_LEN]
    if name:
        song = _song(church_id, arr.song_id)
        other = svc.find_arrangement(song, name)
        if other and other.id != arr.id:
            flash(_('A version with this name already exists.'))
        else:
            arr.name = name
            db.session.commit()
    return redirect(url_for('arr.edit', church_id=church_id, arr_id=arr.id))


@arr_bp.post('/c/<church_id>/arrangements/<arr_id>/delete')
@require_membership('prowadzacy')
def delete(church_id, arr_id, membership):
    arr = _arr(church_id, arr_id)
    if arr.is_main:
        abort(400)
    song_id = arr.song_id
    svc.delete_arrangement(arr)
    db.session.commit()
    flash(_('Version deleted.'))
    return redirect(url_for('arr.song_main', church_id=church_id,
                            song_id=song_id))


# ── edycja (AJAX) ───────────────────────────────────────────────────────
def rev(arr):
    """Znacznik wersji formy/obsady. Zmienia się przy każdym zapisie."""
    return arr.updated_at.isoformat() if arr.updated_at else ''


def state_payload(arr):
    names = _names(arr.church_id, [arr.updated_by])
    return {'rev': rev(arr), 'form': arr.form or [], 'roles': arr.roles or [],
            'markers': arr.markers or {}, 'cells': cells_payload(arr),
            'updated_by': names.get(arr.updated_by, '')}


@arr_bp.get('/c/<church_id>/arrangements/<arr_id>/state')
@require_membership('muzyk')
def state(church_id, arr_id, membership):
    """Aktualny stan dla edytora otwartego u kilku osób naraz (odświeżanie)."""
    return jsonify(state_payload(_arr(church_id, arr_id)))


@arr_bp.post('/c/<church_id>/arrangements/<arr_id>/form')
@require_membership('muzyk')
def save_form(church_id, arr_id, membership):
    arr = _arr(church_id, arr_id)
    data = request.json or {}
    # Ktoś zapisał formę po tym, jak ta osoba ją wczytała — nie nadpisujemy
    # po cichu, tylko oddajemy aktualny stan do pokazania.
    if data.get('base') and data['base'] != rev(arr):
        return jsonify(dict(state_payload(arr), status='conflict')), 409
    song = _song(church_id, arr.song_id)
    form = svc.clean_form(data.get('form'), len(svc.song_sections(song)))
    svc.set_form(arr, form, current_user().id)
    db.session.commit()
    return jsonify({'status': 'ok', 'form': arr.form, 'rev': rev(arr)})


@arr_bp.post('/c/<church_id>/arrangements/<arr_id>/roles')
@require_membership('muzyk')
def save_roles(church_id, arr_id, membership):
    arr = _arr(church_id, arr_id)
    data = request.json or {}
    roles = list(arr.roles or [])
    if data.get('add'):
        base = svc.clean_roles([data['add']])
        if base:
            roles.append(svc.next_role_name(roles, base[0]))
    elif data.get('remove') is not None:
        roles = [r for r in roles if r != data['remove']]
    elif isinstance(data.get('roles'), list):
        # zmiana kolejności — tylko permutacja istniejących ról
        new = svc.clean_roles(data['roles'])
        if sorted(new) == sorted(roles):
            roles = new
    roles = svc.clean_roles(roles)
    if roles != (arr.roles or []):
        svc.set_roles(arr, roles, current_user().id)
        db.session.commit()
    return jsonify({'status': 'ok', 'roles': arr.roles or [], 'rev': rev(arr)})


def _cell(arr, tile, role, create=False):
    if tile not in {t['id'] for t in (arr.form or [])} or \
            role not in (arr.roles or []):
        abort(400)
    c = ArrangementCell.query.filter_by(arrangement_id=arr.id, tile_id=tile,
                                        role=role).first()
    if not c and create:
        c = ArrangementCell(arrangement_id=arr.id, tile_id=tile, role=role)
        db.session.add(c)
    return c


@arr_bp.post('/c/<church_id>/arrangements/<arr_id>/cell')
@require_membership('muzyk')
def save_cell(church_id, arr_id, membership):
    arr = _arr(church_id, arr_id)
    data = request.json or {}
    c = _cell(arr, str(data.get('tile')), str(data.get('role')), create=True)
    # Ktoś inny zmienił tę kratkę od chwili, gdy ta osoba ją otworzyła:
    # nie nadpisujemy, tylko oddajemy aktualną wersję do pokazania.
    base = data.get('base')
    if c.id and base is not None and base != _cell_version(c) \
            and c.updated_by != current_user().id:
        db.session.rollback()
        cur = cells_payload(arr).get(f"{c.tile_id}|{c.role}", {})
        return jsonify({'conflict': True, 'cell': cur}), 409
    # notatka i riff zapisują się osobno — brak pola = bez zmian
    if 'note' in data:
        c.note = str(data.get('note') or '')[:2000]
    if 'riff' in data:
        c.riff = svc.clean_riff(data.get('riff'))
    c.updated_by = current_user().id
    gone = not (c.note or '').strip() and not c.memo and not c.riff
    if gone:
        db.session.delete(c)
    db.session.commit()
    return jsonify({'status': 'ok', 'riff': None if gone else c.riff,
                    'v': '' if gone else _cell_version(c)})


@arr_bp.post('/c/<church_id>/arrangements/<arr_id>/memo')
@require_membership('muzyk')
def save_memo(church_id, arr_id, membership):
    arr = _arr(church_id, arr_id)
    c = _cell(arr, request.form.get('tile', ''), request.form.get('role', ''),
              create=True)
    f = request.files.get('audio')
    got = svc.read_audio(f, svc.MEMO_MAX_BYTES) if f else None
    if not got:
        db.session.rollback()
        return jsonify({'status': 'error',
                        'error': _('This is not an audio file, or it is too big (max 8 MB).')}), 400
    data, ext, mime = got
    old = c.memo
    c.memo = f'memo-{secrets.token_hex(6)}.{ext}'
    c.memo_mime = mime
    c.memo_by = c.updated_by = current_user().id
    with open(os.path.join(svc.arr_dir(arr), c.memo), 'wb') as out:
        out.write(data)
    svc._unlink(arr, old)
    db.session.commit()
    return jsonify({'status': 'ok', 'memo': audio_url(arr, c.memo),
                    'memo_by': _names(church_id, [c.memo_by]).get(c.memo_by, '')})


@arr_bp.post('/c/<church_id>/arrangements/<arr_id>/memo/delete')
@require_membership('muzyk')
def delete_memo(church_id, arr_id, membership):
    arr = _arr(church_id, arr_id)
    data = request.json or {}
    c = _cell(arr, str(data.get('tile')), str(data.get('role')))
    if c and c.memo:
        svc._unlink(arr, c.memo)
        c.memo = ''
        if not (c.note or '').strip() and not c.riff:
            db.session.delete(c)
        db.session.commit()
    return jsonify({'status': 'ok'})


@arr_bp.post('/c/<church_id>/arrangements/<arr_id>/restore/<int:rev_id>')
@require_membership('muzyk')
def restore(church_id, arr_id, rev_id, membership):
    arr = _arr(church_id, arr_id)
    rev = ArrangementRevision.query.filter_by(id=rev_id,
                                              arrangement_id=arr.id).first()
    if not rev:
        abort(404)
    song = _song(church_id, arr.song_id)
    snap = rev.snapshot or {}
    svc.set_form(arr, svc.clean_form(snap.get('form'),
                                     len(svc.song_sections(song))),
                 current_user().id, what='restore')
    arr.roles = svc.clean_roles(snap.get('roles'))
    db.session.commit()
    flash(_('Restored the earlier version of the form and cast.'))
    return redirect(url_for('arr.edit', church_id=church_id, arr_id=arr.id))


@arr_bp.post('/c/<church_id>/arrangements/<arr_id>/my-role')
@require_membership('muzyk')
def set_my_role(church_id, arr_id, membership):
    arr = _arr(church_id, arr_id)
    role = str((request.json or {}).get('role') or '')
    profile = _my_profile(church_id)
    if not profile or (role and role not in (arr.roles or [])):
        abort(400)
    svc.remember_role(arr, profile, role)
    db.session.commit()
    return jsonify({'status': 'ok', 'role': role})


# ── Reaper: token studia + skrypt (admin) ───────────────────────────────
@arr_bp.get('/c/<church_id>/reaper')
@require_membership('admin')
def reaper(church_id, membership):
    church = db.session.get(Church, church_id)
    s = church.settings or {}
    return render_template(
        'arrangements/reaper.html', church=church,
        has_token=bool(s.get('studio_token_hash')),
        created=s.get('studio_token_created', ''),
        used=s.get('studio_token_used', ''),
        new_token=session.pop('new_studio_token', None),
        server=request.host_url.rstrip('/'),
        membership=membership, user=current_user())


@arr_bp.post('/c/<church_id>/reaper/token')
@require_membership('admin')
def reaper_token(church_id, membership):
    church = db.session.get(Church, church_id)
    # Token pokazujemy jeden raz (w bazie jest tylko skrót) — przez sesję,
    # żeby nie wylądował w adresie URL ani w historii przeglądarki.
    session['new_studio_token'] = svc.new_studio_token(church)
    db.session.commit()
    return redirect(url_for('arr.reaper', church_id=church_id))


@arr_bp.post('/c/<church_id>/reaper/revoke')
@require_membership('admin')
def reaper_revoke(church_id, membership):
    church = db.session.get(Church, church_id)
    svc.revoke_studio_token(church)
    db.session.commit()
    flash(_('Studio token revoked. Reaper can no longer send recordings.'))
    return redirect(url_for('arr.reaper', church_id=church_id))


@arr_bp.get('/c/<church_id>/reaper/script')
@require_membership('admin')
def reaper_script(church_id, membership):
    root = os.path.join(current_app.root_path, '..', 'reaper')
    name = SCRIPTS.get(request.args.get('which', 'send'), SCRIPTS['send'])
    return send_from_directory(os.path.abspath(root), name, as_attachment=True)


SCRIPTS = {'send': 'Jonathan - send rehearsal.lua',
           'settings': 'Jonathan - settings.lua'}


# ── audio (tylko członkowie wspólnoty) ──────────────────────────────────
@arr_bp.get('/c/<church_id>/arrangements/<arr_id>/audio/<filename>')
@require_membership('muzyk')
def audio(church_id, arr_id, filename, membership):
    arr = _arr(church_id, arr_id)
    if '/' in filename or '\\' in filename or filename.startswith('.'):
        abort(404)
    d = svc.arr_dir(arr)
    if not os.path.exists(os.path.join(d, filename)):
        abort(404)
    # send_from_directory obsługuje Range — przewijanie w <audio> działa.
    resp = send_from_directory(d, filename, conditional=True)
    resp.headers['Cache-Control'] = 'private, max-age=3600'
    return resp
