# Ochrona przed żądaniami z obcych stron (CSRF) i nagłówki bezpieczeństwa.
#
# CSRF: zamiast tokenu w każdym formularzu sprawdzamy nagłówek Origin
# (a gdy go brak — Referer). Przeglądarka zawsze dokleja Origin do POST-a
# wysłanego z innej strony i strona nie może go podrobić. Żądania bez
# żadnego z nagłówków to nie przeglądarka (aplikacja desktop, skrypt
# Reapera z tokenem) — tych CSRF nie dotyczy. Drugą warstwą jest
# ciasteczko sesji SameSite=Lax.
import os
from urllib.parse import urlparse

from flask import abort, request

_UNSAFE = {'POST', 'PUT', 'PATCH', 'DELETE'}


def _same_origin(value):
    if value == 'null':
        return False
    return urlparse(value).netloc == request.host


def init_security(app):
    @app.before_request
    def _csrf_origin_check():
        if request.method not in _UNSAFE:
            return
        if app.config.get('SESSION_COOKIE_NAME', 'session') not in request.cookies:
            return   # bez ciasteczka sesji nie ma czego podszyć
        origin = request.headers.get('Origin')
        if origin is not None:
            if not _same_origin(origin):
                abort(403)
            return
        referer = request.headers.get('Referer')
        if referer and not _same_origin(referer):
            abort(403)

    behind_proxy = os.environ.get('BEHIND_PROXY') == '1'

    @app.after_request
    def _security_headers(resp):
        h = resp.headers
        h.setdefault('X-Content-Type-Options', 'nosniff')
        h.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        h.setdefault('X-Frame-Options', 'SAMEORIGIN')
        if behind_proxy and request.is_secure:
            # Przeglądarka przez rok łączy się tylko po HTTPS.
            h.setdefault('Strict-Transport-Security', 'max-age=31536000')
        return resp
