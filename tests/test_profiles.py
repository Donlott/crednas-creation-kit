"""Profile slots, paired histories, raw affiliation links and current usages."""
import copy
import os
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from fw_editor import Profile,Person,Item,DataError,Field,Record,suite_project,load_suite_project,export_suite,messages
from profile_data import connections
from fixture import profile_fixture,item_fixture
from item_index import ItemIndex
from test_reliance import compare


class ProfileTests(unittest.TestCase):
    def setUp(self):self.doc=Profile(profile_fixture())
    def edit(self,section,row,offset,value):
        view=self.doc.views[section];view.set(view.records[row],view.by_offset[offset],value)

    def test_scalar_bytes_and_bounds(self):
        d=self.doc;self.assertEqual(d.build(),d.raw)
        self.edit('profiles',0,0x40,65535);self.edit('profiles',0,0xa8,255);self.edit('order',0,0x22,-32768)
        expected=bytearray(d.raw);r=d.views['profiles'].records[0];struct.pack_into('<H',expected,r.offset+0x40,65535);expected[r.offset+0xa8]=255
        struct.pack_into('<h',expected,d.views['order'].records[0].offset+0x22,-32768)
        self.assertEqual(d.build(),bytes(expected))
        for value in (-1,65536,True):
            with self.assertRaises(DataError):self.edit('profiles',0,0x40,value)
        with self.assertRaises(DataError):self.edit('profiles',0,0xc0,[256])
        with self.assertRaises(DataError):self.edit('profiles',0,0x68,[-32769])

    def test_every_section_reopens_and_preserves_other_values(self):
        changes=[('profiles',0,0x20,['new condition','Unicode ★']),('profiles',0,0x30,'PRF_NEW'),
            ('profiles',0,0x68,[-32768,32767,1449]),('profiles',0,0x78,['MID_First','MID_Second','MID_第三']),
            ('profiles',0,0xf0,['IID_NEW','IID_Other|']),('profiles',0,0xc0,[0,255,2]),('profiles',0,0x138,[]),
            ('affiliations',0,0x38,[['new_condition'],[],['!other']]),('affiliations',0,0x48,''),
            ('expressions',0,0x20,'Expression ★'),('expressions',0,0x3c,4294967295),
            ('limits',0,0x20,[]),('order',0,0x22,-1)]
        for args in changes:self.edit(*args)
        result=Profile(self.doc.build());compare(self,self.doc,result,dict(self.doc.changes))
        view=result.views['profiles'];view.set(view.records[1],view.by_offset[0xf0],['IID_AGAIN'])
        self.assertEqual(Profile(result.build()).views['profiles'].value(view.records[0],view.by_offset[0xf0]),['IID_NEW','IID_Other|'])

    def test_paired_history_validation_and_project_rollback(self):
        d=self.doc;self.edit('profiles',0,0x68,[1])
        with self.assertRaisesRegex(DataError,'same number'):d.build()
        self.edit('profiles',0,0x78,['MID_New']);d.build()
        before=copy.deepcopy(d.changes);bad=d.project();bad['changes'][-1]['value']=['one','two']
        with self.assertRaises(DataError):d.load_project(bad)
        self.assertEqual(d.changes,before)
        invalid=d.project();invalid['changes'][0]['row']=True
        with self.assertRaises(DataError):d.load_project(invalid)
        self.assertEqual(d.changes,before)

    def test_suite_legacy_replacement_and_export_safety(self):
        d=self.doc;item=Item(item_fixture());docs={'Profiles & Affiliations':d,'Items':item}
        self.edit('profiles',0,0xf0,['IID_NEW']);project=suite_project(docs)
        d.changes={};load_suite_project(docs,project);self.assertEqual(d.views['profiles'].value(d.views['profiles'].records[0],d.views['profiles'].by_offset[0xf0]),['IID_NEW'])
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);sources={name:root/'romfs/GameData'/doc.filename for name,doc in docs.items()}
            for name,path in sources.items():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(docs[name].raw)
            with self.assertRaises(DataError):export_suite(docs,sources,root)
            out=root/'mod';export_suite(docs,sources,out);self.assertEqual({p.name for p in (out/'romfs/GameData').iterdir()},{'Profile.bin','Item.bin'})
            self.assertEqual(Profile((out/'romfs/GameData/Profile.bin').read_bytes()).views['profiles'].value(d.views['profiles'].records[0],d.views['profiles'].by_offset[0xf0]),['IID_NEW'])
            export_suite(docs,sources,out);self.assertEqual(len(list((out/'romfs/GameData').glob('*.backup-*'))),2)
        load_suite_project(docs,item.project());self.assertEqual(d.changes,{})
        load_suite_project(docs,d.project());self.assertEqual(item.changes,{})

    def test_direct_links_cycles_and_item_users_reflect_current_values(self):
        d=self.doc;v=d.views['affiliations'];rows=v.records
        found=connections(v,rows[0],{'Profiles & Affiliations':d})
        self.assertEqual(len(found),2);self.assertEqual({x.relation for x in found},{'Incoming affiliation transition','Outgoing affiliation transition'})
        self.edit('affiliations',1,0x48,'');found=connections(v,rows[0],{'Profiles & Affiliations':d});self.assertEqual(len(found),1)
        p=d.views['profiles'];record=Record('PID_TEST',0,0);field=Field('Profile','data',16,0x118)
        value=['PRF_ALPHA'];person=SimpleNamespace(records=[record],by_offset={0x118:field},value=lambda r,f:value[0])
        self.assertTrue(any(x.module=='Characters' for x in connections(p,p.records[0],{'Characters':person})))
        value[0]='PRF_BETA';self.assertFalse(any(x.module=='Characters' for x in connections(p,p.records[0],{'Characters':person})))
        uses=ItemIndex().uses('IID_SYNTHETIC',{'Profiles & Affiliations':d});self.assertEqual(len(uses),1)
        self.assertEqual((uses[0].module,uses[0].record),('Profiles & Affiliations','profiles:0'))
        self.edit('profiles',0,0xf0,['IID_REPLACED']);self.assertEqual(ItemIndex().uses('IID_SYNTHETIC',{'Profiles & Affiliations':d}),[])


