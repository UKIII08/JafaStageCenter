# Biblioteka piosenek + setlisty (M1). Cała logika muzyczna z music_core —
# ta sama co w aplikacji desktop (parytet zachowań gwarantują wspólne testy).
import re
from datetime import datetime

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, abort, jsonify)

import music_core as mc
from app import db
from app.auth.routes import current_user, login_required
from app.models import Church, Song, Setlist
from app.panel.routes import require_membership, NOTATIONS

songs_bp = Blueprint('songs', __name__)


def _get_song(church_id, song_id):
    song = Song.query.filter_by(id=song_id, church_id=church_id,
                                deleted=False).first()
    if not song:
        abort(404)
    return song


def _save_song_fields(song, form):
    song.title = (form.get('title') or '').strip()[:200]
    input_notation = form.get('input_notation', 'international')
    if input_notation not in NOTATIONS:
        input_notation = 'international'
    content = (form.get('content') or '').replace('\r', '')
    song.content = mc.normalize_song_chords_to_international(
        content, input_notation=input_notation)
    key = (form.get('key') or '').strip()
    if key:
        key = mc.normalize_chord_to_international(key,
                                                  input_notation=input_notation)
    if not key and song.content:
        key = mc.detect_key_algorithm(song.content)
    if key in ('N/A', '-'):
        key = ''
    song.key = key[:10]
    try:
        song.bpm = max(0, min(300, int(form.get('bpm') or 0)))
    except ValueError:
        song.bpm = 0


# ── Biblioteka ──
@songs_bp.get('/c/<church_id>/songs')
@require_membership('muzyk')
def songs_list(church_id, membership):
    q = (request.args.get('q') or '').strip()
    query = Song.query.filter_by(church_id=church_id, deleted=False)
    if q:
        query = query.filter(db.or_(Song.title.ilike(f'%{q}%'),
                                    Song.content.ilike(f'%{q}%')))
    songs = query.order_by(Song.title).all()
    return render_template('songs/list.html', songs=songs, q=q,
                           church=db.session.get(Church, church_id),
                           membership=membership, user=current_user())


@songs_bp.route('/c/<church_id>/songs/new', methods=['GET', 'POST'])
@require_membership('prowadzacy')
def song_new(church_id, membership):
    if request.method == 'POST':
        song = Song(church_id=church_id, created_by=current_user().id)
        _save_song_fields(song, request.form)
        if not song.title or not song.content.strip():
            flash('Tytuł i treść są wymagane.')
            return render_template('songs/form.html', song=song, is_new=True,
                                   church=db.session.get(Church, church_id),
                                   membership=membership, user=current_user())
        db.session.add(song)
        db.session.commit()
        flash(f'Dodano: {song.title}')
        return redirect(url_for('songs.song_view', church_id=church_id,
                                song_id=song.id))
    return render_template('songs/form.html', song=None, is_new=True,
                           church=db.session.get(Church, church_id),
                           membership=membership, user=current_user())


@songs_bp.get('/c/<church_id>/songs/<song_id>')
@require_membership('muzyk')
def song_view(church_id, song_id, membership):
    song = _get_song(church_id, song_id)
    try:
        transpose = int(request.args.get('t', 0))
    except ValueError:
        transpose = 0
    transpose = max(-11, min(11, transpose))
    _, band_html, _ = mc.process_song(song.content, transpose_amount=transpose)
    shown_key = (mc.apply_transpose_to_single_chord(f'[{song.key}]', transpose)
                 .strip('[]')) if song.key and transpose else song.key
    return render_template('songs/view.html', song=song, band_html=band_html,
                           transpose=transpose, shown_key=shown_key,
                           church=db.session.get(Church, church_id),
                           membership=membership, user=current_user())


@songs_bp.route('/c/<church_id>/songs/<song_id>/edit', methods=['GET', 'POST'])
@require_membership('prowadzacy')
def song_edit(church_id, song_id, membership):
    song = _get_song(church_id, song_id)
    if request.method == 'POST':
        _save_song_fields(song, request.form)
        db.session.commit()
        flash('Zapisano zmiany.')
        return redirect(url_for('songs.song_view', church_id=church_id,
                                song_id=song.id))
    return render_template('songs/form.html', song=song, is_new=False,
                           church=db.session.get(Church, church_id),
                           membership=membership, user=current_user())


