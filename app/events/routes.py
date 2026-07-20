# Granie (służba) — organizacja zespołu wokół nabożeństwa/spotkania:
# prowadzący tworzy granie (nazwa, data, termin zgłoszeń), muzycy zgłaszają
# dostępność (mogę / nie mogę — także po terminie, wspólnota to nie korpo),
# prowadzący układa obsadę (kto na czym gra; jedna osoba może mieć kilka
# instrumentów) i podpina setlistę ze Studia. Muzyk dostaje "tryb nauki":
# kiedy gra, na czym, jaka setlista, linki do ćwiczenia w swojej tonacji.
import json
from datetime import date, datetime

from flask import (Blueprint, abort, flash, redirect, render_template,
                   request, url_for)

from app import db
from app.auth.routes import current_user
from app.models import (Church, Event, EventAssignment, EventSignup,
                        Membership, Song, StudioSetlist, User)
from app.panel.routes import INSTRUMENTS, require_membership
from app.i18n import translate as _
from music_core.chords import apply_transpose_to_single_chord

events_bp = Blueprint('events', __name__)


def _get_event(church_id, eid):
    ev = Event.query.filter_by(id=eid, church_id=church_id,
                               deleted=False).first()
    if not ev:
        abort(404)
    return ev


def _event_view(church_id, ev, me):
    """Komplet danych o graniu: zgłoszenia, obsada, setlista z tonacjami."""
    members = Membership.query.filter_by(church_id=church_id,
                                         status='active').all()
    users = {u.id: u for u in User.query.filter(
        User.id.in_([m.user_id for m in members])).all()}
    signups = {s.user_id: s for s in
               EventSignup.query.filter_by(event_id=ev.id).all()}
    roster = []
    for m in members:
        u = users.get(m.user_id)
        if not u:
            continue
        s = signups.get(u.id)
        roster.append({'user': u, 'signup': s})
    roster.sort(key=lambda r: (0 if (r['signup'] and r['signup'].available)
                               else (2 if r['signup'] is None else 1),
                               r['user'].display_name.lower()))
    assignments = [{'a': a, 'user': users.get(a.user_id)}
                   for a in EventAssignment.query.filter_by(
                       event_id=ev.id).all()]

    setlist, songs = None, []
    if ev.setlist_id:
        setlist = StudioSetlist.query.filter_by(
            id=ev.setlist_id, church_id=church_id).first()
        if setlist:
            existing = {s.id for s in Song.query.filter_by(
                church_id=church_id, deleted=False).all()}
            for item in json.loads(setlist.songs or '[]'):
                t = int(item.get('transpose', 0) or 0)
                key = item.get('key') or ''
                shown = key
                if key and t:
                    shown = apply_transpose_to_single_chord(
                        f'[{key}]', t).strip('[]')
                songs.append({'id': item.get('id'),
                              'title': item.get('title', ''),
                              'key': key, 'shown_key': shown,
                              'bpm': item.get('bpm') or 0, 'transpose': t,
                              'in_library': item.get('id') in existing})
    my_signup = signups.get(me.id)
    my_instruments = [x['a'].instrument for x in assignments
                      if x['a'].user_id == me.id]
    deadline_passed = (ev.signup_deadline is not None
                       and date.today() > ev.signup_deadline)
    return {'roster': roster, 'assignments': assignments,
            'setlist': setlist, 'songs': songs, 'my_signup': my_signup,
            'my_instruments': my_instruments,
            'deadline_passed': deadline_passed}


@events_bp.route('/c/<church_id>/granie', methods=['GET', 'POST'])
@require_membership('muzyk')
def events_list(church_id, membership):
    if request.method == 'POST':
        if membership.role == 'muzyk':
            abort(403)
        name = (request.form.get('name') or '').strip()[:200]
        if not name:
            name = 'Nabożeństwo'
        raw_date = request.form.get('date') or ''
        try:
            ev_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
        except ValueError:
            flash(_('Enter a service date.'))
            return redirect(url_for('events.events_list',
                                    church_id=church_id))
        ev = Event(church_id=church_id, name=name, date=ev_date,
                   time=(request.form.get('time') or '')[:5],
                   created_by=current_user().id)
        raw_deadline = request.form.get('signup_deadline') or ''
        try:
            ev.signup_deadline = datetime.strptime(raw_deadline,
                                                   '%Y-%m-%d').date()
        except ValueError:
            pass
        db.session.add(ev)
        db.session.commit()
        return redirect(url_for('events.event_detail', church_id=church_id,
                                eid=ev.id))

    today = date.today()
    all_events = Event.query.filter_by(church_id=church_id, deleted=False) \
        .order_by(Event.date.asc()).all()
    upcoming = [e for e in all_events if e.date >= today]
    past = [e for e in all_events if e.date < today][-5:][::-1]
    me = current_user()
    my_signups = {s.event_id: s for s in EventSignup.query.filter(
        EventSignup.event_id.in_([e.id for e in all_events]),
        EventSignup.user_id == me.id).all()} if all_events else {}
    my_assignments = {}
    if all_events:
        for a in EventAssignment.query.filter(
                EventAssignment.event_id.in_([e.id for e in all_events]),
                EventAssignment.user_id == me.id).all():
            my_assignments.setdefault(a.event_id, []).append(a.instrument)
    return render_template('events/list.html', upcoming=upcoming, past=past,
                           my_signups=my_signups,
                           my_assignments=my_assignments, today=today,
                           church=db.session.get(Church, church_id),
                           membership=membership, user=me)


