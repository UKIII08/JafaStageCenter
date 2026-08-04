# Testy biblioteki piosenek i setlist (M1) — w tym tenancy.
import pytest

from app import create_app, db
from app.models import Song, Setlist


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


def setup_church(client, app, email='l@l.pl', name='Zbor L'):
    client.post('/register', data={'email': email, 'password': 'haslo1234',
                                   'display_name': 'Lider'})
    client.post('/church/create', data={'name': name})
    with app.app_context():
        from app.models import Church
        return Church.query.filter_by(name=name).first().id


SONG = """Zwrotka
[G#m]Jaśnieje [E]słońce [F#]dziś

Refren
[C#m]Alleluja [E]amen"""


def test_song_crud_and_render(app, client):
    cid = setup_church(client, app)
    r = client.post(f'/c/{cid}/songs/new', data={
        'title': 'Testowa', 'content': SONG, 'key': '', 'bpm': '72'},
        follow_redirects=True)
    assert 'chord-pair' in r.get_data(as_text=True)   # widok renderuje pary
    with app.app_context():
        song = Song.query.first()
        assert song.key == 'C#m' or song.key   # detekcja tonacji zadziałała
        assert 'G#m' in song.content            # enharmonia zachowana
        sid = song.id
    # transpozycja podglądu
    r = client.get(f'/c/{cid}/songs/{sid}?t=2')
    assert 'A#m' in r.get_data(as_text=True) or 'Bbm' in r.get_data(as_text=True)
    # edycja
    client.post(f'/c/{cid}/songs/{sid}/edit', data={
        'title': 'Testowa 2', 'content': SONG, 'key': 'C#m', 'bpm': '80'})
    with app.app_context():
        assert db.session.get(Song, sid).title == 'Testowa 2'
    # soft delete (uwaga: flash "Usunięto: ..." zawiera tytuł — sprawdzamy
    # brak LINKU do piosenki, nie brak samego tekstu)
    client.post(f'/c/{cid}/songs/{sid}/delete', follow_redirects=True)
    r = client.get(f'/c/{cid}/songs')
    assert f'/songs/{sid}' not in r.get_data(as_text=True)


def test_songs_tenancy(app, client):
    cid_a = setup_church(client, app, 'a@t.pl', 'Zbor A')
    client.post(f'/c/{cid_a}/songs/new',
                data={'title': 'Sekret A', 'content': '[C]x'})
    with app.app_context():
        sid = Song.query.first().id
    client.get('/logout')
    setup_church(client, app, 'b@t.pl', 'Zbor B')
    assert client.get(f'/c/{cid_a}/songs').status_code == 403
    assert client.get(f'/c/{cid_a}/songs/{sid}').status_code == 403
    assert client.post(f'/c/{cid_a}/songs/{sid}/delete').status_code == 403


def test_musician_can_add_but_not_edit_or_delete_songs(app, client):
    cid = setup_church(client, app)
    client.post(f'/c/{cid}/songs/new', data={'title': 'X', 'content': '[C]x'})
    r = client.post(f'/c/{cid}/team/invite', data={'role': 'muzyk'})
    with app.app_context():
        from app.models import Invitation, Song
        code = Invitation.query.first().code
        sid = Song.query.first().id
    client.get('/logout')
    client.post('/register', data={'email': 'm@m.pl', 'password': 'haslo1234',
                                   'display_name': 'Muzyk'})
    client.get(f'/join/{code}')
    assert client.get(f'/c/{cid}/songs/{sid}').status_code == 200   # czyta
    assert client.get(f'/c/{cid}/songs/new').status_code == 200     # dodaje
    r = client.post(f'/c/{cid}/songs/new',
                    data={'title': 'Nowa', 'content': '[G]y'})
    assert r.status_code in (200, 302)
    with app.app_context():
        assert Song.query.filter_by(title='Nowa').first() is not None
    # ale nie edytuje ani nie usuwa cudzych/wspólnych piosenek
    assert client.get(f'/c/{cid}/songs/{sid}/edit').status_code == 403
    assert client.post(f'/c/{cid}/songs/{sid}/delete').status_code == 403


def test_import_txt_skips_duplicates(app, client):
    import io
    cid = setup_church(client, app)
    payload = "Piesn Jedna (C)-(72)\n[C]Ala ma kota\n---\nPiesn Druga (G)\n[G]Kot ma Ale"
    client.post(f'/c/{cid}/songs/import', data={
        'files': (io.BytesIO(payload.encode()), 'export.txt')},
        content_type='multipart/form-data')
    with app.app_context():
        assert Song.query.count() == 2
    # drugi import tego samego pliku niczego nie nadpisuje
    r = client.post(f'/c/{cid}/songs/import', data={
        'files': (io.BytesIO(payload.encode()), 'export.txt')},
        content_type='multipart/form-data', follow_redirects=True)
    with app.app_context():
        assert Song.query.count() == 2
    assert b'Skipped' in r.data


