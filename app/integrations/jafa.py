# Integracja z JafaApp (aplikacja wspólnoty Jafa Warszawa, app.jafawarszawa.pl).
#
# Zespół uwielbienia ma w JafaApp swoją przestrzeń posługi. JafaApp:
#  - pokazuje u siebie najbliższe granie, setlistę i obsadę (API poniżej,
#    wywoływane z serwera JafaApp — przeglądarka nie dotyka Jonathana),
#  - po kliknięciu przenosi do Jonathana już zalogowanego: jednorazowy klucz
#    (ważny 2 minuty, raz) → /integracja/jafa/wejdz.
#
# Na stronie logowania Jonathana NIE ma „Zaloguj przez Jafa" — jedyne wejście
# to klucz z JafaApp. Bez JAFA_SECRET i JAFA_CHURCH_ID integracja jest
# wyłączona (wszystkie adresy zwracają 404), więc inne wspólnoty jej nie widzą.
#
# Klucz: base64url(JSON) + "." + base64url(HMAC-SHA256(JAFA_SECRET, część 1)).
# JSON: {typ: "login"|"api", sub: id w JafaApp, email, name,
#        role: "prowadzacy"|"muzyk", exp: unix, jti: losowe (login)}.
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import date, datetime

from flask import Blueprint, abort, current_app, jsonify, redirect, request, session
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app import db, limiter
from app.auth.routes import _safe_next, start_session
from app.i18n import set_lang
from app.models import (Church, Event, EventSignup, ExternalIdentity,
                        Membership, UsedLoginToken, User)

jafa_bp = Blueprint('jafa', __name__)

PROVIDER = 'jafa'
LOGIN_TTL = 120          # sekundy — klucz wejścia z JafaApp
API_TTL = 300            # sekundy — klucz zapytań serwer↔serwer
ROLES = ('prowadzacy', 'muzyk')


# ─── Konfiguracja ───────────────────────────────────────────────────────────

def _cfg():
    """(sekret, id wspólnoty) albo 404, gdy integracja nie jest włączona."""
    secret = current_app.config.get('JAFA_SECRET') or os.environ.get('JAFA_SECRET')
    church_id = (current_app.config.get('JAFA_CHURCH_ID')
                 or os.environ.get('JAFA_CHURCH_ID'))
    if not secret or not church_id or len(secret) < 32:
        abort(404)
    return secret, church_id


# ─── Klucze ─────────────────────────────────────────────────────────────────

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))


def sign(payload: dict, secret: str) -> str:
    """Podpisuje klucz (używane w testach; JafaApp robi to samo po swojej stronie)."""
    body = _b64(json.dumps(payload, separators=(',', ':')).encode())
    sig = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f'{body}.{sig}'


def verify(token: str, secret: str, typ: str, ttl: int) -> dict:
    """Sprawdza podpis, typ i ważność. Zwraca treść albo 403."""
    try:
        body, sig = (token or '').split('.', 1)
        good = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, good):
            abort(403)
        data = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError):
        abort(403)
    now = int(time.time())
    exp = int(data.get('exp') or 0)
    # Klucz musi być krótkotrwały: wygasa w przyszłości, ale nie dalej niż ttl.
    if data.get('typ') != typ or exp < now or exp > now + ttl:
        abort(403)
    if not data.get('sub') or not data.get('email'):
        abort(403)
    if data.get('role') not in ROLES:
        abort(403)
    return data


# ─── Konto i członkostwo ────────────────────────────────────────────────────

def _find_by_email(email: str):
    return User.query.filter_by(email=email).first()


def resolve_user(data: dict, church_id: str, _retry: bool = True) -> User:
    """Konto Jonathana dla osoby z JafaApp: powiązane wcześniej, to samo
    e-mail (łączymy) albo nowe (bez osobnego hasła). Do tego aktywne
    członkostwo we wspólnocie Jafa z rolą z JafaApp (admina nie ruszamy)."""
    sub = str(data['sub'])[:64]
    email = str(data['email']).strip().lower()[:255]
    name = (str(data.get('name') or '').strip() or email.split('@')[0])[:120]

    ident = ExternalIdentity.query.filter_by(provider=PROVIDER, subject=sub).first()
    user = db.session.get(User, ident.user_id) if ident else None
    if user is None:
        user = _find_by_email(email)
        if user is None:
            # Konto bez hasła do logowania (losowe) — wchodzi się przez JafaApp;
            # można je potem ustawić przez „Nie pamiętam hasła".
            user = User(email=email, display_name=name,
                        password_hash=generate_password_hash(secrets.token_urlsafe(32)),
                        email_verified_at=datetime.utcnow())
            db.session.add(user)
            try:
                db.session.flush()
            except IntegrityError:
                # Równoległe pierwsze zapytanie właśnie założyło to konto — bierzemy je
                db.session.rollback()
                if _retry:
                    return resolve_user(data, church_id, _retry=False)
                raise
        if ident is None:
            db.session.add(ExternalIdentity(provider=PROVIDER, subject=sub, user_id=user.id))
        else:
            ident.user_id = user.id

    m = Membership.query.filter_by(user_id=user.id, church_id=church_id).first()
    role = data['role']
    if m is None:
        db.session.add(Membership(user_id=user.id, church_id=church_id, role=role, status='active'))
    else:
        m.status = 'active'
        if m.role != 'admin':
            m.role = role
    try:
        db.session.commit()
    except IntegrityError:
        # Wyścig przy powiązaniu konta albo członkostwie — drugi raz już wszystko istnieje
        db.session.rollback()
        if _retry:
            return resolve_user(data, church_id, _retry=False)
        raise
    return user


