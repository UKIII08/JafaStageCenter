import PyInstaller.__main__
import os
import shutil

# KONFIGURACJA
MAIN_SCRIPT = 'app.py'
APP_NAME = 'JafaStageCenter'
# ZMIANA: Ikona jest teraz w głównym folderze, nie w static
ICON_PATH = 'app.ico' 

def build():
    print("--- BUDOWANIE APLIKACJI (Ikona w głównym folderze) ---")

    # HTTPS (mikrofon/stroik na telefonie) wymaga pakietu cryptography W .exe.
    # Bez niego .exe cicho spada na HTTP i stroik na telefonie nie działa —
    # dlatego przerywamy budowanie od razu, z jasnym komunikatem.
    try:
        from cryptography import x509  # noqa: F401
    except Exception:
        print("\nBLAD: Brak pakietu 'cryptography' w tym srodowisku Pythona.")
        print("Bez niego .exe nie wygeneruje certyfikatu HTTPS i stroik na telefonie NIE zadziala.")
        print("Zainstaluj go i zbuduj ponownie:")
        print("    pip install cryptography")
        raise SystemExit(1)

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