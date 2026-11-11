"""Appearance serialization and live AID rules, without runtime rule evaluation."""
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from fw_editor import (Appearance,AppearanceP0,AppearanceP1,APPEARANCE_TABLES,Item,DataError,Binary,
                       suite_project,load_suite_project,export_suite)
from fixture import asset_fixture,item_fixture
from asset_index import AssetIndex
from test_reliance import snapshot,compare


class AppearanceTests(unittest.TestCase):
    def setUp(self):self.doc=Appearance(asset_fixture())

    def test_color_and_f32_change_exact_bytes(self):
        d=self.doc;v=d.views['rules'];r=v.records[0]
        self.assertEqual(d.build(),d.raw)
        v.set(r,v.by_offset[0x118],'a1b2c3d4');v.set(r,v.by_offset[0xfc],0.73)
        expected=bytearray(d.raw);expected[r.offset+0x118:r.offset+0x11c]=bytes.fromhex('a1b2c3d4')
        struct.pack_into('<f',expected,r.offset+0xfc,0.73)
        self.assertEqual(d.build(),bytes(expected));self.assertEqual(v.value(r,v.by_offset[0x118]),'#A1B2C3D4')
        for bad in ('#123456','#1234567890','#GG001122',1,None):
            with self.assertRaises(DataError):v.set(r,v.by_offset[0x118],bad)
        for bad in (float('nan'),float('inf'),1e100):
            with self.assertRaises(DataError):v.set(r,v.by_offset[0xfc],bad)

    def test_mixed_sections_lists_unicode_headers_and_opaque_bytes(self):
        d=self.doc
        updates=[('rules',0,0x20,[['AID_NEW'],[],['!AID_新規','JID_TEST']]),('rules',0,0x30,'CD_NEW'),
                 ('rules',0,0x80,['AB_NEW','AE_NEW']),('rules',0,0x118,'#12345678'),('rules',0,0x158,'NewBareName'),
                 ('voices',0,0x20,'VoiceNew'),('voices',0,0x28,'FaceNew'),('voices',0,0x4c,1),
                 ('conditions',0,0x30,['flag_NEW'])]
        for section,index,offset,value in updates:
            view=d.views[section];view.set(view.records[index],view.by_offset[offset],value)
        result=Appearance(d.build());compare(self,d,result,dict(d.changes))
        self.assertEqual(result.views['rules'].names['rules:0'],'')
        r=result.views['rules'];r.set(r.records[0],r.by_offset[0x20],[])
        again=Appearance(result.build());self.assertEqual(again.views['rules'].original(again.views['rules'].records[0],r.by_offset[0x20]),[])
        self.assertEqual(again.views['rules'].original(again.views['rules'].records[1],r.by_offset[0x30]),'CD_NEGATED')

    def test_multiline_strings_remain_single_blocks_with_exact_line_endings(self):
        d=Appearance(asset_fixture(include_info=True));v=d.views['info'];r=v.records[0]
        self.assertEqual(v.original(r,v.by_offset[0x48]),'SmallA\r\nSmallB')
        v.set(r,v.by_offset[0x40],'NewA (BoneA)\nNewB (BoneB)\n')
        result=Appearance(d.build());compare(self,d,result,dict(d.changes))
        self.assertEqual(result.views['info'].original(result.views['info'].records[0],v.by_offset[0x40]),'NewA (BoneA)\nNewB (BoneB)\n')
        with self.assertRaises(DataError):d.views['rules'].set(d.views['rules'].records[0],d.views['rules'].by_offset[0x30],'Invalid\nModel')

    def test_file_specific_project_export_rollback_and_legacy_clear(self):
        docs={'Appearance rules':self.doc,'Appearance rules · AssetTable_P0.bin':AppearanceP0(asset_fixture()),
              'Appearance rules · AssetTable_P1.bin':AppearanceP1(asset_fixture()),'Items':Item(item_fixture())}
        for i,doc in enumerate(docs.values()):
            if isinstance(doc,Appearance):v=doc.views['rules'];v.set(v.records[0],v.by_offset[0x30],'CD_FILE_'+str(i))
        project=json.loads(json.dumps(suite_project(docs)));before={k:dict(d.changes) for k,d in docs.items()}
        bad=json.loads(json.dumps(project));bad['documents']['AssetTable_P1.bin']['source_file']='AssetTable.bin'
        with self.assertRaises(DataError):load_suite_project(docs,bad)
        self.assertEqual({k:d.changes for k,d in docs.items()},before)
        for d in docs.values():d.changes={}
        load_suite_project(docs,project);self.assertEqual({k:d.changes for k,d in docs.items()},before)
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);sources={}
            for k,d in docs.items():
                p=base/'source'/d.filename;p.parent.mkdir(exist_ok=True);p.write_bytes(d.raw);sources[k]=p
            paths=export_suite(docs,sources,base/'mod');self.assertEqual(len(paths),4)
            for k,d in docs.items():
                q=type(d)((base/'mod/romfs/GameData'/d.filename).read_bytes())
                for (pid,off),value in d.changes.items():self.assertEqual(q.original(*q.edit_target(pid,off)),value)
                self.assertEqual(sources[k].read_bytes(),d.raw)
        load_suite_project(docs,docs['Items'].project());self.assertFalse(any(d.changes for d in docs.values()))
        load_suite_project(docs,project['documents']['AssetTable_P0.bin']);self.assertTrue(docs['Appearance rules · AssetTable_P0.bin'].changes)
        self.assertFalse(docs['Appearance rules'].changes)

    def test_live_aid_rows_replace_original_refs_and_reset_without_stale_flags(self):
        d=self.doc;v=d.views['rules'];r=v.records[0]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'AssetTable.bin';p.write_bytes(d.raw);index=AssetIndex.load(Path(tmp),Binary)
            docs={'Appearance rules':d};index.refresh_users(docs)
            old_rows=index.rows;index.refresh_users(docs);self.assertIs(index.rows,old_rows)
            v.set(r,v.by_offset[0x20],[['AID_LIVE_ONLY']]);v.set(r,v.by_offset[0x30],'CD_LIVE');index.refresh_users(docs)
            self.assertIn('AID_LIVE_ONLY',index.aids)
            row=next(row for row in index.rows_by_aid['AID_LIVE_ONLY'] if row.index==0)
            self.assertEqual(row.values[0x30],'CD_LIVE');self.assertNotIn(('AID_ALPHA',False),index.mentions_by_row[row.key])
            voices=d.views['voices'];voices.set(voices.records[0],voices.by_offset[0x20],'VoiceLive');index.refresh_users(docs)
            self.assertTrue(any(row.values.get(0x20)=='VoiceLive' for row in index.linked_rows('AID_LIVE_ONLY')))
            d.changes={};index.refresh_users(docs);self.assertNotIn('AID_LIVE_ONLY',index.aids)
            self.assertEqual(p.read_bytes(),d.raw)
            self.assertEqual(len(index.scanned_files),len(set(index.scanned_files)))


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent'))
@unittest.skipUnless((DATA/'AssetTable.bin').is_file(),'Set FW_GAME_DATA for real appearance regression.')
class RealAppearanceTests(unittest.TestCase):
    def test_all_315123_field_values_and_every_untouched_byte_pointer(self):
        total=0
        for kind in APPEARANCE_TABLES:
            with self.subTest(file=kind.filename):
                d=kind((DATA/kind.filename).read_bytes());total+=len(snapshot(d));self.assertEqual(d.build(),d.raw)
                for v in d.views.values():
                    for r in v.records:
                        for f in v.fields:v.set(r,f,v.original(r,f))
                self.assertFalse(d.changes)
                v=d.views['rules'];r=v.records[0]
                for off,value in ((0x20,[['AID_TEST'],[],['!AID_TEST','JID_TEST']]),(0x30,'CD_TEST'),(0xc0,'#12345678'),
                                  (0x80,['AB_TEST']),(0xf8,0.73),(0x158,'NewBareName')):v.set(r,v.by_offset[off],value)
                if 'voices' in d.views:
                    v=d.views['voices'];v.set(v.records[0],v.by_offset[0x20],'VoiceTEST')
                    v.set(v.records[0],v.by_offset[0x4d],1)
                    v=d.views['info'];v.set(v.records[0],v.by_offset[0x78],0.7)
                    v=d.views['variations'];v.set(v.records[0],v.by_offset[0x20],['test_variant'])
                    v=d.views['conditions'];v.set(v.records[0],v.by_offset[0x30],['test_flag'])
                result=kind(d.build());compare(self,d,result,dict(d.changes))
                v=result.views['rules'];v.set(v.records[0],v.by_offset[0x20],[])
                again=kind(result.build());self.assertEqual(again.views['rules'].original(again.views['rules'].records[0],v.by_offset[0x20]),[])
        self.assertEqual(total,315123)

    def test_live_item_flag_owners_and_live_rules_use_distinct_sources(self):
        from fw_editor import read_editable_tables
        docs,_=read_editable_tables(DATA);index=AssetIndex.load(DATA,Binary)
        item=docs['Items · Item_P1.bin'];record=item.records[0];item.set(record,item.by_offset[0x1b8],'AID_ITEM_LIVE')
        index.refresh_users(docs)
        self.assertEqual(index.sources_for('AID_ITEM_LIVE'),('Item_P1.bin',))
        self.assertTrue(any(u.module=='Items · Item_P1.bin' and u.record==record.pid for u in index.users['AID_ITEM_LIVE']))
        side=docs['Appearance rules · AssetTable_P0.bin'].views['rules'];side.set(side.records[0],side.by_offset[0x20],[['AID_ITEM_LIVE']])
        index.refresh_users(docs)
        self.assertEqual(index.sources_for('AID_ITEM_LIVE'),('AssetTable_P0.bin','Item_P1.bin'))
