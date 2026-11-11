"""Primary IID creation, source isolation and full auxiliary-file preservation."""
from copy import deepcopy
import json
import os
from pathlib import Path
import struct
from types import SimpleNamespace
import tempfile
import unittest

from fw_editor import (Item,ItemP0,ItemP1,Person,Learning,DataError,FORMATS,TEXT_TYPES,ARRAY_TYPES,
                       suite_project,load_suite_project,export_suite,validate_new_item_ids)
from item_index import ItemIndex,reference_ids,iid_tokens
from skill_index import SkillIndex
from fixture import item_fixture,shop_fixture
from test_shops import snapshot


def check_preservation(test,source,result):
    ranges=sorted((r.offset-32,result.stride) for r in result.records if r.pid not in {r.pid for r in source._source_records})
    def moved(value):
        for at,size in ranges:
            if at<=value:value+=size
        return value
    for key,offset in source.labels.items():test.assertEqual(result.labels[key],moved(offset-32)+32)
    for at in source.pointers:
        old=struct.unpack_from('<Q',source.raw,at+32)[0];new=struct.unpack_from('<Q',result.raw,moved(at)+32)[0]
        if old>=source.pool:test.assertEqual(source.string(old),result.string(new))
        else:test.assertEqual(moved(old),new)
    original=bytearray(source.raw[32:32+source.size]);current=bytearray(result.raw[32:32+result.size])
    for at,size in reversed(ranges):del current[at:at+size]
    current=current[:source.size]
    for at in source.pointers:original[at:at+8]=current[at:at+8]=b'\0'*8
    test.assertEqual(original,current)
    for row in source._source_records:
        other=result.by_pid[row.pid];test.assertEqual(other.index,row.index)
        test.assertEqual(source.raw[row.offset+16:row.offset+32],result.raw[other.offset+16:other.offset+32])


