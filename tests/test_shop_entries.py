"""Inventory growth, compound item projects, pointer isolation, and source safety."""
from copy import deepcopy
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from fw_editor import Item,ItemP0,DataError,suite_project,load_suite_project,export_suite,edit_summary
from fixture import shop_fixture,item_fixture
from item_index import ItemIndex
from test_shops import snapshot


def values(view,row):return {f.offset:view.value(row,f) for f in view.fields}


def preserve_prefix(test,source,result,expanded):
    """Unreachable old arrays are retained; only expanded container headers change."""
    test.assertEqual(source.labels,result.labels);test.assertEqual(source.label_bytes,result.label_bytes)
    left=bytearray(source.raw[32:32+source.size]);right=bytearray(result.raw[32:32+source.size])
    headers={source.views['shops'].tables_by_id[key].offset-32 for key in expanded}
    for at in source.pointers:
        a=struct.unpack_from('<Q',source.raw,32+at)[0];b=struct.unpack_from('<Q',result.raw,32+at)[0]
        if a>=source.pool:test.assertEqual(source.string(a),result.string(b))
        elif at not in {h+32 for h in headers}:test.assertEqual(a,b)
    for at in set(source.pointers)|set(result.pointers):
        if at+8<=source.size:left[at:at+8]=right[at:at+8]=b'\0'*8
    for h in headers:left[h+18:h+20]=right[h+18:h+20]=b'\0'*2
    test.assertEqual(left,right)


