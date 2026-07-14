# JafaStage Cloud — fabryka aplikacji (M0)
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
    if os.environ.get('BEHIND_PROXY') == '1':
        # Za Caddy: prawdziwy protokół/host z nagłówków X-Forwarded-*
        # (inaczej linki _external i cookies myślą, że jesteśmy na http).
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    db.init_app(app)
    limiter.init_app(app)
    socketio.init_app(app, cors_allowed_origins=[],
                      message_queue=os.environ.get('REDIS_URL')
                      if not app.config.get('TESTING') else None,
                      async_mode='threading' if app.config.get('TESTING') else None)
    if app.config.get('TESTING'):
        limiter.enabled = False

    from app.auth.routes import auth_bp
    from app.panel.routes import panel_bp
    from app.songs.routes import songs_bp
    from app.live.routes import live_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(panel_bp)
    app.register_blueprint(songs_bp)
    app.register_blueprint(live_bp)

    _register_socket_handlers(app)

    with app.app_context():
        db.create_all()   # M0: create_all; migracje Alembic dojdą w M1

    @app.get('/healthz')
    def healthz():
        return {'status': 'ok'}

    return app


def _register_socket_handlers(app):
    """join_live: autoryzacja (członek wspólnoty LUB ważny token ekranu),
    dołączenie do pokoju wspólnoty i natychmiastowy snapshot stanu —
    spóźnieni widzą bieżący slajd od razu."""
    from flask_socketio import emit
    from app.live import state as live_state
    from app.models import Membership, ScreenToken

    @socketio.on('join_live')
    def join_live(data):
        data = data or {}
        church_id = data.get('church_id')
        if not church_id:
            return
        authorized = False
        uid = session.get('user_id')
        if uid and Membership.query.filter_by(
                user_id=uid, church_id=church_id, status='active').first():
            authorized = True
        elif data.get('token'):
            if ScreenToken.query.filter_by(church_id=church_id,
                                           token=data['token'],
                                           revoked_at=None).first():
                authorized = True
        if not authorized:
            return
        join_room(f'live:{church_id}')
        st = live_state.get_state(church_id)
        if st:
            emit('update_slide', st)
