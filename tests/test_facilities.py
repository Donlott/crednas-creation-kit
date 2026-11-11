"""Facility/reward fields and grouped headers, with no runtime rule inference."""
import copy
import os
from pathlib import Path
import struct
import tempfile
import unittest
from fw_editor import (Facility,Reward,RewardP0,RewardP1,FACILITY_TABLES,Profile,DataError,
                       suite_project,load_suite_project,export_suite,messages)
from fixture import facility_fixture,profile_fixture
from test_reliance import compare
from facility_ui import direct_links
from item_index import ItemIndex
from skill_index import SkillIndex


class FacilityTests(unittest.TestCase):
    def setUp(self):self.doc=Facility(facility_fixture())
    def edit(self,key,index,offset,value,doc=None):
        view=(doc or self.doc).views[key];view.set(view.records[index],view.by_offset[offset],value)

    def test_roundtrip_and_exact_scalar_float_bytes(self):
        for kind in FACILITY_TABLES:
            raw=facility_fixture(kind.filename);self.assertEqual(kind(raw).build(),raw)
        d=self.doc;self.edit('cooking',0,0x34,65535);self.edit('theater',0,0x38,0.625)
        expected=bytearray(d.raw);struct.pack_into('<H',expected,d.views['cooking'].records[0].offset+0x34,65535)
        struct.pack_into('<f',expected,d.views['theater'].records[0].offset+0x38,0.625)
        self.assertEqual(d.build(),bytes(expected))
        for value in (-1,65536,True):
            with self.assertRaises(DataError):self.edit('cooking',0,0x34,value)
        for value in (float('nan'),float('inf'),1e100):
            with self.assertRaises(DataError):self.edit('theater',0,0x38,value)

    def test_all_sections_arrays_groups_and_unrelated_bytes(self):
        d=self.doc
        for view in d.views.values():
            field=view.fields[0];value=['Unicode ★'] if field.kind.endswith('[]') else 'Unicode ★' if field.kind in ('string','data') else 1
            view.set(view.records[0],field,value)
        self.edit('baths',0,0x48,['SID_NEW']);self.edit('baths',0,0x58,[255])
        self.edit('training',0,0x78,['JID_NEW']);self.edit('temples',0,0x30,[['condition'],[],['!negated']])
        self.edit('hours',2,0x28,['late_hours']);self.edit('hours',2,0x38,255)
        self.edit('statuses',2,0x20,'STATE_NEW')
        result=Facility(d.build());compare(self,d,result,dict(d.changes))
        self.assertEqual(result.views['statuses'].group_label(result.views['statuses'].records[2]),'statuses_GROUP_B')
        result.views['statuses'].set(result.views['statuses'].records[2],result.views['statuses'].by_offset[0x20],'STATE_AGAIN')
        self.assertEqual(Facility(result.build()).views['statuses'].value(result.views['statuses'].records[1],result.views['statuses'].by_offset[0x20]),'STATE_B')

    def test_collection_counts_empty_groups_and_native_headers_preserved(self):
        d=self.doc;view=d.views['hours'];self.assertEqual(view.collection_names,['hours_GROUP_A','hours_EMPTY','hours_GROUP_B'])
        self.assertEqual([view.locations[r.pid] for r in view.records],[(0,0),(0,1),(2,0)])
        headers={at:d.raw[at:at+48] for at in view.collection_offsets}
        self.edit('hours',1,0x20,'NEW_DEFINITION');self.edit('hours',2,0x38,255)
        result=Facility(d.build())
        for at,raw in headers.items():self.assertEqual(result.raw[at:at+48],raw)
        self.assertEqual([r.pid for r in result.views['hours'].records],[r.pid for r in view.records])

    def test_paired_weights_and_transactional_file_specific_projects(self):
        d=self.doc;self.edit('baths',0,0x48,['SID_NEW'])
        with self.assertRaisesRegex(DataError,'same number'):d.build()
        self.edit('baths',0,0x58,[4]);project=d.project();d.load_project(project)
        before=copy.deepcopy(d.changes);bad=copy.deepcopy(project)
        bad['changes'][-1]['value']=[1,2]
        with self.assertRaises(DataError):d.load_project(bad)
        self.assertEqual(d.changes,before)
        bad=copy.deepcopy(project);bad['changes'][0]['row']=True
        with self.assertRaises(DataError):d.load_project(bad)
        p0=RewardP0(facility_fixture('Reward_P0.bin'));p1=RewardP1(facility_fixture('Reward_P1.bin'))
        self.assertEqual(p0.fingerprint,p1.fingerprint)
        with self.assertRaises(DataError):p1.load_project(p0.project())

    def test_suite_export_guard_backups_and_old_project_replacement(self):
        docs={kind.filename:kind(facility_fixture(kind.filename)) for kind in FACILITY_TABLES}
        docs['Profiles']=Profile(profile_fixture());self.edit('cooking',0,0x34,900,docs['Facility.bin'])
        project=suite_project(docs);docs['Facility.bin'].changes={};load_suite_project(docs,project)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);sources={key:root/'romfs/GameData'/d.filename for key,d in docs.items()}
            for key,path in sources.items():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(docs[key].raw)
            with self.assertRaises(DataError):export_suite(docs,sources,root)
            out=root/'mod';export_suite(docs,sources,out);export_suite(docs,sources,out)
            self.assertEqual(len(list((out/'romfs/GameData').glob('*.bin'))),5)
            self.assertEqual(len(list((out/'romfs/GameData').glob('*.backup-*'))),5)
            self.assertEqual(Facility((out/'romfs/GameData/Facility.bin').read_bytes()).views['cooking'].value(docs['Facility.bin'].views['cooking'].records[0],docs['Facility.bin'].views['cooking'].by_offset[0x34]),900)
        load_suite_project(docs,docs['Profiles'].project());self.assertEqual(docs['Facility.bin'].changes,{})

    def test_live_skill_item_and_dish_links_use_exact_sources(self):
        d=self.doc;profile=Profile(profile_fixture());v=profile.views['profiles'];v.set(v.records[0],v.by_offset[0xd0],['COOK_ALPHA'])
        docs={'Facilities & Rewards':d,'Profiles & Affiliations':profile,'Side':RewardP1(facility_fixture('Reward_P1.bin'))}
        self.assertTrue(any(use.module=='Facilities & Rewards' and use.source=='Facility.bin' for use in SkillIndex().uses('SID_ALPHA',docs)))
        uses=ItemIndex().uses('IID_SYNTHETIC',docs);self.assertEqual({use.source for use in uses},{'Facility.bin','Reward_P1.bin','Profile.bin'})
        links=direct_links(d.views['cooking'],d.views['cooking'].records[0],docs)
        self.assertTrue(any(link[0]=='Profiles & Affiliations' and link[2]=='profiles:0' for link in links))
        v.set(v.records[0],v.by_offset[0xd0],[]);self.assertFalse(any(link[0]=='Profiles & Affiliations' for link in direct_links(d.views['cooking'],d.views['cooking'].records[0],docs)))
        links=direct_links(d.views['questions'],d.views['questions'].records[0],docs)
        self.assertTrue(any(link[2]=='answers:0' and link[4]=='PCHA_ALPHA' for link in links))

    def test_wrong_container_kind_is_rejected(self):
        raw=bytearray(self.doc.raw);schema=self.doc.views['hours'].fields;group=next(g for g in self.doc.groups() if g[0]=='施設営業時間')
        pos=32
        while True:
            pos=raw.find(b'\x01\x12\x25\x20',pos)
            if struct.unpack_from('<Q',raw,pos+24)[0]+32==group[3]:break
            pos+=4
        struct.pack_into('<I',raw,pos+4,1)
        with self.assertRaises(DataError):Facility(bytes(raw))


