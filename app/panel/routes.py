# Panel wspólnoty (M0): dashboard, zakładanie wspólnoty, zespół, zaproszenia.
# TWARDA ZASADA TENANCY: każdy dostęp do danych wspólnoty przechodzi przez
# require_membership() — nigdy przez samo id z URL-a.
import os
import re
import secrets
import string
import unicodedata
from functools import wraps

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, abort, session)

from app import db
from app.models import Church, Membership, Profile, Invitation, ROLES

NOTATIONS = ('international', 'polish')
ENGINES = ('v2', 'v3', 'v4')
INSTRUMENTS = ('', 'wokal', 'gitara', 'gitara elektryczna', 'bas',
               'klawisze', 'perkusja', 'skrzypce', 'inny')
from app.auth.routes import current_user, login_required
from app.i18n import translate as _

panel_bp = Blueprint('panel', __name__)

ROLE_ORDER = {'muzyk': 0, 'prowadzacy': 1, 'admin': 2}


def get_membership(church_id):
    user = current_user()
    if not user:
        return None
    return Membership.query.filter_by(
        user_id=user.id, church_id=church_id, status='active').first()


def require_membership(min_role='muzyk'):
    """Dekorator: route musi mieć parametr church_id; sprawdza członkostwo
    i minimalną rolę, wstrzykuje membership jako kwarg."""
    def deco(f):
        @wraps(f)
        @login_required
        def wrapper(church_id, *args, **kwargs):
            m = get_membership(church_id)
            if not m or ROLE_ORDER[m.role] < ROLE_ORDER[min_role]:
                abort(403)
            return f(church_id, *args, membership=m, **kwargs)
        return wrapper
    return deco


def slugify(name):
    s = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()[:60]
    return s or 'wspolnota'


def unique_slug(name):
    base = slugify(name)
    slug, i = base, 2
    while Church.query.filter_by(slug=slug).first():
        slug = f'{base}-{i}'
        i += 1
    return slug


def new_invite_code():
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(alphabet) for _ in range(6))
        if not Invitation.query.filter_by(code=code).first():
            return code


@panel_bp.get('/')
def dashboard():
    user = current_user()
    if not user:
        # Landing dla niezalogowanych — strona główna produktu
        return render_template('landing.html')
    memberships = Membership.query.filter_by(
        user_id=user.id, status='active').all()
    if not memberships:
        return redirect(url_for('panel.create_church'))
    if len(memberships) == 1:
        return redirect(url_for('panel.church_home',
                                church_id=memberships[0].church_id))
    return render_template('panel/choose_church.html',
                           memberships=memberships, user=user)


@panel_bp.route('/church/create', methods=['GET', 'POST'])
@login_required
def create_church():
    user = current_user()
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        if len(name) < 3:
            flash(_('Enter a community name (min. 3 characters).'))
            return render_template('panel/create_church.html')
        church = Church(name=name, slug=unique_slug(name),
                        owner_user_id=user.id)
        db.session.add(church)
        db.session.flush()
        db.session.add(Membership(user_id=user.id, church_id=church.id,
                                  role='admin'))
        db.session.add(Profile(church_id=church.id, user_id=user.id,
                               name=user.display_name))
        db.session.commit()
        return redirect(url_for('panel.church_home', church_id=church.id))
    return render_template('panel/create_church.html')


AVG_SONG_MIN = 4   # zgrubny czas jednej pieśni (do szacunku długości setlisty)


def _est_minutes(n):
    return int(round(n * AVG_SONG_MIN))


