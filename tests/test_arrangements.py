# Aranżacje: forma, obsada (role z instrumentów), komórki z notatkami
# i nagraniami z telefonu, historia, ćwiczenie wg formy, API Reapera.
import io

import pytest

from app import create_app, db
from app.models import (Arrangement, ArrangementCell, ArrangementRecording,
                        Church, Invitation, Profile, Song)
from app.arrangements import service as svc

SONG = ('Intro\n[G] [D]\n\nZwrotka\n[G]Ty jesteś [C]Panem\n\n'
        'Refren\n[D]Alleluja [G]amen\n\nBridge\n[Em]Zawsze [C]wierny')
WEBM = b'\x1aE\xdf\xa3' + b'\x00' * 64          # nagłówek Matroska/WebM
MP3 = b'ID3\x04\x00' + b'\x00' * 64


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
    cid = Church.query.first().id
    client.post(f'/c/{cid}/songs/new', data={'title': 'Oceany',
                                             'content': SONG, 'key': 'G'})
    sid = Song.query.first().id
    return cid, sid


def main_arr(client, cid, sid):
    r = client.get(f'/c/{cid}/songs/{sid}/arrangement')
    assert r.status_code == 302
    return r.headers['Location'].rsplit('/', 1)[1]


def join_as(client, cid, email, name, role='muzyk'):
    client.post(f'/c/{cid}/team/invite', data={'role': role})
    code = Invitation.query.order_by(Invitation.id.desc()).first().code
    client.get('/logout')
    client.post('/register', data={'email': email, 'password': 'haslo1234',
                                   'display_name': name})
    client.get(f'/join/{code}')


def test_main_arrangement_has_default_form(app, client):
    cid, sid = setup(client, app)
    aid = main_arr(client, cid, sid)
    arr = db.session.get(Arrangement, aid)
    assert arr.is_main
    assert [t['label'] for t in arr.form] == ['Intro', 'Zwrotka', 'Refren', 'Bridge']
    page = client.get(f'/c/{cid}/arrangements/{aid}').get_data(as_text=True)
    assert 'Oceany' in page and 'form-strip' in page
    # drugi GET nie tworzy kolejnej Głównej
    main_arr(client, cid, sid)
    assert Arrangement.query.count() == 1


def test_form_save_validates_and_keeps_history(app, client):
    cid, sid = setup(client, app)
    aid = main_arr(client, cid, sid)
    form = db.session.get(Arrangement, aid).form
    new = [form[0], form[1], form[2], dict(form[1], id='zzz'),   # zły id -> nowy
           dict(form[2], id='abcdef12', repeat=99, dyn='rock'),  # przycięte
           {'id': 'deadbeef', 'sec': None, 'label': 'Solo', 'repeat': 2, 'dyn': 'full'},
           {'id': 'deadbee0', 'sec': 1, 'label': '   '}]         # pusty -> odpada
    d = client.post(f'/c/{cid}/arrangements/{aid}/form', json={'form': new}).get_json()
    labels = [t['label'] for t in d['form']]
    assert labels == ['Intro', 'Zwrotka', 'Refren', 'Zwrotka', 'Refren', 'Solo']
    assert d['form'][4]['repeat'] == 8 and d['form'][4]['dyn'] == ''
    assert d['form'][3]['id'] != 'zzz' and len(d['form'][3]['id']) == 8
    assert d['form'][5]['sec'] is None and d['form'][5]['dyn'] == 'full'
    # historia + przywrócenie
    from app.models import ArrangementRevision
    rev = ArrangementRevision.query.filter_by(arrangement_id=aid).first()
    assert len(rev.snapshot['form']) == 4
    client.post(f'/c/{cid}/arrangements/{aid}/restore/{rev.id}')
    db.session.expire_all()
    assert len(db.session.get(Arrangement, aid).form) == 4


def test_roles_numbering_and_instrument_suggestions(app, client):
    cid, sid = setup(client, app)
    client.post(f'/c/{cid}/profile', data={
        'name': 'Lider', 'instruments': ['wokal', 'gitara'],
        'instruments_custom': 'Cajon, ukulele', 'notation': 'international'})
    p = Profile.query.first()
    assert p.instruments == ['wokal', 'gitara', 'Cajon', 'ukulele']
    assert p.instrument == 'wokal'
    with app.test_request_context():
        assert svc.instrument_suggestions(cid) == ['Cajon', 'Guitar', 'ukulele', 'Vocals']
    aid = main_arr(client, cid, sid)
    url = f'/c/{cid}/arrangements/{aid}/roles'
    client.post(url, json={'add': 'Wokal'})
    client.post(url, json={'add': 'Wokal'})
    d = client.post(url, json={'add': 'wokal'}).get_json()
    assert d['roles'] == ['Wokal', 'Wokal 2', 'wokal 3']
    d = client.post(url, json={'roles': ['Wokal 2', 'Wokal', 'wokal 3']}).get_json()
    assert d['roles'][0] == 'Wokal 2'
    # podmiana na nieistniejącą rolę nie przechodzi
    d = client.post(url, json={'roles': ['Hacker']}).get_json()
    assert 'Hacker' not in d['roles']
    d = client.post(url, json={'remove': 'wokal 3'}).get_json()
    assert d['roles'] == ['Wokal 2', 'Wokal']


