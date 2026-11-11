import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import fw_editor as fw
from platform_support import MESSAGE_LIMIT, config_directory, decompress_windows


class PlatformTests(unittest.TestCase):
    def test_config_override_and_existing_linux_paths(self):
        with patch.dict(os.environ, {'FW_EDITOR_CONFIG':'custom-settings'}, clear=True):
            self.assertEqual(config_directory(), Path('custom-settings'))
        with patch('platform_support.sys.platform', 'linux'), patch.dict(os.environ, {'XDG_CONFIG_HOME':'xdg-settings'}, clear=True):
            self.assertEqual(config_directory(), Path('xdg-settings/fw-character-editor'))
        with patch('platform_support.sys.platform', 'linux'), patch.dict(os.environ, {}, clear=True), patch('platform_support.Path.home', return_value=Path('test-home')):
            self.assertEqual(config_directory(), Path.home()/'.config/fw-character-editor')

    def test_windows_uses_roaming_settings(self):
        with patch('platform_support.sys.platform', 'win32'), patch.dict(os.environ, {'APPDATA':'roaming-settings'}, clear=True):
            self.assertEqual(config_directory(), Path('roaming-settings/fw-character-editor'))
        with patch('platform_support.sys.platform', 'win32'), patch.dict(os.environ, {}, clear=True), patch('platform_support.Path.home', return_value=Path('test-home')):
            self.assertEqual(config_directory(), Path.home()/'AppData/Roaming/fw-character-editor')

    def test_windows_backend_limit_and_errors(self):
        class ZstdError(Exception):pass
        calls=[]
        backend=types.SimpleNamespace(ZstdError=ZstdError, frame_content_size=lambda raw:4,
            ZstdDecompressor=lambda:types.SimpleNamespace(decompress=lambda raw,**kw:calls.append((raw,kw)) or b'text'))
        with patch.dict(sys.modules, {'zstandard':backend}):
            self.assertEqual(decompress_windows(b'frame'), b'text')
            self.assertEqual(calls, [(b'frame', {'max_output_size':MESSAGE_LIMIT})])
            backend.frame_content_size=lambda raw:MESSAGE_LIMIT+1
            with self.assertRaisesRegex(ValueError, 'exceeds'):decompress_windows(b'frame')
            self.assertEqual(len(calls), 1)
            backend.frame_content_size=lambda raw:-1
            self.assertEqual(decompress_windows(b'unknown-size'), b'text')
            def invalid(raw):raise ZstdError('bad frame')
            backend.frame_content_size=invalid
            with self.assertRaisesRegex(ValueError, 'Invalid'):decompress_windows(b'invalid')

    def test_main_uses_windows_backend_and_preserves_raw_messages(self):
        with patch('fw_editor.sys.platform', 'win32'), patch('platform_support.decompress_windows',return_value=b'loaded') as backend:
            self.assertEqual(fw.decompress(b'MsgStdBnraw'), b'MsgStdBnraw')
            backend.assert_not_called()
            self.assertEqual(fw.decompress(b'compressed'), b'loaded')
            backend.side_effect=ValueError('bad data')
            with self.assertRaises(fw.DataError):fw.decompress(b'bad')
