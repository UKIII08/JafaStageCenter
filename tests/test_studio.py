# TESTY STUDIA — port panelu desktop: kontrakt API per wspólnota,
# twarda tenancy (wspólnota A nie widzi danych B), dostęp tokenowy ekranów.
import json

import pytest

from app import create_app, db
from app.models import Church, ScreenToken, Song, StudioSetlist


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


def make_church(app, client, email, name):
    register(client, email)
    client.post('/church/create', data={'name': name},
                follow_redirects=True)
    with app.app_context():
        return Church.query.filter_by(name=name).first().id


SONG = '[Zwrotka]\n[G]Wielki [C]Bog, [D]swiety [G]Pan'


def test_studio_page_and_song_crud(app, client):
    cid = make_church(app, client, 'a@a.pl', 'Zbor A')
    r = client.get(f'/c/{cid}/studio')
    assert r.status_code == 200
    assert b'control_logic.js' in r.data

    r = client.post(f'/c/{cid}/studio/add_song', data={
        'title': 'Test Studio', 'content': SONG, 'key': '', 'bpm': '72'})
    assert r.status_code == 302
    with app.app_context():
        s = Song.query.filter_by(church_id=cid, title='Test Studio').first()
        assert s is not None and s.key == 'G' and s.bpm == 72
        sid = s.id

    # edycja i miękkie usunięcie (tombstone pod sync)
    client.post(f'/c/{cid}/studio/edit_song/{sid}', data={
        'title': 'Test Studio', 'content': SONG, 'key': 'A', 'bpm': '80'})
    client.post(f'/c/{cid}/studio/delete_song/{sid}')
    with app.app_context():
        s = db.session.get(Song, sid)
        assert s.deleted is True


def test_studio_tenancy(app, client):
    cid_a = make_church(app, client, 'a@a.pl', 'Zbor A')
    client.get('/logout')
    cid_b = make_church(app, client, 'b@b.pl', 'Zbor B')
    # zalogowany admin B nie wejdzie do studia A ani jego API
    assert client.get(f'/c/{cid_a}/studio').status_code == 403
    assert client.post(f'/c/{cid_a}/studio/send_text',
                       json={'text': 'x'}).status_code == 403
    assert client.get(f'/c/{cid_a}/studio/api/profiles').status_code == 403
    # a do własnego tak
    assert client.get(f'/c/{cid_b}/studio').status_code == 200


def test_send_text_and_current_slide(app, client):
    cid = make_church(app, client, 'a@a.pl', 'Zbor A')
    r = client.post(f'/c/{cid}/studio/send_text', json={
        'text': SONG, 'transpose': 2, 'key': 'A', 'bpm': 72,
        'song_title': 'Testowa'})
    assert r.get_json()['status'] == 'ok'
    slide = client.get(f'/c/{cid}/studio/api/current-slide').get_json()
    assert slide['mode'] == 'worship'
    assert slide['song_title'] == 'Testowa'
    assert 'A' in slide['band']          # G +2 = A w wierszu akordów
    assert '[' not in slide['people']    # tekst dla zboru bez akordów


def test_send_note_spontaneous_text(app, client):
    # Spontaniczny kafelek: tekst leci na ekran jako slajd „note", HTML jest
    # zescapowany, a nowe linie zamieniane na <br>.
    cid = make_church(app, client, 'n@n.pl', 'Zbor N')
    r = client.post(f'/c/{cid}/studio/send_text', json={
        'mode': 'note', 'text': 'Wyciszmy się\n<script>x</script>'})
    assert r.get_json()['status'] == 'ok'
    slide = client.get(f'/c/{cid}/studio/api/current-slide').get_json()
    assert slide['mode'] == 'note'
    assert '<br>' in slide['html']                 # nowa linia → <br>
    assert '<script>' not in slide['html']         # HTML zescapowany
    assert '&lt;script&gt;' in slide['html']
    assert slide['is_blackout'] is False