def test_legacy_single_instrument_field_still_works(app, client):
    cid, sid = setup(client, app)
    client.post(f'/c/{cid}/profile', data={'name': 'X', 'instrument': 'bas'})
    p = Profile.query.first()
    assert p.instrument == 'bas' and p.instruments == ['bas']


def test_cell_note_and_phone_memo(app, client):
    cid, sid = setup(client, app)
    aid = main_arr(client, cid, sid)
    arr = db.session.get(Arrangement, aid)
    tile = arr.form[2]['id']
    client.post(f'/c/{cid}/arrangements/{aid}/roles', json={'add': 'Wokal 2'})
    assert client.post(f'/c/{cid}/arrangements/{aid}/cell',
                       json={'tile': tile, 'role': 'Wokal 2',
                             'note': 'tercja w górę'}).status_code == 200
    # nieznana rola / kafelek
    assert client.post(f'/c/{cid}/arrangements/{aid}/cell',
                       json={'tile': tile, 'role': 'Bas', 'note': 'x'}).status_code == 400
    # notatka głosowa z telefonu
    r = client.post(f'/c/{cid}/arrangements/{aid}/memo', data={
        'tile': tile, 'role': 'Wokal 2',
        'audio': (io.BytesIO(WEBM), 'memo')}, content_type='multipart/form-data')
    d = r.get_json()
    assert r.status_code == 200 and d['memo'].endswith('.webm')
    assert client.get(d['memo']).data == WEBM
    # nie-audio odrzucone
    r = client.post(f'/c/{cid}/arrangements/{aid}/memo', data={
        'tile': tile, 'role': 'Wokal 2',
        'audio': (io.BytesIO(b'<html>'), 'x.mp3')}, content_type='multipart/form-data')
    assert r.status_code == 400
    page = client.get(f'/c/{cid}/arrangements/{aid}').get_data(as_text=True)
    assert 'tercja w g\\u00f3r\\u0119' in page or 'tercja w górę' in page
    # usunięcie memo zostawia notatkę
    client.post(f'/c/{cid}/arrangements/{aid}/memo/delete',
                json={'tile': tile, 'role': 'Wokal 2'})
    c = ArrangementCell.query.first()
    assert c.memo == '' and c.note == 'tercja w górę'


def test_private_audio_only_for_members(app, client):
    cid, sid = setup(client, app)
    aid = main_arr(client, cid, sid)
    arr = db.session.get(Arrangement, aid)
    client.post(f'/c/{cid}/arrangements/{aid}/roles', json={'add': 'Gitara'})
    d = client.post(f'/c/{cid}/arrangements/{aid}/memo', data={
        'tile': arr.form[0]['id'], 'role': 'Gitara',
        'audio': (io.BytesIO(MP3), 'm.mp3')}, content_type='multipart/form-data').get_json()
    fname = d['memo'].rsplit('/', 1)[1]
    # publiczne /media (dla ekranów) nie sięga do plików prywatnych
    assert client.get(f'/c/{cid}/media/../../private/{cid}/arrangements/{aid}/{fname}').status_code == 404
    assert client.get(f'/c/_x/media/../private/{cid}/arrangements/{aid}/{fname}').status_code == 404
    client.get('/logout')
    assert client.get(d['memo']).status_code in (302, 401, 403)
    client.post('/register', data={'email': 'obcy@o.pl', 'password': 'haslo1234',
                                   'display_name': 'Obcy'})
    client.post('/church/create', data={'name': 'Obcy Zbor'})
    assert client.get(d['memo']).status_code == 403
    assert client.get(f'/c/{cid}/arrangements/{aid}').status_code == 403
    assert client.post(f'/c/{cid}/arrangements/{aid}/form', json={'form': []}).status_code == 403


def test_musician_edits_but_cannot_delete_version(app, client):
    cid, sid = setup(client, app)
    aid = main_arr(client, cid, sid)
    r = client.post(f'/c/{cid}/songs/{sid}/arrangements', data={'name': 'Akustyczna', 'copy_from': aid})
    acu = r.headers['Location'].rsplit('/', 1)[1]
    join_as(client, cid, 'm@m.pl', 'Marta')
    assert client.post(f'/c/{cid}/arrangements/{acu}/form',
                       json={'form': []}).status_code == 200
    assert client.post(f'/c/{cid}/arrangements/{acu}/delete').status_code == 403
    # nazwa zajęta
    client.post(f'/c/{cid}/songs/{sid}/arrangements', data={'name': 'akustyczna'})
    assert Arrangement.query.filter_by(deleted=False).count() == 2


