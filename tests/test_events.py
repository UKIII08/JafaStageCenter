# TESTY GRANIA — organizacja służby: tworzenie, zgłoszenia dostępności
# (także po terminie), obsada z instrumentami, setlista + tryb nauki.
import json
from datetime import date, timedelta

import pytest

from app import create_app, db
from app.models import Church, Event, EventAssignment, Invitation, \
    StudioSetlist, User


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


def setup_church_with_musician(app, client):
    """Admin + zaproszony muzyk; zwraca (church_id, kod_zaproszenia)."""
    register(client, 'lider@x.pl', 'Lider')
    client.post('/church/create', data={'name': 'Zbor X'},
                follow_redirects=True)
    with app.app_context():
        cid = Church.query.filter_by(name='Zbor X').first().id
    client.post(f'/c/{cid}/team/invite', data={'role': 'muzyk'},
                follow_redirects=True)
    with app.app_context():
        code = Invitation.query.filter_by(church_id=cid).first().code
    client.get('/logout')
    register(client, 'muzyk@x.pl', 'Marek')
    client.get(f'/join/{code}', follow_redirects=True)
    client.get('/logout')
    return cid


def test_event_lifecycle_and_learning_view(app, client):
    cid = setup_church_with_musician(app, client)

    # prowadzący tworzy granie z terminem zgłoszeń
    login(client, 'lider@x.pl')
    d = (date.today() + timedelta(days=7)).isoformat()
    deadline = (date.today() + timedelta(days=3)).isoformat()
    client.post(f'/c/{cid}/granie', data={
        'name': 'Niedziela poranna', 'date': d, 'time': '10:00',
        'signup_deadline': deadline}, follow_redirects=True)
    with app.app_context():
        ev = Event.query.filter_by(church_id=cid).first()
        assert ev.name == 'Niedziela poranna' and ev.time == '10:00'
        eid = ev.id

    # setlista ze Studia podpięta pod granie
    client.post(f'/c/{cid}/studio/add_song', data={
        'title': 'Pieśń', 'content': '[G]Alleluja [C]Panu'})
    with app.app_context():
        from app.models import Song
        sid = Song.query.filter_by(church_id=cid).first().id
        sl = StudioSetlist(church_id=cid, name='Setlista N', date='',
                           songs=json.dumps([{'id': sid, 'title': 'Pieśń',
                                              'key': 'G', 'bpm': 0,
                                              'transpose': 2}]))
        db.session.add(sl)
        db.session.commit()
        slid = sl.id
    client.post(f'/c/{cid}/granie/{eid}/setlist', data={'setlist_id': slid})
    client.get('/logout')

    # muzyk: zgłasza dostępność i widzi tryb nauki
    login(client, 'muzyk@x.pl')
    client.post(f'/c/{cid}/granie/{eid}/signup',
                data={'available': '1', 'comment': 'moge do 12'})
    r = client.get(f'/c/{cid}/granie/{eid}')
    assert 'Pieśń'.encode() in r.data
    assert b'(oryg. G)' in r.data   # transpozycja +2 pokazana (G -> A)
    assert f'/songs/{sid}/practice?t=2'.encode() in r.data
    client.get('/logout')

    # prowadzący układa obsadę: Marek na basie i na gitarze
    login(client, 'lider@x.pl')
    with app.app_context():
        uid = User.query.filter_by(email='muzyk@x.pl').first().id
    client.post(f'/c/{cid}/granie/{eid}/assign',
                data={'user_id': uid, 'instrument': 'bas'})
    client.post(f'/c/{cid}/granie/{eid}/assign',
                data={'user_id': uid, 'instrument': 'gitara'})
    with app.app_context():
        assert EventAssignment.query.filter_by(event_id=eid).count() == 2
    client.get('/logout')

    # muzyk widzi na czym gra
    login(client, 'muzyk@x.pl')
    r = client.get(f'/c/{cid}/granie/{eid}')
    assert b'bas' in r.data and b'gitara' in r.data


def test_signup_after_deadline_still_allowed(app, client):
    cid = setup_church_with_musician(app, client)
    login(client, 'lider@x.pl')
    client.post(f'/c/{cid}/granie', data={
        'name': 'Test', 'date': (date.today() + timedelta(days=2)).isoformat(),
        'signup_deadline': (date.today() - timedelta(days=1)).isoformat()},
        follow_redirects=True)
    with app.app_context():
        eid = Event.query.filter_by(church_id=cid).first().id
    client.get('/logout')
    login(client, 'muzyk@x.pl')
    r = client.get(f'/c/{cid}/granie/{eid}')
    assert 'po terminie'.encode() in r.data
    r = client.post(f'/c/{cid}/granie/{eid}/signup',
                    data={'available': '0'}, follow_redirects=True)
    assert r.status_code == 200
    assert 'nie mogę'.encode() in r.data


def test_events_tenancy_and_roles(app, client):
    cid = setup_church_with_musician(app, client)
    # muzyk nie tworzy grania ani nie układa obsady
    login(client, 'muzyk@x.pl')
    r = client.post(f'/c/{cid}/granie', data={
        'name': 'X', 'date': date.today().isoformat()})
    assert r.status_code == 403
    client.get('/logout')
    # obca wspólnota nie widzi grań
    register(client, 'obcy@y.pl', 'Obcy')
    client.post('/church/create', data={'name': 'Zbor Y'},
                follow_redirects=True)
    assert client.get(f'/c/{cid}/granie').status_code == 403
