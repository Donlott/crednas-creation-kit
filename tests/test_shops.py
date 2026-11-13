"""Main items and shop/loot edits share one binary, transaction and export."""
import copy
import os
from pathlib import Path
import struct
import tempfile
import unittest
from fw_editor import Item,ItemP0,ItemP1,Facility,Binary,DataError,suite_project,load_suite_project,export_suite
from fixture import shop_fixture,item_fixture,facility_fixture
from item_index import ItemIndex
from skill_index import document_views
from shop_ui import collection_links


def snapshot(doc):
    return {(row.pid,field.offset):view.original(row,field)
            for view in [doc,*doc.views.values()] for row in view.records for field in view.fields}


def verify(test,doc,result):
    test.assertEqual(snapshot(result),{**snapshot(doc),**doc.changes})
    test.assertEqual(result.labels,doc.labels);test.assertEqual(result.label_bytes,doc.label_bytes)
    left=bytearray(doc.raw[32:32+doc.size]);right=bytearray(result.raw[32:32+doc.size]);changed=set()
    for pid,off in doc.changes:
        row,field=doc.edit_target(pid,off);start=row.offset-32+off;changed.update(range(start,start+field.size))
    for at in doc.pointers:
        if any(at+i in changed for i in range(8)):continue
        a=struct.unpack_from('<Q',doc.raw,at+32)[0];b=struct.unpack_from('<Q',result.raw,at+32)[0]
        if a>=doc.pool:test.assertEqual(doc.string(a),result.string(b))
        else:test.assertEqual(a,b)
    for at in set(doc.pointers)|set(result.pointers):
        if at+8<=doc.size:left[at:at+8]=right[at:at+8]=b'\0'*8
    for at in changed:left[at]=right[at]=0
    test.assertEqual(left,right)
    for key,view in doc.views.items():
        test.assertEqual(view.names,result.views[key].names)
        test.assertEqual({k:len(v) for k,v in view.rows_by_table.items()},{k:len(v) for k,v in result.views[key].rows_by_table.items()})


