# Jonathan App (dawniej JafaStage Cloud) — fabryka aplikacji
import os

from flask import Flask, request, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO, join_room
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix

db = SQLAlchemy()
socketio = SocketIO()
# Rate limiting (ochrona logowania/resetu przed brute-force).
# Prod: magazyn w Redisie (wielu workerów); dev/test: pamięć procesu.
limiter = Limiter(key_func=get_remote_address,
                  storage_uri=os.environ.get('REDIS_URL', 'memory://'),
                  default_limits=[])


def create_app(config_object='app.config.Config'):
    app = Flask(__name__, template_folder='templates',
                static_folder='../static')
    app.config.from_object(config_object)
    # Fail-closed: w produkcji nie wolno wystartować z domyślnym/pustym
    # SECRET_KEY — podpisuje ciasteczka sesji i tokeny resetu hasła. Do
    # lokalnego devu można świadomie ustawić ALLOW_INSECURE_SECRET=1.
    if (not app.config.get('TESTING')
            and os.environ.get('ALLOW_INSECURE_SECRET') != '1'):
        sk = app.config.get('SECRET_KEY')
        if not sk or sk == 'dev-only-change-me':
            raise RuntimeError(
                'SECRET_KEY nie jest ustawiony (lub ma wartość domyślną). '
                'Ustaw silny, unikalny SECRET_KEY w środowisku (deploy/.env). '
                'Lokalnie do testów: ALLOW_INSECURE_SECRET=1.')
    if os.environ.get('BEHIND_PROXY') == '1':
        # Za Caddy: prawdziwy protokół/host z nagłówków X-Forwarded-*
        # (inaczej linki _external i cookies myślą, że jesteśmy na http).
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    db.init_app(app)
    limiter.init_app(app)
    socketio.init_app(app, cors_allowed_origins=[],
                      message_queue=os.environ.get('REDIS_URL')
                      if not app.config.get('TESTING') else None,
                      async_mode='threading')
    if app.config.get('TESTING'):
        limiter.enabled = False

    from app.auth.routes import auth_bp
    from app.panel.routes import panel_bp
    from app.songs.routes import songs_bp
    from app.live.routes import live_bp
    from app.studio.routes import studio_bp
    from app.events.routes import events_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(panel_bp)
    app.register_blueprint(songs_bp)
    app.register_blueprint(live_bp)
    app.register_blueprint(studio_bp)
    app.register_blueprint(events_bp)

    _register_socket_handlers(app)

    # i18n panelu (gettext, EN domyślny) — dostępne w każdym szablonie jako _()
    from app.i18n import translate, get_lang, set_lang, LANGUAGES
    app.jinja_env.globals['_'] = translate
    app.jinja_env.globals['current_lang'] = get_lang
    app.jinja_env.globals['languages'] = LANGUAGES

    @app.get('/lang/<code>')
    def switch_lang(code):
        from flask import redirect, request as _req
        from urllib.parse import urlparse
        set_lang(code)
        # Anty open-redirect: ?next tylko jako lokalna ścieżka; referrer tylko
        # jeśli z tego samego hosta (bierzemy samą ścieżkę), inaczej '/'.
        target = _req.args.get('next') or ''
        if (target.startswith('/') and not target.startswith('//')
                and not urlparse(target).netloc):
            return redirect(target)
        ref = _req.referrer
        if ref and urlparse(ref).netloc == urlparse(_req.host_url).netloc:
            rp = urlparse(ref)
            return redirect(rp.path + (('?' + rp.query) if rp.query else ''))
        return redirect('/')

    with app.app_context():
        db.create_all()   # M0: create_all; migracje Alembic dojdą w M1
        _ensure_columns()   # drobne ALTER-y dla kolumn dodanych po M3

    @app.get('/healthz')
    def healthz():
        return {'status': 'ok'}

    return app


def _ensure_columns():
    """Mini-migracja: dodaje brakujące kolumny do istniejących tabel
    (create_all tworzy tylko nowe tabele). Bezpieczne przy każdym starcie."""
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    wanted = {
        'song_personal': [
            ('capo_fret', 'INTEGER'),
            ('section_notes', "TEXT DEFAULT '{}'"),
        ],
        'songs': [
            ('ccli_number', "VARCHAR(20) DEFAULT ''"),
            ('author', "VARCHAR(300) DEFAULT ''"),
            ('copyright', "VARCHAR(300) DEFAULT ''"),
            ('link', "VARCHAR(500) DEFAULT ''"),
        ],
        'events': [
            ('welcome_json', "TEXT DEFAULT ''"),
        ],
        'studio_setlists': [
            ('welcome_json', "TEXT DEFAULT ''"),
        ],
    }
    for table, cols in wanted.items():
        if table not in insp.get_table_names():
            continue
        existing = {c['name'] for c in insp.get_columns(table)}
        for name, ddl in cols:
            if name not in existing:
                db.session.execute(text(
                    f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))
    db.session.commit()


