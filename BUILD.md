# JafaStageCenter — Build Instructions

## Requirements

- Python 3.10+ (tested on 3.11/3.12)
- pip

## Development Setup

```bash
# Clone the repository
git clone https://github.com/ukiii08/jafastagecenter.git
cd jafastagecenter

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running in Development

```bash
python app.py
```

The app opens a native window (pywebview) with a splash screen.
The Flask server starts on `http://127.0.0.1:5000`.

Available endpoints:
- `/control` — Control panel
- `/stage` — Band/stage monitor view
- `/projector` — Projector/audience view
- `/print/<song_id>` — Print view for a song

## Building a Standalone .exe (Windows)

### 1. Install PyInstaller

```bash
pip install pyinstaller
```

### 2. Build

```bash
pyinstaller --noconfirm --onedir --windowed ^
    --name "JafaStageCenter" ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --hidden-import "engineio.async_drivers.threading" ^
    --hidden-import "socketio" ^
    --hidden-import "flask_socketio" ^
    --hidden-import "sqlalchemy.dialects.sqlite" ^
    app.py
```

On Linux/Mac use `:` instead of `;` as the path separator:

```bash
pyinstaller --noconfirm --onedir --windowed \
    --name "JafaStageCenter" \
    --add-data "templates:templates" \
    --add-data "static:static" \
    --hidden-import "engineio.async_drivers.threading" \
    --hidden-import "socketio" \
    --hidden-import "flask_socketio" \
    --hidden-import "sqlalchemy.dialects.sqlite" \
    app.py
```

### 3. Output

The built app will be in `dist/JafaStageCenter/`.

The database file `worship.db` is created next to the executable on first run.

### 4. Optional: Single-file build

Replace `--onedir` with `--onefile` for a single `.exe`. Startup will be slower because files are extracted to a temp directory each launch.

## Notes

- The app uses `sys._MEIPASS` (PyInstaller) to locate templates and static files when frozen.
- The database (`worship.db`) is always stored next to the executable, not inside the bundle.
- Font files (`static/fonts/Sen-*.ttf`) are bundled via the `--add-data` flag.
- If QR codes fail with Pillow errors, the app falls back to SVG-based QR rendering automatically.
