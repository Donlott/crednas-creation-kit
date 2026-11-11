"""IID layout, live SID/IID links, distinct files and combined nine-file exports."""
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from fw_editor import (Item,ItemP0,ItemP1,Person,Job,Skill,SkillP0,SkillP1,Learning,Binary,DataError,
                       suite_project,load_suite_project,export_suite,read_editable_tables)
from item_index import ItemIndex,iid_tokens
from skill_index import SkillIndex
from fixture import item_fixture,person_fixture,job_fixture,skill_fixture,growth_fixture
from test_skills import verify_preserved


class ItemTests(unittest.TestCase):
    def setUp(self):self.doc=Item(item_fixture())

    def test_signed_values_shared_skill_lists_and_opaque_data(self):
        d=self.doc;r=d.records[0];self.assertEqual(d.build(),d.raw)
        for row in d.records:
            for f in d.fields:d.set(row,f,d.original(row,f))
        self.assertFalse(d.changes)
        edits={0x4c:2**32-1,0x50:0,0x118:-2**31,0x11c:2**31-1,0x6c:-32768,
               0x98:['SID_NEW','SID_新規'],0xb8:'',0x108:'IID_新規|',0x20:'MIID_NEW',0x150:2**32-1}
        for off,value in edits.items():d.set(r,d.by_offset[off],value)
        result=Item(d.build());verify_preserved(self,d,result,dict(d.changes))
        self.assertEqual(result.original(result.records[1],result.by_offset[0x98]),['SID_SYNTHETIC_A','SID_SYNTHETIC_B'])
        result.set(result.records[0],result.by_offset[0x98],[]);again=Item(result.build())
        self.assertEqual(again.original(again.records[0],again.by_offset[0x98]),[])
        for off,bad in ((0x118,-2**31-1),(0x11c,2**31),(0x4c,-1),(0x4c,2**32),(0x6c,32768),(0x48,256)):
            with self.assertRaises(DataError):d.set(r,d.by_offset[off],bad)

    def test_all_nine_source_files_project_rollback_export_and_legacy_replacement(self):
        docs={'Characters':Person(person_fixture()),'Classes':Job(job_fixture()),'Learning tables':Learning(growth_fixture()),
              'Skills':Skill(skill_fixture()),'Skills · Skill_P0.bin':SkillP0(skill_fixture()),'Skills · Skill_P1.bin':SkillP1(skill_fixture()),
              'Items':self.doc,'Items · Item_P0.bin':ItemP0(item_fixture()),'Items · Item_P1.bin':ItemP1(item_fixture())}
        for i,doc in enumerate(docs.values()):
            if isinstance(doc,Item):doc.set(doc.records[0],doc.by_offset[0x118],i)
        project=json.loads(json.dumps(suite_project(docs)));before={k:dict(d.changes) for k,d in docs.items()}
        bad=json.loads(json.dumps(project));bad['documents']['Item_P1.bin']['source_file']='Item.bin'
        with self.assertRaises(DataError):load_suite_project(docs,bad)
        self.assertEqual(before,{k:d.changes for k,d in docs.items()})
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);sources={}
            for key,doc in docs.items():
                p=base/'source'/doc.filename;p.parent.mkdir(exist_ok=True);p.write_bytes(doc.raw);sources[key]=p
            targets=export_suite(docs,sources,base/'mod');self.assertEqual(len(targets),9)
            for key,doc in docs.items():
                self.assertEqual(sources[key].read_bytes(),doc.raw)
                result=type(doc)((base/'mod/romfs/GameData'/doc.filename).read_bytes())
                for (pid,off),value in doc.changes.items():self.assertEqual(result.original(*result.edit_target(pid,off)),value)
            export_suite(docs,sources,base/'mod');self.assertEqual(len(list((base/'mod/romfs/GameData').glob('*.backup-*'))),9)
        for d in docs.values():d.changes={}
        load_suite_project(docs,project);self.assertEqual(before,{k:d.changes for k,d in docs.items()})
        old={'format':'fw-hacking-suite-project-v1','documents':{k:v for k,v in project['documents'].items() if not k.startswith('Item')}}
        load_suite_project(docs,old);self.assertFalse(any(d.changes for d in docs.values()))
        load_suite_project(docs,project['documents']['Item_P0.bin']);self.assertTrue(docs['Items · Item_P0.bin'].changes)
        self.assertFalse(docs['Items'].changes)

    def test_pipe_ids_live_item_refs_glid_and_skill_usage_replacement(self):
        self.assertEqual(iid_tokens('IID_A|, IID_A|| !IID_A||| MIID_A'),(('IID_A|',False),('IID_A||',False),('IID_A|||',True)))
        self.assertNotIn(('IID_A',False),iid_tokens('IID_A|'))
        d=self.doc;growth=Learning(growth_fixture());skill=Skill(skill_fixture());docs={'Items':d,'Learning tables':growth,'Skills':skill}
        sid='SID_SYNTHETIC_A';idx=SkillIndex()
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);(base/'Item.bin').write_bytes(d.raw)
            idx=SkillIndex.load(base,Binary)
            baseline=idx.uses(sid,docs)
            self.assertEqual(sum(u.source=='Item.bin' and '0x98' in u.field for u in baseline),2)
            d.set(d.records[0],d.by_offset[0x98],[]);d.set(d.records[0],d.by_offset[0xb8],'')
            uses=idx.uses(sid,docs)
            self.assertFalse(any(u.record==d.records[0].pid and u.source=='Item.bin' for u in uses))
            self.assertTrue(any(u.module=='Items' and u.source=='Item.bin' for u in uses))
        itemindex=ItemIndex();target='IID_SYNTHETIC_A|';uses=itemindex.uses(target,docs)
        self.assertTrue(any(u.record=='IID_SYNTHETIC_A' and '0x108' in u.field for u in uses))
        p=growth.progression;r=p.rows_by_table['GLID_SYNTHETIC_A'][1]
        p.set(r,p.by_offset[0x20],4);p.set(r,p.by_offset[0x2a0],'SYNTHETIC_A|')
        uses=itemindex.uses(target,docs)
        self.assertTrue(any(u.module=='GLID progression' and u.row==1 and u.level==80 for u in uses))
        p.set(r,p.by_offset[0x20],0)
        self.assertFalse(any(u.module=='GLID progression' for u in itemindex.uses(target,docs)))


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent'))
@unittest.skipUnless((DATA/'Item.bin').is_file(),'Set FW_GAME_DATA for real item regression.')
class RealItemTests(unittest.TestCase):
    def test_all_111040_fields_pointers_auxiliary_groups_and_reopen(self):
        for kind,count in ((Item,1356),(ItemP0,16),(ItemP1,16)):
            with self.subTest(file=kind.filename):
                d=kind((DATA/kind.filename).read_bytes());self.assertEqual((len(d.records),len(d.fields)),(count,80))
                self.assertEqual(d.build(),d.raw)
                for row in d.records:
                    for f in d.fields:d.set(row,f,d.original(row,f))
                self.assertFalse(d.changes)
                r=d.records[1]
                for off,v in ((0x4c,2**32-1),(0x118,-2**31),(0x11c,2**31-1),(0x140,-1),(0x6c,-300),
                              (0x98,['SID_TEST','SID_新規']),(0x108,'IID_TEST|'),(0x120,''),(0x38,['new text']),
                              (0x180,['raw classification']),(0x150,2**32-1)):
                    d.set(r,d.by_offset[off],v)
                result=kind(d.build());verify_preserved(self,d,result,dict(d.changes))
                result.set(result.records[1],result.by_offset[0x98],[])
                again=kind(result.build());self.assertEqual(again.original(again.records[1],again.by_offset[0x98]),[])

    def test_shop_lottery_collection_links_and_live_skill_item_glid_coverage(self):
        index=ItemIndex.load(DATA,Binary);docs,_=read_editable_tables(DATA)
        self.assertEqual(len(index.collections),250);self.assertEqual(sum(n for _,_,_,n in index.collections),1937)
        self.assertEqual(len(index.static_uses),585)
        self.assertEqual([p for p,_ in index.errors],['Gmap/Data.bin'])
        self.assertTrue(any(u.module=='Shop & Loot' for u in index.uses('IID_木製の剣',docs)))
        uses=index.uses('IID_傷薬',docs)
        self.assertTrue(any(u.module=='GLID progression' for u in uses))
        self.assertTrue(any(u.module=='Characters' for u in uses))
        self.assertIn('IID_試作品１号|||',docs['Items · Item_P1.bin'].by_pid)
