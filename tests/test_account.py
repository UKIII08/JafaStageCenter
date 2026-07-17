# TESTY KONTA — usuwanie konta (RODO), weryfikacja e-mail, strony prawne.
import pytest

from app import create_app, db
from app.models import (Church, Event, EventSignup, Membership, Profile,
                        Song, SongPersonal, User, Invitation)


@pytest.fixture()
def app():
    app = create_app('app.config.TestConfig')
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def register(client, email, name='Test'):
    return client.post('/register', data={
        'email': email, 'password': 'haslo1234', 'display_name': name},
        follow_redirects=True)


def login(client, email):
    return client.post('/login', data={
        'email': email, 'password': 'haslo1234'}, follow_redirects=True)


def test_legal_pages(client):
    assert client.get('/privacy').status_code == 200
    assert client.get('/terms').status_code == 200


def test_email_verification_flow(app, client):
    register(client, 'v@v.pl', 'Vera')
    with app.app_context():
        user = User.query.filter_by(email='v@v.pl').first()
        assert user.email_verified_at is None
        from app.auth.routes import _verify_serializer
        token = _verify_serializer().dumps(user.id)
    r = client.get(f'/verify/{token}', follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        assert User.query.filter_by(
            email='v@v.pl').first().email_verified_at is not None
    # zepsuty token nie wywala się, tylko komunikat
    r = client.get('/verify/zly-token', follow_redirects=True)
    assert r.status_code == 200


def test_account_delete_sole_owner_purges_church(app, client):
    register(client, 'solo@x.pl', 'Solo')
    client.post('/church/create', data={'name': 'Solo Zbor'},
                follow_redirects=True)
    with app.app_context():
        cid = Church.query.filter_by(name='Solo Zbor').first().id
    client.post(f'/c/{cid}/studio/add_song', data={
        'title': 'P', 'content': '[G]La'})
    # złe hasło = brak usunięcia
    r = client.post('/account/delete', data={'password': 'zle-haslo'},
                    follow_redirects=True)
    with app.app_context():
        assert User.query.filter_by(email='solo@x.pl').first() is not None
    # dobre hasło = konto + cała wspólnota znikają
    client.post('/account/delete', data={'password': 'haslo1234'},
                follow_redirects=True)
    with app.app_context():
        assert User.query.filter_by(email='solo@x.pl').first() is None
        assert db.session.get(Church, cid) is None
        assert Song.query.filter_by(church_id=cid).count() == 0
        assert Membership.query.filter_by(church_id=cid).count() == 0


def test_account_delete_blocked_when_others_in_church(app, client):
    register(client, 'wl@x.pl', 'Wlasciciel')
    client.post('/church/create', data={'name': 'Duzy Zbor'},
                follow_redirects=True)
    with app.app_context():
        cid = Church.query.filter_by(name='Duzy Zbor').first().id
    client.post(f'/c/{cid}/team/invite', data={'role': 'muzyk'},
                follow_redirects=True)
    with app.app_context():
        code = Invitation.query.filter_by(church_id=cid).first().code
    client.get('/logout')
    register(client, 'czlonek@x.pl', 'Czlonek')
    client.get(f'/join/{code}', follow_redirects=True)
    client.get('/logout')
    # właściciel z członkami nie może usunąć konta
    login(client, 'wl@x.pl')
    r = client.post('/account/delete', data={'password': 'haslo1234'},
                    follow_redirects=True)
    with app.app_context():
        assert User.query.filter_by(email='wl@x.pl').first() is not None
    # ale zwykły członek może — a wspólnota zostaje
    client.get('/logout')
    login(client, 'czlonek@x.pl')
    client.post('/account/delete', data={'password': 'haslo1234'},
                follow_redirects=True)
    with app.app_context():
        assert User.query.filter_by(email='czlonek@x.pl').first() is None
        assert db.session.get(Church, cid) is not None


def test_reset_token_single_use(app, client):
    # Regresja: token resetu jest jednorazowy — po zmianie hasła stary link
    # przestaje działać (nie da się nim ponownie przejąć konta).
    register(client, 'r@r.pl')
    client.get('/logout')
    with app.app_context():
        from app.auth.routes import _reset_serializer, _pw_key
        u = User.query.filter_by(email='r@r.pl').first()
        token = _reset_serializer().dumps({'uid': u.id, 'k': _pw_key(u)})
    r = client.post(f'/reset/{token}', data={'password': 'noweHaslo123'},
                    follow_redirects=True)
    assert r.status_code == 200
    # ten sam token po zmianie hasła jest już nieważny
    r2 = client.get(f'/reset/{token}', follow_redirects=True)
    assert b'request a new one' in r2.data


def test_open_redirect_blocked(app, client):
    # Regresja: ?next / lang nie mogą przekierować na obcy host (phishing).
    register(client, 'o@o.pl')
    client.get('/logout')
    r = client.post('/login?next=https://evil.com',
                    data={'email': 'o@o.pl', 'password': 'haslo1234'})
    assert r.status_code == 302 and 'evil.com' not in r.headers['Location']
    r2 = client.get('/lang/en?next=https://evil.com')
    assert r2.status_code == 302 and 'evil.com' not in r2.headers['Location']
