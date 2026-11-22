import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///jafastage_dev.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    # Limit uploadu (prezentacje PDF). Obniżony z 256 MB — ochrona przed DoS
    # (przy 1 workerze kilka wielkich uploadów potrafiło zablokować serwer).
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # Prod (HTTPS przez Caddy): cookie tylko po HTTPS.
    SESSION_COOKIE_SECURE = os.environ.get('BEHIND_PROXY') == '1'
    # Integracja z JafaApp (Jafa Warszawa) — wspólny sekret i id wspólnoty.
    # Puste = integracja wyłączona (app/integrations/jafa.py).
    JAFA_SECRET = os.environ.get('JAFA_SECRET', '')
    JAFA_CHURCH_ID = os.environ.get('JAFA_CHURCH_ID', '')


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'   # in-memory
    WTF_CSRF_ENABLED = False
