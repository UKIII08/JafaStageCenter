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
    assert b'(orig. G)' in r.data   # transpose +2 shown (G -> A)
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
    assert b'past due' in r.data
    r = client.post(f'/c/{cid}/granie/{eid}/signup',
                    data={'available': '0'}, follow_redirects=True)
    assert r.status_code == 200
    assert b"can&#39;t" in r.data


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


def test_studio_event_mode_saves_and_attaches(app, client):
    """Zapis setlisty w Studiu w trybie ?granie= podpina ją pod granie."""
    cid = setup_church_with_musician(app, client)
    login(client, 'lider@x.pl')
    client.post(f'/c/{cid}/granie', data={
        'name': 'Wieczór chwały',
        'date': (date.today() + timedelta(days=5)).isoformat()},
        follow_redirects=True)
    with app.app_context():
        eid = Event.query.filter_by(church_id=cid).first().id

    # Studio w trybie grania: baner + kontekst w JS
    r = client.get(f'/c/{cid}/studio?granie={eid}')
    assert r.status_code == 200
    assert f'window.JAFA_EVENT = {{"date"'.encode() in r.data
    assert f'"id": {eid}'.encode() in r.data

    # zapis setlisty z event_id (tak wysyła wrapper fetch w szablonie)
    r = client.post(f'/c/{cid}/studio/api/setlist-history', json={
        'name': 'Set X', 'date': '2026-07-20', 'event_id': eid,
        'songs': [{'id': 'a', 'title': 'P', 'key': 'G', 'bpm': 0,
                   'transpose': 1}]})
    data = r.get_json()
    assert data['attached_event'] is True
    with app.app_context():
        ev = db.session.get(Event, eid)
        assert ev.setlist_id == data['id']

    # cudze granie nie da się podpiąć (tenancy przez church filter)
    client.get('/logout')
    register(client, 'obcy2@y.pl', 'Obcy')
    client.post('/church/create', data={'name': 'Zbor Z'},
                follow_redirects=True)
    with app.app_context():
        cid_z = Church.query.filter_by(name='Zbor Z').first().id
    r = client.post(f'/c/{cid_z}/studio/api/setlist-history', json={
        'name': 'Hack', 'date': '', 'event_id': eid, 'songs': []})
    assert r.get_json()['attached_event'] is False


def test_team_prefs_endpoint(app, client):
    cid = setup_church_with_musician(app, client)
    # muzyk zapisuje swoja tonacje w cwiczeniu
    login(client, 'lider@x.pl')
    client.post(f'/c/{cid}/studio/add_song', data={
        'title': 'Pref', 'content': '[G]La [C]la'})
    with app.app_context():
        from app.models import Song
        sid = Song.query.filter_by(church_id=cid, title='Pref').first().id
    client.get('/logout')
    login(client, 'muzyk@x.pl')
    client.post(f'/c/{cid}/songs/{sid}/personal', json={'transpose': 2})
    client.get('/logout')
    # prowadzacy widzi preferencje
    login(client, 'lider@x.pl')
    d = client.get(f'/c/{cid}/studio/api/song/{sid}/team-prefs').get_json()
    assert d['song_key'] == 'G'
    assert any(p['name'] == 'Marek' and (p['key'] == 'A'
               or p['transpose'] == 2) for p in d['prefs'])
