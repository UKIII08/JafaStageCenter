# Rejestracja / logowanie (M0). Sesje cookie; hasła: werkzeug (scrypt).
# Reset hasła mailem i weryfikacja e-mail dochodzą pod koniec M0 (wymagają SMTP).
import os
from datetime import datetime
from functools import wraps

from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, g, current_app)
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, limiter
from app.emails import send_email
from app.models import User, Membership

auth_bp = Blueprint('auth', __name__)


def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    if getattr(g, '_user', None) is None or g._user.id != uid:
        g._user = db.session.get(User, uid)
    return g._user


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return wrapper


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit('10 per hour', methods=['POST'])
def register():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        name = (request.form.get('display_name') or '').strip()
        if not email or '@' not in email:
            flash('Podaj poprawny adres e-mail.'); return render_template('auth/register.html')
        if len(password) < 8:
            flash('Hasło musi mieć co najmniej 8 znaków.'); return render_template('auth/register.html')
        if not name:
            flash('Podaj swoje imię.'); return render_template('auth/register.html')
        if User.query.filter_by(email=email).first():
            flash('Konto z tym adresem już istnieje — zaloguj się.')
            return redirect(url_for('auth.login'))
        user = User(email=email, display_name=name,
                    password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        _send_verification(user)
        nxt = request.args.get('next')
        return redirect(nxt or url_for('panel.dashboard'))
    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute;50 per hour', methods=['POST'])
def login():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash('Nieprawidłowy e-mail lub hasło.')
            return render_template('auth/login.html')
        if user.totp_secret:
            # 2FA: hasło OK, ale sesja dopiero po kodzie z aplikacji
            session['pending_2fa'] = user.id
            return redirect(url_for('auth.login_2fa',
                                    next=request.args.get('next') or ''))
        user.last_login_at = datetime.utcnow()
        db.session.commit()
        session['user_id'] = user.id
        nxt = request.args.get('next')
        return redirect(nxt or url_for('panel.dashboard'))
    return render_template('auth/login.html')


@auth_bp.route('/login/2fa', methods=['GET', 'POST'])
@limiter.limit('10 per minute', methods=['POST'])
def login_2fa():
    import pyotp
    uid = session.get('pending_2fa')
    if not uid:
        return redirect(url_for('auth.login'))
    user = db.session.get(User, uid)
    if request.method == 'POST':
        code = (request.form.get('code') or '').strip()
        if user and pyotp.TOTP(user.totp_secret).verify(code, valid_window=1):
            session.pop('pending_2fa', None)
            session['user_id'] = user.id
            user.last_login_at = datetime.utcnow()
            db.session.commit()
            nxt = request.args.get('next')
            return redirect(nxt or url_for('panel.dashboard'))
        flash('Nieprawidłowy kod — spróbuj ponownie.')
    return render_template('auth/login_2fa.html')


# ── Konto: bezpieczeństwo (2FA) ──
@auth_bp.route('/account', methods=['GET'])
@login_required
def account():
    return render_template('auth/account.html', user=current_user())


@auth_bp.post('/account/2fa/enable')
@login_required
def twofa_enable():
    import pyotp
    user = current_user()
    if user.totp_secret:
        return redirect(url_for('auth.account'))
    session['totp_setup'] = pyotp.random_base32()
    return redirect(url_for('auth.twofa_confirm'))


@auth_bp.route('/account/2fa/confirm', methods=['GET', 'POST'])
@login_required
def twofa_confirm():
    import base64
    import io
    import pyotp
    import qrcode
    import qrcode.image.svg
    user = current_user()
    secret = session.get('totp_setup')
    if not secret:
        return redirect(url_for('auth.account'))
    if request.method == 'POST':
        code = (request.form.get('code') or '').strip()
        if pyotp.TOTP(secret).verify(code, valid_window=1):
            user.totp_secret = secret
            db.session.commit()
            session.pop('totp_setup', None)
            flash('Weryfikacja dwuetapowa włączona.')
            return redirect(url_for('auth.account'))
        flash('Kod się nie zgadza — zeskanuj QR jeszcze raz i spróbuj.')
    uri = pyotp.TOTP(secret).provisioning_uri(
        name=user.email, issuer_name='Jonathan App')
    img = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage)
    buf = io.BytesIO(); img.save(buf)
    qr_svg = base64.b64encode(buf.getvalue()).decode()
    return render_template('auth/twofa_confirm.html', qr_svg=qr_svg,
                           secret=secret, user=user)


