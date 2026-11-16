# Luki z audytu bezpieczeństwa: kod w danych (XSS), cudze profile,
# pliki HTML z uploadów.
import io
import json
import re
import shutil
import subprocess

import pytest

from app import create_app, db
from app.models import Church, Invitation, Profile

NODE = shutil.which('node')
PAYLOAD = '<img src=x onerror=alert(1)>'


@pytest.fixture()
def app():
    app = create_app('app.config.TestConfig')
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()


def team(app):
    """Lider + muzyk w jednej wspólnocie, każdy na własnym kliencie."""
    lead, mus = app.test_client(), app.test_client()
    lead.post('/register', data={'email': 'l@l.pl', 'password': 'haslo1234', 'display_name': 'Lider'})
    lead.post('/church/create', data={'name': 'Zbor'})
    cid = Church.query.first().id
    lead.post(f'/c/{cid}/team/invite', data={'role': 'muzyk'})
    code = Invitation.query.first().code
    mus.post('/register', data={'email': 'm@m.pl', 'password': 'haslo1234', 'display_name': 'Muzyk'})
    mus.get(f'/join/{code}')
    return cid, lead, mus


def test_musician_cannot_change_or_delete_someone_elses_profile(app):
    cid, lead, mus = team(app)
    lp = Profile.query.filter_by(name='Lider').first()
    mp = Profile.query.filter_by(name='Muzyk').first()
    base = f'/c/{cid}/studio/api/profiles'
    assert mus.put(f'{base}/{lp.id}', json={'name': 'X'}).status_code == 403
    assert mus.delete(f'{base}/{lp.id}').status_code == 403
    assert db.session.get(Profile, lp.id).name == 'Lider' and not db.session.get(Profile, lp.id).deleted
    # swój profil: tak; lider cudzy: tak
    assert mus.put(f'{base}/{mp.id}', json={'name': 'Ola', 'capo_fret': 2}).status_code == 200
    assert lead.put(f'{base}/{mp.id}', json={'instrument': 'gitara'}).status_code == 200
    p = db.session.get(Profile, mp.id)
    assert p.name == 'Ola' and p.instrument == 'gitara' and p.prefs['capo_fret'] == 2


def test_musician_cannot_touch_someone_elses_song_notes(app):
    cid, lead, mus = team(app)
    lead.post(f'/c/{cid}/songs/new', data={'title': 'A', 'content': 'Zwrotka\n[G]tekst', 'key': 'G'})
    from app.models import Song
    sid = Song.query.first().id
    lp = Profile.query.filter_by(name='Lider').first()
    url = f'/c/{cid}/studio/api/profiles/{lp.id}/song/{sid}'
    assert lead.put(url, json={'notes': {'0': 'moja'}}).status_code == 200
    assert mus.put(url, json={'notes': {'0': 'cudza'}}).status_code == 403
    assert mus.get(url).status_code == 403
    assert lead.get(url).get_json()['notes'] == {'0': 'moja'}


def test_profile_fields_are_validated(app):
    cid, lead, mus = team(app)
    mp = Profile.query.filter_by(name='Muzyk').first()
    mus.put(f'/c/{cid}/studio/api/profiles/{mp.id}',
            json={'name': 'x' * 500, 'color': 'red" onmouseover="alert(1)'})
    p = db.session.get(Profile, mp.id)
    assert len(p.name) == 120 and p.color.startswith('#')


def test_uploaded_html_is_sandboxed(app):
    cid, lead, mus = team(app)
    lead.post(f'/c/{cid}/studio/upload_transition', data={
        'transition_file': (io.BytesIO(b'<html><script>1</script></html>'), 't.html')},
        content_type='multipart/form-data')
    r = app.test_client().get(f'/c/{cid}/media/transition.html')
    assert r.status_code == 200
    assert r.headers['Content-Security-Policy'] == 'sandbox allow-scripts'
    page = open('app/templates/studio/projector.html', encoding='utf-8').read()
    assert 'id="transition-html" sandbox="allow-scripts"' in page


def test_studio_and_band_screen_escape_user_data():
    studio = open('static/js/control_logic.js', encoding='utf-8').read()
    band = open('app/templates/studio/band_member.html', encoding='utf-8').read()
    # dawne niezabezpieczone wstawienia nie mogą wrócić
    for raw in ('<b>${s.title}</b>', '${sec.label}</span>', "'</span> ${s.title}",
                '<div class="lib-content-preview">${preview}</div>'):
        assert raw not in studio, raw
    for raw in ("'<div class=\"profile-card-name\">' + p.name +", "+ (song.title || 'Untitled') +",
                "'<div class=\"browse-tile-label\">' + sec.label +", "')\">' + note + '</div>'"):
        assert raw not in band, raw
    assert studio.count('escHtml(') > 15 and band.count('escHtml(') > 12


@pytest.mark.skipif(not NODE, reason='node not installed')
def test_escaping_helpers_neutralise_markup():
    code = r"""
const fs=require('fs');
const studio=fs.readFileSync('static/js/control_logic.js','utf8');
const m=studio.match(/function escHtml[\s\S]*?\n}\n/)[0] + studio.match(/function safeId[^\n]*\n/)[0];
const f=new Function(m+';return {escHtml,safeId};')();
const d=new Function(fs.readFileSync('static/js/chord_diagrams.js','utf8')+';return {renderPianoSVG,renderChordSVG,lookupChord};')();
const P=%s;
console.log(JSON.stringify({
  esc: f.escHtml(P), id: f.safeId("a');alert(1);//"),
  piano: d.renderPianoSVG(P,[0,4,7]), guitar: d.renderChordSVG(P, d.lookupChord('C'))}));
""" % json.dumps(PAYLOAD)
    out = json.loads(subprocess.run([NODE, '-e', code], capture_output=True, text=True, check=True).stdout)
    assert '<' not in out['esc'] and out['esc'].startswith('&lt;img')
    assert re.fullmatch(r'[A-Za-z0-9_.:-]*', out['id'])
    assert '<img' not in out['piano'] and '<img' not in out['guitar']