@songs_bp.post('/c/<church_id>/songs/<song_id>/delete')
@require_membership('prowadzacy')
def song_delete(church_id, song_id, membership):
    song = _get_song(church_id, song_id)
    song.deleted = True   # tombstone (sync M5); twarde kasowanie po 30 dniach
    db.session.commit()
    flash(f'Usunięto: {song.title}')
    return redirect(url_for('songs.songs_list', church_id=church_id))


# ── Import .txt (format eksportu aplikacji desktop) ──
@songs_bp.post('/c/<church_id>/songs/import')
@require_membership('prowadzacy')
def songs_import(church_id, membership):
    files = request.files.getlist('files')
    added, skipped = [], []
    header_re = re.compile(r'^(.*?)(?:\s*\(([^)]+)\))?(?:-\((\d+)\))?$')
    for f in files:
        if not f or not f.filename.endswith('.txt'):
            continue
        try:
            content = f.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            f.seek(0)
            content = f.read().decode('cp1250', errors='ignore')
        content = content.replace('\r', '')
        chunks = content.split('---') if '---' in content else None
        if chunks is None:
            # jeden plik = jedna piosenka; tytuł z nazwy pliku
            raw = f.filename.rsplit('.', 1)[0]
            m = header_re.match(raw)
            chunks = [f"{raw}\n{content}"] if not m else [
                f"{m.group(0)}\n{content}"]
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            lines = chunk.splitlines()
            m = header_re.match(lines[0].strip())
            title = (m.group(1) if m else lines[0]).strip()[:200]
            key = (m.group(2) or '').strip() if m else ''
            if key and not mc.is_valid_chord(key):
                title, key = f'{title} ({key})'[:200], ''
            try:
                bpm = int(m.group(3)) if (m and m.group(3)) else 0
            except ValueError:
                bpm = 0
            body = '\n'.join(lines[1:]).strip()
            if not title or not body:
                continue
            if Song.query.filter_by(church_id=church_id, title=title,
                                    deleted=False).first():
                skipped.append(title)   # nie nadpisujemy po cichu
                continue
            body = mc.normalize_song_chords_to_international(body)
            if not key:
                key = mc.detect_key_algorithm(body)
            if key in ('N/A', '-'):
                key = ''
            db.session.add(Song(church_id=church_id, title=title,
                                content=body, key=key[:10], bpm=bpm,
                                created_by=current_user().id))
            added.append(title)
    db.session.commit()
    msg = f'Zaimportowano: {len(added)}.'
    if skipped:
        msg += f' Pominięto (tytuł już istnieje): {len(skipped)}.'
    flash(msg)
    return redirect(url_for('songs.songs_list', church_id=church_id))


# ── API pomocnicze edytora (walidacja na żywo, konwerter, tonacja) ──
@songs_bp.post('/api/songs/convert-format')
@login_required
def api_convert_format():
    text = (request.json or {}).get('text', '')
    converted, changed = mc.convert_chords_over_lyrics(text)
    return jsonify({'text': converted, 'changed': changed})


@songs_bp.post('/api/songs/analyze')
@login_required
def api_analyze():
    """Walidacja akordów + sugestia tonacji dla edytora (debounce w JS)."""
    text = (request.json or {}).get('text', '')
    tokens = re.findall(r'\[([^\[\]]{1,15})\]', text)
    bad = sorted({t for t in tokens if not mc.is_valid_chord(t)
                  and not re.match(r'^(x\d+|\d+x)$', t.strip(), re.I)})
    key = mc.detect_key_algorithm(text) if tokens else ''
    if key in ('N/A', '-'):
        key = ''
    return jsonify({'total': len(tokens), 'invalid': bad, 'key': key})


