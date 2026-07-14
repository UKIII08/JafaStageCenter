# Rejestracja / logowanie (M0). Sesje cookie; hasła: werkzeug (scrypt).
# Reset hasła mailem i weryfikacja e-mail dochodzą pod koniec M0 (wymagają SMTP).
from datetime import datetime
from functools import wraps

from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, g)
from werkzeug.security import generate_password_hash, check_password_hash

from app import db
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
        nxt = request.args.get('next')
        return redirect(nxt or url_for('panel.dashboard'))
    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash('Nieprawidłowy e-mail lub hasło.')
            return render_template('auth/login.html')
        user.last_login_at = datetime.utcnow()
        db.session.commit()
        session['user_id'] = user.id
        nxt = request.args.get('next')
        return redirect(nxt or url_for('panel.dashboard'))
    return render_template('auth/login.html')


@auth_bp.get('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
