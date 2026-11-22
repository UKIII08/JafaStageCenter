# TESTY INTEGRACJI Z JAFAAPP — wejście jednorazowym kluczem (bez logowania),
# łączenie kont po e-mailu, role z przestrzeni posługi, API dla JafaApp
# (granie, setlista, zgłoszenia) i to, że bez konfiguracji nic nie widać.
import json
import secrets
import time
from datetime import date, timedelta

import pytest

from app import create_app, db
from app.integrations.jafa import sign
from app.models import (Church, Event, ExternalIdentity, Membership,
                        StudioSetlist, User)

SECRET = 'x' * 40


@pytest.fixture()
def app():
    app = create_app('app.config.TestConfig')
    with app.app_context():
        church = Church(name='Jafa Warszawa', slug='jafa-warszawa')
        db.session.add(church)
        db.session.commit()
        app.config['JAFA_SECRET'] = SECRET
        app.config['JAFA_CHURCH_ID'] = church.id
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def token(typ='login', sub='jafa-1', email='ola@jafa.pl', name='Ola', role='muzyk',
          exp_in=60, jti=None, secret=SECRET):
    data = {'typ': typ, 'sub': sub, 'email': email, 'name': name, 'role': role,
            'exp': int(time.time()) + exp_in}
    if typ == 'login':
        data['jti'] = jti or secrets.token_hex(16)
    return sign(data, secret)


def api(client, method, path, body=None, **kw):
    headers = {'Authorization': f'Bearer {token(typ="api", **kw)}'}
    if method == 'get':
        return client.get(path, headers=headers)
    return client.post(path, headers=headers, data=json.dumps(body or {}),
                       content_type='application/json')


def church_id(app):
    return app.config['JAFA_CHURCH_ID']


# ─── Wejście ────────────────────────────────────────────────────────────────

def test_enter_creates_account_membership_and_session(app, client):
    cid = church_id(app)
    r = client.get(f'/integracja/jafa/wejdz?t={token()}&next=/c/{cid}/granie')
    assert r.status_code == 302 and r.headers['Location'].endswith(f'/c/{cid}/granie')
    u = User.query.filter_by(email='ola@jafa.pl').one()
    assert u.display_name == 'Ola'
    m = Membership.query.filter_by(user_id=u.id, church_id=cid).one()
    assert (m.role, m.status) == ('muzyk', 'active')
    # Zalogowany: panel wspólnoty się otwiera bez logowania
    assert client.get(f'/c/{cid}').status_code == 200
    with client.session_transaction() as sess:
        assert sess['lang'] == 'pl'


def test_same_key_works_only_once(app, client):
    t = token()
    assert client.get(f'/integracja/jafa/wejdz?t={t}').status_code == 302
    client.get('/logout')
    assert client.get(f'/integracja/jafa/wejdz?t={t}').status_code == 403


def test_rejects_bad_signature_expired_and_long_lived(app, client):
    assert client.get(f'/integracja/jafa/wejdz?t={token(secret="y" * 40)}').status_code == 403
    assert client.get(f'/integracja/jafa/wejdz?t={token(exp_in=-5)}').status_code == 403
    assert client.get(f'/integracja/jafa/wejdz?t={token(exp_in=3600)}').status_code == 403
    assert client.get(f'/integracja/jafa/wejdz?t={token(typ="api")}').status_code == 403
    assert client.get('/integracja/jafa/wejdz?t=smieci').status_code == 403
    assert User.query.count() == 0


def test_no_open_redirect(app, client):
    r = client.get(f'/integracja/jafa/wejdz?t={token()}&next=https://evil.example/x')
    assert r.headers['Location'].endswith(f'/c/{church_id(app)}')


def test_links_existing_account_by_email_and_keeps_it(app, client):
    client.post('/register', data={'email': 'ola@jafa.pl', 'password': 'haslo1234',
                                   'display_name': 'Ola z Jonathana'})
    client.get('/logout')
    existing = User.query.filter_by(email='ola@jafa.pl').one().id
    client.get(f'/integracja/jafa/wejdz?t={token(email="OLA@jafa.pl")}')
    assert User.query.count() == 1
    ident = ExternalIdentity.query.filter_by(provider='jafa', subject='jafa-1').one()
    assert ident.user_id == existing
    # Stare hasło dalej działa
    client.get('/logout')
    r = client.post('/login', data={'email': 'ola@jafa.pl', 'password': 'haslo1234'})
    assert r.status_code == 302


def test_role_follows_jafa_but_admin_is_kept(app, client):
    cid = church_id(app)
    client.get(f'/integracja/jafa/wejdz?t={token(role="prowadzacy")}')
    u = User.query.filter_by(email='ola@jafa.pl').one()
    assert Membership.query.filter_by(user_id=u.id, church_id=cid).one().role == 'prowadzacy'
    client.get(f'/integracja/jafa/wejdz?t={token(role="muzyk")}')
    assert Membership.query.filter_by(user_id=u.id, church_id=cid).one().role == 'muzyk'
    m = Membership.query.filter_by(user_id=u.id, church_id=cid).one()
    m.role = 'admin'
    db.session.commit()
    client.get(f'/integracja/jafa/wejdz?t={token(role="muzyk")}')
    assert Membership.query.filter_by(user_id=u.id, church_id=cid).one().role == 'admin'


