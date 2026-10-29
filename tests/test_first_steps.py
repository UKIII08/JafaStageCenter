# Pierwsze kroki muzyka, „Możesz grać?" na pulpicie, powiadomienia e-mail.
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


@pytest.fixture()
def mails(monkeypatch):
    sent = []
    monkeypatch.setattr('app.notify.send_email', lambda to, subj, body: sent.append((to, subj, body)))
    return sent


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


def test_new_service_mails_the_team_but_not_the_author(app, client, mails):
    cid = leader_and_musician(client)
    login(client, 'l@l.pl')
    ev = new_service(client, cid)
    assert [m[0] for m in mails] == ['m@m.pl']
    assert f'/granie/{ev.id}' in mails[0][2] and '/profile' in mails[0][2]


def test_assigned_part_mails_the_person(app, client, mails):
    cid = leader_and_musician(client)
    login(client, 'l@l.pl')
    ev = new_service(client, cid)
    mails.clear()
    ola = User.query.filter_by(email='m@m.pl').first()
    client.post(f'/c/{cid}/granie/{ev.id}/assign', data={'user_id': ola.id, 'instrument': 'gitara'})
    assert len(mails) == 1 and mails[0][0] == 'm@m.pl' and 'guitar' in mails[0][2].lower()


def test_mails_can_be_turned_off(app, client, mails):
    cid = leader_and_musician(client)
    assert client.post('/account/notify', json={'on': False}).get_json()['on'] is False
    login(client, 'l@l.pl')
    new_service(client, cid)
    assert mails == []


def test_musician_answers_from_dashboard(app, client, mails):
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
