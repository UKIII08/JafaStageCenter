# Biblioteka piosenek + setlisty (M1). Cała logika muzyczna z music_core —
# ta sama co w aplikacji desktop (parytet zachowań gwarantują wspólne testy).
import json
import re
from datetime import datetime

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, abort, jsonify)

import music_core as mc
from app import db
from app.auth.routes import current_user, login_required
from app.models import Church, Song, Setlist, Profile, SongPersonal
from app.panel.routes import require_membership, NOTATIONS
from app.i18n import translate as _

songs_bp = Blueprint('songs', __name__)

# Limity importu .txt — piosenka to zwykły tekst (kilka KB), więc trzymamy je
# ciasno, żeby jeden śmieciowy plik nie zapchał bazy/dysku serwera.
IMPORT_MAX_FILES = 200          # ile plików naraz przyjmiemy w jednym imporcie
IMPORT_MAX_BYTES = 512 * 1024   # 512 KB na plik (nawet długi zbiór pieśni)
SONG_MAX_CHARS = 20000          # górny limit długości treści pojedynczej pieśni
# Przyjmowane rozszerzenia: .txt (eksport desktop) + formaty ChordPro
# (m.in. pobrania z CCLI SongSelect, OnSong, OpenSong).
IMPORT_EXTS = ('.txt', '.cho', '.pro', '.chopro', '.chordpro', '.crd', '.onsong')

# Separator między piosenkami w zbiorczym pliku .txt: CAŁA linia złożona z
# 3+ znaków „myślnika". Akceptujemy warianty, które ludzie realnie wstawiają:
# ASCII (---), podkreślenie (___), półpauzę (–), pauzę (—), myślnik poziomy (―)
# itd. Dawniej dzieliliśmy tylko po dokładnym „---", więc plik z „———" trafiał
# w całości jako jedna piosenka.
SONG_SEPARATOR_RE = re.compile(r'(?m)^[ \t]*[-_‐-―]{3,}[ \t]*$')


def _get_song(church_id, song_id):
    song = Song.query.filter_by(id=song_id, church_id=church_id,
                                deleted=False).first()
    if not song:
        abort(404)
    return song


def _clean_link(raw):
    """Zwraca bezpieczny URL (http/https) albo ''. Chroni przed javascript:/data:
    w atrybucie href. Sam URL nie może zawierać znaków białych."""
    url = (raw or '').strip()
    if not url:
        return ''
    if url.lower().startswith(('javascript:', 'data:', 'vbscript:', 'file:')):
        return ''                       # niebezpieczne schematy — odrzuć
    if not re.match(r'^https?://', url, re.I):
        url = 'https://' + url          # użytkownik wkleił bez schematu
    if re.match(r'^https?://\S+$', url, re.I):
        return url[:500]
    return ''


ISSUE_TEXT = {
    'unclosed': 'Line %(line)s: bracket “[” is never closed — add “]” after the chord.',
    'bad_key': 'The key “%(key)s” is not a chord — use e.g. G, Em, F#, Bb.',
}


def _save_song_fields(song, form):
    """Wypełnia piosenkę z formularza. Zwraca (błędy, uwagi): przy błędach
    nic nie jest zapisywane, a formularz wraca z treścią użytkownika."""
    errors, notes = [], []
    song.title = (form.get('title') or '').strip()[:200]
    song.link = _clean_link(form.get('link'))
    input_notation = form.get('input_notation', 'international')
    if input_notation not in NOTATIONS:
        input_notation = 'international'
    content = (form.get('content') or '').replace('\r', '')
    # Błędy liczymy na tekście DOKŁADNIE takim, jak w edytorze — numery linii
    # muszą się zgadzać z tym, co widzi użytkownik (przeróbki niżej je zmieniają).
    report = mc.analyze_song(content, input_notation)
    for issue in report['issues']:
        if issue['kind'] == 'unclosed':
            errors.append(_(ISSUE_TEXT['unclosed']) % {'line': issue['line']})
    # Ta sama ścieżka co Studio i import: ChordPro, akordy nad tekstem,
    # porządki, notacja międzynarodowa.
    prep = mc.prepare_song(content, input_notation)
    changes, meta = prep['changes'], prep['meta']
    if 'chordpro' in changes:
        notes.append(_('Pasted ChordPro was converted — check the result.'))
    if 'above_lyrics' in changes:
        notes.append(_('Chords written above the lyrics were moved into the text — check the result.'))
    if 'labels' in changes:
        notes.append(_('Section names in brackets, like [Chorus], are now plain labels.'))
    song.content = prep['content']
    # ChordPro niesie tytuł/tonację/tempo — uzupełniamy tylko puste pola
    if not song.title and meta.get('title'):
        song.title = meta['title'][:200]
    form_key = form.get('key') or meta.get('key') or ''
    key = mc.canon_chord(form_key)
    if key and not mc.is_valid_chord(key):
        errors.append(_(ISSUE_TEXT['bad_key']) % {'key': key})
        key = ''
    if key:
        key = mc.normalize_chord_to_international(key,
                                                  input_notation=input_notation)
    if not key and song.content:
        key = mc.detect_key_algorithm(song.content)
    if key in ('N/A', '-'):
        key = ''
    song.key = key[:10]
    try:
        song.bpm = max(0, min(300, int(form.get('bpm') or meta.get('bpm') or 0)))
    except ValueError:
        song.bpm = 0
    return errors, notes