@events_bp.get('/c/<church_id>/granie/<int:eid>')
@require_membership('muzyk')
def event_detail(church_id, eid, membership):
    ev = _get_event(church_id, eid)
    me = current_user()
    view = _event_view(church_id, ev, me)
    # Dropdown „podepnij setlistę": każdy zapis w Studiu tworzy nowy wiersz,
    # więc bez dedupu lista puchła od starych wersji. Pokazujemy najnowszą
    # wersję per nazwa, pomijamy puste, a aktualnie podpiętą zawsze pokazujemy.
    setlists = []
    if membership.role != 'muzyk':
        seen = set()
        for sl in StudioSetlist.query.filter_by(church_id=church_id) \
                .order_by(StudioSetlist.id.desc()).limit(60).all():
            key = (sl.name or '').strip().lower()
            if key in seen:
                continue
            try:
                if not json.loads(sl.songs or '[]'):
                    continue
            except (ValueError, TypeError):
                continue
            seen.add(key)
            setlists.append(sl)
            if len(setlists) >= 25:
                break
        if ev.setlist_id and not any(s.id == ev.setlist_id for s in setlists):
            attached = StudioSetlist.query.filter_by(
                id=ev.setlist_id, church_id=church_id).first()
            if attached:
                setlists.insert(0, attached)
    return render_template('events/detail.html', ev=ev, today=date.today(),
                           instruments=INSTRUMENTS, setlists=setlists,
                           church=db.session.get(Church, church_id),
                           membership=membership, user=me, **view)


@events_bp.post('/c/<church_id>/granie/<int:eid>/signup')
@require_membership('muzyk')
def event_signup(church_id, eid, membership):
    ev = _get_event(church_id, eid)
    me = current_user()
    available = request.form.get('available') == '1'
    s = EventSignup.query.filter_by(event_id=ev.id, user_id=me.id).first()
    if not s:
        s = EventSignup(event_id=ev.id, user_id=me.id, available=available)
        db.session.add(s)
    s.available = available
    s.comment = (request.form.get('comment') or '')[:200]
    db.session.commit()
    return redirect(url_for('events.event_detail', church_id=church_id,
                            eid=ev.id))


@events_bp.post('/c/<church_id>/granie/<int:eid>/assign')
@require_membership('prowadzacy')
def event_assign(church_id, eid, membership):
    ev = _get_event(church_id, eid)
    action = request.form.get('action', 'add')
    if action == 'remove':
        a = EventAssignment.query.filter_by(
            id=request.form.get('aid', type=int), event_id=ev.id).first()
        if a:
            db.session.delete(a)
            db.session.commit()
    else:
        user_id = request.form.get('user_id')
        member_ok = Membership.query.filter_by(
            church_id=church_id, user_id=user_id, status='active').first()
        if member_ok:
            instrument = (request.form.get('instrument') or '').strip()[:60]
            exists = EventAssignment.query.filter_by(
                event_id=ev.id, user_id=user_id,
                instrument=instrument).first()
            if not exists:
                db.session.add(EventAssignment(event_id=ev.id,
                                               user_id=user_id,
                                               instrument=instrument))
                db.session.commit()
    return redirect(url_for('events.event_detail', church_id=church_id,
                            eid=ev.id))


@events_bp.post('/c/<church_id>/granie/<int:eid>/setlist')
@require_membership('prowadzacy')
def event_setlist(church_id, eid, membership):
    ev = _get_event(church_id, eid)
    sl_id = request.form.get('setlist_id', type=int)
    if sl_id:
        sl = StudioSetlist.query.filter_by(id=sl_id,
                                           church_id=church_id).first()
        ev.setlist_id = sl.id if sl else None
    else:
        ev.setlist_id = None
    db.session.commit()
    return redirect(url_for('events.event_detail', church_id=church_id,
                            eid=ev.id))


@events_bp.post('/c/<church_id>/granie/<int:eid>/edit')
@require_membership('prowadzacy')
def event_edit(church_id, eid, membership):
    ev = _get_event(church_id, eid)
    name = (request.form.get('name') or '').strip()[:200]
    if name:
        ev.name = name
    raw_date = request.form.get('date') or ''
    try:
        ev.date = datetime.strptime(raw_date, '%Y-%m-%d').date()
    except ValueError:
        pass
    ev.time = (request.form.get('time') or '')[:5]
    raw_deadline = request.form.get('signup_deadline') or ''
    try:
        ev.signup_deadline = datetime.strptime(raw_deadline,
                                               '%Y-%m-%d').date()
    except ValueError:
        ev.signup_deadline = None
    ev.notes = (request.form.get('notes') or '')[:2000]
    db.session.commit()
    return redirect(url_for('events.event_detail', church_id=church_id,
                            eid=ev.id))


@events_bp.post('/c/<church_id>/granie/<int:eid>/delete')
@require_membership('prowadzacy')
def event_delete(church_id, eid, membership):
    ev = _get_event(church_id, eid)
    ev.deleted = True
    db.session.commit()
    flash(_('Service deleted.'))
    return redirect(url_for('events.events_list', church_id=church_id))
