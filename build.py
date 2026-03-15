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