def test_practice_follows_form_and_shows_my_part(app, client):
    cid, sid = setup(client, app)
    client.post(f'/c/{cid}/profile', data={'name': 'Lider', 'instruments': ['wokal']})
    aid = main_arr(client, cid, sid)
    arr = db.session.get(Arrangement, aid)
    f = arr.form
    client.post(f'/c/{cid}/arrangements/{aid}/form',
                json={'form': [f[2], f[1], dict(f[2], id='0000aaaa', repeat=2)]})
    client.post(f'/c/{cid}/arrangements/{aid}/roles', json={'add': 'Vocals'})
    client.post(f'/c/{cid}/arrangements/{aid}/cell',
                json={'tile': f[2]['id'], 'role': 'Vocals', 'note': 'wejście na 2'})
    page = client.get(f'/c/{cid}/songs/{sid}/practice').get_data(as_text=True)
    # kolejność wg formy: Refren, Zwrotka, Refren×2
    i1 = page.index('>Refren'); i2 = page.index('>Zwrotka'); i3 = page.rindex('>Refren')
    assert i1 < i2 < i3 and '×2' in page
    # rola dobrana z instrumentu „wokal" (etykieta Vocals) i moja notatka widoczna
    assert 'wejście na 2' in page and 'pr-part' in page
    # bez aranżacji (inna piosenka) — stary widok sekcji
    client.post(f'/c/{cid}/songs/new', data={'title': 'Druga', 'content': 'Zwrotka\n[C]La'})
    s2 = Song.query.filter_by(title='Druga').first().id
    page = client.get(f'/c/{cid}/songs/{s2}/practice').get_data(as_text=True)
    assert 'Set up the arrangement' in page


# ── Reaper API ─────────────────────────────────────────────────────────
def token(client, cid):
    client.post(f'/c/{cid}/reaper/token')
    with client.session_transaction() as s:
        tok = s['new_studio_token']
    page = client.get(f'/c/{cid}/reaper').get_data(as_text=True)
    assert tok in page                       # pokazany raz
    assert tok not in client.get(f'/c/{cid}/reaper').get_data(as_text=True)
    return {'Authorization': f'Bearer {tok}'}


def test_studio_token_auth(app, client):
    cid, sid = setup(client, app)
    h = token(client, cid)
    assert client.get('/api/studio/ping', headers=h).get_json()['church'] == 'Zbor'
    assert client.get('/api/studio/ping', headers={'Authorization': 'Bearer jst_zly'}).status_code == 401
    assert client.get('/api/studio/ping').status_code == 401
    # nowy token unieważnia stary
    h2 = token(client, cid)
    assert client.get('/api/studio/ping', headers=h).status_code == 401
    assert client.get('/api/studio/ping', headers=h2).status_code == 200
    client.post(f'/c/{cid}/reaper/revoke')
    assert client.get('/api/studio/ping', headers=h2).status_code == 401
    # muzyk nie zarządza tokenem
    join_as(client, cid, 'm@m.pl', 'Marta')
    assert client.post(f'/c/{cid}/reaper/token').status_code == 403


def test_plan_matches_song_tiles_and_tracks(app, client):
    cid, sid = setup(client, app)
    aid = main_arr(client, cid, sid)
    client.post(f'/c/{cid}/arrangements/{aid}/roles', json={'add': 'Wokal 2'})
    h = token(client, cid)
    regions = [
        {'name': 'oceany', 'markers': [
            {'name': 'Intro', 'start': 0, 'end': 10}, {'name': 'Z1', 'start': 10, 'end': 40},
            {'name': 'R', 'start': 40, 'end': 70}, {'name': 'B', 'start': 70, 'end': 90}],
         'tracks': ['Wokal 2', 'Gitara']},
        {'name': 'Oceany | Akustyczna', 'markers': [], 'tracks': []},
        {'name': 'Nieznana', 'markers': [], 'tracks': []},
    ]
    d = client.post('/api/studio/plan', json={'regions': regions}, headers=h).get_json()
    a, b, c = d['regions']
    assert a['ok'] and a['song_title'] == 'Oceany' and not a['create']
    assert a['tiles_matched'] == 4 and not a['form_differs']
    assert a['missing_roles'] == ['Gitara']
    assert b['create'] and b['arrangement'] == 'Akustyczna'
    assert not c['ok'] and c['error'] == 'song_not_found'


