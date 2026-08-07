import PyInstaller.__main__
import importlib.util
import os
import shutil
import sys

# KONFIGURACJA
MAIN_SCRIPT = 'app.py'
APP_NAME = 'JafaStageCenter'
# ZMIANA: Ikona jest teraz w głównym folderze, nie w static
ICON_PATH = 'app.ico'

# Wszystko, co app.py importuje na sztywno, i pakiet, z którego to pochodzi.
# PyInstaller pakuje TYLKO to, co potrafi zaimportować w Pythonie, którym go
# uruchomiono. Jeśli pakietu tam nie ma, PyInstaller wypisuje ostrzeżenie w
# zalewie innych logów i mimo to buduje .exe — który wywala się dopiero u
# użytkownika, komunikatem "No module named ...". Dlatego sprawdzamy to tutaj
# i przerywamy, zamiast wypuścić popsuty plik.
#
# Najczęstsza przyczyna: zależności są w venv, a build.py poszedł systemowym
# Pythonem (albo odwrotnie). Stąd wypisanie ścieżki interpretera niżej.
REQUIRED = {
    'cryptography': 'cryptography',
    'fitz': 'PyMuPDF',
    'flask': 'Flask',
    'flask_socketio': 'Flask-SocketIO',
    'flask_sqlalchemy': 'Flask-SQLAlchemy',
    'qrcode': 'qrcode',
    'sqlalchemy': 'SQLAlchemy',
    'webview': 'pywebview',
    'werkzeug': 'Werkzeug',
}


def check_dependencies():
    missing = [(mod, pkg) for mod, pkg in sorted(REQUIRED.items())
               if importlib.util.find_spec(mod) is None]

    if not missing:
        return

    print("\nBLAD: w tym srodowisku Pythona brakuje pakietow, ktorych app.py potrzebuje.")
    print("Zbudowany .exe wywalilby sie przy starcie na 'No module named ...'.\n")
    print("Python uzyty do budowania:")
    print("    " + sys.executable + "\n")
    print("Brakuje:")

    for mod, pkg in missing:
        print("    %-18s -> pip install %s" % (mod, pkg))

    print("\nNajczestsza przyczyna: zaleznosci siedza w venv, a build.py poszedl")
    print("innym Pythonem. Aktywuj to samo srodowisko i zbuduj ponownie:")
    print("    venv\\Scripts\\activate")
    print("    pip install -r requirements.txt")
    print("    python build.py")
    raise SystemExit(1)


def build():
    print("--- BUDOWANIE APLIKACJI (Ikona w głównym folderze) ---")
    print("Python: " + sys.executable)

    # Sprawdzenie zaleznosci PRZED budowaniem: bez tego brakujacy pakiet
    # wychodzi dopiero na maszynie uzytkownika.
    check_dependencies()

    # Czyszczenie starych folderów
    if os.path.exists('dist'): shutil.rmtree('dist')
    if os.path.exists('build'): shutil.rmtree('build')

    # Separator dla Windows (;)
    sep = ';' if os.name == 'nt' else ':'

    params = [
        MAIN_SCRIPT,
        f'--name={APP_NAME}',
        '--onefile',
        '--noconsole',
        '--clean',
        
        # Zasoby
        f'--add-data=templates{sep}templates',
        f'--add-data=static{sep}static',
        
        # Ukryte importy
        '--hidden-import=engineio.async_drivers.threading',
        '--hidden-import=socketio',
        '--hidden-import=flask_socketio',
        '--hidden-import=sqlalchemy.sql.default_comparator',
        # cryptography (certyfikat HTTPS): _cffi_backend to natywny moduł,
        # którego PyInstaller często nie wykrywa sam — bez niego cryptography
        # pada w .exe i telefon nie dostaje HTTPS (mikrofon nie działa).
        '--hidden-import=_cffi_backend',
        '--collect-submodules=cryptography',
        # Kody QR na widoku zespołu: SvgPathImage jest importowany dopiero
        # wewnątrz funkcji, w gałęzi except, więc analiza PyInstallera potrafi go
        # przegapić. Wtedy .exe ma qrcode, ale QR w wersji SVG się nie renderuje.
        '--collect-submodules=qrcode',
    ]

    # Dodanie ikony (jeśli istnieje w głównym folderze)
    if os.path.exists(ICON_PATH):
        params.append(f'--icon={ICON_PATH}')
        print(f"Znaleziono ikonę: {ICON_PATH}")
    else:
        print(f"UWAGA: Nie znaleziono pliku {ICON_PATH} w folderze głównym!")

    PyInstaller.__main__.run(params)
    print(f"\nGOTOWE! Plik jest w folderze: dist/{APP_NAME}.exe")

if __name__ == '__main__':
    build()