@panel_bp.get('/c/<church_id>')
@require_membership('muzyk')
def church_home(church_id, membership):
    # Przyjazny dashboard na wejście (design „Precision"): najbliższa służba
    # z podglądem setlisty, Live ze statusem, profil, Studio, powrót do
    # ćwiczenia z postępem, zespół z podziałem ról. Dane liczone realnie;
    # to, czego nie ma, chowa się z gracją.
    import json
    from types import SimpleNamespace
    from datetime import date
    from app.models import (Event, EventAssignment, StudioSetlist,
                            SongPersonal, Song)
    user = current_user()
    today = date.today()
    # ── Najbliższa służba (moja obsada > dowolna) ──
    my_event = Event.query.join(
        EventAssignment, EventAssignment.event_id == Event.id).filter(
        Event.church_id == church_id, Event.deleted.is_(False),
        Event.date >= today, EventAssignment.user_id == user.id).order_by(
        Event.date.asc()).first()
    next_event = my_event or Event.query.filter(
        Event.church_id == church_id, Event.deleted.is_(False),
        Event.date >= today).order_by(Event.date.asc()).first()
    # Podgląd setlisty najbliższego grania.
    next_event_songs = []
    if next_event and next_event.setlist_id:
        sl = StudioSetlist.query.filter_by(
            id=next_event.setlist_id, church_id=church_id).first()
        if sl:
            try:
                next_event_songs = [
                    SimpleNamespace(title=s.get('title', ''),
                                    key=s.get('key', ''))
                    for s in json.loads(sl.songs or '[]')]
            except (ValueError, AttributeError):
                next_event_songs = []

    # Mój profil — potrzebny do postępu ćwiczenia (ostatnio ćwiczone).
    my_profile = Profile.query.filter_by(
        church_id=church_id, user_id=user.id, deleted=False).first()

    # ── Studio: ostatnia setlista (string „N pieśni · M min") ──
    last_setlist = None
    last_sl = StudioSetlist.query.filter_by(church_id=church_id) \
        .order_by(StudioSetlist.id.desc()).first()
    if last_sl:
        try:
            n = len(json.loads(last_sl.songs or '[]'))
        except (ValueError, TypeError):
            n = 0
        if n:
            last_setlist = (f'{n} ' + _('songs') + ' · '
                            + f'{_est_minutes(n)} ' + _('min'))

    # ── Ćwiczenie: ostatnio ćwiczona pieśń (string) + postęp ──
    last_practiced = None
    practice_done = practice_total = 0
    if my_profile:
        sp = SongPersonal.query.filter_by(profile_id=my_profile.id) \
            .order_by(SongPersonal.updated_at.desc()).first()
        if sp:
            song = db.session.get(Song, sp.song_id)
            if song and not song.deleted:
                key = sp.preferred_key or song.key or ''
                last_practiced = song.title + (f' — {key}' if key else '')
        # postęp = ile z pieśni najbliższej setlisty mam już „ruszonych"
        if next_event_songs:
            titles = {s.title for s in next_event_songs}
            practice_total = len(titles)
            done_titles = {
                song.title for song in Song.query.filter(
                    Song.church_id == church_id, Song.title.in_(titles)).all()
                if SongPersonal.query.filter_by(
                    profile_id=my_profile.id, song_id=song.id).first()}
            practice_done = len(done_titles)

    # ── Zespół: awatary (imiona z profili) ──
    memberships = Membership.query.filter_by(
        church_id=church_id, status='active').all()
    profiles = {p.user_id: p.name for p in Profile.query.filter_by(
        church_id=church_id, deleted=False).all()}
    team_members = [
        SimpleNamespace(user_id=m.user_id,
                        display_name=profiles.get(m.user_id) or '?')
        for m in memberships]

    church = db.session.get(Church, church_id)

    # ── Onboarding „Pierwsze kroki" (tylko admin) — realne wykrywanie postępu.
    onboarding = None
    if membership.role == 'admin':
        from app.studio.routes import media_dir
        from app.models import Song, ScreenToken
        onboarding = {
            'logo': os.path.exists(os.path.join(media_dir(church_id), 'logo.png')),
            'songs': Song.query.filter_by(church_id=church_id, deleted=False).count() > 0,
            'members': len(memberships) > 1,
            'screen': ScreenToken.query.filter_by(church_id=church_id).first() is not None,
            'event': Event.query.filter_by(church_id=church_id, deleted=False).first() is not None,
        }
        onboarding['done'] = sum(1 for v in onboarding.values() if v)
        onboarding['total'] = len(onboarding) - 1   # bez klucza 'done'
        onboarding['complete'] = onboarding['done'] == onboarding['total']

    # Ekran powitalny pokazujemy tylko raz — zaraz po zalogowaniu (flaga w sesji
    # ustawiona przy logowaniu, tu ją zdejmujemy). Klik w logo itd. go nie wywoła.
    show_welcome = session.pop('show_welcome', False)
    return render_template(
        'panel/dashboard.html', church=church, membership=membership,
        user=user, next_event=next_event, my_event=my_event is not None,
        next_event_songs=next_event_songs, last_setlist=last_setlist,
        last_practiced=last_practiced, practice_done=practice_done,
        practice_total=practice_total, team_members=team_members,
        today=today, show_welcome=show_welcome, onboarding=onboarding)