def _form_again(song, is_new, church_id, membership, errors):
    """Formularz z powrotem — z tym, co użytkownik wpisał, i listą błędów."""
    return render_template('songs/form.html', song=song, is_new=is_new,
                           errors=errors,
                           draft=request.form,
                           church=db.session.get(Church, church_id),
                           membership=membership, user=current_user())


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
@require_membership('muzyk')   # każdy muzyk (i prowadzący) może dodawać piosenki
def song_new(church_id, membership):
    if request.method == 'POST':
        song = Song(church_id=church_id, created_by=current_user().id)
        errors, notes = _save_song_fields(song, request.form)
        if not song.title or not song.content.strip():
            errors.insert(0, _('Title and content are required.'))
        if errors:
            return _form_again(song, True, church_id, membership, errors)
        db.session.add(song)
        db.session.commit()
        flash(_('Added:') + ' ' + song.title)
        for n in notes:
            flash(n)
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
    profile = _my_profile(church_id)
    return render_template('songs/view.html', song=song, band_html=band_html,
                           transpose=transpose, shown_key=shown_key,
                           prefs=(profile.prefs if profile else {}) or {},
                           church=db.session.get(Church, church_id),
                           membership=membership, user=current_user())


@songs_bp.route('/c/<church_id>/songs/<song_id>/edit', methods=['GET', 'POST'])
@require_membership('prowadzacy')
def song_edit(church_id, song_id, membership):
    song = _get_song(church_id, song_id)
    if request.method == 'POST':
        errors, notes = _save_song_fields(song, request.form)
        if not song.title or not song.content.strip():
            errors.insert(0, _('Title and content are required.'))
        if errors:
            page = _form_again(song, False, church_id, membership, errors)
            db.session.rollback()          # nic z błędnego formularza nie trafia do bazy
            return page
        db.session.commit()
        flash(_('Saved changes.'))
        for n in notes:
            flash(n)
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
    flash(_('Deleted:') + ' ' + song.title)
    return redirect(url_for('songs.songs_list', church_id=church_id))


