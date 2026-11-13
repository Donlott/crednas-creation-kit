"""Format regression tests against the user's supplied 1.00 tables. No game writes."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import os

from fw_editor import Person, Binary, DataError, messages, export_mod, ARRAY_TYPES

DATA = Path(os.environ.get('FW_GAME_DATA', '/nonexistent/fw-game-data'))
ENGLISH = Path(os.environ.get('FW_MESSAGES', '/nonexistent/fw-messages'))
DIETRICH = 'PID_ディートリヒ'
MAJIDE = 'PID_マジーデ'


@unittest.skipUnless((DATA/'Person.bin').is_file() and (ENGLISH/'Person.msbt.zst').is_file(),
                     'Set FW_GAME_DATA and FW_MESSAGES to run the optional real-data tests.')
class EditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (DATA/'Person.bin').read_bytes()
        cls.reference = Person(cls.raw)
        cls.values = {(r.pid, f.offset): cls.reference.original(r, f)
                      for r in cls.reference.records for f in cls.reference.fields}

    def setUp(self):
        self.doc = Person(self.raw)

    def edit(self, pid, offset, value):
        self.doc.set(self.doc.by_pid[pid], self.doc.by_offset[offset], value)

    def verify_all(self, raw):
        actual = Person(raw)
        self.assertEqual([r.pid for r in actual.records], [r.pid for r in self.reference.records])
        for r in actual.records:
            for f in actual.fields:
                expected = self.doc.changes.get((r.pid, f.offset), self.values[(r.pid, f.offset)])
                self.assertEqual(actual.original(r, f), expected, (r.pid, f.offset))
        return actual

    def test_unchanged_exact_roundtrip(self):
        self.assertEqual(len(self.doc.records), 2923)
        self.assertEqual(len(self.doc.fields), 143)
        self.assertEqual(self.doc.build(), self.raw)

    def test_numeric_edit_changes_only_value_bytes(self):
        self.edit(DIETRICH, 0x1c2, 50)
        result = self.doc.build()
        at = self.doc.by_pid[DIETRICH].offset + 0x1c2
        expected = bytearray(self.raw)
        struct.pack_into('<h', expected, at, 50)
        self.assertEqual(result, bytes(expected))

    def test_strings_refs_nulls_and_copy_on_write(self):
        diet = self.doc.by_pid[DIETRICH]
        maj = self.doc.by_pid[MAJIDE]
        self.assertEqual(self.doc.original(diet, self.doc.by_offset[0x48]),
                         self.doc.original(maj, self.doc.by_offset[0x48]))
        self.edit(DIETRICH, 0x48, ['JID_闘士', 'JID_猟兵', 'JID_新規参照テスト'])
        self.edit(DIETRICH, 0x20, 'MPID_Majiide')
        self.edit(MAJIDE, 0x20, 'MPID_Ditlih')
        self.edit(DIETRICH, 0x278, 'AID_マジーデ')
        self.edit(MAJIDE, 0x278, 'AID_ディートリヒ')
        self.edit(DIETRICH, 0x268, MAJIDE)  # null -> non-null data ref
        self.edit(DIETRICH, 0x108, '')  # non-null -> null
        self.edit(DIETRICH, 0x1a8, ['new Unicode condition ★', 'second condition'])
        self.edit(MAJIDE, 0x98, [])
        actual = self.verify_all(self.doc.build())
        self.assertEqual(actual.original(actual.by_pid[MAJIDE], actual.by_offset[0x48]),
                         self.reference.original(maj, self.reference.by_offset[0x48]))
        self.assertEqual(self.doc.raw, self.raw)

    def test_reopen_edit_export_again(self):
        self.edit(DIETRICH, 0x268, MAJIDE)
        self.edit(DIETRICH, 0x78, ['IID_new_item'])
        first = Person(self.doc.build())
        first.set(first.by_pid[DIETRICH], first.by_offset[0x268], '')
        first.set(first.by_pid[DIETRICH], first.by_offset[0x78], [])
        first.set(first.by_pid[MAJIDE], first.by_offset[0x28], 'NewIdentifier')
        reopened = Person(first.build())
        self.assertEqual(reopened.original(reopened.by_pid[DIETRICH], reopened.by_offset[0x78]), [])
        self.assertEqual(reopened.original(reopened.by_pid[MAJIDE], reopened.by_offset[0x28]), 'NewIdentifier')

    def test_ranges_identity_and_projects(self):
        for offset, value in [(0x30, 59), (0x1c2, 32768), (0x1c2, -32769),
                              (0x1b9, 256), (0x20, 'bad\0name'), (0x78, [''])]:
            with self.assertRaises(DataError): self.edit(DIETRICH, offset, value)
        self.edit(DIETRICH, 0x1c2, 42)
        project = json.loads(json.dumps(self.doc.project()))
        restored = Person(self.raw); restored.load_project(project)
        self.assertEqual(restored.build(), self.doc.build())
        previous = dict(restored.changes)
        bad = copy.deepcopy(project)
        bad['changes'].append({'pid': DIETRICH, 'offset': 0x30, 'value': 59})
        with self.assertRaises(DataError): restored.load_project(bad)
        self.assertEqual(restored.changes, previous)
        bad = copy.deepcopy(project); bad['source_sha256'] = 'different'
        with self.assertRaises(DataError): restored.load_project(bad)

    def test_english_names_and_related_tables(self):
        names = messages((ENGLISH/'Person.msbt.zst').read_bytes())
        self.assertEqual(len(names), 589)
        self.assertEqual(names['MPID_Ditlih'], 'Dietrich')
        self.assertEqual(names['MPID_Majiide'], 'Majide')
        self.assertEqual(names['MPID_Kiroica'], 'Kiroc')
        for name in ('Job', 'Skill', 'Item'):
            self.assertTrue(messages((ENGLISH/(name+'.msbt.zst')).read_bytes()))
        for name in ('Job', 'Skill', 'Item', 'Growth', 'Profile'):
            self.assertTrue(Binary((DATA/(name+'.bin')).read_bytes()).labels)

    def test_export_source_protection_without_backups(self):
        self.edit(DIETRICH, 0x1c2, 42)
        digest = hashlib.sha256((DATA/'Person.bin').read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory)/'source'
            source_file = source_root/'romfs/GameData/Person.bin'
            source_file.parent.mkdir(parents=True)
            source_file.write_bytes(self.raw)
            with self.assertRaises(DataError): export_mod(self.doc, source_file, source_root)
            directory = Path(directory)/'mod'
            target = export_mod(self.doc, DATA/'Person.bin', directory)
            original_export = target.read_bytes()
            self.edit(DIETRICH, 0x1c2, 43)
            export_mod(self.doc, DATA/'Person.bin', directory)
            backups = list(target.parent.glob('Person.bin.backup-*'))
            self.assertEqual(backups, [])
            self.assertNotEqual(target.read_bytes(), original_export)
            self.assertTrue((Path(directory)/'character-edits.json').is_file())
        self.assertEqual(hashlib.sha256((DATA/'Person.bin').read_bytes()).hexdigest(), digest)

    def test_malformed_header_rejected(self):
        for raw in (b'', self.raw[:200], b'\0' * 32):
            with self.assertRaises(DataError): Person(raw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