@panel_bp.get('/c/<church_id>/team')
@require_membership('muzyk')
def team(church_id, membership):
    church = db.session.get(Church, church_id)
    members = Membership.query.filter_by(
        church_id=church_id, status='active').all()
    profiles = Profile.query.filter_by(
        church_id=church_id, deleted=False).all()
    invite = None
    if membership.role == 'admin':
        invite = Invitation.query.filter(
            Invitation.church_id == church_id,
            Invitation.email.is_(None)).order_by(Invitation.id.desc()).first()
        if invite and not invite.is_valid():
            invite = None
    return render_template('panel/team.html', church=church, members=members,
                           profiles=profiles, invite=invite,
                           membership=membership, user=current_user())


@panel_bp.get('/c/<church_id>/guide')
@require_membership('muzyk')
def guide(church_id, membership):
    """Przewodnik po funkcjach — „co potrafi Jonathan", żeby użytkownicy
    odkryli unikalne możliwości bez przytłoczenia (osobna, opcjonalna strona)."""
    church = db.session.get(Church, church_id)
    return render_template('panel/guide.html', church=church,
                           membership=membership, user=current_user())


@panel_bp.post('/c/<church_id>/team/invite')
@require_membership('admin')
def team_invite(church_id, membership):
    inv = Invitation(church_id=church_id, code=new_invite_code(),
                     role=request.form.get('role', 'muzyk'),
                     expires_at=Invitation.default_expiry(),
                     created_by=current_user().id)
    if inv.role not in ROLES:
        inv.role = 'muzyk'
    db.session.add(inv)
    db.session.commit()
    return redirect(url_for('panel.team', church_id=church_id))


@panel_bp.get('/join/<code>')
def join(code):
    inv = Invitation.query.filter_by(code=code.upper()).first()
    if not inv or not inv.is_valid():
        return render_template('panel/join_invalid.html'), 404
    user = current_user()
    if not user:
        return redirect(url_for('auth.register',
                                next=url_for('panel.join', code=code)))
    existing = Membership.query.filter_by(
        user_id=user.id, church_id=inv.church_id).first()
    if not existing:
        db.session.add(Membership(user_id=user.id, church_id=inv.church_id,
                                  role=inv.role))
        db.session.add(Profile(church_id=inv.church_id, user_id=user.id,
                               name=user.display_name))
        inv.uses += 1
        db.session.commit()
        flash(_('You joined the team! Set your instrument and preferences.'))
    return redirect(url_for('panel.team', church_id=inv.church_id))