def _register_socket_handlers(app):
    """Protokół LIVE = protokół aplikacji desktop (sync_state_to_client /
    update_slide / timer_update / silent_md), zawężony do pokoju wspólnoty.
    join_live: autoryzacja (członek wspólnoty LUB ważny token ekranu),
    dołączenie do pokoju i natychmiastowy snapshot stanu — spóźnieni widzą
    bieżący slajd od razu."""
    from flask_socketio import emit
    from app.live import state as live_state
    from app.models import Membership, ScreenToken

    def _authorized(data):
        church_id = (data or {}).get('church_id')
        if not church_id:
            return None
        uid = session.get('user_id')
        if uid and Membership.query.filter_by(
                user_id=uid, church_id=church_id, status='active').first():
            return church_id
        if data.get('token') and ScreenToken.query.filter_by(
                church_id=church_id, token=data['token'],
                revoked_at=None).first():
            return church_id
        return None

    def _leader(data):
        """Zapis stanu tylko dla prowadzącego/admina zalogowanego w panelu."""
        church_id = (data or {}).get('church_id')
        uid = session.get('user_id')
        if not (church_id and uid):
            return None
        m = Membership.query.filter_by(user_id=uid, church_id=church_id,
                                       status='active').first()
        if m and m.role in ('prowadzacy', 'admin'):
            return church_id
        return None

    @socketio.on('join_live')
    def join_live(data):
        church_id = _authorized(data)
        if not church_id:
            return
        join_room(f'live:{church_id}')
        # Snapshot jak w desktopowym handle_connect
        emit('sync_state_to_client',
             live_state.studio_get(church_id, 'server_state',
                                   {'setlist': [], 'current_index': -1,
                                    'is_blackout': False}))
        last = live_state.studio_get(church_id, 'last_slide')
        if last:
            emit('update_slide', last)
        emit('timer_update',
             live_state.studio_get(church_id, 'conf_timer',
                                   {'timer': '00:00',
                                    'timer_color': 'white', 'message': ''}))
        smd = live_state.studio_get(church_id, 'silent_md')
        if smd and smd.get('active'):
            emit('silent_md', smd)

    @socketio.on('client_update_state')
    def client_update_state(data):
        church_id = _leader(data)
        if not church_id:
            return
        st = live_state.studio_get(church_id, 'server_state',
                                   {'setlist': [], 'current_index': -1,
                                    'is_blackout': False})
        st['setlist'] = data.get('setlist', [])
        st['current_index'] = data.get('current_index', -1)
        live_state.studio_set(church_id, 'server_state', st)
        emit('sync_state_to_client', st, room=f'live:{church_id}')
        # Pusta setlista => nie ma LIVE. Kasujemy ostatni slajd (logo) i gasimy
        # ekrany — niezależnie od tego, jak setlista została opróżniona. Bez
        # tego dashboard i telefony zespołu pokazują "na żywo" po staremu.
        if not st['setlist']:
            live_state.studio_set(church_id, 'last_slide', {'mode': 'logo'})
            emit('update_slide', {'mode': 'logo'}, room=f'live:{church_id}')

    @socketio.on('request_current_slide')
    def request_current_slide(data):
        church_id = _authorized(data)
        if not church_id:
            return
        last = live_state.studio_get(church_id, 'last_slide')
        if last:
            emit('update_slide', last)

    @socketio.on('silent_md')
    def silent_md(data):
        church_id = _leader(data)
        if not church_id:
            return
        st = {'active': bool(data.get('active')),
              'current': data.get('current'),
              'history': (data.get('history') or [])[-4:]}
        live_state.studio_set(church_id, 'silent_md', st)
        emit('silent_md', st, room=f'live:{church_id}')

    @socketio.on('set_language')
    def set_language(data):
        church_id = _leader(data)
        if not church_id:
            return
        emit('apply_settings', {'lang': (data or {}).get('lang', 'pl')},
             room=f'live:{church_id}')
