# Pierwsze kroki muzyka i „Możesz grać?" na pulpicie.
from datetime import date, timedelta

import pytest

from app import create_app, db
from app.models import Church, Event, EventSignup, Invitation, User


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


def leader_and_musician(client):
    client.post('/register', data={'email': 'l@l.pl', 'password': 'haslo1234', 'display_name': 'Lider'})
    client.post('/church/create', data={'name': 'Zbor'})
    cid = Church.query.first().id
    client.post(f'/c/{cid}/team/invite', data={'role': 'muzyk'})
    code = Invitation.query.order_by(Invitation.id.desc()).first().code
    client.get('/logout')
    client.post('/register', data={'email': 'm@m.pl', 'password': 'haslo1234', 'display_name': 'Ola'})
    client.get(f'/join/{code}')
    return cid


def login(client, email):
    client.get('/logout')
    client.post('/login', data={'email': email, 'password': 'haslo1234'})


def new_service(client, cid, days=7):
    client.post(f'/c/{cid}/granie', data={'name': 'Niedziela', 'date': (date.today() + timedelta(days=days)).isoformat(),
                                          'signup_deadline': (date.today() + timedelta(days=3)).isoformat()})
    return Event.query.order_by(Event.id.desc()).first()


def test_musician_answers_from_dashboard(app, client):
    cid = leader_and_musician(client)
    login(client, 'l@l.pl')
    ev = new_service(client, cid)
    login(client, 'm@m.pl')
    page = client.get(f'/c/{cid}').get_data(as_text=True)
    assert 'id="first-steps"' in page and f'/granie/{ev.id}/signup' in page
    r = client.post(f'/c/{cid}/granie/{ev.id}/signup', data={'available': '1', 'back': 'home'})
    assert r.status_code == 302 and r.headers['Location'].endswith(f'/c/{cid}')
    assert EventSignup.query.filter_by(event_id=ev.id).first().available is True
    page = client.get(f'/c/{cid}').get_data(as_text=True)
    assert f'/granie/{ev.id}/signup' not in page        # już odpowiedziała


def test_first_steps_not_for_admin(app, client):
    client.post('/register', data={'email': 'l@l.pl', 'password': 'haslo1234', 'display_name': 'Lider'})
    client.post('/church/create', data={'name': 'Zbor'})
    cid = Church.query.first().id
    assert 'id="first-steps"' not in client.get(f'/c/{cid}').get_data(as_text=True)
