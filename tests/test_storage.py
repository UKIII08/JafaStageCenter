# Miejsce na pliki wspólnoty: licznik, limit przy wgrywaniu, zwalnianie.
import io

import pytest

from app import create_app, db
from app.models import Arrangement, ArrangementRecording, Church
from app.storage import human, usage
from tests.test_arrangements import MP3, WEBM, main_arr, setup, token


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


def set_limit(cid, mb):
    church = db.session.get(Church, cid)
    church.settings = dict(church.settings or {}, storage_limit_mb=mb)
    db.session.commit()


def upload(client, aid, h, blob):
    return client.post(f'/api/studio/arrangements/{aid}/file', headers=h,
                       data={'kind': 'mix', 'role': '', 'file': (io.BytesIO(blob), 'x.mp3')},
                       content_type='multipart/form-data')


def test_usage_counts_recordings_and_memos(app, client):
    cid, sid = setup(client, app)
    aid = main_arr(client, cid, sid)
    h = token(client, cid)
    assert upload(client, aid, h, MP3 + b'\x00' * 5000).status_code == 200
    tile = db.session.get(Arrangement, aid).form[1]['id']
    client.post(f'/c/{cid}/arrangements/{aid}/roles', json={'add': 'Wokal'})
    client.post(f'/c/{cid}/arrangements/{aid}/memo', data={
        'tile': tile, 'role': 'Wokal', 'audio': (io.BytesIO(WEBM), 'memo')},
        content_type='multipart/form-data')
    u = usage(db.session.get(Church, cid))
    assert u['parts']['recordings'] >= 5000 and u['parts']['memos'] > 0
    assert u['by_arr'][aid] >= 5000
    assert u['limit'] == 2048 * 1024 * 1024


def test_upload_refused_when_full(app, client):
    cid, sid = setup(client, app)
    aid = main_arr(client, cid, sid)
    h = token(client, cid)
    set_limit(cid, 1)                                  # 1 MB
    big = MP3 + b'\x00' * (1024 * 1024)
    r = upload(client, aid, h, big)
    assert r.status_code == 413 and r.get_json()['error'] == 'storage_full'
    assert ArrangementRecording.query.count() == 0
    # podmiana nagrania tego samego rodzaju liczy zwolnione miejsce
    assert upload(client, aid, h, MP3 + b'\x00' * 600 * 1024).status_code == 200
    assert upload(client, aid, h, MP3 + b'\x00' * 700 * 1024).status_code == 200


def test_memo_refused_when_full(app, client):
    cid, sid = setup(client, app)
    aid = main_arr(client, cid, sid)
    set_limit(cid, 1)
    tile = db.session.get(Arrangement, aid).form[1]['id']
    client.post(f'/c/{cid}/arrangements/{aid}/roles', json={'add': 'Wokal'})
    r = client.post(f'/c/{cid}/arrangements/{aid}/memo', data={
        'tile': tile, 'role': 'Wokal', 'audio': (io.BytesIO(WEBM + b'\x00' * 1100 * 1024), 'memo')},
        content_type='multipart/form-data')
    assert r.status_code == 413 and 'Settings' in r.get_json()['error']


def test_admin_sees_usage_and_frees_space(app, client):
    cid, sid = setup(client, app)
    aid = main_arr(client, cid, sid)
    h = token(client, cid)
    upload(client, aid, h, MP3 + b'\x00' * 5000)
    page = client.get(f'/c/{cid}/settings').get_data(as_text=True)
    assert 'id="storage"' in page and f'/arrangements/{aid}/recordings/delete' in page
    client.post(f'/c/{cid}/arrangements/{aid}/recordings/delete')
    assert ArrangementRecording.query.count() == 0
    assert db.session.get(Arrangement, aid) is not None       # aranżacja zostaje
    assert usage(db.session.get(Church, cid))['parts']['recordings'] == 0


def test_dashboard_warns_admin_near_limit(app, client):
    cid, sid = setup(client, app)
    aid = main_arr(client, cid, sid)
    h = token(client, cid)
    upload(client, aid, h, MP3 + b'\x00' * 900 * 1024)
    assert 'Free up space' not in client.get(f'/c/{cid}').get_data(as_text=True)
    set_limit(cid, 1)
    assert 'Free up space' in client.get(f'/c/{cid}').get_data(as_text=True)


def test_human_sizes():
    assert [human(x) for x in (500, 350000, 12.5 * 2 ** 20, 2 ** 31)] == \
        ['500 B', '342 KB', '12.5 MB', '2 GB']
