import json
from pathlib import Path
import tempfile
import unittest

from fw_editor import Person, DataError, export_mod
from tests.fixture import person_fixture


class FormatTests(unittest.TestCase):
    def setUp(self):
        self.raw=person_fixture()
        self.doc=Person(self.raw)
        self.a,self.b=self.doc.records

    def set(self,offset,value):
        self.doc.set(self.a,self.doc.by_offset[offset],value)

    def test_no_changes_are_byte_identical(self):
        self.assertEqual(len(self.doc.records),2)
        self.assertEqual(self.doc.build(),self.raw)

    def test_scalar_ranges_and_fixed_identity(self):
        self.set(0x1c2,-20)
        after=Person(self.doc.build())
        self.assertEqual(after.original(after.records[0],after.by_offset[0x1c2]),-20)
        for offset,value in [(0x30,99),(0x1c2,32768),(0x1c2,-32769)]:
            with self.assertRaises(DataError): self.set(offset,value)

    def test_shared_array_is_not_changed_for_other_character(self):
        before=self.doc.original(self.b,self.doc.by_offset[0x78])
        self.set(0x78,['IID_NEW','IID_UNICODE_★'])
        after=Person(self.doc.build())
        self.assertEqual(after.original(after.records[0],after.by_offset[0x78]),['IID_NEW','IID_UNICODE_★'])
        self.assertEqual(after.original(after.records[1],after.by_offset[0x78]),before)

    def test_new_strings_empty_lists_and_null_reference(self):
        self.set(0x278,'AID_NEW_★');self.set(0x268,self.b.pid)
        self.set(0x78,[]);self.set(0x1a8,['Flag1','Flag2'])
        after=Person(self.doc.build())
        for offset,value in [(0x278,'AID_NEW_★'),(0x268,self.b.pid),(0x78,[]),(0x1a8,['Flag1','Flag2'])]:
            self.assertEqual(after.original(after.records[0],after.by_offset[offset]),value)
        after.set(after.records[0],after.by_offset[0x268],'')
        again=Person(after.build())
        self.assertEqual(again.original(again.records[0],again.by_offset[0x268]),'')

    def test_projects_are_transactional(self):
        self.set(0x1c2,44)
        project=json.loads(json.dumps(self.doc.project()))
        restored=Person(self.raw);restored.load_project(project)
        self.assertEqual(restored.build(),self.doc.build())
        project['changes'].append({'pid':self.a.pid,'offset':0x30,'value':44})
        before=dict(restored.changes)
        with self.assertRaises(DataError): restored.load_project(project)
        self.assertEqual(restored.changes,before)

    def test_export_does_not_overwrite_source_or_unrelated_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            source=root/'game/romfs/GameData/Person.bin';source.parent.mkdir(parents=True);source.write_bytes(self.raw)
            with self.assertRaises(DataError): export_mod(self.doc,source,root/'game')
            unrelated=root/'other/romfs/GameData/Person.bin';unrelated.parent.mkdir(parents=True);unrelated.write_bytes(self.raw)
            with self.assertRaises(DataError): export_mod(self.doc,source,root/'other')
            self.set(0x1c2,44)
            target=export_mod(self.doc,source,root/'mod')
            export_mod(self.doc,source,root/'mod')
            self.assertEqual(len(list(target.parent.glob('*.backup-*'))),1)
            self.assertEqual(source.read_bytes(),self.raw)


if __name__=='__main__': unittest.main()