BASE=Path(os.environ.get('FW_GAME_DATA','/nonexistent'))
ENGLISH=Path(os.environ.get('FW_MESSAGES','/nonexistent'))
@unittest.skipUnless((BASE/'Facility.bin').is_file(),'Set FW_GAME_DATA for facility/reward regressions.')
class RealFacilityTests(unittest.TestCase):
    def test_all_8512_values_and_every_native_header_pointer(self):
        total=0;rows=0
        for kind in FACILITY_TABLES:
            d=kind((BASE/kind.filename).read_bytes());self.assertEqual(d.build(),d.raw)
            rows+=len(d.records);total+=sum(len(v.records)*len(v.fields) for v in d.views.values())
            for view in d.views.values():
                for f in view.fields:
                    if f.kind in ('string','data'):value='TEST_Unicode_★'
                    elif f.kind in ('string[]','data[]'):value=['TEST_Unicode_★','IID_NEW']
                    elif f.kind=='string[,]':value=[['TEST'],[],['!other']]
                    elif f.kind=='u8[]':value=[0,255]
                    elif f.kind=='f32':value=0.625
                    else:value=1
                    if view.key=='baths' and f.offset==0x48:value=['SID_NEW','SID_SECOND']
                    view.set(view.records[0],f,value)
            result=type(d)(d.build());compare(self,d,result,dict(d.changes))
            if kind is Facility:
                for key,groups,count in (('hours',20,21),('statuses',8,51)):
                    v=d.views[key];self.assertEqual(len(v.collection_names),groups);self.assertEqual(len(v.records),count)
                    for at in v.collection_offsets:
                        self.assertEqual(result.raw[at:at+8]+result.raw[at+16:at+48],d.raw[at:at+8]+d.raw[at+16:at+48])
        self.assertEqual((rows,total),(1053,8512))

    @unittest.skipUnless((ENGLISH/'System_Facility.msbt.zst').is_file(),'Set FW_MESSAGES for facility names.')
    def test_english_food_references_and_bath_weight_pairs(self):
        d=Facility((BASE/'Facility.bin').read_bytes());english=messages((ENGLISH/'System_Facility.msbt.zst').read_bytes());v=d.views['cooking']
        for r in v.records:self.assertIn(v.value(r,v.by_offset[0x20]),english)
        baths=d.views['baths']
        for r in baths.records:self.assertEqual(len(baths.value(r,baths.by_offset[0x48])),len(baths.value(r,baths.by_offset[0x58])))
        profile=Profile((BASE/'Profile.bin').read_bytes())
        self.assertTrue(any(x[0]=='Profiles & Affiliations' for x in direct_links(v,v.records[0],{'Facilities & Rewards':d,'Profiles & Affiliations':profile})))