# ── Setlisty ──
@songs_bp.route('/c/<church_id>/setlists', methods=['GET', 'POST'])
@require_membership('muzyk')
def setlists(church_id, membership):
    if request.method == 'POST':
        if membership.role == 'muzyk':
            abort(403)
        name = (request.form.get('name') or '').strip()[:200]
        if not name:
            name = f'Nabożeństwo {datetime.utcnow():%d.%m.%Y}'
        sl = Setlist(church_id=church_id, name=name,
                     created_by=current_user().id)
        date_raw = request.form.get('service_date')
        if date_raw:
            try:
                sl.service_date = datetime.strptime(date_raw, '%Y-%m-%d').date()
            except ValueError:
                pass
        db.session.add(sl)
        db.session.commit()
        return redirect(url_for('songs.setlist_edit', church_id=church_id,
                                setlist_id=sl.id))
    items = Setlist.query.filter_by(church_id=church_id, deleted=False) \
        .order_by(Setlist.created_at.desc()).all()
    return render_template('songs/setlists.html', setlists=items,
                           church=db.session.get(Church, church_id),
                           membership=membership, user=current_user())


def _get_setlist(church_id, setlist_id):
    sl = Setlist.query.filter_by(id=setlist_id, church_id=church_id,
                                 deleted=False).first()
    if not sl:
        abort(404)
    return sl


@songs_bp.get('/c/<church_id>/setlists/<setlist_id>')
@require_membership('muzyk')
def setlist_edit(church_id, setlist_id, membership):
    sl = _get_setlist(church_id, setlist_id)
    songs_by_id = {s.id: s for s in Song.query.filter_by(
        church_id=church_id, deleted=False).all()}
    rows = []
    for item in (sl.items or []):
        song = songs_by_id.get(item.get('song_id'))
        if not song:
            continue
        t = int(item.get('transpose', 0))
        shown_key = song.key
        if song.key and t:
            shown_key = mc.apply_transpose_to_single_chord(
                f'[{song.key}]', t).strip('[]')
        rows.append({'song': song, 'transpose': t, 'shown_key': shown_key})
    available = sorted(songs_by_id.values(), key=lambda s: s.title.lower())
    return render_template('songs/setlist_edit.html', sl=sl, rows=rows,
                           available=available,
                           church=db.session.get(Church, church_id),
                           membership=membership, user=current_user())


@songs_bp.post('/c/<church_id>/setlists/<setlist_id>/items')
@require_membership('prowadzacy')
def setlist_items(church_id, setlist_id, membership):
    """Jedna akcja modyfikująca pozycje: add / remove / move / transpose."""
    sl = _get_setlist(church_id, setlist_id)
    # głęboka kopia: mutacja słowników w miejscu aliasowałaby snapshot
    # SQLAlchemy i zmiana nigdy nie trafiłaby do bazy (JSON column trap)
    items = [dict(i) for i in (sl.items or [])]
    action = request.form.get('action')
    if action == 'add':
        song = _get_song(church_id, request.form.get('song_id', ''))
        items.append({'song_id': song.id, 'transpose': 0})
    else:
        try:
            idx = int(request.form.get('idx', -1))
        except ValueError:
            idx = -1
        if not (0 <= idx < len(items)):
            abort(400)
        if action == 'remove':
            items.pop(idx)
        elif action == 'up' and idx > 0:
            items[idx-1], items[idx] = items[idx], items[idx-1]
        elif action == 'down' and idx < len(items) - 1:
            items[idx+1], items[idx] = items[idx], items[idx+1]
        elif action in ('t_up', 't_down'):
            delta = 1 if action == 't_up' else -1
            t = int(items[idx].get('transpose', 0)) + delta
            items[idx]['transpose'] = max(-11, min(11, t))
    sl.items = items
    db.session.commit()
    return redirect(url_for('songs.setlist_edit', church_id=church_id,
                            setlist_id=setlist_id))


@songs_bp.post('/c/<church_id>/setlists/<setlist_id>/delete')
@require_membership('prowadzacy')
def setlist_delete(church_id, setlist_id, membership):
    sl = _get_setlist(church_id, setlist_id)
    sl.deleted = True
    db.session.commit()
    return redirect(url_for('songs.setlists', church_id=church_id))


@songs_bp.post('/c/<church_id>/setlists/<setlist_id>/duplicate')
@require_membership('prowadzacy')
def setlist_duplicate(church_id, setlist_id, membership):
    src = _get_setlist(church_id, setlist_id)
    copy = Setlist(church_id=church_id, name=f'{src.name} (kopia)'[:200],
                   items=list(src.items or []), created_by=current_user().id)
    db.session.add(copy)
    db.session.commit()
    return redirect(url_for('songs.setlist_edit', church_id=church_id,
                            setlist_id=copy.id))
