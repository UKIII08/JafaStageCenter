# Testy poprawek z audytu UX/logiki: brak nadpisywania, unikalne tytuły,
# konflikty edycji, notatki po nazwie części, cofanie usunięcia.
import io
import json

import pytest

from app import create_app, db
from app.models import (Arrangement, Church, Invitation, Song,
                        SongUsage)
from app.songs.service import notes_by_index, notes_with, section_keys


SONG = """Zwrotka
[G]Pierwsza linia

Refren
[C]Druga linia"""


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
    cid = Church.query.first().id
    client.post(f'/c/{cid}/songs/new', data={'title': 'Oceany', 'content': SONG, 'key': 'G'})
    return cid, Song.query.first().id


def join_as(client, cid, email, name, role='muzyk'):
    client.post(f'/c/{cid}/team/invite', data={'role': role})
    code = Invitation.query.order_by(Invitation.id.desc()).first().code
    client.get('/logout')
    client.post('/register', data={'email': email, 'password': 'haslo1234',
                                   'display_name': name})
    client.get(f'/join/{code}')


def test_panel_refuses_duplicate_title(app, client):
    cid, sid = setup(client)
    r = client.post(f'/c/{cid}/songs/new', data={'title': '  oceany ', 'content': SONG})
    assert r.status_code == 200 and Song.query.count() == 1
    # edycja innej piosenki na zajęty tytuł też nie przejdzie
    client.post(f'/c/{cid}/songs/new', data={'title': 'Inna', 'content': SONG})
    other = Song.query.filter_by(title='Inna').first()
    client.post(f'/c/{cid}/songs/{other.id}/edit', data={'title': 'Oceany', 'content': SONG})
    assert db.session.get(Song, other.id).title == 'Inna'


def test_studio_add_never_overwrites(app, client):
    cid, sid = setup(client)
    client.post(f'/c/{cid}/studio/add_song', data={'title': 'Oceany', 'content': '[D]Coś innego'})
    titles = sorted(s.title for s in Song.query.all())
    assert titles == ['Oceany', 'Oceany (2)']
    assert 'Pierwsza' in db.session.get(Song, sid).content


def test_studio_import_skips_existing(app, client):
    cid, sid = setup(client)
    client.post(f'/c/{cid}/studio/import_songs', data={
        'import_files': (io.BytesIO('[D]Nadpisane'.encode()), 'Oceany.txt')},
        content_type='multipart/form-data')
    assert 'Pierwsza' in db.session.get(Song, sid).content


def test_song_edit_conflict_keeps_both_versions(app, client):
    cid, sid = setup(client)
    page = client.get(f'/c/{cid}/songs/{sid}/edit').get_data(as_text=True)
    base = page.split('name="base" value="')[1].split('"')[0]
    # ktoś inny zapisał w międzyczasie
    song = db.session.get(Song, sid)
    song.content = SONG + '\n\nBridge\n[Em]Cudza zmiana'
    song.updated_by = 'ktos-inny'
    from datetime import datetime, timedelta
    song.updated_at = datetime.utcnow() + timedelta(seconds=5)
    db.session.commit()
    r = client.post(f'/c/{cid}/songs/{sid}/edit',
                    data={'title': 'Oceany', 'content': SONG, 'base': base})
    assert r.status_code == 200 and 'Cudza zmiana' in r.get_data(as_text=True)
    assert 'Cudza zmiana' in db.session.get(Song, sid).content   # nic nie nadpisane


def test_section_notes_follow_the_part_not_the_position():
    raw = notes_with(None, SONG, {'1': 'refren głośno'})
    longer = 'Intro\n[G]Wstęp\n\n' + SONG          # na początku doszła nowa część
    assert section_keys(longer)[2] == 'refren#1'
    assert notes_by_index(raw, longer) == {'2': 'refren głośno'}
    # stare zapisy (po numerze) wciąż się czytają
    assert notes_by_index(json.dumps({'0': 'stare'}), SONG) == {'0': 'stare'}


def test_delete_shows_undo_and_restore_works(app, client):
    cid, sid = setup(client)
    r = client.post(f'/c/{cid}/songs/{sid}/delete', follow_redirects=True)
    assert f'/songs/{sid}/restore' in r.get_data(as_text=True)
    client.post(f'/c/{cid}/songs/{sid}/restore')
    assert db.session.get(Song, sid).deleted is False


def test_restore_avoids_title_clash(app, client):
    cid, sid = setup(client)
    client.post(f'/c/{cid}/songs/{sid}/delete')
    client.post(f'/c/{cid}/songs/new', data={'title': 'Oceany', 'content': SONG})
    client.post(f'/c/{cid}/songs/{sid}/restore')
    assert db.session.get(Song, sid).title == 'Oceany (2)'


def test_ccli_usage_logged_by_song_id(app, client):
    cid, sid = setup(client)
    # tytuł na liście Studia różni się od biblioteki, ale id się zgadza
    client.post(f'/c/{cid}/studio/send_text', json={
        'text': '[G]Amen', 'song_title': 'Oceany (live)', 'song_id': sid,
        'setlist': [{'title': 'Oceany (live)', 'id': sid}]})
    assert SongUsage.query.filter_by(song_id=sid).count() == 1


def test_default_notation_used_in_editor(app, client):
    cid, sid = setup(client)
    church = db.session.get(Church, cid)
    church.settings = dict(church.settings or {}, default_notation='polish')
    db.session.commit()
    page = client.get(f'/c/{cid}/songs/new').get_data(as_text=True)
    assert 'id="f-notation" value="polish"' in page


def test_cell_conflict_returns_409(app, client):
    cid, sid = setup(client)
    aid = client.get(f'/c/{cid}/songs/{sid}/arrangement').headers['Location'].rsplit('/', 1)[1]
    tile = db.session.get(Arrangement, aid).form[1]['id']
    client.post(f'/c/{cid}/arrangements/{aid}/roles', json={'add': 'Wokal'})
    url = f'/c/{cid}/arrangements/{aid}/cell'
    v0 = client.post(url, json={'tile': tile, 'role': 'Wokal', 'note': 'lider'}).get_json()['v']
    join_as(client, cid, 'm@m.pl', 'Muzyk')
    # muzyk otworzył kratkę w wersji v0, a lider w tym czasie zmienił ją znowu
    client2 = app.test_client()
    client2.post('/login', data={'email': 'l@l.pl', 'password': 'haslo1234'})
    import time
    time.sleep(1.1)
    client2.post(url, json={'tile': tile, 'role': 'Wokal', 'note': 'lider 2', 'base': v0})
    r = client.post(url, json={'tile': tile, 'role': 'Wokal', 'note': 'muzyk', 'base': v0})
    assert r.status_code == 409 and r.get_json()['cell']['note'] == 'lider 2'


def test_practice_shows_where_the_key_comes_from(app, client):
    cid, sid = setup(client)
    page = client.get(f'/c/{cid}/songs/{sid}/practice').get_data(as_text=True)
    assert '<em class="key-src">original</em>' in page
    client.post(f'/c/{cid}/songs/{sid}/personal', json={'transpose': 2})
    page = client.get(f'/c/{cid}/songs/{sid}/practice').get_data(as_text=True)
    assert '<em class="key-src">your key</em>' in page


def test_old_live_routes_point_to_studio(app, client):
    cid, sid = setup(client)
    r = client.post(f'/c/{cid}/live/start/stary')
    assert r.status_code == 302 and '/studio' in r.headers['Location']