class ShopEntryTests(unittest.TestCase):
    def setUp(self):self.d=Item(shop_fixture());self.v=self.d.views['shops']

    def test_blank_empty_and_multiple_shop_arrays_preserve_every_existing_value(self):
        d=self.d;v=self.v;original=snapshot(d)
        a=v.append_entry('shops:0');b=v.append_entry('shops:1');c=v.append_entry('shops:2')
        self.assertEqual(v.value(a,v.by_offset[0x20]),'MID_Shop_ALPHA');self.assertEqual(v.value(b,v.by_offset[0x6b]),1)
        self.assertTrue(d.modified and v.modified and v.table_changed('shops:1') and v.record_changed(b.pid))
        self.assertEqual(d.added_count,3);self.assertIn('3 added entries',edit_summary(d))
        for i,r in enumerate((a,b,c)):v.set(r,v.by_offset[0x28],f'IID_New_{i}|||')
        result=Item(d.build());after=snapshot(result)
        self.assertTrue(all(after[k]==value for k,value in original.items()))
        for r in (a,b,c):self.assertEqual(values(v,r),values(result.views['shops'],result.views['shops'].by_pid[r.pid]))
        self.assertEqual([len(rows) for rows in result.views['shops'].rows_by_table.values()],[3,1,2])
        preserve_prefix(self,d,result,['shops:0','shops:1','shops:2'])

    def test_duplicate_current_values_arrays_headers_and_new_items_together(self):
        d=self.d;v=self.v;source=v.records[0]
        for off,value in ((0x28,'IID_New'),(0x38,['chapter','!blocked']),(0x48,['IID_Material','IID_New']),
                          (0x58,[2,255]),(0x68,65535),(0x6a,-128),(0x6b,255),(0x6c,255)):v.set(source,v.by_offset[off],value)
        a=v.duplicate_entry(source);self.assertEqual(values(v,a),values(v,source))
        v.set(a,v.by_offset[0x48],['IID_New']);v.set(a,v.by_offset[0x58],[5]);b=v.duplicate_entry(a)
        self.assertEqual(values(v,a),values(v,b));self.assertEqual(v.value(source,v.by_offset[0x58]),[2,255])
        outside=v.value(b,v.by_offset[0x38]);outside.append('outside');self.assertEqual(v.value(b,v.by_offset[0x38]),['chapter','!blocked'])
        d.create_item('IID_New',d.records[0].pid);d.set(d.by_pid['IID_New'],d.by_offset[0x4c],777)
        d.views['loot'].set(d.views['loot'].records[0],d.views['loot'].by_offset[0x30],321)
        d.views['values'].set(d.views['values'].records[0],d.views['values'].by_offset[0x22],444)
        result=Item(d.build());rv=result.views['shops']
        for r in (source,a,b):self.assertEqual(values(v,r),values(rv,rv.by_pid[r.pid]))
        self.assertEqual(result.value(result.by_pid['IID_New'],result.by_offset[0x4c]),777)
        self.assertEqual(result.views['loot'].value(result.views['loot'].records[0],result.views['loot'].by_offset[0x30]),321)
        self.assertEqual(result.views['values'].value(result.views['values'].records[0],result.views['values'].by_offset[0x22]),444)
        headers=[*result.records,*rv.records,*rv.collections,*result.views['loot'].records,*result.views['values'].records]
        new_tags=[struct.unpack_from('<H',result.raw,rv.by_pid[r.pid].offset+22)[0] for r in (a,b)]
        self.assertEqual(len(set(new_tags)),2)
        for tag in new_tags:self.assertEqual(sum(struct.unpack_from('<H',result.raw,r.offset+22)[0]==tag for r in headers),1)

    def test_all_empty_inventories_can_receive_first_entries(self):
        d=Item(shop_fixture(empty_shops=True));v=d.views['shops'];self.assertFalse(v.records)
        row=v.append_entry('shops:1');v.set(row,v.by_offset[0x28],'IID_First')
        result=Item(d.build());other=result.views['shops'];r=other.by_pid[row.pid]
        self.assertEqual(other.value(r,other.by_offset[0x28]),'IID_First')
        self.assertEqual(other.names[r.pid],other.names['shops:1'])
        preserve_prefix(self,d,result,['shops:1'])

    def test_undo_reset_snapshots_and_draft_seed_restoration(self):
        d=self.d;v=self.v;clean=d.project();a=v.duplicate_entry(v.records[0]);v.set(a,v.by_offset[0x68],200)
        state=d.snapshot_edits();v.append_entry('shops:1');v.remove_last_added('shops:0')
        self.assertNotIn(a.pid,v.by_pid);d.restore_edits(state);self.assertEqual(v.value(v.by_pid[a.pid],v.by_offset[0x68]),200)
        v.changes={key:value for key,value in v.changes.items() if key[0]!=a.pid}
        self.assertEqual(v.value(v.by_pid[a.pid],v.by_offset[0x68]),150)
        v.append_entry('shops:2');v.reset_table('shops:0');self.assertEqual(d.added_count,1)
        v.remove_last_added('shops:2');self.assertFalse(d.modified);self.assertEqual(d.build(),d.raw)
        with self.assertRaises(DataError):v.remove_last_added('shops:0')
        v.append_entry('shops:1');d.load_project(clean);self.assertFalse(d.added_count);self.assertFalse(d.modified)

    def test_bad_values_and_capacity_fail_without_mutating_other_edits(self):
        d=self.d;v=self.v;d.create_item('IID_Keep');v.duplicate_entry(v.records[0]);before=d.project()
        bad=values(v,v.records[0]);bad[0x58]=[]
        for key,data in [('missing',None),('shops:0',{}),('shops:0',bad),('shops:0',{**bad,0x68:65536})]:
            with self.assertRaises(DataError):v.append_entry(key,data)
            self.assertEqual(d.project(),before)
        with self.assertRaises(DataError):d.views['loot'].append_entry('loot:0')
        with patch.object(v,'rows_by_table',{'shops:0':[None]*65535}):
            with self.assertRaises(DataError):v.append_entry('shops:0')
        raw=bytearray(d.raw);struct.pack_into('<H',raw,d._source_records[0].offset+22,65535);full=Item(bytes(raw))
        with self.assertRaises(DataError):full.views['shops'].append_entry('shops:0')
        self.assertFalse(full.modified)

    def test_v4_projects_reject_malformed_data_and_roll_back_atomically(self):
        d=self.d;v=self.v;d.create_item('IID_New');r=v.append_entry('shops:1');v.set(r,v.by_offset[0x28],'IID_New')
        before=json.loads(json.dumps(d.project()));self.assertEqual(before['format'],'fw-item-edits-v4')
        other=Item(d.raw);load_suite_project({'Items':other},before);self.assertEqual(other.project(),before);self.assertEqual(other.build(),d.build())
        for mode in ('source','sha','downgrade','missing_items','missing_shops','notlist','empty','unknown','duplicate','fields','range','pair','row'):
            bad=deepcopy(before)
            if mode=='source':bad['source_file']='Item_P0.bin'
            elif mode=='sha':bad['source_sha256']='bad'
            elif mode=='downgrade':bad['format']='fw-item-edits-v3'
            elif mode=='missing_items':del bad['new_items']
            elif mode=='missing_shops':del bad['new_shop_entries']
            elif mode=='notlist':bad['new_shop_entries']={}
            elif mode=='empty':bad['new_shop_entries'][0]['entries']=[]
            elif mode=='unknown':bad['new_shop_entries'][0]['shop']='MISSING'
            elif mode=='duplicate':bad['new_shop_entries']*=2
            elif mode=='fields':del bad['new_shop_entries'][0]['entries'][0]['32']
            elif mode=='range':bad['new_shop_entries'][0]['entries'][0]['104']=65536
            elif mode=='pair':bad['new_shop_entries'][0]['entries'][0]['88']=[1]
            else:bad['changes'].append({'pid':'shops:1:99','offset':40,'value':'IID_Invalid'})
            with self.assertRaises((DataError,KeyError)):other.load_project(bad)
            self.assertEqual(other.project(),before)
        docs={'Items':other,'Side':ItemP0(item_fixture())};project=suite_project(docs)
        project['documents']['Item_P0.bin']['source_sha256']='bad'
        with self.assertRaises(DataError):load_suite_project(docs,project)
        self.assertEqual(other.project(),before)

    def test_live_new_item_references_export_reedit_and_no_backups(self):
        d=self.d;v=self.v;d.create_item('IID_New');r=v.append_entry('shops:1');v.set(r,v.by_offset[0x28],'IID_New')
        hits=ItemIndex().uses('IID_New',{'Items':d});self.assertTrue(any(u.record==r.pid and u.table=='shops:1' for u in hits))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source/romfs/GameData/Item.bin';source.parent.mkdir(parents=True);source.write_bytes(d.raw)
            with self.assertRaises(DataError):export_suite({'Items':d},{'Items':source},root/'source')
            out=root/'mod';export_suite({'Items':d},{'Items':source},out);export_suite({'Items':d},{'Items':source},out)
            target=out/'romfs/GameData/Item.bin';result=Item(target.read_bytes());self.assertFalse(list(target.parent.glob('*.backup-*')))
            project=json.loads((out/'suite-edits.json').read_text());self.assertEqual(project['documents']['Item.bin']['format'],'fw-item-edits-v4')
            result.views['shops'].duplicate_entry(result.views['shops'].by_pid[r.pid]);again=Item(result.build())
            self.assertEqual(len(again.views['shops'].rows_by_table['shops:1']),2);self.assertEqual(source.read_bytes(),d.raw)

    def test_shared_source_arrays_are_isolated_when_expanded(self):
        d=self.d;v=self.v;raw=bytearray(d.raw);a=v.tables_by_id['shops:0'];b=v.tables_by_id['shops:2']
        pointer=struct.unpack_from('<Q',raw,a.offset+32)[0];struct.pack_into('<Q',raw,b.offset+32,pointer);struct.pack_into('<H',raw,b.offset+18,2)
        d=Item(bytes(raw));v=d.views['shops'];source=values(v,v.rows_by_table['shops:0'][0])
        r=v.duplicate_entry(v.rows_by_table['shops:2'][0]);v.set(v.rows_by_table['shops:2'][0],v.by_offset[0x68],900)
        result=Item(d.build());rv=result.views['shops']
        self.assertEqual(values(rv,rv.rows_by_table['shops:0'][0]),source)
        self.assertEqual(rv.value(rv.rows_by_table['shops:2'][0],rv.by_offset[0x68]),900)
        self.assertEqual(rv.value(rv.by_pid[r.pid],rv.by_offset[0x68]),150)

    def test_unverified_direct_or_indexed_leaf_references_are_rejected(self):
        d=self.d;row=self.v.records[0]
        raw=bytearray(d.raw);struct.pack_into('<Q',raw,d.records[0].offset+0x20,row.offset-32)
        direct=Item(bytes(raw));before=direct.project()
        with self.assertRaisesRegex(DataError,'direct references'):direct.views['shops'].append_entry('shops:0')
        self.assertEqual(direct.project(),before)
        raw=bytearray(d.raw);label_start=32+d.size+8*len(d.pointers)
        for i,(offset,_) in enumerate(struct.iter_unpack('<II',d.label_bytes)):
            if offset+32==d.labels['TIER_ALPHA']:struct.pack_into('<I',raw,label_start+i*8,row.offset-32);break
        indexed=Item(bytes(raw));before=indexed.project()
        with self.assertRaisesRegex(DataError,'indexed leaf'):indexed.views['shops'].append_entry('shops:0')
        self.assertEqual(indexed.project(),before)


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent'))
@unittest.skipUnless((DATA/'Item.bin').is_file(),'Set FW_GAME_DATA for native shop expansion tests.')
class RealShopEntryTests(unittest.TestCase):
    def test_native_multiple_shop_additions_preserve_all_existing_values_and_bytes(self):
        d=Item((DATA/'Item.bin').read_bytes());v=d.views['shops'];original=snapshot(d)
        tables=[t for t in v.collections if v.rows_by_table[t.pid]][:3]
        for t in tables:v.duplicate_entry(v.rows_by_table[t.pid][0])
        result=Item(d.build());after=snapshot(result)
        self.assertTrue(all(after[k]==value for k,value in original.items()))
        self.assertEqual(len(result.views['shops'].records),1155)
        for t in tables:
            r=v.rows_by_table[t.pid][-1];self.assertEqual(values(v,r),values(result.views['shops'],result.views['shops'].by_pid[r.pid]))
            self.assertEqual(result.views['shops'].names[r.pid],v.names[t.pid])
        preserve_prefix(self,d,result,[t.pid for t in tables])

    def test_native_new_item_and_inventory_roundtrip_reopen_and_reedit(self):
        d=Item((DATA/'Item.bin').read_bytes());v=d.views['shops'];d.create_item('IID_New_Shop_Test',d.records[1].pid)
        r=v.duplicate_entry(v.records[0]);v.set(r,v.by_offset[0x28],'IID_New_Shop_Test');v.set(r,v.by_offset[0x68],123)
        project=json.loads(json.dumps(d.project()));other=Item(d.raw);other.load_project(project)
        self.assertEqual(other.build(),d.build());result=Item(d.build());rv=result.views['shops']
        self.assertEqual(rv.value(rv.by_pid[r.pid],rv.by_offset[0x28]),'IID_New_Shop_Test')
        self.assertEqual(rv.value(rv.by_pid[r.pid],rv.by_offset[0x68]),123)
        rv.duplicate_entry(rv.by_pid[r.pid]);again=Item(result.build());self.assertEqual(len(again.records),len(d._source_records)+1)
        self.assertEqual(len(again.views['shops'].records),1154)
