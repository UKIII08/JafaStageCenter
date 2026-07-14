# TESTY TENANCY (M0) — twarda zasada z PLAN.md: użytkownik wspólnoty A
# nie ma ŻADNEGO dostępu do danych wspólnoty B. Ten plik rośnie z każdym
# nowym modułem (piosenki, setlisty, live, sync).
import pytest

from app import create_app, db
from app.models import Church, Membership, Invitation


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


def create_church(client, name):
    return client.post('/church/create', data={'name': name},
                       follow_redirects=True)


def church_id_by_name(app, name):
    with app.app_context():
        return Church.query.filter_by(name=name).first().id


def test_two_churches_are_isolated(app, client):
    # wspólnota A (user A = admin)
    register(client, 'a@a.pl', 'Adam')
    create_church(client, 'Zbor A')
    id_a = church_id_by_name(app, 'Zbor A')
    client.get('/logout')

    # wspólnota B (user B = admin)
    register(client, 'b@b.pl', 'Beata')
    create_church(client, 'Zbor B')
    id_b = church_id_by_name(app, 'Zbor B')

    # B NIE widzi niczego we wspólnocie A
    assert client.get(f'/c/{id_a}').status_code == 403
    assert client.get(f'/c/{id_a}/team').status_code == 403
    assert client.post(f'/c/{id_a}/team/invite',
                       data={'role': 'muzyk'}).status_code == 403
    # B widzi swoją
    assert client.get(f'/c/{id_b}').status_code == 200


def test_join_flow_and_roles(app, client):
    register(client, 'admin@zbor.pl', 'Admin')
    create_church(client, 'Zbor X')
    id_x = church_id_by_name(app, 'Zbor X')

    # admin generuje link
    r = client.post(f'/c/{id_x}/team/invite', data={'role': 'muzyk'},
                    follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        code = Invitation.query.filter_by(church_id=id_x).first().code
    client.get('/logout')

    # muzyk dołącza przez kod
    register(client, 'muzyk@zbor.pl', 'Marek')
    r = client.get(f'/join/{code}', follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        m = Membership.query.join(Church).filter(
            Church.id == id_x).filter(Membership.role == 'muzyk').first()
        assert m is not None

    # muzyk widzi zespół, ale NIE może zapraszać (rola za niska)
    assert client.get(f'/c/{id_x}/team').status_code == 200
    assert client.post(f'/c/{id_x}/team/invite',
                       data={'role': 'muzyk'}).status_code == 403


def test_invalid_invite_code(client):
    register(client, 'x@x.pl')
    assert client.get('/join/ZLYKOD').status_code == 404


def test_anonymous_redirected_to_login(client):
    r = client.get('/', follow_redirects=False)
    assert r.status_code == 302 and '/login' in r.headers['Location']


def test_profile_prefs_roundtrip(app, client):
    register(client, 'p@p.pl', 'Piotr')
    create_church(client, 'Zbor P')
    cid = church_id_by_name(app, 'Zbor P')
    r = client.post(f'/c/{cid}/profile', data={
        'name': 'Piotrek', 'instrument': 'gitara', 'notation': 'polish',
        'capo_default': '2', 'show_chords': 'on', 'lowercase_minor': 'on'},
        follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        from app.models import Profile
        p = Profile.query.filter_by(church_id=cid).first()
        assert p.instrument == 'gitara'
        assert p.prefs['notation'] == 'polish'
        assert p.prefs['capo_default'] == 2
        assert p.prefs['lowercase_minor'] is True
        assert p.prefs['beginner_mode'] is False


def test_owner_cannot_be_demoted_or_removed(app, client):
    register(client, 'owner@o.pl', 'Owner')
    create_church(client, 'Zbor O')
    cid = church_id_by_name(app, 'Zbor O')
    with app.app_context():
        m = Membership.query.filter_by(church_id=cid).first()
        mid = m.id
    client.post(f'/c/{cid}/team/{mid}/role', data={'role': 'muzyk'},
                follow_redirects=True)
    client.post(f'/c/{cid}/team/{mid}/remove', follow_redirects=True)
    with app.app_context():
        m = db.session.get(Membership, mid)
        assert m.role == 'admin' and m.status == 'active'


def test_member_management_cross_tenant_denied(app, client):
    register(client, 'adm1@x.pl'); create_church(client, 'Zbor 1')
    id1 = church_id_by_name(app, 'Zbor 1')
    with app.app_context():
        mid1 = Membership.query.filter_by(church_id=id1).first().id
    client.get('/logout')
    register(client, 'adm2@x.pl'); create_church(client, 'Zbor 2')
    # admin zboru 2 nie może zarządzać członkiem zboru 1
    assert client.post(f'/c/{id1}/team/{mid1}/role',
                       data={'role': 'muzyk'}).status_code == 403
    assert client.post(f'/c/{id1}/team/{mid1}/remove').status_code == 403


def test_password_reset_flow(app, client):
    register(client, 'r@r.pl', 'Renia')
    client.get('/logout')
    r = client.post('/reset', data={'email': 'r@r.pl'}, follow_redirects=True)
    assert 'wysłaliśmy link'.encode() in r.data or b'wys' in r.data
    # token generowany tak jak w aplikacji
    with app.app_context():
        from app.auth.routes import _reset_serializer
        from app.models import User
        uid = User.query.filter_by(email='r@r.pl').first().id
        token = _reset_serializer().dumps(uid)
    r = client.post(f'/reset/{token}', data={'password': 'nowehaslo1'},
                    follow_redirects=True)
    assert r.status_code == 200
    r = login(client, 'r@r.pl')   # stare hasło już nie działa
    assert 'Nieprawid'.encode() in r.data
    r = client.post('/login', data={'email': 'r@r.pl',
                    'password': 'nowehaslo1'}, follow_redirects=True)
    assert 'Nieprawid'.encode() not in r.data


def test_2fa_full_cycle(app, client):
    import pyotp
    register(client, 'tfa@t.pl', 'Tefa')
    create_church(client, 'Zbor T')
    # włącz 2FA
    client.post('/account/2fa/enable', follow_redirects=True)
    with client.session_transaction() as s:
        secret = s['totp_setup']
    code = pyotp.TOTP(secret).now()
    r = client.post('/account/2fa/confirm', data={'code': code},
                    follow_redirects=True)
    assert 'włączona'.encode() in r.data
    # wyloguj i zaloguj: hasło NIE wystarcza
    client.get('/logout')
    r = client.post('/login', data={'email': 'tfa@t.pl',
                    'password': 'haslo1234'}, follow_redirects=False)
    assert '/login/2fa' in r.headers['Location']
    # bez kodu brak dostępu
    assert client.get('/').status_code == 302
    # poprawny kod wpuszcza
    code = pyotp.TOTP(secret).now()
    r = client.post('/login/2fa', data={'code': code}, follow_redirects=True)
    assert r.status_code == 200
    assert client.get('/').status_code in (200, 302)  # dashboard/redirect do zboru


def test_2fa_wrong_code_rejected(app, client):
    import pyotp
    register(client, 'tfa2@t.pl')
    client.post('/account/2fa/enable')
    with client.session_transaction() as s:
        secret = s['totp_setup']
    client.post('/account/2fa/confirm', data={'code': pyotp.TOTP(secret).now()})
    client.get('/logout')
    client.post('/login', data={'email': 'tfa2@t.pl', 'password': 'haslo1234'})
    r = client.post('/login/2fa', data={'code': '000000'},
                    follow_redirects=True)
    assert 'Nieprawidłowy kod'.encode() in r.data
    with client.session_transaction() as s:
        assert 'user_id' not in s
