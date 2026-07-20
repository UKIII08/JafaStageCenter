# Testy M3: tryb ćwiczenia, "moje tonacje", podpowiedzi dla prowadzącego.
import pytest

from app import create_app, db
from app.models import Song, SongPersonal, Invitation


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


def setup(client, app):
    client.post('/register', data={'email': 'l@l.pl', 'password': 'haslo1234',
                                   'display_name': 'Lider'})
    client.post('/church/create', data={'name': 'Zbor'})
    with app.app_context():
        from app.models import Church
        cid = Church.query.first().id
    client.post(f'/c/{cid}/songs/new', data={
        'title': 'Pieśń', 'content': 'Zwrotka\n[G]Alleluja [C]amen', 'key': 'G',
        'bpm': '80'})
    with app.app_context():
        sid = Song.query.first().id
    return cid, sid


def test_personal_transpose_saved_and_applied(app, client):
    cid, sid = setup(client, app)
    # zapis mojej tonacji +2
    d = client.post(f'/c/{cid}/songs/{sid}/personal',
                    json={'transpose': 2}).get_json()
    assert d['preferred_key'] == 'A'      # G+2
    # ćwiczenie otwiera się w mojej tonacji
    r = client.get(f'/c/{cid}/songs/{sid}/practice')
    page = r.get_data(as_text=True)
    assert '>A<' in page and 'chord-pair' in page   # akord A (G+2)
    # notatka
    client.post(f'/c/{cid}/songs/{sid}/personal', json={'note': 'wejście na 3'})
    r = client.get(f'/c/{cid}/songs/{sid}/practice')
    assert 'wejście na 3' in r.get_data(as_text=True)


def test_section_note_saved_and_shown(app, client):
    cid, sid = setup(client, app)
    # notatka do konkretnej sekcji (kafelka) — jak w widoku live muzyka
    d = client.post(f'/c/{cid}/songs/{sid}/personal',
                    json={'section': 0, 'section_note': 'graj cicho tu'}).get_json()
    assert d['status'] == 'ok'
    with app.app_context():
        import json
        sp = SongPersonal.query.first()
        assert json.loads(sp.section_notes) == {'0': 'graj cicho tu'}
    # widoczna po ponownym wejściu w tryb ćwiczenia
    r = client.get(f'/c/{cid}/songs/{sid}/practice')
    assert 'graj cicho tu' in r.get_data(as_text=True)
    # pusta notatka usuwa wpis
    client.post(f'/c/{cid}/songs/{sid}/personal',
                json={'section': 0, 'section_note': '  '})
    with app.app_context():
        import json
        sp = SongPersonal.query.first()
        assert json.loads(sp.section_notes) == {}


def test_personal_is_per_user(app, client):
    cid, sid = setup(client, app)
    client.post(f'/c/{cid}/songs/{sid}/personal', json={'transpose': 2})
    # zaproszenie drugiego muzyka
    client.post(f'/c/{cid}/team/invite', data={'role': 'muzyk'})
    with app.app_context():
        code = Invitation.query.first().code
    client.get('/logout')
    client.post('/register', data={'email': 'm@m.pl', 'password': 'haslo1234',
                                   'display_name': 'Marta'})
    client.get(f'/join/{code}')
    # Marta ma własną (pustą) preferencję — widzi oryginał G
    r = client.get(f'/c/{cid}/songs/{sid}/practice')
    assert '>G<' in r.get_data(as_text=True)
    client.post(f'/c/{cid}/songs/{sid}/personal', json={'transpose': -2})
    with app.app_context():
        prefs = {sp.preferred_key for sp in SongPersonal.query.all()}
        assert prefs == {'A', 'F'}    # Lider G+2=A, Marta G-2=F


def test_leader_sees_team_hints(app, client):
    cid, sid = setup(client, app)
    # muzyk ustawia preferencję
    client.post(f'/c/{cid}/team/invite', data={'role': 'muzyk'})
    with app.app_context():
        code = Invitation.query.first().code
    client.get('/logout')
    client.post('/register', data={'email': 'w@w.pl', 'password': 'haslo1234',
                                   'display_name': 'Wokalistka'})
    client.get(f'/join/{code}')
    client.post(f'/c/{cid}/songs/{sid}/personal', json={'transpose': 3})
    client.get('/logout')
    # prowadzący widzi podpowiedź w setliście
    client.post('/login', data={'email': 'l@l.pl', 'password': 'haslo1234'})
    client.post(f'/c/{cid}/setlists', data={'name': 'X'})
    with app.app_context():
        from app.models import Setlist
        slid = Setlist.query.first().id
    client.post(f'/c/{cid}/setlists/{slid}/items',
                data={'action': 'add', 'song_id': sid})
    r = client.get(f'/c/{cid}/setlists/{slid}')
    page = r.get_data(as_text=True)
    assert 'Wokalistka woli Bb' in page    # G+3


def test_personal_tenancy(app, client):
    cid, sid = setup(client, app)
    client.get('/logout')
    client.post('/register', data={'email': 'obcy@o.pl',
                                   'password': 'haslo1234',
                                   'display_name': 'Obcy'})
    client.post('/church/create', data={'name': 'Obcy Zbor'})
    assert client.get(f'/c/{cid}/songs/{sid}/practice').status_code == 403
    assert client.post(f'/c/{cid}/songs/{sid}/personal',
                       json={'transpose': 1}).status_code == 403