class ShopTests(unittest.TestCase):
    def setUp(self):self.doc=Item(shop_fixture())
    def edit(self,key,pid,offset,value):
        view=self.doc.views[key];view.set(view.by_pid[pid],view.by_offset[offset],value)

    def test_shared_owner_scalar_bytes_signed_discount_and_bounds(self):
        d=self.doc;v=d.views['shops'];r=v.records[0];self.assertEqual(d.build(),d.raw)
        self.assertIs(v.changes,d.changes);self.assertEqual(len(d.records),2)
        d.set(d.records[0],d.by_offset[0x4c],555);self.edit('shops',r.pid,0x68,65535);self.edit('shops',r.pid,0x6a,-128)
        expected=bytearray(d.raw);struct.pack_into('<I',expected,d.records[0].offset+0x4c,555)
        struct.pack_into('<H',expected,r.offset+0x68,65535);struct.pack_into('<b',expected,r.offset+0x6a,-128)
        self.assertEqual(d.build(),bytes(expected))
        for offset,value in ((0x68,65536),(0x6a,-129),(0x6a,128),(0x6b,256),(0x6c,-1)):
            with self.assertRaises(DataError):self.edit('shops',r.pid,offset,value)

    def test_all_auxiliary_kinds_and_primary_values_survive_joint_export(self):
        d=self.doc;v=d.views['shops'];r=v.records[0];d.set(d.records[0],d.by_offset[0x98],['SID_NEW'])
        for offset,value in ((0x20,'MID_Shop_NEW'),(0x28,'IID_NEW|||'),(0x38,['new','!blocked']),
                             (0x48,['IID_MATERIAL','IID_OTHER|']),(0x58,[0,255]),(0x68,900),(0x6a,-5),(0x6b,0),(0x6c,255)):
            self.edit('shops',r.pid,offset,value)
        self.edit('loot','loot:0:1',0x20,'IID_NEW|||');self.edit('loot','loot:0:1',0x30,65535);self.edit('loot','loot:0:1',0x38,['Unicode ★'])
        self.edit('values','values:1',0x20,65535);self.edit('values','values:1',0x22,0)
        result=Item(d.build());verify(self,d,result)
        result.views['shops'].set(result.views['shops'].records[0],result.views['shops'].by_offset[0x38],[])
        self.assertEqual(Item(result.build()).views['shops'].original(result.views['shops'].records[1],result.views['shops'].by_offset[0x28]),'IID_SYNTHETIC_A|')

    def test_exchange_pair_validation_and_transactional_projects(self):
        d=self.doc;self.edit('shops','shops:0:0',0x58,[])
        with self.assertRaisesRegex(DataError,'same number'):d.build()
        self.edit('shops','shops:0:0',0x48,[]);d.build();project=d.project();self.assertEqual(project['format'],'fw-item-edits-v2')
        before=copy.deepcopy(d.changes);bad=copy.deepcopy(project);bad['changes'][-1]['value']=[1,2]
        with self.assertRaises(DataError):d.load_project(bad)
        self.assertEqual(d.changes,before)
        bad=copy.deepcopy(project);bad['format']='fw-item-edits-v1'
        with self.assertRaises(DataError):d.load_project(bad)
        self.assertEqual(d.changes,before)
        bad=copy.deepcopy(project);bad['source_file']='Item_P0.bin'
        with self.assertRaises(DataError):d.load_project(bad)
        self.assertEqual(d.changes,before)

    def test_legacy_primary_projects_clear_auxiliary_edits_and_keep_compatibility(self):
        d=self.doc;d.set(d.records[0],d.by_offset[0x4c],500);legacy=d.project();self.assertEqual(legacy['format'],'fw-item-edits-v1')
        self.edit('loot','loot:0:0',0x30,200);self.assertEqual(d.project()['format'],'fw-item-edits-v2')
        d.load_project(legacy);self.assertEqual(d.changes,{(d.records[0].pid,0x4c):500})
        side=ItemP1(item_fixture());docs={'Items':d,'Side':side}
        self.edit('loot','loot:0:0',0x30,200);suite=suite_project(docs);before={k:dict(v.changes) for k,v in docs.items()}
        broken=copy.deepcopy(suite);broken['documents']['Item_P1.bin']['source_sha256']='wrong'
        with self.assertRaises(DataError):load_suite_project(docs,broken)
        self.assertEqual(before,{k:v.changes for k,v in docs.items()})
        load_suite_project(docs,legacy);self.assertEqual(d.changes,{(d.records[0].pid,0x4c):500})

    def test_empty_collections_reset_table_and_file_export_safety(self):
        d=self.doc;shops=d.views['shops'];self.assertEqual(shops.rows_by_table['shops:1'],[])
        d.set(d.records[0],d.by_offset[0x4c],200);self.edit('shops','shops:0:0',0x68,900);self.edit('shops','shops:2:0',0x68,800);self.edit('loot','loot:0:0',0x30,111)
        shops.reset_table('shops:0');self.assertNotIn(('shops:0:0',0x68),d.changes);self.assertEqual(len(d.changes),3)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'romfs/GameData/Item.bin';source.parent.mkdir(parents=True);source.write_bytes(d.raw)
            docs={'Items':d};sources={'Items':source}
            with self.assertRaises(DataError):export_suite(docs,sources,root)
            export_suite(docs,sources,root/'mod');self.assertEqual([p.name for p in (root/'mod/romfs/GameData').iterdir()],['Item.bin'])
            verify(self,d,Item((root/'mod/romfs/GameData/Item.bin').read_bytes()))
            export_suite(docs,sources,root/'mod');self.assertEqual(len(list((root/'mod/romfs/GameData').glob('*.backup-*'))),0)

    def test_live_iid_usage_replaces_static_rows_and_preserves_primary_view(self):
        d=self.doc
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'Item.bin').write_bytes(d.raw);index=ItemIndex.load(root,Binary)
            uses=index.uses('IID_SYNTHETIC_A',{'Items':d});self.assertFalse(any(u.module=='' for u in uses))
            self.assertTrue(any(u.module=='Shop & Loot' for u in uses));self.assertTrue(any(u.module=='Items' for u in index.uses('IID_SYNTHETIC_A|',{'Items':d})))
            self.edit('shops','shops:0:0',0x28,'IID_NEW')
            self.assertFalse(any(u.record=='shops:0:0' for u in index.uses('IID_SYNTHETIC_A',{'Items':d})))
            self.assertTrue(any(u.record=='shops:0:0' for u in index.uses('IID_NEW',{'Items':d})))
        self.assertEqual([view.prefix for _,view in document_views({'Items':d})],['IID_','SHOP_','SHOP_','SHOP_'])

    def test_facility_lottery_links_use_current_unsaved_reference(self):
        d=self.doc;facility=Facility(facility_fixture());v=facility.views['theater'];v.set(v.records[0],v.by_offset[0x28],'LOT_ALPHA')
        loot=d.views['loot'];links=collection_links(loot,loot.collections[0],{'Facilities & Rewards':facility,'Items':d})
        self.assertTrue(any(x[0]=='Facilities & Rewards' and x[2]=='theater:0' for x in links))
        v.set(v.records[0],v.by_offset[0x28],'LOT_BETA');self.assertEqual(collection_links(loot,loot.collections[0],{'Facilities & Rewards':facility,'Items':d}),[])


