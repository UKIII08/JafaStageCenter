"""Most do wtyczki Jafa Worship Piano.

Aplikacja wie, która piosenka jest na ekranie, w jakim tempie i tonacji.
Pianino nie wie, a na scenie nie ma wolnej ręki, żeby mu powiedzieć. Więc
aplikacja zostawia to na dysku, a wtyczka to czyta.

Plik, a nie gniazdo sieciowe — świadomie. Obie strony chodzą na tym samym
komputerze (to jest cały sens), a plik nie potrzebuje portu, nie wywoła pytania
zapory w środku nabożeństwa i nie wymaga sieci we wtyczce audio. Przeżywa też
restart którejkolwiek strony, czego gniazdo nie robi.

Wymiana idzie przez folder, w którym wtyczka i tak trzyma swoje presety:

    Windows:  %APPDATA%\\Jafa Stage\\Worship Piano
    macOS:    ~/Library/Application Support/Jafa Stage/Worship Piano
    Linux:    ~/.config/Jafa Stage/Worship Piano

    live.json    — piszemy my, czyta wtyczka (co jest grane)
    plugin.json  — pisze wtyczka, czytamy my (jakie presety istnieją)

Świadomie NIE przekazujemy transpozycji. Jeśli akordy, z których gra pianista,
są już przeniesione przez aplikację, ustawienie transpozycji jeszcze raz we
wtyczce przesunęłoby dźwięk drugi raz. Tonacja jedzie tylko do pokazania.
"""

import json
import os
import subprocess
import sys
import tempfile
import time


def shared_dir():
    """Folder wymiany. Ta sama ścieżka, którą wylicza wtyczka."""
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
    elif sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support')
    else:
        base = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')

    path = os.path.join(base, 'Jafa Stage', 'Worship Piano')

    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        return None

    return path


def _write_atomic(path, payload):
    """Zapis przez plik tymczasowy i podmianę.

    Wtyczka czyta ten plik pięć razy na sekundę i trafiłaby w połowę zapisu.
    Podmiana nazwy na tym samym wolumenie jest niepodzielna wszędzie, gdzie to
    chodzi, więc wtyczka zawsze widzi albo stary plik, albo cały nowy.
    """
    folder = os.path.dirname(path)
    handle, temp = tempfile.mkstemp(dir=folder, suffix='.tmp')

    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(temp, path)
        return True
    except OSError:
        try:
            os.unlink(temp)
        except OSError:
            pass
        return False


def publish_song(song_id, title, key, bpm, preset):
    """Mówi wtyczce, co jest grane. Cicho zawodzi — to nie jest ścieżka krytyczna.

    Jeśli tego nie da się zapisać, nabożeństwo ma się toczyć dalej: pianino po
    prostu zostaje na brzmieniu, które ma.
    """
    folder = shared_dir()

    if not folder:
        return False

    return _write_atomic(os.path.join(folder, 'live.json'), {
        'song_id': int(song_id) if song_id is not None else -1,
        'title': title or '',
        'key': key or '',
        'bpm': int(bpm) if bpm else 0,
        'preset': preset or '',
        'updated': int(time.time()),
    })


def plugin_state():
    """Co wtyczka o sobie mówi: jakie presety ma i co jest w niej wczytane.

    Zwraca pusty stan, gdy wtyczka nigdy nie chodziła — wtedy lista presetów w
    edycji piosenki jest po prostu pusta, zamiast wywalić stronę.
    """
    folder = shared_dir()
    empty = {'presets': [], 'current': '', 'library': '', 'seen': False}

    if not folder:
        return empty

    path = os.path.join(folder, 'plugin.json')

    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        return empty

    if not isinstance(data, dict):
        return empty

    presets = [str(p) for p in data.get('presets', []) if str(p).strip()]

    return {
        'presets': presets,
        'current': str(data.get('current', '')),
        'library': str(data.get('library', '')),
        'seen': True,
    }


def _candidate_paths():
    """Gdzie może leżeć wersja standalone wtyczki."""
    names = ['Jafa Worship Piano.exe', 'Jafa Worship Piano']
    roots = [
        os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__)),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'WorshipPiano', 'build',
                     'JafaWorshipPiano_artefacts', 'Release', 'Standalone'),
        os.environ.get('PROGRAMFILES', r'C:\Program Files'),
    ]

    for root in roots:
        if not root:
            continue
        for name in names:
            yield os.path.join(root, name)
            yield os.path.join(root, 'Jafa Worship Piano', name)


def find_plugin():
    """Ścieżka do wersji standalone, albo None. Ustawiona ręcznie ma pierwszeństwo."""
    manual = os.environ.get('JAFA_PIANO_PATH')

    if manual and os.path.isfile(manual):
        return manual

    for path in _candidate_paths():
        if os.path.isfile(path):
            return path

    return None


def launch():
    """Odpala pianino w osobnym oknie.

    Zwraca (ok, komunikat). Osobny proces, nie wątek: to jest oddzielny program
    z własnym oknem i własnym urządzeniem audio, a jeśli się wywali, nie ma
    zabrać ze sobą ekranów nabożeństwa.
    """
    path = find_plugin()

    if not path:
        return False, ('Nie znalazłem pianina. Wskaż plik zmienną '
                       'JAFA_PIANO_PATH albo połóż go obok aplikacji.')

    try:
        # Strumienie w /dev/null i osobna sesja: inaczej pianino zostaje
        # przywiązane do procesu aplikacji przez odziedziczone stdout, a wtedy
        # zamknięcie aplikacji potrafi zabrać ze sobą dźwięk w środku pieśni.
        kwargs = {
            'cwd': os.path.dirname(path),
            'stdin': subprocess.DEVNULL,
            'stdout': subprocess.DEVNULL,
            'stderr': subprocess.DEVNULL,
        }

        if sys.platform == 'win32':
            kwargs['creationflags'] = (getattr(subprocess, 'DETACHED_PROCESS', 0)
                                       | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))
        else:
            kwargs['start_new_session'] = True

        subprocess.Popen([path], **kwargs)
        return True, 'Pianino uruchomione.'
    except OSError as e:
        return False, 'Nie udało się uruchomić pianina: %s' % e
