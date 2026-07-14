# Panel wspólnoty (M0): dashboard, zakładanie wspólnoty, zespół, zaproszenia.
# TWARDA ZASADA TENANCY: każdy dostęp do danych wspólnoty przechodzi przez
# require_membership() — nigdy przez samo id z URL-a.
import re
import secrets
import string
import unicodedata
from functools import wraps

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, abort)

from app import db
from app.models import Church, Membership, Profile, Invitation, ROLES
from app.auth.routes import current_user, login_required

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
@login_required
def dashboard():
    user = current_user()
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
            flash('Podaj nazwę wspólnoty (min. 3 znaki).')
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


@panel_bp.get('/c/<church_id>')
@require_membership('muzyk')
def church_home(church_id, membership):
    church = db.session.get(Church, church_id)
    return render_template('panel/dashboard.html', church=church,
                           membership=membership, user=current_user())


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
        flash('Dołączyłeś do zespołu! Ustaw swój instrument i preferencje.')
    return redirect(url_for('panel.team', church_id=inv.church_id))