# ── Import .txt (format eksportu aplikacji desktop) ──
@songs_bp.post('/c/<church_id>/songs/import')
@require_membership('muzyk')   # dodawanie piosenek (import) dostępne dla muzyków
def songs_import(church_id, membership):
    files = request.files.getlist('files')
    added, skipped, too_big, key_fixed = [], [], [], []
    header_re = re.compile(r'^(.*?)(?:\s*\(([^)]+)\))?(?:-\((\d+)\))?$')

    def _add(title, body, key, bpm, author='', copyright='', ccli=''):
        title = (title or '').strip()[:200]
        body = (body or '').strip()[:SONG_MAX_CHARS]
        if not title or not body:
            return
        if Song.query.filter_by(church_id=church_id, title=title,
                                deleted=False).first():
            skipped.append(title)   # nie nadpisujemy po cichu
            return
        # notacja zgadywana dla każdej piosenki osobno (w jednym pliku bywają
        # obie), tonacja z nagłówka sprawdzana z akordami
        imp = mc.import_song(body, key)
        body, key = imp['content'], imp['key']
        if imp['key_fixed']:
            key_fixed.append(title)
        db.session.add(Song(church_id=church_id, title=title,
                            content=body, key=(key or '')[:10], bpm=bpm or 0,
                            author=(author or '')[:300],
                            copyright=(copyright or '')[:300],
                            ccli_number=(ccli or '')[:20],
                            created_by=current_user().id))
        added.append(title)

    for f in files[:IMPORT_MAX_FILES]:
        if not f or not f.filename.lower().endswith(IMPORT_EXTS):
            continue
        # Czytamy tylko do limitu +1 bajt — jeśli plik jest większy, pomijamy go
        # bez ładowania całości do pamięci.
        raw_bytes = f.read(IMPORT_MAX_BYTES + 1)
        if len(raw_bytes) > IMPORT_MAX_BYTES:
            too_big.append(f.filename)
            continue
        try:
            content = raw_bytes.decode('utf-8-sig')
        except UnicodeDecodeError:
            content = raw_bytes.decode('cp1250', errors='ignore')
        content = content.replace('\r', '')

        # ── ChordPro (np. pobranie z CCLI SongSelect) ──
        if mc.is_chordpro(content):
            for song in mc.parse_chordpro(content):
                title = song['title'] or f.filename.rsplit('.', 1)[0]
                _add(title, song['content'], song['key'], song['bpm'],
                     author=song['author'], copyright=song['copyright'],
                     ccli=song['ccli'])
            continue

        # ── Format eksportu aplikacji desktop / zbiorczy śpiewnik (.txt) ──
        chunks = (SONG_SEPARATOR_RE.split(content)
                  if SONG_SEPARATOR_RE.search(content) else None)
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
            _add(title, '\n'.join(lines[1:]), key, bpm)
    db.session.commit()
    msg = _('Imported:') + f' {len(added)}.'
    if skipped:
        msg += ' ' + _('Skipped (title already exists):') + f' {len(skipped)}.'
    if too_big:
        msg += ' ' + _('Skipped (file too large, max 512 KB):') + f' {len(too_big)}.'
    if key_fixed:
        msg += ' ' + _('Key in the title did not match the chords — detected instead:') + ' ' + ', '.join(key_fixed[:5]) + '.'
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
    """Edytor piosenki (debounce w JS): problemy z numerami linii, akordy
    nierozpoznane, podpowiedź notacji i podgląd dokładnie takiej piosenki,
    jaka zostanie zapisana i pokazana zespołowi."""
    data = request.json or {}
    text = (data.get('text') or '')[:SONG_MAX_CHARS * 2]
    notation = data.get('notation') if data.get('notation') in NOTATIONS else 'international'
    report = mc.analyze_song(text, notation)
    # Podgląd = dokładnie ta sama ścieżka co zapis
    prep = mc.prepare_song(text, notation)
    stored, changes = prep['content'], prep['changes']
    sections = []
    for sec in mc.parse_song_sections(stored):
        _p, band, _x = mc.process_song(sec['content'])
        auto = sec['label'].startswith('SLAJD ')
        # linie z tekstem (bez linii samych akordów) — slajd ma mieć max 8
        n_lines = sum(1 for l in sec['content'].split('\n')
                      if re.search(r'[^\W\d_]', re.sub(r'\[[^\]]*\]', '', l)))
        sections.append({'label': sec['label'], 'html': band, 'auto': auto, 'lines': n_lines,
                         'known': auto or mc.is_section_label(sec['label'])})
    report.update({'sections': sections, 'fixes': changes, 'meta': prep['meta'],
                   'converted': prep['converted'],
                   # zgodność wstecz (stary edytor oczekiwał listy nazw)
                   'invalid_names': [i['chord'] for i in report['invalid']]})
    return jsonify(report)


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
    hints = team_preferences(church_id, [r['song'].id for r in rows])
    for r in rows:
        r['hints'] = hints.get(r['song'].id, [])
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


# ── Tryb ćwiczenia + moje tonacje ──
def _my_profile(church_id):
    return Profile.query.filter_by(church_id=church_id,
                                   user_id=current_user().id,
                                   deleted=False).first()


def _my_personal(church_id, song_id, create=False):
    profile = _my_profile(church_id)
    if not profile:
        return None, None
    sp = SongPersonal.query.filter_by(profile_id=profile.id,
                                      song_id=song_id).first()
    if not sp and create:
        sp = SongPersonal(profile_id=profile.id, song_id=song_id)
        db.session.add(sp)
    return profile, sp


def _load_section_notes(sp):
    """Notatki per sekcja z SongPersonal.section_notes (JSON) — bezpieczny parse."""
    if not sp:
        return {}
    try:
        d = json.loads(sp.section_notes or '{}')
        return d if isinstance(d, dict) else {}
    except (ValueError, TypeError):
        return {}


