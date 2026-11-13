"""Appended PIDs, unique creation serials, full native preservation and shared exports."""
from copy import deepcopy
import json
import os
from pathlib import Path
import struct
from types import SimpleNamespace
import tempfile
import unittest
from fw_editor import Person,Job,Item,Learning,DataError,FORMATS,TEXT_TYPES,suite_project,load_suite_project,export_suite
from fixture import person_fixture,job_fixture
from test_item_creation import check_preservation
from test_shops import snapshot
from person_index import uses
from item_index import reference_ids


def values(d,r):return {f.offset:d.value(r,f) for f in d.fields}


class CharacterCreationTests(unittest.TestCase):
    def setUp(self):self.d=Person(person_fixture())

    def test_blank_zero_serial_label_and_original_bytes_preserved(self):
        d=self.d;r=d.create_character('PID_New_新規|||')
        self.assertTrue(d.modified and d.record_changed(r.pid));self.assertFalse(d.changes)
        self.assertEqual(values(d,r),{f.offset:0 if f.kind in FORMATS else '' if f.kind in TEXT_TYPES else [] for f in d.fields})
        result=Person(d.build());self.assertEqual(result.labels[r.pid],result.by_pid[r.pid].offset)
        self.assertEqual(struct.unpack_from('<HH',result.raw,result.by_pid[r.pid].offset+16),(2,1));check_preservation(self,d,result)

    def test_duplicate_current_values_except_serial_and_independent_lists(self):
        d=self.d;src=d.records[0];d.set(src,d.by_offset[0x1c2],-30);d.set(src,d.by_offset[0x78],['IID_CURRENT'])
        r=d.create_character('PID_Copy',src.pid);expected=values(d,src);expected[0x30]=0
        self.assertEqual(values(d,r),expected)
        d.set(r,d.by_offset[0x78],['IID_COPY']);r2=d.create_character('PID_Copy2',r.pid,serial=3)
        expected=values(d,r);expected[0x30]=3;self.assertEqual(values(d,r2),expected)
        self.assertEqual(d.value(src,d.by_offset[0x78]),['IID_CURRENT'])
        outside=d.value(r,d.by_offset[0x78]);outside.append('mutation');self.assertEqual(d.value(r,d.by_offset[0x78]),['IID_COPY'])
        result=Person(d.build());self.assertEqual(values(result,result.by_pid[r2.pid]),values(d,r2))

    def test_serial_uniqueness_zero_reuse_range_and_immutable_slots(self):
        d=self.d;originals=[(r.pid,d.value(r,d.by_offset[0x30])) for r in d.records]
        d.create_character('PID_A',serial=3);d.create_character('PID_ZeroA');d.create_character('PID_ZeroB')
        self.assertNotIn(3,d.available_serials());before=d.project()
        for serial in (1,2,3,-1,256,True,'4'):
            with self.assertRaises(DataError):d.create_character('PID_Bad',serial=serial)
            self.assertEqual(d.project(),before)
        for r in d.records:
            with self.assertRaises(DataError):d.set(r,d.by_offset[0x30],4)
        result=Person(d.build())
        self.assertEqual([(r.pid,result.value(result.by_pid[r.pid],result.by_offset[0x30])) for r in d._source_records],originals)
        self.assertEqual(result.value(result.by_pid['PID_A'],result.by_offset[0x30]),3)
        d.remove_character('PID_A');self.assertIn(3,d.available_serials())

    def test_references_to_source_self_new_cycles_roundtrip_literally(self):
        d=self.d;a=d.create_character('PID_A');b=d.create_character('PID_B')
        for r,off,key in [(a,0x268,b.pid),(b,0x2b0,a.pid),(a,0x278,a.pid),(d.records[0],0x268,a.pid)]:d.set(r,d.by_offset[off],key)
        r=d.create_character('PID_Copy',a.pid);self.assertEqual(d.value(r,d.by_offset[0x278]),a.pid)
        result=Person(d.build())
        for row in d.records:self.assertEqual(values(result,result.by_pid[row.pid]),values(d,row))
        p=json.loads(json.dumps(d.project()));p['new_characters'].reverse();other=Person(d.raw);other.load_project(p)
        self.assertEqual(other.value(other.by_pid[a.pid],other.by_offset[0x268]),b.pid)

    def test_invalid_ids_definitions_and_failed_creations_are_transactional(self):
        d=self.d;d.create_character('PID_Before',serial=3);before=d.project()
        for key in ('PID_','PID_ a','PID_A::0','PID_A,B','PID_A!B','PID_A&B','PID_A\0','IID_A',None,d.records[0].pid,'PID_Before'):
            with self.assertRaises(DataError):d.create_character(key)
            self.assertEqual(d.project(),before)
        bad=deepcopy(d.new_characters['PID_Before']);bad[0x1c2]=32768;bad[0x30]=4
        with self.assertRaises(DataError):d.create_character('PID_Invalid',values=bad,serial=4)
        with self.assertRaises(DataError):d.create_character('PID_MissingCopy','PID_Absent')
        with self.assertRaises(DataError):d.create_character('PID_NoFields',values={})
        self.assertEqual(d.project(),before)

    def test_v3_project_source_values_serial_guards_and_legacy_replacement(self):
        d=self.d;old=d.project();d.create_character('PID_New',d.records[0].pid,serial=3);before=d.project()
        self.assertEqual(before['format'],'fw-character-edits-v3');other=Person(d.raw)
        load_suite_project({'Characters':other},json.loads(json.dumps(before)));self.assertEqual(other.build(),d.build())
        for mode in ('source','hash','offset','range','occupied','duplicate','native_serial','new_serial','downgrade'):
            bad=deepcopy(before)
            if mode=='source':bad['source_file']='Job.bin'
            elif mode=='hash':bad['source_sha256']='wrong'
            elif mode=='offset':del bad['new_characters'][0]['values']['32']
            elif mode=='range':bad['new_characters'][0]['values']['48']=256
            elif mode=='occupied':bad['new_characters'][0]['values']['48']=1
            elif mode=='duplicate':bad['new_characters'].append(deepcopy(bad['new_characters'][0]))
            elif mode in ('native_serial','new_serial'):bad['changes'].append({'pid':d.records[0].pid if mode=='native_serial' else 'PID_New','offset':0x30,'value':4})
            else:bad['format']='fw-character-edits-v2'
            with self.assertRaises(DataError):d.load_project(bad)
            self.assertEqual(d.project(),before)
        d.load_project(old);self.assertFalse(d.modified);self.assertEqual(d.build(),d.raw)

    def test_removal_snapshot_reindex_reset_and_header_tag_capacity(self):
        d=self.d;ids=[(r.pid,r.index) for r in d.records];d.create_character('PID_A',serial=3);d.create_character('PID_B',serial=4)
        state=d.snapshot_edits();d.remove_character('PID_A');self.assertEqual(d.by_pid['PID_B'].index,2)
        with self.assertRaises(DataError):d.remove_character(d.records[0].pid)
        d.restore_edits(state);self.assertEqual(d.by_pid['PID_B'].index,3)
        self.assertEqual([(r.pid,r.index) for r in d.records[:2]],ids)
        raw=bytearray(d.raw);struct.pack_into('<H',raw,d._source_records[-1].offset+22,65535);full=Person(bytes(raw))
        with self.assertRaises(DataError):full.create_character('PID_NoTag')
        self.assertFalse(full.modified)

    def test_current_pid_choosers_and_exact_nested_reference_index(self):
        d=self.d;r=d.create_character('PID_New');j=Job(job_fixture())
        d.set(d.records[0],d.by_offset[0x268],r.pid);j.set(j.records[0],j.by_offset[0x1b8],[['!PID_New','PID_NewLonger']])
        docs={'Characters':d,'Classes':j};found=uses(r.pid,docs)
        self.assertEqual(len(found),2);self.assertEqual(found[0].module,'Characters');self.assertEqual(found[1].path,'[0][0]')
        app=SimpleNamespace(catalog={},documents=docs);self.assertIn(r.pid,reference_ids(app,'PID_'))
        d.remove_character(r.pid);self.assertNotIn(r.pid,reference_ids(app,'PID_'))

    def test_exports_manifest_no_backups_reedit_source_guard_and_no_native_deletion(self):
        d=self.d;d.create_character('PID_Export',d.records[0].pid,serial=3)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'game/romfs/GameData/Person.bin';source.parent.mkdir(parents=True);source.write_bytes(d.raw)
            export_suite({'Characters':d},{'Characters':source},root/'mod');target=root/'mod/romfs/GameData/Person.bin'
            result=Person(target.read_bytes());result.create_character('PID_Reedit',serial=4)
            self.assertEqual(len(Person(result.build()).records),4)
            manifest=json.loads((root/'mod/suite-edits.json').read_text());self.assertEqual(manifest['documents']['Person.bin']['format'],'fw-character-edits-v3')
            export_suite({'Characters':d},{'Characters':source},root/'mod');self.assertEqual(len(list(target.parent.glob('*.backup-*'))),0)
            self.assertEqual(source.read_bytes(),d.raw)
            with self.assertRaises(DataError):export_suite({'Characters':d},{'Characters':source},root/'game')


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent/fw-game-data'))
@unittest.skipUnless((DATA/'Person.bin').is_file(),'Set FW_GAME_DATA for native character creation tests.')
class RealCharacterCreationTests(unittest.TestCase):
    def test_all_418750_original_primary_aux_values_headers_bytes_and_slots(self):
        d=Person((DATA/'Person.bin').read_bytes());before=snapshot(d);self.assertEqual(len(before),418750)
        d.create_character('PID_Blank');d.create_character('PID_Copy','PID_ディートリヒ',serial=42)
        result=Person(d.build());after=snapshot(result);self.assertEqual(len(result.records),2925)
        self.assertTrue(all(after[k]==v for k,v in before.items()));check_preservation(self,d,result)

    def test_all_143_new_typed_fields_roundtrip_and_positive_serial(self):
        d=Person((DATA/'Person.bin').read_bytes());r=d.create_character('PID_AllFields',serial=42)
        for f in d.fields:
            if f.offset==0x30:continue
            v=(-1 if f.kind.startswith('s') else 1) if f.kind in FORMATS else ['Test_'+str(f.offset)] if f.kind.endswith('[]') else 'Test_'+str(f.offset)
            d.set(r,f,v)
        result=Person(d.build());self.assertEqual(values(result,result.by_pid[r.pid]),values(d,r))
        self.assertEqual(d.raw,(DATA/'Person.bin').read_bytes())

    def test_shared_difficulty_auto_gear_v2_v3_projects_and_cross_file_rollback(self):
        d=Person((DATA/'Person.bin').read_bytes());gear=d.views['auto_gear'];row=gear.records[0]
        gear.set(row,gear.by_offset[0x30],['IID_TEST']);old=d.project();self.assertEqual(old['format'],'fw-character-edits-v2')
        new=d.create_character('PID_NewShared','PID_ディートリヒ',serial=42);gear.set(row,gear.by_offset[0x20],new.pid)
        diff=d.views['difficulty'];diff.set(diff.records[0],diff.by_offset[0x40],[['IID_TEST'],[]])
        other=Person(d.raw);other.load_project(json.loads(json.dumps(d.project())));result=Person(other.build())
        self.assertEqual(snapshot(result)[(row.pid,0x20)],new.pid);self.assertEqual(snapshot(result)[(diff.records[0].pid,0x40)],[['IID_TEST'],[]])
        self.assertTrue(any(u.module=='Progression & Difficulty' for u in uses(new.pid,{'Characters':other})))
        d.load_project(old);self.assertFalse(d.new_characters);self.assertEqual(d.project(),old)
        j=Job((DATA/'Job.bin').read_bytes());j.create_class('JID_NewShared');docs={'Characters':other,'Classes':j};before=suite_project(docs)
        broken=deepcopy(before);broken['documents']['Job.bin']['new_classes'][0]['values']['72']='JID_Missing'
        with self.assertRaises(DataError):load_suite_project(docs,broken)
        self.assertEqual(suite_project(docs),before)

    def test_character_class_item_learning_definitions_and_deployment_combined(self):
        from fw_editor import read_editable_tables
        docs,sources=read_editable_tables(DATA);p=docs['Characters'];new=p.create_character('PID_NewIntegrated','PID_ディートリヒ',serial=42)
        j=docs['Classes'];j.create_class('JID_NewIntegrated',j.records[0].pid);p.set(new,p.by_offset[0x38],'JID_NewIntegrated')
        i=next(d for d in docs.values() if d.filename=='Item.bin');i.create_item('IID_NewIntegrated');p.set(new,p.by_offset[0x78],['IID_NewIntegrated'])
        g=docs['Learning tables'];g.create_list('LID_NewIntegrated');p.set(new,p.by_offset[0x88],['LID_NewIntegrated'])
        battle=next(d for d in docs.values() if d.prefix=='DEPLOY_' and d.views['units'].records);view=battle.views['units'];view.set(view.records[0],view.by_offset[0x20],new.pid)
        self.assertTrue(any(u.module=='Battle deployment' for u in uses(new.pid,docs)))
        project=json.loads(json.dumps(suite_project(docs)));other,_=read_editable_tables(DATA);load_suite_project(other,project)
        self.assertEqual(suite_project(other),project)
        with tempfile.TemporaryDirectory() as temp:
            export_suite(other,sources,Path(temp)/'mod');self.assertEqual(len(list((Path(temp)/'mod/romfs/GameData').rglob('*.bin'))),204)
            result=Person((Path(temp)/'mod/romfs/GameData/Person.bin').read_bytes());self.assertEqual(values(result,result.by_pid[new.pid]),values(p,new))
