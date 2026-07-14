# JafaStage Cloud — fabryka aplikacji (M0)
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config_object='app.config.Config'):
    app = Flask(__name__, template_folder='templates',
                static_folder='../static')
    app.config.from_object(config_object)
    db.init_app(app)

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