@songs_bp.get('/c/<church_id>/songs/<song_id>/practice')
@require_membership('muzyk')
def practice(church_id, song_id, membership):
    song = _get_song(church_id, song_id)
    profile, sp = _my_personal(church_id, song_id)
    transpose = (sp.preferred_transpose if sp and
                 sp.preferred_transpose is not None else 0)
    try:
        transpose = int(request.args.get('t', transpose))
    except ValueError:
        pass
    transpose = max(-11, min(11, transpose))
    shown_key = song.key
    if song.key and transpose:
        shown_key = mc.apply_transpose_to_single_chord(
            f'[{song.key}]', transpose).strip('[]')

    # Aranżacja: kafelki w kolejności formy + moja partia + nagranie z próby.
    # Bez aranżacji — jak dotąd, sekcje w kolejności tekstu.
    from app.arrangements import service as arr_svc
    from app.arrangements.routes import cells_payload, recordings_payload
    arrangements = arr_svc.song_arrangements(song)
    arr = None
    if arrangements:
        want = request.args.get('a')
        arr = next((a for a in arrangements if a.id == want), arrangements[0])
    if arr:
        rendered = [dict(t, sec_idx=t.get('sec'))
                    for t in arr_svc.tiles_with_content(arr, song, transpose)]
    else:
        rendered = []
        for i, sec in enumerate(mc.parse_song_sections(song.content)):
            _, band, _ = mc.process_song(sec['content'],
                                         transpose_amount=transpose)
            rendered.append({'label': sec['label'], 'band_html': band,
                             'sec_idx': i, 'repeat': 1, 'dyn': '', 'id': ''})
    return render_template('songs/practice.html', song=song,
                           sections=rendered, transpose=transpose,
                           shown_key=shown_key,
                           arr=arr, arrangements=arrangements,
                           my_role=arr_svc.my_role(arr, profile) if arr else '',
                           cells=cells_payload(arr) if arr else {},
                           rec=recordings_payload(arr) if arr else {},
                           dyn_labels=arr_svc.DYNAMICS,
                           note=(sp.note if sp else ''),
                           section_notes=(_load_section_notes(sp) if sp else {}),
                           prefs=(profile.prefs if profile else {}) or {},
                           church=db.session.get(Church, church_id),
                           membership=membership, user=current_user())


@songs_bp.post('/c/<church_id>/songs/<song_id>/personal')
@require_membership('muzyk')
def save_personal(church_id, song_id, membership):
    """Zapis "mojej tonacji" / notatki (AJAX z widoku ćwiczenia)."""
    song = _get_song(church_id, song_id)
    profile, sp = _my_personal(church_id, song_id, create=True)
    if not profile:
        abort(400)
    data = request.json or {}
    if 'transpose' in data:
        try:
            t = max(-11, min(11, int(data['transpose'])))
            sp.preferred_transpose = t
            if song.key:
                sp.preferred_key = mc.apply_transpose_to_single_chord(
                    f'[{song.key}]', t).strip('[]')[:10]
        except (TypeError, ValueError):
            pass
    if 'note' in data:
        sp.note = str(data['note'])[:2000]
    # Notatka do konkretnej sekcji (kafelka) — ten sam model co widok live
    # (section_notes: JSON {"<idx>": "..."}), więc notatki się współdzielą.
    if 'section' in data and 'section_note' in data:
        notes = _load_section_notes(sp)
        try:
            key = str(int(data['section']))
        except (TypeError, ValueError):
            key = None
        if key is not None:
            txt = str(data['section_note'])[:1000]
            if txt.strip():
                notes[key] = txt
            else:
                notes.pop(key, None)
            sp.section_notes = json.dumps(notes)
    db.session.commit()
    return jsonify({'status': 'ok',
                    'preferred_key': sp.preferred_key,
                    'preferred_transpose': sp.preferred_transpose})


def team_preferences(church_id, song_ids):
    """Podpowiedzi dla prowadzącego: kto woli jaką tonację (per piosenka)."""
    if not song_ids:
        return {}
    rows = db.session.query(SongPersonal, Profile).join(
        Profile, SongPersonal.profile_id == Profile.id).filter(
        Profile.church_id == church_id,
        SongPersonal.song_id.in_(song_ids),
        SongPersonal.preferred_transpose.isnot(None)).all()
    hints = {}
    for sp, profile in rows:
        if sp.preferred_transpose == 0:
            continue
        txt = profile.name
        if sp.preferred_key:
            txt += f' woli {sp.preferred_key}'
        else:
            t = sp.preferred_transpose
            txt += f' woli {"+" if t > 0 else ""}{t}'
        hints.setdefault(sp.song_id, []).append(txt)
    return hints
