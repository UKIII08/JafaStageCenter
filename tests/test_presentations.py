# Prezentacje PDF online: slajdy (obrazki z przeglądarki) zapisane per
# wspólnota, lista dla panelu i dla aplikacji na komputer, limit miejsca,
# przełączanie slajdu z widoku prezentera.
import io

import pytest

from app import create_app, db, socketio
from app.models import Church, Invitation

JPG = b'\xff\xd8\xff\xe0' + b'0' * 200
PNG = b'\x89PNG\r\n\x1a\n' + b'0' * 200


@pytest.fixture()
def app(tmp_path):
    app = create_app('app.config.TestConfig')
    app.instance_path = str(tmp_path)
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()


def team(app):
    lead, mus = app.test_client(), app.test_client()
    lead.post('/register', data={'email': 'l@l.pl', 'password': 'haslo1234', 'display_name': 'Lider'})
    lead.post('/church/create', data={'name': 'Zbor'})
    cid = Church.query.first().id
    lead.post(f'/c/{cid}/team/invite', data={'role': 'muzyk'})
    code = Invitation.query.first().code
    mus.post('/register', data={'email': 'm@m.pl', 'password': 'haslo1234', 'display_name': 'Muzyk'})
    mus.get(f'/join/{code}')
    return cid, lead, mus


def upload(client, cid, slides, name='Kazanie.pdf'):
    data = {'name': name,
            'slide': [(io.BytesIO(b), f's{i}.jpg') for i, b in enumerate(slides)]}
    return client.post(f'/c/{cid}/studio/upload_presentation', data=data,
                       content_type='multipart/form-data')


def test_upload_list_serve_delete(app):
    cid, lead, mus = team(app)
    r = upload(lead, cid, [JPG, PNG, JPG])
    assert r.status_code == 200, r.get_json()
    j = r.get_json()
    assert j['name'] == 'Kazanie' and len(j['slides']) == 3
    assert j['slides'][1].endswith('/s001.png')
    # slajd dostępny dla ekranu (media bez sesji)
    img = app.test_client().get(j['slides'][0])
    assert img.status_code == 200 and img.data == JPG
    # lista: panel i aplikacja na komputer (files do pobrania)
    lst = lead.get(f'/c/{cid}/studio/api/presentations').get_json()['presentations']
    assert [p['id'] for p in lst] == [j['id']]
    assert lst[0]['files'] == ['s000.jpg', 's001.png', 's002.jpg']
    assert lead.post(f'/c/{cid}/studio/delete_presentation', json={'id': j['id']}).status_code == 200
    assert lead.get(f'/c/{cid}/studio/api/presentations').get_json()['presentations'] == []


def test_only_leaders_and_only_images(app):
    cid, lead, mus = team(app)
    assert upload(mus, cid, [JPG]).status_code == 403
    assert mus.get(f'/c/{cid}/studio/api/presentations').status_code == 403
    assert upload(lead, cid, [b'<html><script>1</script>']).status_code == 400
    assert upload(lead, cid, []).status_code == 400
    assert lead.post(f'/c/{cid}/studio/delete_presentation',
                     json={'id': '../../x'}).status_code == 400


def test_storage_limit_applies(app):
    cid, lead, mus = team(app)
    church = db.session.get(Church, cid)
    church.settings = dict(church.settings or {}, storage_limit_mb=1)
    db.session.commit()
    big = b'\xff\xd8\xff' + b'0' * (700 * 1024)
    assert upload(lead, cid, [big]).status_code == 200
    assert upload(lead, cid, [big]).status_code == 413


def test_presenter_nav_goes_only_to_leader_room(app):
    cid, lead, mus = team(app)
    lead_sock = socketio.test_client(app, flask_test_client=lead)
    mus_sock = socketio.test_client(app, flask_test_client=mus)
    lead_sock.emit('join_live', {'church_id': cid})
    mus_sock.emit('join_live', {'church_id': cid})
    lead_sock.get_received(); mus_sock.get_received()
    # muzyk nie może przełączać slajdów
    mus_sock.emit('presenter_nav', {'church_id': cid, 'dir': 1, 'pres_id': 'a', 'at': 1})
    assert not [m for m in lead_sock.get_received() if m['name'] == 'presenter_nav']
    lead_sock.emit('presenter_nav', {'church_id': cid, 'dir': 1, 'pres_id': 'a', 'at': 2})
    got = [m for m in lead_sock.get_received() if m['name'] == 'presenter_nav']
    assert got and got[0]['args'][0] == {'dir': 1, 'at': 2, 'pres_id': 'a'}
    lead_sock.emit('presenter_nav', {'church_id': cid, 'dir': 5})
    assert not [m for m in lead_sock.get_received() if m['name'] == 'presenter_nav']


def test_panel_has_presentation_card(app):
    cid, lead, mus = team(app)
    html = lead.get(f'/c/{cid}/studio').get_data(as_text=True)
    assert 'id="pdf-upload"' in html and 'id="pdf-list"' in html
    assert 'pdf.js/3.11.174/' in html
    pres = lead.get(f'/c/{cid}/studio/presenter').get_data(as_text=True)
    assert 'id="pres-next"' in pres and "presenter_nav" in pres
