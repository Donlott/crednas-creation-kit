"""Legion definitions have their own LID namespace and one guarded source owner."""
import copy
import os
from pathlib import Path
import struct
import tempfile
import unittest
from fw_editor import Legion,Deployment,Learning,DataError,Binary,suite_project,load_suite_project,export_suite,read_editable_tables,messages
from fixture import legion_fixture,deployment_fixture,learning_fixture
from asset_index import AssetIndex
from item_index import ItemIndex
from skill_index import SkillIndex
from legion_ui import uses
from test_skills import verify_preserved as compare


def snapshot(doc):return {(r.pid,f.offset):doc.original(r,f) for r in doc.records for f in doc.fields}


class LegionTests(unittest.TestCase):
    def setUp(self):self.doc=Legion(legion_fixture());self.row=self.doc.records[1]
    def test_unchanged_source_and_numeric_encoding_bounds(self):
        d=self.doc;r=self.row;self.assertEqual(d.build(),d.raw);expected=bytearray(d.raw)
        for off,fmt,value in [(0x31,'B',255),(0x34,'H',65535),(0x70,'h',-32768),(0x84,'h',32767),(0x98,'H',12345)]:
            d.set(r,d.by_offset[off],value);struct.pack_into('<'+fmt,expected,r.offset+off,value)
        self.assertEqual(d.build(),bytes(expected))
        for off,value in [(0x31,256),(0x34,-1),(0x70,-32769),(0x84,32768)]:
            with self.assertRaises(DataError):d.set(r,d.by_offset[off],value)

    def test_all_reference_kinds_shared_lists_unicode_and_reedit(self):
        d=self.doc;r=self.row;before=snapshot(d)
        for off,value in [(0x20,'MLID_NEW'),(0x28,'MLID_H_新しい'),(0x38,'SID_NEW'),(0x48,['IID_NEW|||','IID_SECOND']),
                          (0x58,['SID_OTHER','SID_NEXT']),(0x68,'NEW_AMBIENT'),(0x88,['new_flag','!blocked']),
                          (0xa0,['AID_NEW','!AID_NEGATIVE']),(0xb0,'VID_NEW')]:d.set(r,d.by_offset[off],value)
        result=Legion(d.build());self.assertEqual(snapshot(result),{**before,**d.changes});compare(self,d,result,dict(d.changes))
        result.set(result.records[1],result.by_offset[0x48],[]);again=Legion(result.build())
        self.assertEqual(again.value(again.records[1],again.by_offset[0x48]),[])
        self.assertEqual(again.labels,d.labels)

    def test_guarded_project_rollback_and_old_suite_replacement(self):
        d=self.doc;d.set(self.row,d.by_offset[0x98],777);project=d.project()
        self.assertEqual(project['format'],'fw-legion-edits-v1');self.assertEqual(project['source_file'],'Legion.bin')
        for patch in [{'source_file':'Growth.bin'},{'source_sha256':'wrong'},
                      {'changes':project['changes']+[{'pid':self.row.pid,'offset':0x31,'value':256}]}]:
            bad=copy.deepcopy(project);bad.update(patch);before=dict(d.changes)
            with self.assertRaises(DataError):d.load_project(bad)
            self.assertEqual(d.changes,before)
        growth=Learning(learning_fixture());docs={'Legion':d,'Learning tables':growth}
        load_suite_project(docs,project);self.assertTrue(d.changes)
        legacy={'format':'fw-hacking-suite-project-v1','documents':{'Growth.bin':growth.project()}}
        load_suite_project(docs,legacy);self.assertEqual(d.changes,{})

    def test_item_skill_and_aid_links_are_current(self):
        d=self.doc;r=self.row;docs={'Legion':d}
        self.assertEqual(ItemIndex().uses('IID_SYNTHETIC_A|',docs)[0].module,'Legion')
        self.assertEqual(SkillIndex().uses('SID_SYNTHETIC',docs)[0].record,r.pid)
        index=AssetIndex();index.refresh_users(docs);self.assertEqual(index.direct_count('AID_ALPHA'),1)
        self.assertEqual(index.users['AID_BETA'][0].relationship,'Negated flag')
        d.set(r,d.by_offset[0x48],['IID_NEW|||']);d.set(r,d.by_offset[0x38],'SID_NEW');d.set(r,d.by_offset[0xa0],['AID_NEW'])
        self.assertFalse(ItemIndex().uses('IID_SYNTHETIC_A|',docs));self.assertFalse(SkillIndex().uses('SID_SYNTHETIC',docs))
        index.refresh_users(docs);self.assertEqual(index.direct_count('AID_ALPHA'),0);self.assertEqual(index.direct_count('AID_NEW'),1)
        d.set(r,d.by_offset[0xa0],['AID_NEW','AID_NEW','!AID_NEW']);index.refresh_users(docs)
        self.assertEqual(index.direct_count('AID_NEW'),1);self.assertEqual(len(index.users['AID_NEW']),2)

    def test_deployment_lid_lookups_do_not_match_learning_references(self):
        d=self.doc;deployment=Deployment(deployment_fixture(),'Dispos/SYNTHETIC.bin');v=deployment.views['units'];row=v.records[0]
        v.set(row,v.by_offset[0x40],'LID_無し');growth=Learning(learning_fixture())
        docs={'Learning tables':growth,'Legion':d,'deployed':deployment}
        found=uses('LID_無し',docs);self.assertEqual([(s,p) for s,p,_,_ in found],[(deployment.filename,row.pid)])
        v.set(row,v.by_offset[0x40],'LID_SYNTHETIC');self.assertFalse(uses('LID_無し',docs));self.assertEqual(len(uses('LID_SYNTHETIC',docs)),1)

    def test_export_guards_original_headers_and_standalone_loading(self):
        d=self.doc;d.set(self.row,d.by_offset[0x70],-7)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'romfs/GameData/Legion.bin';source.parent.mkdir(parents=True);source.write_bytes(d.raw)
            docs={'Legion':d};sources={'Legion':source}
            with self.assertRaises(DataError):export_suite(docs,sources,root)
            target=root/'mod';export_suite(docs,sources,target)
            result=Legion((target/'romfs/GameData/Legion.bin').read_bytes());compare(self,d,result,dict(d.changes))
            export_suite(docs,sources,target);self.assertEqual(len(list((target/'romfs/GameData').glob('Legion.bin.backup-*'))),1)
            loaded,_=read_editable_tables(root/'romfs/GameData');self.assertEqual(set(loaded),{'Legion'})
            self.assertEqual(source.read_bytes(),d.raw)

    def test_schema_guard(self):
        raw=bytearray(self.doc.raw);schema=list(Binary(raw).groups())[0][3]
        struct.pack_into('<I',raw,schema+28,0x24)
        with self.assertRaises(DataError):Legion(bytes(raw))


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent/fw-data'))
ENGLISH=Path(os.environ.get('FW_MESSAGES','/nonexistent/fw-names'))
@unittest.skipUnless((DATA/'Legion.bin').is_file(),'Set FW_GAME_DATA for private Legion regressions.')
class RealLegionTests(unittest.TestCase):
    def test_all_3052_fields_after_joint_edits_and_native_bytes(self):
        d=Legion((DATA/'Legion.bin').read_bytes());self.assertEqual(len(d.records),109);self.assertEqual(len(d.fields),28)
        self.assertEqual(d.build(),d.raw);expected=snapshot(d)
        for r in d.records[1:]:
            for off,value in [(0x31,255),(0x70,-32768),(0x98,65535),(0x38,'SID_SYNTHETIC'),(0x48,['IID_SYNTHETIC|||']),
                              (0x58,[]),(0x88,['SYNTHETIC']), (0xa0,['AID_SYNTHETIC'])]:d.set(r,d.by_offset[off],value)
        result=Legion(d.build());self.assertEqual(snapshot(result),{**expected,**d.changes});compare(self,d,result,dict(d.changes))
        self.assertEqual(len(snapshot(result)),3052)
    def test_english_and_real_deployment_links(self):
        docs,_=read_editable_tables(DATA);lid='LID_ダグザ戦士隊';found=uses(lid,docs);self.assertEqual(len(found),62)
        if (ENGLISH/'Legion.msbt.zst').is_file():
            names=messages((ENGLISH/'Legion.msbt.zst').read_bytes());self.assertEqual(names['MLID_DagdaWarriors'],'Trap Springers')
        self.assertIn('LID_無し',docs['Legion'].by_pid);self.assertIn('LID_無し',docs['Learning tables'].tables_by_id)
