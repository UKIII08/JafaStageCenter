# Wybór wyglądu: pastelowy motyw, okno „Wybierz wygląd” przy pierwszym wejściu.
import pytest

from app import create_app, db
from app.models import Church, User


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


def setup(client):
    client.post('/register', data={'email': 'l@l.pl', 'password': 'haslo1234',
                                   'display_name': 'Lider'})
    client.post('/church/create', data={'name': 'Zbor'})
    return Church.query.first().id


def test_picker_shows_until_a_look_is_chosen(app, client):
    cid = setup(client)
    assert 'id="look-pick"' in client.get(f'/c/{cid}').get_data(as_text=True)
    assert client.post('/account/theme', json={'theme': 'pastel'}).status_code == 200
    assert User.query.first().theme == 'pastel'
    page = client.get(f'/c/{cid}').get_data(as_text=True)
    assert 'id="look-pick"' not in page
    assert 'var t = "pastel"' in page        # wygląd z konta, na każdym urządzeniu


def test_bad_theme_rejected(app, client):
    setup(client)
    assert client.post('/account/theme', json={'theme': 'neon'}).status_code == 400
    assert User.query.first().theme is None


def test_profile_offers_pastel(app, client):
    cid = setup(client)
    page = client.get(f'/c/{cid}/profile').get_data(as_text=True)
    assert 'data-theme-val="pastel"' in page


def test_live_screens_ignore_panel_look(app, client):
    # widoki na żywo mają własne szablony, bez panelowego wyglądu
    for t in ('studio/band_member.html', 'studio/stage.html', 'studio/projector.html'):
        src = open('app/templates/' + t, encoding='utf-8').read()
        assert 'jonathan-look' not in src and 'base.html' not in src
