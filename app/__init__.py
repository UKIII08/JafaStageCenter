# JafaStage Cloud — fabryka aplikacji (M0)
import os

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
# Rate limiting (ochrona logowania/resetu przed brute-force).
# Prod: magazyn w Redisie (wielu workerów); dev/test: pamięć procesu.
limiter = Limiter(key_func=get_remote_address,
                  storage_uri=os.environ.get('REDIS_URL', 'memory://'),
                  default_limits=[])


def create_app(config_object='app.config.Config'):
    app = Flask(__name__, template_folder='templates',
                static_folder='../static')
    app.config.from_object(config_object)
    db.init_app(app)
    limiter.init_app(app)
    if app.config.get('TESTING'):
        limiter.enabled = False

    from app.auth.routes import auth_bp
    from app.panel.routes import panel_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(panel_bp)

    with app.app_context():
        db.create_all()   # M0: create_all; migracje Alembic dojdą w M1

    @app.get('/healthz')
    def healthz():
        return {'status': 'ok'}

    return app