BASE=Path(os.environ.get('FW_GAME_DATA','/nonexistent'))
@unittest.skipUnless((BASE/'Item.bin').is_file(),'Set FW_GAME_DATA for shop/loot regressions.')
class RealShopTests(unittest.TestCase):
    def test_all_123785_primary_and_auxiliary_values_and_opaque_bytes(self):
        total=0
        for kind in (Item,ItemP0,ItemP1):
            d=kind((BASE/kind.filename).read_bytes());self.assertEqual(d.build(),d.raw);d.set(d.records[0],d.by_offset[0x4c],12345)
            total+=len(snapshot(d))
            for key,view in d.views.items():
                row=view.records[0]
                for field in view.fields:
                    if key=='shops':value={0x20:'MID_NEW',0x28:'IID_NEW|||',0x38:['test','!flag'],0x48:['IID_MAT','IID_OTHER'],0x58:[1,255],0x68:65535,0x6a:-128,0x6b:255,0x6c:0}[field.offset]
                    elif key=='loot':value={0x20:'IID_NEW|||',0x30:65535,0x38:['Unicode ★']}[field.offset]
                    else:value=65535
                    view.set(row,field,value)
            result=kind(d.build());verify(self,d,result)
            for view in d.views.values():
                for at in view.collection_offsets:self.assertEqual(result.raw[at:at+8]+result.raw[at+16:at+48],d.raw[at:at+8]+d.raw[at+16:at+48])
        self.assertEqual(total,123785)

    def test_counts_ids_exchange_lengths_and_source_scope(self):
        d=Item((BASE/'Item.bin').read_bytes());self.assertEqual((len(d.views['shops'].collections),len(d.views['shops'].records)),(114,1152));self.assertEqual((len(d.views['loot'].collections),len(d.views['loot'].records)),(136,785))
        self.assertEqual(len(d.views['values'].records),11);self.assertEqual(sum(len(v.records)*len(v.fields) for v in d.views.values()),12745)
        for row in d.views['shops'].records:d.views['shops'].validate_record(row)
        self.assertEqual(ItemP0((BASE/'Item_P0.bin').read_bytes()).views,{})
        self.assertEqual(ItemP1((BASE/'Item_P1.bin').read_bytes()).views,{})