BASE=Path(os.environ.get('FW_GAME_DATA','/nonexistent'))
ENGLISH=Path(os.environ.get('FW_MESSAGES','/nonexistent'))
@unittest.skipUnless((BASE/'Profile.bin').is_file(),'Set FW_GAME_DATA for Profile.bin regressions.')
class RealProfileTests(unittest.TestCase):
    def test_all_18445_values_headers_names_and_opaque_bytes(self):
        d=Profile((BASE/'Profile.bin').read_bytes());self.assertEqual(len(d.records),915)
        self.assertEqual(sum(len(v.records)*len(v.fields) for v in d.views.values()),18445);self.assertEqual(d.build(),d.raw)
        updates=[('profiles',10,0x68,[1400,1430]),('profiles',10,0x78,['MID_NEW_ONE','MID_NEW_TWO']),('profiles',10,0xf0,['IID_NEW']),
          ('profiles',10,0xc0,[255,0,1]),('profiles',10,0xa0,'TEST_CODE'),('affiliations',4,0x38,[['routeA'],[],['!routeB']]),
          ('affiliations',4,0x48,'BID_NEW'),('expressions',1,0x20,'TestExpression'),('limits',0,0x20,['test_condition']),('order',2,0x22,-1)]
        for key,index,offset,value in updates:
            view=d.views[key];view.set(view.records[index],view.by_offset[offset],value)
        compare(self,d,Profile(d.build()),dict(d.changes))
        person=Person((BASE/'Person.bin').read_bytes());view=d.views['profiles'];r=next(r for r in view.records if view.names[r.pid]=='PRF_ディートリヒ')
        self.assertTrue(any(x.raw=='PID_ディートリヒ' for x in connections(view,r,{'Characters':person})))

    @unittest.skipUnless((ENGLISH/'Roster.msbt.zst').is_file(),'Set FW_MESSAGES for profile English previews.')
    def test_profile_message_sources_and_independent_conditions(self):
        d=Profile((BASE/'Profile.bin').read_bytes());view=d.views['profiles'];r=next(r for r in view.records if view.names[r.pid]=='PRF_ディートリヒ')
        texts={}
        for name in ('Roster','Clan','ScoutInfo','System_Facility'):texts.update(messages((ENGLISH/(name+'.msbt.zst')).read_bytes()))
        for offset in (0x50,0x58,0x60,0x88,0x90,0x98):self.assertIn(view.value(r,view.by_offset[offset]),texts)
        self.assertEqual(texts['MID_Roster_Position_Dit_001'],'Foreign Swordsman')
        for r in view.records:self.assertEqual(len(view.value(r,view.by_offset[0x68])),len(view.value(r,view.by_offset[0x78])))
