"""Persistence and malformed-preference handling for last-used project paths."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fw_editor import RecentPaths


class RecentPathTests(unittest.TestCase):
    def test_persistence_keeps_project_context_separate_from_last_browsed_data(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);file=base/'recent.json';settings=RecentPaths(file)
            context={'path':str(base/'project.json'),'data':str(base/'game_a'),'names':str(base/'USen'),'module':'Classes'}
            settings.update(last_data=str(base/'game_a'),last_names=str(base/'USen'),last_project=context)
            settings.update(last_data=str(base/'game_b'),last_export=str(base/'mod'))
            restored=RecentPaths(file)
            self.assertEqual(restored.values['last_project'],context)
            self.assertEqual(restored.values['last_data'],str(base/'game_b'))
            self.assertEqual(restored.initial_dir('last_project'),str(base))
            with patch('fw_editor.atomic_write',side_effect=OSError('read-only settings')):
                with self.assertRaises(OSError):restored.update(last_data='must not persist')
            self.assertEqual(RecentPaths(file).values,restored.values)

    def test_missing_corrupt_and_wrong_type_preferences_do_not_block_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'recent.json'
            self.assertEqual(RecentPaths(file).values,{})
            for raw in ('invalid JSON','[]','{"last_data":42,"last_project":{"path":[],"data":"x"}}'):
                file.write_text(raw);self.assertEqual(RecentPaths(file).values,{})
