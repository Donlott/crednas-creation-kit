"""Shared Person/Growth edits, auxiliary namespace guards and native structures."""
import copy
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from fw_editor import Person,Learning,GrowthSide,ExpandedView,DataError,Binary,read_editable_tables,suite_project,load_suite_project,export_suite
from fixture import expanded_fixture
from test_shops import verify as verify_shared
from item_index import ItemIndex
from skill_index import SkillIndex
from expanded_ui import connections


def snapshot(doc):
    views=[doc,*doc.views.values()]
    if getattr(doc,'progression',None):views.append(doc.progression)
    return {(r.pid,f.offset):view.original(r,f) for view in views for r in view.records for f in view.fields}


def verify(test,doc,result):
    with patch('test_shops.snapshot',snapshot):verify_shared(test,doc,result)


class ExpandedTests(unittest.TestCase):
    def setUp(self):
        self.person=Person(expanded_fixture('Person.bin'));self.growth=Learning(expanded_fixture('Growth.bin'))
        self.side=GrowthSide(expanded_fixture('Growth_P0.bin'))
    def test_unchanged_sources_empty_curves_and_one_shared_owner(self):
        self.assertEqual(len(self.growth.views),10);self.assertEqual(len(self.person.views),2)
        for owner in (self.person,self.growth,self.side):
            self.assertEqual(owner.build(),owner.raw)
            for view in owner.views.values():self.assertIs(view.changes,owner.changes)
        curve=self.growth.views['exp_curve'];self.assertEqual(curve.rows_by_table['exp_curve:1'],[])

    def test_primary_serial_locked_but_difficulty_barrier_at_same_offset_editable(self):
        p=self.person;view=p.views['difficulty'];r=view.records[0]
        with self.assertRaises(DataError):p.set(p.records[0],p.by_offset[0x30],3)
        p.set(p.records[0],p.by_offset[0x1c2],123)
        view.set(r,view.by_offset[0x30],['IID_NEW|||']);project=p.project()
        self.assertEqual(project['format'],'fw-character-edits-v2')
        result=Person(p.build());verify(self,p,result)
        restored=Person(p.raw);restored.load_project(project);self.assertEqual(restored.changes,p.changes)
        self.assertEqual(result.original(result.records[0],result.by_offset[0x30]),p.original(p.records[0],p.by_offset[0x30]))

    def test_lid_glid_and_expanded_growth_edits_save_together(self):
        g=self.growth;lid=g.records[0];glid=g.progression.records[0]
        g.set(lid,g.by_offset[0x20],55);g.progression.set(glid,g.progression.by_offset[0x28],'SyntheticClass')
        legacy=g.project();self.assertEqual(legacy['format'],'fw-growth-edits-v1')
        v=g.views['exp_curve'];v.set(v.records[0],v.by_offset[0x22],65535)
        project=g.project();self.assertEqual(project['format'],'fw-growth-edits-v2');self.assertEqual(len(project['changes']),2);self.assertEqual(len(project['aux_changes']),1)
        result=Learning(g.build());verify(self,g,result);self.assertEqual(snapshot(result),{**snapshot(g),**g.changes})
        restored=Learning(g.raw);restored.load_project(project);self.assertEqual(restored.changes,g.changes)
        g.load_project(legacy);self.assertFalse(any(pid.startswith('exp_curve:') for pid,_ in g.changes));self.assertEqual(len(g.changes),2)

    def test_every_auxiliary_kind_nested_skill_rows_and_independent_quantities(self):
        for owner in (self.person,self.growth,self.side):
            for view in owner.views.values():
                row=view.records[0]
                for f in view.fields:
                    value=-128 if f.kind=='s8' else 65535 if f.kind=='u16' else 255 if f.kind=='u8' else 'REFERENCE_★|||' if f.kind=='data' else ['REFERENCE_★|||'] if f.kind in ('data[]','string[]') else [[],['SID_NEW','SID_OTHER']] if f.kind=='data[,]' else [0,255]
                    view.set(row,f,value)
            result=owner.reparse(owner.build());verify(self,owner,result);self.assertEqual(snapshot(result),{**snapshot(owner),**owner.changes})
        supply=self.side.views['part2_items'];row=supply.records[0]
        for items,amounts in [(['IID_ONE','IID_TWO'],[1]),(['IID_ONE'],[]),([],[1,2])]:
            supply.set(row,supply.by_offset[0x38],items);supply.set(row,supply.by_offset[0x48],amounts);self.side.build()
        for f,value in [(self.growth.views['exp_modifiers'].by_offset[0x20],-129),(self.side.views['part2_items'].by_offset[0x48],[256])]:
            view=self.growth.views['exp_modifiers'] if f.kind=='s8' else self.side.views['part2_items']
            with self.assertRaises(DataError):view.set(view.records[0],f,value)

    def test_project_guards_legacy_replacement_and_atomic_suite_rollback(self):
        p,g,s=self.person,self.growth,self.side
        p.set(p.records[0],p.by_offset[0x1c2],101);legacy=p.project()
        for owner in (p,g,s):
            view=next(iter(owner.views.values()));f=view.fields[0];r=view.records[0]
            view.set(r,f,['SID_NEW'] if f.kind=='data[]' else 99)
        docs={'Characters':p,'Learning tables':g,'Side':s};before={k:copy.deepcopy(d.changes) for k,d in docs.items()}
        bad=suite_project(docs);bad['documents']['Growth_P0.bin']['source_sha256']='wrong'
        with self.assertRaises(DataError):load_suite_project(docs,bad)
        self.assertEqual({k:d.changes for k,d in docs.items()},before)
        for owner in (p,g,s):
            bad=copy.deepcopy(owner.project());bad['source_file']='Other.bin'
            with self.assertRaises(DataError):owner.load_project(bad)
            self.assertEqual(owner.changes,before[next(k for k,d in docs.items() if d is owner)])
        load_suite_project(docs,legacy);self.assertEqual(p.changes,{(p.records[0].pid,0x1c2):101});self.assertFalse(g.changes);self.assertFalse(s.changes)

    def test_reset_scope_retains_primary_and_other_auxiliary_changes(self):
        p=self.person;p.set(p.records[0],p.by_offset[0x1c2],77)
        d=p.views['difficulty'];a=p.views['auto_gear'];d.set(d.records[0],d.by_offset[0x20],['SID_NEW']);a.set(a.records[0],a.by_offset[0x30],['IID_NEW'])
        d.reset_table(d.collections[0].pid);self.assertEqual(len(p.changes),2)
        g=self.growth;g.set(g.records[0],g.by_offset[0x20],9);v=g.views['exp_curve']
        v.set(v.records[0],v.by_offset[0x22],999);v.reset_table(v.collections[0].pid);self.assertEqual(len(g.changes),1)

    def test_live_item_skill_and_experience_links(self):
        p,g=self.person,self.growth;d=p.views['difficulty'];r=d.records[0];docs={'Characters':p,'Learning tables':g}
        self.assertTrue(any(u.module=='Progression & Difficulty' and u.source=='Person.bin' for u in SkillIndex().uses('SID_SYNTHETIC',docs)))
        d.set(r,d.by_offset[0x20],['SID_NEW']);d.set(r,d.by_offset[0x40],[['SID_NEW']]);d.set(r,d.by_offset[0x30],['IID_NEW|||'])
        self.assertFalse(any(u.record==r.pid for u in SkillIndex().uses('SID_SYNTHETIC',docs)))
        self.assertEqual(ItemIndex().uses('IID_NEW|||',docs)[0].module,'Progression & Difficulty')
        curve=g.views['exp_curve'];links=connections(curve,curve.collections[0],docs)
        self.assertTrue(any(target[0]=='Progression & Difficulty' and target[3]=='References this table' for target in links))

    def test_three_file_exports_source_protection_schema_without_backups(self):
        docs={'Characters':self.person,'Learning tables':self.growth,'Side':self.side}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);base=root/'romfs/GameData';base.mkdir(parents=True);sources={}
            for key,owner in docs.items():sources[key]=base/owner.filename;sources[key].write_bytes(owner.raw)
            with self.assertRaises(DataError):export_suite(docs,sources,root)
            target=root/'mod';export_suite(docs,sources,target)
            self.assertEqual({p.name for p in (target/'romfs/GameData').glob('*.bin')},{'Person.bin','Growth.bin','Growth_P0.bin'})
            export_suite(docs,sources,target);self.assertEqual(len(list((target/'romfs/GameData').glob('*.backup-*'))),0)
            loaded,_=read_editable_tables(base);self.assertEqual(len(loaded),3)
        raw=bytearray(self.side.raw);group=next(g for g in Binary(raw).groups() if g[0]=='2部支給アイテム')
        struct.pack_into('<I',raw,group[3]+28,0x24)
        with self.assertRaises(DataError):GrowthSide(bytes(raw))


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent/fw-data'))
@unittest.skipUnless((DATA/'Growth_P0.bin').is_file(),'Set FW_GAME_DATA for private expanded-table regressions.')
class RealExpandedTests(unittest.TestCase):
    def test_all_sections_and_all_values_with_joint_primary_edits(self):
        owners=[Person((DATA/'Person.bin').read_bytes()),Learning((DATA/'Growth.bin').read_bytes()),GrowthSide((DATA/'Growth_P0.bin').read_bytes())]
        self.assertEqual(sum(len(d.views) for d in owners),13);self.assertEqual(sum(len(v.records) for d in owners for v in d.views.values()),510)
        self.assertEqual(sum(len(v.records)*len(v.fields) for d in owners for v in d.views.values()),2397)
        for owner in owners:
            self.assertEqual(owner.build(),owner.raw)
            if isinstance(owner,Person):owner.set(owner.records[1],owner.by_offset[0x1c2],101)
            elif isinstance(owner,Learning):owner.set(owner.records[0],owner.by_offset[0x20],66);owner.progression.set(owner.progression.records[0],owner.progression.by_offset[0x28],'SyntheticClass')
            for view in owner.views.values():
                row=view.records[0]
                for f in view.fields:
                    value=-7 if f.kind=='s8' else 123 if f.kind in ('u8','u16') else 'SYNTHETIC_REFERENCE' if f.kind=='data' else ['SYNTHETIC_REFERENCE'] if f.kind in ('data[]','string[]') else [['SID_SYNTHETIC'],[]] if f.kind=='data[,]' else [1,2]
                    view.set(row,f,value)
            result=owner.reparse(owner.build());verify(self,owner,result);self.assertEqual(snapshot(result),{**snapshot(owner),**owner.changes})
    def test_current_character_difficulty_links_and_native_supply_shapes(self):
        docs,_=read_editable_tables(DATA);p=docs['Characters'];v=p.views['difficulty']
        collection=next(c for c in v.collections if any(p.value(r,p.by_offset[0x138])==v.names[c.pid] for r in p.records))
        self.assertTrue(any(x[0]=='Characters' for x in connections(v,collection,docs)))
        for filename,kind in [('Growth.bin',Learning),('Growth_P0.bin',GrowthSide)]:
            d=kind((DATA/filename).read_bytes());view=d.views['part2_items']
            self.assertTrue(any(len(view.value(r,view.by_offset[0x38]))!=len(view.value(r,view.by_offset[0x48])) for r in view.records))