def test_commit_and_upload_overwrites(app, client):
    cid, sid = setup(client, app)
    aid = main_arr(client, cid, sid)
    old_ids = [t['id'] for t in db.session.get(Arrangement, aid).form]
    h = token(client, cid)
    markers = [{'name': 'Intro', 'start': 0, 'end': 8},
               {'name': 'Refren', 'start': 8, 'end': 30},
               {'name': 'Refren', 'start': 30, 'end': 52}]
    d = client.post('/api/studio/commit', headers=h, json={
        'song_id': sid, 'version': '', 'markers': markers,
        'tracks': ['Gitara', 'Wokal 2'], 'duration': 52}).get_json()
    assert d['arrangement_id'] == aid
    arr = db.session.get(Arrangement, aid)
    # forma poszła za nagraniem; kafelki odzyskały stare id (Intro, Refren)
    assert [t['label'] for t in arr.form] == ['Intro', 'Refren', 'Refren']
    assert arr.form[0]['id'] == old_ids[0] and arr.form[1]['id'] == old_ids[2]
    assert arr.markers[arr.form[2]['id']] == [30, 52]
    assert arr.roles == ['Gitara', 'Wokal 2']
    up = lambda kind, role, blob: client.post(
        f'/api/studio/arrangements/{aid}/file', headers=h,
        data={'kind': kind, 'role': role, 'file': (io.BytesIO(blob), 'x.mp3')},
        content_type='multipart/form-data')
    assert up('mix', '', MP3).status_code == 200
    assert up('loud', 'Gitara', MP3).status_code == 200
    assert up('minus', 'Gitara', MP3).status_code == 200
    assert up('loud', 'Perkusja', MP3).status_code == 400
    assert up('mix', '', b'not audio').status_code == 400
    assert ArrangementRecording.query.count() == 3
    # ćwiczenie pokazuje odtwarzacz z trybami Nauka / Gram sam
    client.post(f'/c/{cid}/arrangements/{aid}/my-role', json={'role': 'Gitara'})
    page = client.get(f'/c/{cid}/songs/{sid}/practice').get_data(as_text=True)
    assert 'id="tp-play"' in page and 'data-start="30' in page
    assert 'Learn' in page and 'Play along' in page
    # ponowne wysłanie nadpisuje
    client.post('/api/studio/commit', headers=h, json={
        'song_id': sid, 'markers': markers, 'tracks': ['Gitara']})
    assert ArrangementRecording.query.count() == 0
    up('mix', '', MP3)
    assert ArrangementRecording.query.count() == 1


def test_form_from_markers_resets_repeats(app, client):
    cid, sid = setup(client, app)
    aid = main_arr(client, cid, sid)
    form = db.session.get(Arrangement, aid).form
    client.post(f'/c/{cid}/arrangements/{aid}/form',
                json={'form': [dict(form[0], repeat=2, dyn='soft'), form[2]]})
    h = token(client, cid)
    client.post('/api/studio/commit', headers=h, json={
        'song_id': sid, 'markers': [
            {'name': 'Intro', 'start': 0, 'end': 5},
            {'name': 'Z1', 'start': 5, 'end': 15},
            {'name': 'Refren', 'start': 15, 'end': 25}]})
    db.session.expire_all()
    arr = db.session.get(Arrangement, aid)
    assert [(t['label'], t['repeat']) for t in arr.form] == \
        [('Intro', 1), ('Z1', 1), ('Refren', 1)]
    assert arr.form[0]['id'] == form[0]['id'] and arr.form[0]['dyn'] == 'soft'


def test_commit_creates_named_version(app, client):
    cid, sid = setup(client, app)
    h = token(client, cid)
    d = client.post('/api/studio/commit', headers=h, json={
        'song_id': sid, 'version': 'Akustyczna', 'markers': [], 'tracks': ['Piano']}).get_json()
    arr = db.session.get(Arrangement, d['arrangement_id'])
    assert arr.name == 'Akustyczna' and not arr.is_main and arr.roles == ['Piano']
    # tokenem obcej wspólnoty nie dosięgniesz cudzej piosenki
    client.get('/logout')
    client.post('/register', data={'email': 'o@o.pl', 'password': 'haslo1234',
                                   'display_name': 'O'})
    client.post('/church/create', data={'name': 'Inny'})
    other = Church.query.filter_by(name='Inny').first().id
    h2 = token(client, other)
    assert client.post('/api/studio/commit', headers=h2,
                       json={'song_id': sid}).status_code == 404
    assert client.post(f'/api/studio/arrangements/{arr.id}/file', headers=h2,
                       data={'kind': 'mix'}).status_code == 404


def test_section_aliases():
    assert svc.section_key('Z1') == ('verse', '1')
    assert svc.section_key('Zwrotka 2') == ('verse', '2')
    assert svc.section_key('R') == ('chorus', '')
    assert svc.section_key('Refren') == ('chorus', '')
    assert svc.section_key('Zakończenie') == ('outro', '')
    assert svc.fold('Głos 2') == 'glos 2'