def test_live_flag_clears_when_setlist_emptied(app, client):
    # Regresja: po opróżnieniu setlisty (Studio wysyła pusty/logo slajd)
    # dashboard nie może dalej pokazywać "na żywo".
    cid = make_church(app, client, 'a@a.pl', 'Zbor A')
    # gramy piosenkę z niepustą setlistą -> LIVE
    client.post(f'/c/{cid}/studio/send_text', json={
        'text': SONG, 'song_title': 'Testowa', 'key': 'G',
        'setlist': [{'title': 'Testowa'}], 'current_index': 0})
    assert client.get(f'/api/live/current/{cid}').get_json()['active'] is True
    # opróżnienie setlisty = clearLiveDisplay -> logo + pusta setlista
    client.post(f'/c/{cid}/studio/send_text', json={
        'logo': True, 'setlist': [], 'current_index': -1})
    assert client.get(f'/api/live/current/{cid}').get_json()['active'] is False
    # ekrany dostają czysty slajd (logo), nie stary tekst
    slide = client.get(f'/c/{cid}/studio/api/current-slide').get_json()
    assert slide['mode'] == 'logo'


def test_live_flag_clears_when_setlist_emptied_via_socket(app, client):
    # Regresja (ścieżka realna): usunięcie wszystkich pieśni w Studiu leci
    # przez socket client_update_state z pustą setlistą — musi zgasić LIVE
    # i wyczyścić ostatni slajd, nawet bez osobnego /send_text.
    from app import socketio
    cid = make_church(app, client, 'a@a.pl', 'Zbor A')
    client.post(f'/c/{cid}/studio/send_text', json={
        'text': SONG, 'song_title': 'X', 'key': 'G',
        'setlist': [{'title': 'X'}], 'current_index': 0})
    assert client.get(f'/api/live/current/{cid}').get_json()['active'] is True
    sio = socketio.test_client(app, flask_test_client=client)
    assert sio.is_connected()
    sio.emit('client_update_state',
             {'church_id': cid, 'setlist': [], 'current_index': -1})
    sio.disconnect()
    assert client.get(f'/api/live/current/{cid}').get_json()['active'] is False
    slide = client.get(f'/c/{cid}/studio/api/current-slide').get_json()
    assert slide['mode'] == 'logo'


def test_screen_token_access(app, client):
    cid = make_church(app, client, 'a@a.pl', 'Zbor A')
    client.post(f'/c/{cid}/studio/send_text', json={'text': SONG})
    with app.app_context():
        t = ScreenToken(church_id=cid, token='x' * 43, type='stage')
        db.session.add(t)
        db.session.commit()
    fresh = app.test_client()   # bez sesji
    # bez tokenu: brak dostępu
    assert fresh.get(f'/c/{cid}/studio/api/current-slide').status_code == 403
    # z tokenem: ekran czyta slajd
    r = fresh.get(f'/c/{cid}/studio/api/current-slide?token={"x" * 43}')
    assert r.status_code == 200 and r.get_json()['mode'] == 'worship'
    # strona ekranu po tokenie
    r = fresh.get(f'/screen/{"x" * 43}')
    assert r.status_code == 200
    # regresja bezpieczeństwa: token ekranu (półpubliczny) NIE MOŻE zapisywać
    # ani kasować danych — tylko odczyt.
    tok = f'?token={"x" * 43}'
    assert fresh.post(f'/c/{cid}/studio/api/profiles{tok}',
                      json={'name': 'Haker'}).status_code == 403
    assert fresh.delete(
        f'/c/{cid}/studio/api/profiles/whatever{tok}').status_code == 403
    assert fresh.post(f'/c/{cid}/studio/api/presets{tok}',
                      json={'name': 'x'}).status_code == 403


