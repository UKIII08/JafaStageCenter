# Testy pokoju LIVE (M2): cykl życia, slajdy, przejścia, ekrany, tenancy.
import pytest

from app import create_app, db
from app.live import state as live_state
from app.models import LiveSession, ScreenToken, Setlist, Song


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


SONG_A = "Zwrotka\n[G]Alleluja [C]Panu [D]dziś\n\nRefren\n[G]Amen [D]amen"
SONG_B = "Zwrotka\n[Am]Wielki [F]Bóg [C]nasz [G]Pan"


def setup_live(client, app):
    client.post('/register', data={'email': 'lead@l.pl', 'password': 'haslo1234',
                                   'display_name': 'Lider'})
    client.post('/church/create', data={'name': 'Zbor Live'})
    with app.app_context():
        from app.models import Church
        cid = Church.query.first().id
    client.post(f'/c/{cid}/songs/new', data={'title': 'A', 'content': SONG_A,
                                             'key': 'G', 'bpm': '80'})
    client.post(f'/c/{cid}/songs/new', data={'title': 'B', 'content': SONG_B,
                                             'key': 'Am'})
    return cid, None


def test_old_live_is_retired_studio_is_the_only_source(app, client):
    # Stary LIVE (ze starej setlisty) i Studio wysyłały slajdy na te same
    # ekrany. Teraz jedynym źródłem jest Studio.
    cid, _ = setup_live(client, app)
    r = client.post(f'/c/{cid}/live/start/123')
    assert r.status_code == 302 and '/studio' in r.headers['Location']
    for path in ('slide', 'transition', 'blackout', 'logo'):
        assert client.post(f'/c/{cid}/live/{path}', json={}).status_code == 410
    with app.app_context():
        assert LiveSession.query.count() == 0
    assert live_state.get_state(cid) is None
    # Studio dalej wysyła slajdy
    assert client.post(f'/c/{cid}/studio/send_text',
                       json={'text': '[G]Amen', 'song_title': 'A', 'setlist': [{'title': 'A'}]}).get_json()['status'] == 'ok'
    assert client.get(f'/api/live/current/{cid}').get_json()['active'] is True


def test_live_requires_role_and_tenancy(app, client):
    cid, _ = setup_live(client, app)
    client.get('/logout')
    # obcy admin z innej wspólnoty
    client.post('/register', data={'email': 'obcy@o.pl', 'password': 'haslo1234',
                                   'display_name': 'Obcy'})
    client.post('/church/create', data={'name': 'Zbor Obcy'})
    assert client.post(f'/c/{cid}/live/end').status_code == 403
    assert client.get(f'/c/{cid}/live').status_code == 403
    assert client.get(f'/api/live/current/{cid}').status_code == 403


def test_screen_tokens(app, client):
    cid, slid = setup_live(client, app)
    client.post(f'/c/{cid}/screens', data={'type': 'projector', 'name': 'Rzutnik'})
    # 'na żywo' liczy się dopiero, gdy realnie coś jest na ekranie: slajd ze Studia
    client.post(f'/c/{cid}/studio/send_text', json={'text': '[G]Amen', 'song_title': 'A', 'setlist': [{'title': 'A'}]})
    with app.app_context():
        tok = ScreenToken.query.first().token
        sid = ScreenToken.query.first().id
    # strona ekranu bez logowania
    anon = client
    client.get('/logout')
    assert anon.get(f'/screen/{tok}').status_code == 200
    # snapshot przez token
    d = anon.get(f'/api/live/current/{cid}?token={tok}').get_json()
    assert d['active'] is True
    # zly token
    assert anon.get('/screen/zlytoken').status_code == 404
    assert anon.get(f'/api/live/current/{cid}?token=zly').status_code == 403
    # odwolanie
    client.post('/login', data={'email': 'lead@l.pl', 'password': 'haslo1234'})
    client.post(f'/c/{cid}/screens/{sid}/revoke')
    assert anon.get(f'/screen/{tok}').status_code == 404


def test_musician_can_view_band_not_control(app, client):
    cid, slid = setup_live(client, app)
    r = client.post(f'/c/{cid}/team/invite', data={'role': 'muzyk'})
    with app.app_context():
        from app.models import Invitation
        code = Invitation.query.first().code
    client.get('/logout')
    client.post('/register', data={'email': 'm@m.pl', 'password': 'haslo1234',
                                   'display_name': 'Muzyk'})
    client.get(f'/join/{code}')
    assert client.get(f'/c/{cid}/live/band').status_code == 200
    assert client.get(f'/c/{cid}/live').status_code == 403
    assert client.post(f'/c/{cid}/live/slide',
                       json={'song_idx': 0, 'section_idx': 0}).status_code == 403


def test_section_parser():
    import music_core as mc
    secs = mc.parse_song_sections(
        "Zwrotka 1\n[C]a\n[G]b\n\nRefren\n[F]c\n\n[Am] [F] [C]")
    assert [s['label'] for s in secs] == ['Zwrotka 1', 'Refren', 'SLAJD 3']
    assert secs[2]['content'] == '[Am] [F] [C]'
