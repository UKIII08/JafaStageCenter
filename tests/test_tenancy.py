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