@auth_bp.post('/account/2fa/disable')
@login_required
def twofa_disable():
    user = current_user()
    if not check_password_hash(user.password_hash,
                               request.form.get('password') or ''):
        flash('Błędne hasło — 2FA pozostaje włączone.')
        return redirect(url_for('auth.account'))
    user.totp_secret = None
    db.session.commit()
    flash('Weryfikacja dwuetapowa wyłączona.')
    return redirect(url_for('auth.account'))


@auth_bp.get('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


def _reset_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'],
                                  salt='password-reset')


@auth_bp.route('/reset', methods=['GET', 'POST'])
@limiter.limit('5 per hour', methods=['POST'])
def reset_request():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = _reset_serializer().dumps(user.id)
            link = url_for('auth.reset_token', token=token, _external=True)
            send_email(email, 'Jonathan App — reset hasła',
                       f'Aby ustawić nowe hasło, otwórz link (ważny 2 godziny):\n{link}')
        # celowo ta sama odpowiedź niezależnie od istnienia konta
        flash('Jeśli konto istnieje, wysłaliśmy link do resetu hasła.')
    return render_template('auth/reset_request.html')


@auth_bp.route('/reset/<token>', methods=['GET', 'POST'])
def reset_token(token):
    try:
        uid = _reset_serializer().loads(token, max_age=7200)
    except (BadSignature, SignatureExpired):
        flash('Link wygasł lub jest nieprawidłowy — poproś o nowy.')
        return redirect(url_for('auth.reset_request'))
    user = db.session.get(User, uid)
    if not user:
        return redirect(url_for('auth.reset_request'))
    if request.method == 'POST':
        password = request.form.get('password') or ''
        if len(password) < 8:
            flash('Hasło musi mieć co najmniej 8 znaków.')
            return render_template('auth/reset_form.html')
        user.password_hash = generate_password_hash(password)
        db.session.commit()
        session.clear()
        flash('Hasło zmienione — zaloguj się.')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_form.html')


# ── Weryfikacja adresu e-mail ──
def _verify_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'],
                                  salt='email-verify')


def _send_verification(user):
    token = _verify_serializer().dumps(user.id)
    link = url_for('auth.verify_email', token=token, _external=True)
    send_email(user.email, 'Jonathan App — potwierdź adres e-mail',
               f'Cześć {user.display_name}!\n\n'
               f'Potwierdź swój adres e-mail, otwierając link '
               f'(ważny 3 dni):\n{link}\n\n'
               f'Jeśli to nie Ty zakładałeś konto — zignoruj tę wiadomość.')


@auth_bp.post('/account/verify/send')
@login_required
@limiter.limit('3 per hour')
def verify_send():
    user = current_user()
    if not user.email_verified_at:
        _send_verification(user)
        flash('Wysłaliśmy link weryfikacyjny na Twój adres e-mail.')
    return redirect(url_for('auth.account'))


@auth_bp.get('/verify/<token>')
def verify_email(token):
    try:
        uid = _verify_serializer().loads(token, max_age=3 * 24 * 3600)
    except (BadSignature, SignatureExpired):
        flash('Link weryfikacyjny wygasł — wyślij nowy z ustawień konta.')
        return redirect(url_for('auth.login'))
    user = db.session.get(User, uid)
    if user and not user.email_verified_at:
        user.email_verified_at = datetime.utcnow()
        db.session.commit()
    flash('Adres e-mail potwierdzony.')
    return redirect(url_for('panel.dashboard') if session.get('user_id')
                    else url_for('auth.login'))