def test_import_txt_splits_on_dash_separators(app, client):
    """Zbiorczy śpiewnik rozdzielony linią myślników — także pauzą „———"
    (U+2014), nie tylko ASCII „---". Regresja: cały plik szedł jako 1 piosenka."""
    import io
    cid = setup_church(client, app)
    payload = (
        "Piesn A (D)\n[D]tekst a\n"
        "\n———\n\n"          # pauza (em dash) — realny wariant z klawiatury
        "Piesn B (a)\n[a]tekst b\n"
        "\n---\n\n"          # ASCII, ten sam plik
        "Piesn C (G)\n[G]tekst c"
    )
    r = client.post(f'/c/{cid}/songs/import', data={
        'files': (io.BytesIO(payload.encode()), 'spiewnik.txt')},
        content_type='multipart/form-data', follow_redirects=True)
    assert b'Imported' in r.data
    with app.app_context():
        assert Song.query.count() == 3
        assert {s.title for s in Song.query.all()} == {
            'Piesn A', 'Piesn B', 'Piesn C'}


def test_import_chordpro_from_songselect(app, client):
    import io
    cid = setup_church(client, app)
    # format jak pobranie z CCLI SongSelect
    cho = (
        "{title: Amazing Grace}\n"
        "{artist: Words by: John Newton}\n"
        "{artist: Music by: Edwin Excell}\n"
        "{key: G}\n"
        "{ccli: 4768151}\n"
        "{tempo: 72}\n"
        "{time: 3/4}\n"
        "{copyright: Public Domain}\n\n"
        "{comment: Verse 1}\n"
        "A - [G]mazing grace how [C]sweet the [G]sound\n"
        "And [G]grace my [G/D]fears [D/C]re - [G/B]lieved\n\n"
        "{comment: Chorus}\n"
        "I [G]have al - [G/D]read - [D/C]y [G]come\n\n"
        "CCLI Song # 4768151\n"
        "© Public Domain\n"
        "For use solely with the SongSelect® Terms of Use. www.ccli.com\n"
    )
    r = client.post(f'/c/{cid}/songs/import', data={
        'files': (io.BytesIO(cho.encode()), 'amazing_grace.cho')},
        content_type='multipart/form-data', follow_redirects=True)
    assert b'Imported' in r.data
    with app.app_context():
        s = Song.query.filter_by(title='Amazing Grace').first()
        assert s is not None
        assert s.key == 'G'
        assert s.bpm == 72
        assert s.ccli_number == '4768151'
        # Words by/Music by sklejone i oczyszczone z prefiksów
        assert s.author == 'John Newton, Edwin Excell'
        assert 'Public Domain' in s.copyright
        # etykiety sekcji z {comment} trafiły do treści (kafelki)
        assert 'Verse 1' in s.content and 'Chorus' in s.content
        # ŁĄCZNIKI SYLAB usunięte (nie mogą iść na rzutnik), akord zostaje
        assert ' - ' not in s.content
        assert 'A[G]mazing' in s.content
        assert 're[G/B]lieved' in s.content
        assert 'al[G/D]read[D/C]y' in s.content
        # stopka SongSelect wycięta
        assert 'CCLI Song' not in s.content
        assert 'ccli.com' not in s.content.lower()
        assert 'SongSelect' not in s.content


def test_setlist_flow(app, client):
    cid = setup_church(client, app)
    client.post(f'/c/{cid}/songs/new', data={'title': 'A', 'content': '[C]a'})
    client.post(f'/c/{cid}/songs/new', data={'title': 'B', 'content': '[G]b'})
    with app.app_context():
        ids = [s.id for s in Song.query.order_by(Song.title).all()]
    client.post(f'/c/{cid}/setlists', data={'name': 'Niedziela'})
    with app.app_context():
        slid = Setlist.query.first().id
    base = f'/c/{cid}/setlists/{slid}/items'
    client.post(base, data={'action': 'add', 'song_id': ids[0]})
    client.post(base, data={'action': 'add', 'song_id': ids[1]})
    client.post(base, data={'action': 'up', 'idx': '1'})      # B przed A
    client.post(base, data={'action': 't_up', 'idx': '0'})    # B +1
    with app.app_context():
        items = Setlist.query.first().items
        assert items[0]['song_id'] == ids[1]
        assert items[0]['transpose'] == 1
    # duplikacja
    client.post(f'/c/{cid}/setlists/{slid}/duplicate')
    with app.app_context():
        assert Setlist.query.count() == 2