class ItemCreationTests(unittest.TestCase):
    def setUp(self):self.doc=Item(shop_fixture())

    def test_blank_defaults_and_indexed_unicode_pipe_id(self):
        d=self.doc;row=d.create_item('IID_New_新規|||')
        self.assertTrue(d.modified);self.assertTrue(d.record_changed(row.pid));self.assertFalse(d.changes)
        self.assertEqual(row.index,len(d._source_records));self.assertEqual(d.added_item_count,1)
        for f in d.fields:self.assertEqual(d.value(row,f),0 if f.kind in FORMATS else [] if f.kind in ARRAY_TYPES else '')
        result=Item(d.build());r=result.by_pid[row.pid]
        self.assertEqual(result.labels[row.pid],r.offset);self.assertEqual(iid_tokens(row.pid),((row.pid,False),))
        self.assertEqual(struct.unpack_from('<HH',result.raw,r.offset+16),(row.index,1))
        check_preservation(self,d,result)

    def test_all_current_fields_duplicate_and_lists_are_independent(self):
        d=self.doc;source=d.records[1];d.set(source,d.by_offset[0x4c],8765);d.set(source,d.by_offset[0x98],['SID_CURRENT'])
        values={f.offset:d.value(source,f) for f in d.fields};row=d.create_item('IID_Copy',source.pid)
        self.assertEqual({f.offset:d.value(row,f) for f in d.fields},values)
        d.set(row,d.by_offset[0x98],['SID_INDEPENDENT']);d.create_item('IID_Copy2',row.pid)
        self.assertEqual(d.value(source,d.by_offset[0x98]),['SID_CURRENT'])
        value=d.value(row,d.by_offset[0x98]);value.append('outside mutation')
        self.assertEqual(d.value(row,d.by_offset[0x98]),['SID_INDEPENDENT'])
        result=Item(d.build());self.assertEqual(result.original(result.by_pid['IID_Copy2'],result.by_offset[0x98]),['SID_INDEPENDENT'])
        self.assertEqual(result.original(result.by_pid[source.pid],result.by_offset[0x4c]),8765)

    def test_invalid_ids_values_and_source_guards_are_transactional(self):
        d=self.doc;d.create_item('IID_Before');before=d.project()
        for key in ('IID_','IID_ spaces',' IID_Test','IID_Test\n','IID_Test\0','IID_A::0','IID_A,B','IID_A!B','IID_A&B',None,'SID_Test',d.records[0].pid,'IID_Before'):
            with self.assertRaises(DataError):d.create_item(key)
            self.assertEqual(d.project(),before)
        with self.assertRaises(DataError):d.create_item('IID_Copy','IID_Missing')
        bad_values=deepcopy(d.new_items['IID_Before']);bad_values[0x4c]=1<<32
        with self.assertRaises(DataError):d.create_item('IID_Invalid',values=bad_values)
        self.assertEqual(d.project(),before)
        for mode in ('source','hash','offset','value','downgrade'):
            bad=deepcopy(before)
            if mode=='source':bad['source_file']='Item_P1.bin'
            elif mode=='hash':bad['source_sha256']='bad'
            elif mode=='offset':del bad['new_items'][0]['values']['32']
            elif mode=='value':bad['new_items'][0]['values']['76']=-1
            else:bad['format']='fw-item-edits-v2'
            with self.assertRaises(DataError):d.load_project(bad)
            self.assertEqual(d.project(),before)

    def test_reset_remove_keeps_original_ids_and_old_formats(self):
        d=self.doc;old=d.project();ids=[(r.pid,r.index) for r in d.records]
        a=d.create_item('IID_A',d.records[0].pid);b=d.create_item('IID_B')
        d.set(a,d.by_offset[0x4c],123);d.changes={k:v for k,v in d.changes.items() if k[0]!=a.pid}
        self.assertEqual(d.value(a,d.by_offset[0x4c]),d.new_items[a.pid][0x4c])
        d.remove_item(a.pid);self.assertEqual(d.by_pid[b.pid].index,len(ids))
        self.assertEqual([(r.pid,r.index) for r in d.records[:len(ids)]],ids)
        with self.assertRaises(DataError):d.remove_item(d.records[0].pid)
        d.load_project(old);self.assertFalse(d.modified);self.assertEqual(d.build(),d.raw)
        v=d.views['shops'];v.set(v.records[0],v.by_offset[0x68],777);old=d.project()
        self.assertEqual(old['format'],'fw-item-edits-v2');d.create_item('IID_New');d.load_project(old)
        self.assertFalse(d.new_items);self.assertTrue(d.changes)

    def test_v3_projects_share_primary_and_shop_edits(self):
        d=self.doc;row=d.create_item('IID_Custom',d.records[0].pid);d.set(row,d.by_offset[0x4c],4444)
        shop=d.views['shops'];shop.set(shop.records[0],shop.by_offset[0x28],row.pid);shop.set(shop.records[0],shop.by_offset[0x68],987)
        project=json.loads(json.dumps(d.project()));self.assertEqual(project['format'],'fw-item-edits-v3')
        other=Item(d.raw);load_suite_project({'Items':other},project)
        self.assertEqual(other.project(),project);self.assertEqual(other.build(),d.build())
        result=Item(other.build());v=result.views['shops']
        self.assertEqual(v.original(v.records[0],v.by_offset[0x28]),row.pid)
        self.assertEqual(result.original(result.by_pid[row.pid],result.by_offset[0x4c]),4444)

    def test_cross_file_new_id_collisions_roll_back_and_prevent_writes(self):
        d=self.doc;seed=ItemP0(item_fixture());seed.create_item('IID_SIDE_NATIVE');side=ItemP0(seed.build())
        d.create_item('IID_SIDE_NATIVE');docs={'Items':d,'Side':side}
        with self.assertRaises(DataError):validate_new_item_ids(docs)
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'out'
            with self.assertRaises(DataError):export_suite(docs,{},out)
            self.assertFalse(out.exists())
        d.remove_item('IID_SIDE_NATIVE');d.create_item('IID_Unique');before={k:v.project() for k,v in docs.items()}
        bad=suite_project(docs);copy=ItemP0(side.raw);copy.create_item('IID_Unique')
        bad['documents']['Item_P0.bin']=copy.project()
        with self.assertRaises(DataError):load_suite_project(docs,bad)
        self.assertEqual({k:v.project() for k,v in docs.items()},before)

    def test_every_original_value_header_label_and_opaque_byte_preserved(self):
        d=self.doc;before=snapshot(d);d.create_item('IID_Blank');d.create_item('IID_Copy',d.records[1].pid)
        result=Item(d.build());after=snapshot(result)
        self.assertTrue(all(after[k]==v for k,v in before.items()))
        self.assertEqual(set(result.labels)-set(d.labels),set(d.new_items))
        tags=[struct.unpack_from('<H',result.raw,r.offset+22)[0] for r in result.records]
        self.assertEqual(len(tags),len(set(tags)));check_preservation(self,d,result)
        raw=bytearray(d.raw);struct.pack_into('<H',raw,d._source_records[-1].offset+22,65535);full=Item(bytes(raw))
        with self.assertRaises(DataError):full.create_item('IID_NoTag')
        self.assertFalse(full.modified)

    def test_live_choosers_item_and_skill_usage_include_new_records(self):
        d=self.doc;row=d.create_item('IID_New|||');d.set(row,d.by_offset[0x98],['SID_NEW'])
        d.set(d.records[0],d.by_offset[0x108],row.pid)
        shop=d.views['shops'];shop.set(shop.records[0],shop.by_offset[0x28],row.pid)
        docs={'Items':d};app=SimpleNamespace(catalog={'IID_CATALOG':'','SID_OTHER':''},documents=docs)
        self.assertIn(row.pid,reference_ids(app,'IID_'))
        uses=ItemIndex().uses(row.pid,docs);self.assertTrue(any(u.module=='Items' for u in uses));self.assertTrue(any(u.module=='Shop & Loot' for u in uses))
        self.assertTrue(any(u.record==row.pid for u in SkillIndex().uses('SID_NEW',docs)))
        d.remove_item(row.pid);self.assertNotIn(row.pid,reference_ids(app,'IID_'))

    def test_three_file_exports_manifests_backups_reedit_and_legacy_clear(self):
        docs={'Items':self.doc,'Side0':ItemP0(item_fixture()),'Side1':ItemP1(item_fixture())}
        for i,d in enumerate(docs.values()):d.create_item('IID_New_'+str(i),d.records[0].pid)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);sources={}
            for key,d in docs.items():sources[key]=root/d.filename;sources[key].write_bytes(d.raw)
            export_suite(docs,sources,root/'mod');manifest=json.loads((root/'mod/suite-edits.json').read_text(encoding='utf8'))
            for key,d in docs.items():
                self.assertEqual(manifest['documents'][d.filename]['format'],'fw-item-edits-v3')
                target=root/'mod/romfs/GameData'/d.filename;result=type(d)(target.read_bytes())
                result.create_item('IID_Reedit_'+key);self.assertEqual(len(type(d)(result.build()).records),len(d.records)+1)
                self.assertEqual(sources[key].read_bytes(),d.raw)
            export_suite(docs,sources,root/'mod');self.assertEqual(len(list((root/'mod/romfs/GameData').glob('*.backup-*'))),3)
        load_suite_project(docs,Item(self.doc.raw).project());self.assertFalse(any(d.new_items for d in docs.values()))


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent/fw-game-data'))
@unittest.skipUnless((DATA/'Item.bin').is_file(),'Set FW_GAME_DATA for native item creation regressions.')
class RealItemCreationTests(unittest.TestCase):
    def test_all_123785_original_values_and_original_bytes_across_three_sources(self):
        total=0
        for cls in (Item,ItemP0,ItemP1):
            d=cls((DATA/cls.filename).read_bytes());before=snapshot(d);total+=len(before)
            d.create_item('IID_Blank_'+cls.filename);d.create_item('IID_Copy_'+cls.filename,d.records[1].pid)
            result=cls(d.build());after=snapshot(result)
            self.assertTrue(all(after[k]==v for k,v in before.items()))
            self.assertEqual(len(result.records),len(d._source_records)+2);check_preservation(self,d,result)
        self.assertEqual(total,123785)

    def test_new_items_character_inventory_shop_new_lid_and_glid_export_together(self):
        item=Item((DATA/'Item.bin').read_bytes());row=item.create_item('IID_New_Integrated',item.records[1].pid)
        view=item.views['shops'];view.set(view.records[0],view.by_offset[0x28],row.pid)
        person=Person((DATA/'Person.bin').read_bytes());p=person.by_pid['PID_ディートリヒ'];person.set(p,person.by_offset[0x78],[row.pid])
        growth=Learning((DATA/'Growth.bin').read_bytes());growth.create_list('LID_New_Integrated');person.set(p,person.by_offset[0x88],['LID_New_Integrated'])
        g=growth.progression;r=next(r for r in g.records if g.value(r,g.by_offset[0x20]) in range(4,9));g.set(r,g.fields[1],row.pid.removeprefix('IID_'))
        docs={'Items':item,'Characters':person,'Learning tables':growth};project=json.loads(json.dumps(suite_project(docs)))
        other={'Items':Item(item.raw),'Characters':Person(person.raw),'Learning tables':Learning(growth.raw)};load_suite_project(other,project)
        self.assertEqual(suite_project(other),project)
        uses=ItemIndex().uses(row.pid,other);self.assertTrue(any(u.module=='Characters' for u in uses));self.assertTrue(any(u.module=='GLID progression' for u in uses))
        for d in other.values():self.assertTrue(d.build())

    def test_all_eighty_new_fields_and_independent_arrays_roundtrip(self):
        d=ItemP1((DATA/'Item_P1.bin').read_bytes());row=d.create_item('IID_AllFields|||',d.records[0].pid)
        for f in d.fields:
            value=(-1 if f.kind in ('s8','s16','s32','int') else 1) if f.kind in FORMATS else ['Test_'+str(f.offset)] if f.kind in ARRAY_TYPES else 'Test_'+str(f.offset)
            d.set(row,f,value)
        expected={f.offset:d.value(row,f) for f in d.fields};result=ItemP1(d.build())
        self.assertEqual({f.offset:result.original(result.by_pid[row.pid],f) for f in result.fields},expected)
        self.assertEqual(d.raw,(DATA/'Item_P1.bin').read_bytes())
