"""Folder discovery and transactional dependency loading, with synthetic data."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from fw_editor import DataError,Item,Job,Skill
from fixture import item_fixture,job_fixture,skill_fixture
from mount_data import load_sources,source_tables


class MountSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.raw={'Item.bin':item_fixture(),'Job.bin':job_fixture(),'Skill.bin':skill_fixture()}

    def write(self,directory):
        directory.mkdir(parents=True,exist_ok=True)
        for name,raw in self.raw.items():(directory/name).write_bytes(raw)

    def test_game_folder_gamedata_folder_and_selected_file(self):
        for layout in ('','GameData','romfs/GameData'):
            with self.subTest(layout=layout):
                root=self.root/('case'+str(len(layout)));directory=root/layout;self.write(directory)
                for selected in (root,directory,directory/'Item.bin'):
                    docs={};sources={};self.assertEqual(load_sources(docs,sources,selected),3)
                    item,job,skill=source_tables(docs);self.assertIsInstance(item,Item);self.assertIsInstance(job,Job);self.assertIsInstance(skill,Skill)
                    self.assertEqual({p.parent for p in sources.values()},{directory.resolve()})
                    self.assertEqual(load_sources(docs,sources,selected),0)

    def test_keeps_loaded_tables_and_unsaved_edits(self):
        self.write(self.root);item=Item(self.raw['Item.bin']);item.set(item.records[0],item.by_offset[0x4c],1234)
        before=item.snapshot_edits();docs={'Items':item};sources={'Items':self.root/'Item.bin'}
        self.assertEqual(load_sources(docs,sources,self.root),2)
        self.assertIs(docs['Items'],item);self.assertEqual(item.snapshot_edits(),before)
        self.assertEqual((self.root/'Item.bin').read_bytes(),self.raw['Item.bin'])

    def test_missing_or_invalid_files_do_not_partially_load(self):
        self.write(self.root);(self.root/'Skill.bin').unlink();docs={};sources={}
        with self.assertRaisesRegex(DataError,'Skill.bin'):load_sources(docs,sources,self.root)
        self.assertEqual((docs,sources),({},{}))
        self.write(self.root);(self.root/'Job.bin').write_bytes(b'invalid')
        with self.assertRaisesRegex(DataError,'Job.bin'):load_sources(docs,sources,self.root)
        self.assertEqual((docs,sources),({},{}))

    def test_existing_complete_session_does_not_need_source_files(self):
        docs={'Items':Item(self.raw['Item.bin']),'Classes':Job(self.raw['Job.bin']),'Skills':Skill(self.raw['Skill.bin'])}
        self.assertEqual(load_sources(docs,{},None),0)

    def test_clear_missing_folder_and_loaded_layout_errors(self):
        with self.assertRaisesRegex(DataError,'Open data'):load_sources({}, {},None)
        with self.assertRaisesRegex(DataError,'unsupported'):load_sources({'Items':SimpleNamespace(filename='Item.bin')},{},self.root)


if __name__=='__main__':unittest.main()
