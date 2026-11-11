#!/usr/bin/env bash
set -euo pipefail
editor_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
/usr/bin/python3 - "$editor_dir" <<'PY'
from pathlib import Path
import subprocess
import sys

try:
    import tkinter
except ImportError:
    raise SystemExit('Install Tk first: sudo apt install python3-tk')

source = Path(sys.argv[1]) / 'fw_editor.py'
if not source.is_file():
    raise SystemExit('fw_editor.py is missing.')
desktop = Path.home() / 'Desktop'
try:
    result = subprocess.run(['xdg-user-dir', 'DESKTOP'], capture_output=True, text=True, check=True)
    if result.stdout.strip():
        desktop = Path(result.stdout.strip())
except (OSError, subprocess.CalledProcessError):
    pass
applications = Path.home() / '.local/share/applications'
applications.mkdir(parents=True, exist_ok=True)
desktop.mkdir(parents=True, exist_ok=True)
quoted = str(source).replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$').replace('`', '\\`').replace('%', '%%')
entry = f'''[Desktop Entry]
Type=Application
Name=Credna's Creation Kit
Comment=Edit Fortune's Weave 1.00 characters, classes, skills, items, supports, recruitment, progression, appearance rules, profiles, affiliations, facilities, rewards, shops and loot
Exec=/usr/bin/python3 "{quoted}"
Icon=applications-games
Terminal=false
Categories=Game;Utility;
'''
for folder in (applications, desktop):
    path = folder / 'fw-character-editor.desktop'
    path.write_text(entry)
    path.chmod(0o755)
try:
    subprocess.run(['gio', 'set', str(desktop / 'fw-character-editor.desktop'),
                    'metadata::trusted', 'true'], capture_output=True)
except OSError:
    pass
print("Created desktop and applications-menu shortcuts for Credna's Creation Kit.")
print('Keep this repository folder in place; the shortcuts launch its fw_editor.py.')
PY