def test_presets_and_profiles(app, client):
    cid = make_church(app, client, 'a@a.pl', 'Zbor A')
    r = client.post(f'/c/{cid}/studio/api/presets', json={
        'name': 'Gitara capo 2', 'capo_fret': 2, 'show_chords': True})
    pid = r.get_json()['id']
    presets = client.get(f'/c/{cid}/studio/api/presets').get_json()
    assert any(p['id'] == pid and p['capo_fret'] == 2 for p in presets)

    r = client.post(f'/c/{cid}/studio/api/profiles', json={
        'name': 'Basia', 'instrument': 'wokal'})
    prof_id = r.get_json()['id']
    client.put(f'/c/{cid}/studio/api/profiles/{prof_id}', json={
        'capo_fret': 4, 'theme': 'light'})
    p = client.get(f'/c/{cid}/studio/api/profiles/{prof_id}').get_json()
    assert p['capo_fret'] == 4 and p['theme'] == 'light'

    # ustawienia per piosenka (capo + notatki sekcji)
    client.post(f'/c/{cid}/studio/add_song', data={
        'title': 'X', 'content': SONG})
    with app.app_context():
        sid = Song.query.filter_by(church_id=cid, title='X').first().id
    client.put(f'/c/{cid}/studio/api/profiles/{prof_id}/song/{sid}',
               json={'capo_fret': 3, 'notes': {'0': 'palcami'}})
    s = client.get(
        f'/c/{cid}/studio/api/profiles/{prof_id}/song/{sid}').get_json()
    assert s['capo_fret'] == 3 and s['notes']['0'] == 'palcami'


def test_setlist_history_and_share(app, client):
    cid = make_church(app, client, 'a@a.pl', 'Zbor A')
    songs = [{'id': 'abc', 'title': 'X', 'key': 'G', 'bpm': 70,
              'transpose': 0}]
    r = client.post(f'/c/{cid}/studio/api/setlist-history', json={
        'name': 'Niedziela', 'date': '2026-07-19', 'songs': songs})
    hid = r.get_json()['id']
    items = client.get(f'/c/{cid}/studio/api/setlist-history').get_json()
    assert items[0]['id'] == hid and items[0]['song_count'] == 1

    r = client.post(f'/c/{cid}/studio/api/setlist-share', json={
        'name': 'Niedziela', 'date': '', 'songs': songs})
    code = r.get_json()['code']
    got = client.get(
        f'/c/{cid}/studio/api/setlist-share/{code}').get_json()
    assert got['songs'][0]['title'] == 'X'

    # tenancy: druga wspólnota nie odczyta cudzego kodu
    client.get('/logout')
    cid_b = make_church(app, client, 'b@b.pl', 'Zbor B')
    r = client.get(f'/c/{cid_b}/studio/api/setlist-share/{code}')
    assert r.status_code == 404


def test_transition_endpoint(app, client):
    cid = make_church(app, client, 'a@a.pl', 'Zbor A')
    client.post(f'/c/{cid}/studio/add_song', data={
        'title': 'A', 'content': SONG})
    client.post(f'/c/{cid}/studio/add_song', data={
        'title': 'B', 'content': '[Refren]\n[E]Alleluja [A]Panu [H]nasz'})
    with app.app_context():
        ida = Song.query.filter_by(church_id=cid, title='A').first().id
        idb = Song.query.filter_by(church_id=cid, title='B').first().id
    r = client.post(f'/c/{cid}/studio/generate_transition', json={
        'id_start': ida, 'id_end': idb,
        'transpose_start': 0, 'transpose_end': 0})
    data = r.get_json()
    assert data['status'] == 'ok' and len(data['chords_list']) >= 2
    assert data['engine_used'] == 'v4'


def test_global_pads_serving(app, client):
    import os
    # Wspólne pady (jeden zestaw wgrywany przez dewelopera na serwer) —
    # globalny endpoint /pads/<key>.mp3, nie per-wspólnota.
    shared = os.path.join(app.instance_path, 'uploads', '_shared', 'pads')
    os.makedirs(shared, exist_ok=True)
    with open(os.path.join(shared, 'C.mp3'), 'wb') as f:
        f.write(b'ID3fakemp3')
    with open(os.path.join(shared, 'D#.mp3'), 'wb') as f:
        f.write(b'ID3fakemp3')
    assert client.get('/pads/C.mp3').status_code == 200
    assert client.get('/pads/D%23.mp3').status_code == 200
    # tonacja której nie wgrano -> 404, zła nazwa -> 404
    assert client.get('/pads/A.mp3').status_code == 404
    assert client.get('/pads/X.mp3').status_code == 404


