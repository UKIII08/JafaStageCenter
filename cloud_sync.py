# cloud_sync.py — pobieranie danych z chmury (web app Jonathan) do lokalnej
# bazy offline. Świadomie używa WYŁĄCZNIE biblioteki standardowej
# (urllib + http.cookiejar), żeby nie dodawać zależności do builda .exe.
#
# Zasada: wszystko best-effort. Gdy nie ma sieci / serwer nieosiągalny —
# funkcje rzucają CloudUnavailable, a aplikacja po prostu działa offline na
# tym, co ma lokalnie. Logujemy się kontem prowadzącego/admina i pobieramy:
#   - piosenki   (GET /c/<id>/studio/export_songs  -> format .txt eksportu)
#   - setlisty   (GET /c/<id>/studio/api/setlist-history -> JSON)
#   - profile    (GET /c/<id>/studio/api/profiles        -> JSON)
import http.cookiejar
import json
import re
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_URL = 'https://jonathanapp.com'
_TIMEOUT = 8
_UUID_RE = re.compile(r'/c/([0-9a-fA-F-]{36})')
_HEADER_RE = re.compile(r'^(.*?)(?:\s*\(([^)]+)\))?(?:-\((\d+)\))?$')


class CloudError(Exception):
    """Błąd ogólny synchronizacji."""


class CloudUnavailable(CloudError):
    """Brak sieci / serwer nieosiągalny — aplikacja działa offline."""


class CloudAuthError(CloudError):
    """Złe dane logowania albo brak dostępu do wspólnoty."""


def _opener():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def _open(opener, url, data=None):
    """Zwraca odpowiedź. Sieć padła -> CloudUnavailable. 4xx -> HTTPError
    (przekazujemy dalej, żeby rozróżnić 403/404 od braku sieci)."""
    req = urllib.request.Request(
        url, data=data, headers={'User-Agent': 'JonathanDesktop'})
    try:
        return opener.open(req, timeout=_TIMEOUT)
    except urllib.error.HTTPError:
        raise
    except (urllib.error.URLError, OSError):
        raise CloudUnavailable()


def connect(base_url, email, password):
    """Loguje się do chmury i wykrywa wspólnotę. Zwraca (opener, church_id).
    CloudUnavailable — brak sieci; CloudAuthError — złe hasło / brak wspólnoty."""
    base = (base_url or DEFAULT_URL).rstrip('/')
    opener = _opener()
    body = urllib.parse.urlencode(
        {'email': email or '', 'password': password or ''}).encode()
    try:
        after_login = _open(opener, base + '/login', data=body).geturl()
        home = _open(opener, base + '/').geturl()
    except urllib.error.HTTPError:
        raise CloudUnavailable()
    # Po poprawnym logowaniu wejście na '/' przekierowuje na /c/<church_id>.
    m = _UUID_RE.search(home) or _UUID_RE.search(after_login)
    if not m:
        raise CloudAuthError(
            'Nie udało się zalogować albo wykryć wspólnoty — '
            'sprawdź adres, e-mail i hasło.')
    return opener, m.group(1)


def _get_text(opener, url):
    try:
        return _open(opener, url).read().decode('utf-8-sig', errors='ignore')
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 404):
            return None            # brak dostępu do zasobu — pomijamy
        raise CloudUnavailable()


def _get_json(opener, url):
    txt = _get_text(opener, url)
    if txt is None:
        return None
    try:
        return json.loads(txt)
    except (ValueError, json.JSONDecodeError):
        return None


def fetch_songs(opener, base_url, church_id):
    """Lista (title, content, key, bpm) z chmury (format .txt eksportu).
    None -> brak dostępu (np. konto bez roli prowadzącego)."""
    base = (base_url or DEFAULT_URL).rstrip('/')
    raw = _get_text(opener, f'{base}/c/{church_id}/studio/export_songs')
    if raw is None:
        return None
    songs = []
    for chunk in raw.replace('\r', '').split('---'):
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = chunk.splitlines()
        m = _HEADER_RE.match(lines[0].strip())
        if m:
            title = m.group(1).strip()
            key = (m.group(2) or '').strip()
            try:
                bpm = int(m.group(3)) if m.group(3) else 0
            except ValueError:
                bpm = 0
        else:
            title, key, bpm = lines[0].strip(), '', 0
        body = '\n'.join(lines[1:]).strip()
        if title and body:
            songs.append((title, body, key, bpm))
    return songs


def fetch_profiles(opener, base_url, church_id):
    base = (base_url or DEFAULT_URL).rstrip('/')
    return _get_json(opener, f'{base}/c/{church_id}/studio/api/profiles')


def fetch_setlists(opener, base_url, church_id):
    base = (base_url or DEFAULT_URL).rstrip('/')
    return _get_json(opener, f'{base}/c/{church_id}/studio/api/setlist-history')