def _api_user(church_id: str):
    secret, _ = _cfg()
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        abort(403)
    data = verify(auth[7:], secret, 'api', API_TTL)
    return resolve_user(data, church_id)


# ─── Wejście z JafaApp ──────────────────────────────────────────────────────

@jafa_bp.get('/integracja/jafa/wejdz')
@limiter.limit('30 per minute')
def enter():
    secret, church_id = _cfg()
    data = verify(request.args.get('t', ''), secret, 'login', LOGIN_TTL)
    jti = str(data.get('jti') or '')[:64]
    if len(jti) < 16:
        abort(403)
    # Jednorazowość: ten sam klucz drugi raz nie wpuści
    UsedLoginToken.query.filter(UsedLoginToken.expires_at < datetime.utcnow()).delete()
    if db.session.get(UsedLoginToken, jti):
        abort(403)
    db.session.add(UsedLoginToken(jti=jti, expires_at=datetime.utcfromtimestamp(int(data['exp']))))
    user = resolve_user(data, church_id)   # commit też zapisuje zużyty klucz
    start_session(user)
    # Jafa to polska wspólnota — po polsku, chyba że ktoś już wybrał inny język
    if 'lang' not in session:
        set_lang('pl')
    user.last_login_at = datetime.utcnow()
    db.session.commit()
    nxt = request.args.get('next') or ''
    return redirect(nxt if _safe_next(nxt) == nxt else f'/c/{church_id}')


# ─── API dla JafaApp (serwer ↔ serwer) ──────────────────────────────────────

def _event_json(church_id, ev, me):
    from app.events.routes import _event_view
    v = _event_view(church_id, ev, me)
    songs = [{
        'title': s['title'],
        'key': s['shown_key'] or s['key'],
        'bpm': s['bpm'] or None,
        'path': (f"/c/{church_id}/songs/{s['id']}/practice?t={s['transpose']}"
                 if s['in_library'] else None),
    } for s in v['songs']]
    my = v['my_signup']
    lineup = [{'name': a['user'].display_name if a['user'] else '?',
               'instrument': a['a'].instrument,
               'me': a['a'].user_id == me.id} for a in v['assignments']]
    return {
        'id': ev.id,
        'name': ev.name,
        'date': ev.date.isoformat(),
        'time': ev.time or '',
        'signup_deadline': ev.signup_deadline.isoformat() if ev.signup_deadline else None,
        'deadline_passed': v['deadline_passed'],
        'my_signup': None if my is None else bool(my.available),
        'my_instruments': v['my_instruments'],
        'lineup': lineup,
        'setlist': {'name': v['setlist'].name, 'songs': songs} if v['setlist'] else None,
        'path': f'/c/{church_id}/granie/{ev.id}',
    }


@jafa_bp.get('/api/jafa/overview')
@limiter.limit('120 per minute')
def overview():
    _, church_id = _cfg()
    me = _api_user(church_id)
    church = db.session.get(Church, church_id)
    events = (Event.query.filter(Event.church_id == church_id, Event.deleted.is_(False),
                                 Event.date >= date.today())
              .order_by(Event.date, Event.time).limit(4).all())
    return jsonify({
        'church': {'id': church_id, 'name': church.name if church else ''},
        'home_path': f'/c/{church_id}',
        'events': [_event_json(church_id, ev, me) for ev in events],
    })


@jafa_bp.post('/api/jafa/events/<int:eid>/signup')
@limiter.limit('60 per minute')
def signup(eid):
    _, church_id = _cfg()
    me = _api_user(church_id)
    ev = Event.query.filter_by(id=eid, church_id=church_id, deleted=False).first()
    if not ev:
        abort(404)
    body = request.get_json(silent=True) or {}
    if not isinstance(body.get('available'), bool):
        abort(400)
    s = EventSignup.query.filter_by(event_id=ev.id, user_id=me.id).first()
    if s is None:
        s = EventSignup(event_id=ev.id, user_id=me.id, available=body['available'])
        db.session.add(s)
    s.available = body['available']
    db.session.commit()
    return jsonify(_event_json(church_id, ev, me))


@jafa_bp.post('/api/jafa/members/remove')
@limiter.limit('60 per minute')
def remove_member():
    """Ktoś wypadł z przestrzeni Uwielbienie w JafaApp — traci dostęp do
    wspólnoty Jafa w Jonathanie (konto zostaje; admina nie ruszamy)."""
    secret, church_id = _cfg()
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        abort(403)
    verify(auth[7:], secret, 'api', API_TTL)
    sub = str((request.get_json(silent=True) or {}).get('subject') or '')[:64]
    ident = ExternalIdentity.query.filter_by(provider=PROVIDER, subject=sub).first()
    if ident:
        m = Membership.query.filter_by(user_id=ident.user_id, church_id=church_id).first()
        if m and m.role != 'admin':
            m.status = 'inactive'
            db.session.commit()
    return jsonify({'ok': True})