# ── Usunięcie konta (RODO: prawo do bycia zapomnianym) ──
@auth_bp.route('/account/delete', methods=['GET', 'POST'])
@login_required
def account_delete():
    from app.models import (Church, EventAssignment, EventSignup, Profile,
                            SongPersonal)
    user = current_user()
    # Wspólnoty, których użytkownik jest właścicielem
    owned = Church.query.filter_by(owner_user_id=user.id).all()
    blockers = []
    sole_churches = []
    for ch in owned:
        others = Membership.query.filter(
            Membership.church_id == ch.id,
            Membership.user_id != user.id,
            Membership.status == 'active').count()
        if others:
            blockers.append(ch)
        else:
            sole_churches.append(ch)

    if request.method == 'POST':
        if not check_password_hash(user.password_hash,
                                   request.form.get('password') or ''):
            flash('Błędne hasło — konto nie zostało usunięte.')
            return redirect(url_for('auth.account_delete'))
        if blockers:
            flash('Najpierw przekaż wspólnotę innemu adminowi albo usuń '
                  'pozostałych członków.')
            return redirect(url_for('auth.account_delete'))
        # Dane osobiste użytkownika we wszystkich wspólnotach
        profile_ids = [p.id for p in
                       Profile.query.filter_by(user_id=user.id).all()]
        if profile_ids:
            SongPersonal.query.filter(
                SongPersonal.profile_id.in_(profile_ids)) \
                .delete(synchronize_session=False)
            Profile.query.filter(Profile.id.in_(profile_ids)) \
                .delete(synchronize_session=False)
        EventSignup.query.filter_by(user_id=user.id) \
            .delete(synchronize_session=False)
        EventAssignment.query.filter_by(user_id=user.id) \
            .delete(synchronize_session=False)
        Membership.query.filter_by(user_id=user.id) \
            .delete(synchronize_session=False)
        # Wspólnoty, w których był jedynym członkiem — kasujemy w całości
        for ch in sole_churches:
            _purge_church(ch.id)
        db.session.delete(user)
        db.session.commit()
        session.clear()
        flash('Konto i dane zostały usunięte.')
        return redirect(url_for('auth.login'))
    return render_template('auth/account_delete.html', user=user,
                           blockers=blockers, sole_churches=sole_churches)


def _purge_church(church_id):
    """Twarde usunięcie wspólnoty i wszystkich jej danych (gdy właściciel
    kasuje konto będąc jedynym członkiem)."""
    import shutil

    from app.models import (BandPreset, Event, EventAssignment, EventSignup,
                            Invitation, LiveSession, Profile, ScreenToken,
                            Song, SongPersonal, StudioSetlist, Church)
    event_ids = [e.id for e in Event.query.filter_by(
        church_id=church_id).all()]
    if event_ids:
        EventSignup.query.filter(EventSignup.event_id.in_(event_ids)) \
            .delete(synchronize_session=False)
        EventAssignment.query.filter(
            EventAssignment.event_id.in_(event_ids)) \
            .delete(synchronize_session=False)
        Event.query.filter(Event.id.in_(event_ids)) \
            .delete(synchronize_session=False)
    profile_ids = [p.id for p in Profile.query.filter_by(
        church_id=church_id).all()]
    if profile_ids:
        SongPersonal.query.filter(SongPersonal.profile_id.in_(profile_ids)) \
            .delete(synchronize_session=False)
    Profile.query.filter_by(church_id=church_id) \
        .delete(synchronize_session=False)
    song_ids = [s.id for s in Song.query.filter_by(
        church_id=church_id).all()]
    if song_ids:
        SongPersonal.query.filter(SongPersonal.song_id.in_(song_ids)) \
            .delete(synchronize_session=False)
    for model in (StudioSetlist, BandPreset, ScreenToken, Invitation,
                  LiveSession, Membership):
        model.query.filter_by(church_id=church_id) \
            .delete(synchronize_session=False)
    Song.query.filter_by(church_id=church_id) \
        .delete(synchronize_session=False)
    from app.models import Setlist
    Setlist.query.filter_by(church_id=church_id) \
        .delete(synchronize_session=False)
    ch = db.session.get(Church, church_id)
    if ch:
        db.session.delete(ch)
    # pliki wspólnoty (logo, tła, pady, prezentacje)
    upload_dir = os.path.join(current_app.instance_path, 'uploads',
                              church_id)
    shutil.rmtree(upload_dir, ignore_errors=True)


# ── Strony prawne ──
@auth_bp.get('/privacy')
def privacy():
    return render_template('legal/privacy.html', user=current_user())


@auth_bp.get('/terms')
def terms():
    return render_template('legal/terms.html', user=current_user())