def test_ccli_usage_logging_and_report(app, client):
    cid = make_church(app, client, 'a@a.pl', 'Zbor A')
    # numer licencji wspólnoty + piosenka z danymi CCLI
    client.post(f'/c/{cid}/settings', data={
        'name': 'Zbor A', 'default_notation': 'international',
        'transition_engine': 'v4', 'ccli_license': '987654',
        'ccli_notice': 'on'},
        follow_redirects=True)
    client.post(f'/c/{cid}/studio/add_song', data={
        'title': 'Amazing Grace', 'content': SONG,
        'ccli_number': '22025', 'author': 'John Newton',
        'copyright': 'Public Domain'})

    # wyświetlenie na żywo -> log użycia + notka copyright w slajdzie
    client.post(f'/c/{cid}/studio/send_text', json={
        'text': SONG, 'transpose': 0, 'song_title': 'Amazing Grace'})
    slide = client.get(f'/c/{cid}/studio/api/current-slide').get_json()
    assert 'Amazing Grace' in slide['copyright_line']
    assert 'John Newton' in slide['copyright_line']
    assert 'CCLI License #987654' in slide['copyright_line']

    # drugi raz tego samego dnia = nadal jedno użycie
    client.post(f'/c/{cid}/studio/send_text', json={
        'text': SONG, 'transpose': 0, 'song_title': 'Amazing Grace'})
    r = client.get(f'/c/{cid}/studio/ccli-report')
    assert b'Amazing Grace' in r.data and b'22025' in r.data
    assert b'<b>1</b>' in r.data

    # eksport CSV
    r = client.get(f'/c/{cid}/studio/ccli-report?format=csv')
    assert r.mimetype == 'text/csv'
    assert b'Amazing Grace,22025,John Newton,1' in r.data


def test_ccli_no_data_no_notice(app, client):
    cid = make_church(app, client, 'a@a.pl', 'Zbor A')
    client.post(f'/c/{cid}/studio/add_song', data={
        'title': 'Wlasna piesn', 'content': SONG})
    client.post(f'/c/{cid}/studio/send_text', json={
        'text': SONG, 'song_title': 'Wlasna piesn'})
    slide = client.get(f'/c/{cid}/studio/api/current-slide').get_json()
    # piosenka bez autora/copyright (np. własna) = brak notki
    assert slide['copyright_line'] == ''


def test_ccli_notice_toggle(app, client):
    cid = make_church(app, client, 'a@a.pl', 'Zbor A')
    client.post(f'/c/{cid}/studio/add_song', data={
        'title': 'Hymn', 'content': SONG, 'author': 'J. Doe',
        'copyright': 'Good Music Co'})
    # domyślnie notka włączona
    client.post(f'/c/{cid}/studio/send_text', json={
        'text': SONG, 'song_title': 'Hymn'})
    slide = client.get(f'/c/{cid}/studio/api/current-slide').get_json()
    assert 'J. Doe' in slide['copyright_line']
    # wyłączenie w ustawieniach (checkbox nieobecny w formularzu)
    client.post(f'/c/{cid}/settings', data={
        'name': 'Zbor A', 'default_notation': 'international',
        'transition_engine': 'v4', 'ccli_license': '111'},
        follow_redirects=True)
    client.post(f'/c/{cid}/studio/send_text', json={
        'text': SONG, 'song_title': 'Hymn'})
    slide = client.get(f'/c/{cid}/studio/api/current-slide').get_json()
    assert slide['copyright_line'] == ''
    # użycie nadal logowane mimo wyłączonej notki
    r = client.get(f'/c/{cid}/studio/ccli-report')
    assert b'Hymn' in r.data