def test_disabled_without_config(app, client):
    app.config['JAFA_SECRET'] = ''
    assert client.get(f'/integracja/jafa/wejdz?t={token()}').status_code == 404
    assert api(client, 'get', '/api/jafa/overview').status_code == 404


def test_login_page_has_no_jafa_button(app, client):
    html = client.get('/login').get_data(as_text=True)
    assert 'Jafa' not in html and 'jafa' not in html


# ─── API ────────────────────────────────────────────────────────────────────

def make_event(app, days=7, with_setlist=True):
    cid = church_id(app)
    sl = None
    if with_setlist:
        sl = StudioSetlist(church_id=cid, name='Sobota', date='',
                           songs=json.dumps([{'title': 'Oceans', 'key': 'D', 'bpm': 66, 'transpose': 2}]))
        db.session.add(sl)
        db.session.flush()
    ev = Event(church_id=cid, name='Sobota Jafy', date=date.today() + timedelta(days=days),
               time='10:00', signup_deadline=date.today() + timedelta(days=3),
               setlist_id=sl.id if sl else None)
    db.session.add(ev)
    db.session.commit()
    return ev.id


def test_api_requires_valid_key(app, client):
    assert client.get('/api/jafa/overview').status_code == 403
    r = client.get('/api/jafa/overview', headers={'Authorization': f'Bearer {token(typ="login")}'})
    assert r.status_code == 403


def test_overview_with_setlist_and_signup(app, client):
    eid = make_event(app)
    make_event(app, days=-3)   # przeszłe — nie pokazujemy
    r = api(client, 'get', '/api/jafa/overview')
    assert r.status_code == 200
    data = r.get_json()
    assert [e['id'] for e in data['events']] == [eid]
    ev = data['events'][0]
    assert ev['name'] == 'Sobota Jafy' and ev['time'] == '10:00'
    assert ev['my_signup'] is None and ev['deadline_passed'] is False
    assert ev['setlist']['songs'][0]['title'] == 'Oceans'
    assert ev['setlist']['songs'][0]['key'] == 'E'   # D +2
    assert ev['path'] == f'/c/{church_id(app)}/granie/{eid}'

    r = api(client, 'post', f'/api/jafa/events/{eid}/signup', {'available': True})
    assert r.status_code == 200 and r.get_json()['my_signup'] is True
    r = api(client, 'post', f'/api/jafa/events/{eid}/signup', {'available': False})
    assert r.get_json()['my_signup'] is False
    assert api(client, 'post', f'/api/jafa/events/{eid}/signup', {'available': 'tak'}).status_code == 400
    assert api(client, 'post', '/api/jafa/events/999999/signup', {'available': True}).status_code == 404


def test_remove_member_keeps_account_but_drops_access(app, client):
    cid = church_id(app)
    client.get(f'/integracja/jafa/wejdz?t={token()}')
    client.get('/logout')
    r = api(client, 'post', '/api/jafa/members/remove', {'subject': 'jafa-1'}, sub='lider-1', role='prowadzacy',
            email='lider@jafa.pl')
    assert r.status_code == 200
    u = User.query.filter_by(email='ola@jafa.pl').one()
    assert Membership.query.filter_by(user_id=u.id, church_id=cid).one().status == 'inactive'
    # Po ponownym dodaniu do przestrzeni w JafaApp wejście przywraca dostęp
    client.get(f'/integracja/jafa/wejdz?t={token()}')
    assert Membership.query.filter_by(user_id=u.id, church_id=cid).one().status == 'active'



def test_parallel_first_request_reuses_account(app, client, monkeypatch):
    """Dwa równoległe pierwsze zapytania: to drugie nie wywala się na „e-mail zajęty”,
    tylko bierze konto założone przed chwilą przez pierwsze."""
    import app.integrations.jafa as j
    db.session.add(User(email='ola@jafa.pl', display_name='Ola', password_hash='x'))
    db.session.commit()
    real = j._find_by_email
    calls = {'n': 0}

    def miss_first(email):
        calls['n'] += 1
        return None if calls['n'] == 1 else real(email)
    monkeypatch.setattr(j, '_find_by_email', miss_first)
    u = j.resolve_user({'sub': 'jafa-1', 'email': 'ola@jafa.pl', 'name': 'Ola', 'role': 'muzyk'}, church_id(app))
    assert calls['n'] == 2   # pierwsza próba trafiła na wyścig, druga wzięła istniejące konto
    assert User.query.count() == 1 and u.email == 'ola@jafa.pl'
    assert ExternalIdentity.query.filter_by(subject='jafa-1').one().user_id == u.id