# ── Mój profil w tej wspólnocie (instrument + preferencje wyświetlania) ──
@panel_bp.route('/c/<church_id>/profile', methods=['GET', 'POST'])
@require_membership('muzyk')
def my_profile(church_id, membership):
    user = current_user()
    profile = Profile.query.filter_by(
        church_id=church_id, user_id=user.id, deleted=False).first()
    if not profile:
        profile = Profile(church_id=church_id, user_id=user.id,
                          name=user.display_name)
        db.session.add(profile)
        db.session.commit()
    if request.method == 'POST':
        profile.name = (request.form.get('name') or profile.name).strip()
        inst = request.form.get('instrument', '')
        profile.instrument = inst if inst in INSTRUMENTS else ''
        prefs = dict(profile.prefs or {})
        prefs['notation'] = (request.form.get('notation')
                             if request.form.get('notation') in NOTATIONS
                             else 'international')
        prefs['show_chords'] = bool(request.form.get('show_chords'))
        prefs['lowercase_minor'] = bool(request.form.get('lowercase_minor'))
        prefs['beginner_mode'] = bool(request.form.get('beginner_mode'))
        try:
            prefs['capo_default'] = max(0, min(11, int(request.form.get('capo_default') or 0)))
        except ValueError:
            prefs['capo_default'] = 0
        profile.prefs = prefs
        db.session.commit()
        flash(_('Profile saved.'))
        return redirect(url_for('panel.my_profile', church_id=church_id))
    return render_template('panel/profile.html', church=db.session.get(Church, church_id),
                           profile=profile, membership=membership,
                           instruments=INSTRUMENTS, user=user)


# ── Zarządzanie zespołem (admin): zmiana roli, usuwanie ──
@panel_bp.post('/c/<church_id>/team/<int:member_id>/role')
@require_membership('admin')
def team_change_role(church_id, member_id, membership):
    m = Membership.query.filter_by(id=member_id, church_id=church_id).first()
    new_role = request.form.get('role')
    if not m or new_role not in ROLES:
        abort(404)
    church = db.session.get(Church, church_id)
    if m.user_id == church.owner_user_id and new_role != 'admin':
        flash(_('The community owner stays an administrator.'))
        return redirect(url_for('panel.team', church_id=church_id))
    m.role = new_role
    db.session.commit()
    return redirect(url_for('panel.team', church_id=church_id))


@panel_bp.post('/c/<church_id>/team/<int:member_id>/remove')
@require_membership('admin')
def team_remove(church_id, member_id, membership):
    m = Membership.query.filter_by(id=member_id, church_id=church_id).first()
    if not m:
        abort(404)
    church = db.session.get(Church, church_id)
    if m.user_id == church.owner_user_id:
        flash(_('The community owner can\'t be removed.'))
        return redirect(url_for('panel.team', church_id=church_id))
    m.status = 'removed'
    db.session.commit()
    flash(_('Removed from the team.'))
    return redirect(url_for('panel.team', church_id=church_id))


# ── Ustawienia wspólnoty (admin) ──
@panel_bp.route('/c/<church_id>/settings', methods=['GET', 'POST'])
@require_membership('admin')
def church_settings(church_id, membership):
    church = db.session.get(Church, church_id)
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        if len(name) >= 3:
            church.name = name
        settings = dict(church.settings or {})
        if request.form.get('default_notation') in NOTATIONS:
            settings['default_notation'] = request.form.get('default_notation')
        if request.form.get('transition_engine') in ENGINES:
            settings['transition_engine'] = request.form.get('transition_engine')
        if request.form.get('ccli_license') is not None:
            settings['ccli_license'] = \
                (request.form.get('ccli_license') or '').strip()[:20]
            # checkbox: obecny = wł., brak (przy wysłanym formularzu) = wył.
            settings['ccli_notice'] = \
                '1' if request.form.get('ccli_notice') else '0'
        church.settings = settings
        db.session.commit()
        flash(_('Settings saved.'))
        return redirect(url_for('panel.church_settings', church_id=church_id))
    from app.studio.routes import get_settings, media_dir
    appearance = get_settings(church)
    has_bg = os.path.exists(os.path.join(media_dir(church_id), 'background.png'))
    return render_template('panel/settings.html', church=church,
                           appearance=appearance, has_bg=has_bg,
                           membership=membership, user=current_user())


@panel_bp.get('/pl')
def landing_pl():
    """Polska wersja landinga (domyślny '/' jest po angielsku — rynek USA)."""
    return render_template('landing_pl.html')
