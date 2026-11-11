"""Small platform differences; Linux keeps its existing system-library setup."""
import os
from pathlib import Path
import sys

MESSAGE_LIMIT = 64 * 1024 * 1024


def config_directory():
    if os.environ.get('FW_EDITOR_CONFIG'):
        return Path(os.environ['FW_EDITOR_CONFIG'])
    if sys.platform == 'win32':
        return Path(os.environ.get('APPDATA') or Path.home()/'AppData'/'Roaming')/'fw-character-editor'
    return Path(os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')/'fw-character-editor'


def decompress_windows(raw):
    # python-zstandard's Windows wheel includes its native implementation.
    # It is included in the executable; source users install it with pip.
    try:
        import zstandard
    except ImportError as exc:
        raise ValueError('Windows source setup requires: py -m pip install zstandard') from exc
    try:
        size = zstandard.frame_content_size(raw)
        if size > MESSAGE_LIMIT:
            raise ValueError('Decompressed message file exceeds 64 MiB.')
        return zstandard.ZstdDecompressor().decompress(raw, max_output_size=MESSAGE_LIMIT)
    except zstandard.ZstdError as exc:
        raise ValueError('Invalid or oversized Zstandard message file: '+str(exc)) from exc
