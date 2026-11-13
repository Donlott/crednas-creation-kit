"""Appended classes, direct pointers, projects and opaque group preservation."""
from copy import deepcopy
import json
import os
from pathlib import Path
import struct
from types import SimpleNamespace
import tempfile
import unittest
from fw_editor import Job,Person,Learning,Item,DataError,FORMATS,TEXT_TYPES,LIST_TYPES,suite_project,load_suite_project,export_suite
from fixture import job_fixture,person_fixture
from test_item_creation import check_preservation
from class_index import uses
from item_index import reference_ids


def values(d,r):return {f.offset:d.value(r,f) for f in d.fields}


class ClassCreationTests(unittest.TestCase):
    def setUp(self):self.d=Job(job_fixture())

    def test_blank_defaults_labels_header_and_original_bytes(self):
        d=self.d;r=d.create_class('JID_New_新規|||');self.assertTrue(d.modified and d.record_changed(r.pid))
        self.assertEqual(values(d,r),{f.offset:0 if f.kind in FORMATS else '' if f.kind in TEXT_TYPES else [] for f in d.fields})
        result=Job(d.build());self.assertEqual(result.labels[r.pid],result.by_pid[r.pid].offset)
        self.assertEqual(struct.unpack_from('<HH',result.raw,result.by_pid[r.pid].offset+16),(2,1));check_preservation(self,d,result)

    def test_current_copy_nested_arrays_are_independent_and_links_retained(self):
        d=self.d;a=d.records[0];d.set(a,d.by_offset[0x120],-40);d.set(a,d.by_offset[0x1b8],[['custom'],[]])
        r=d.create_class('JID_Copy',a.pid);self.assertEqual(values(d,r),values(d,a))
        d.set(r,d.by_offset[0x1b8],[['copy']]);d.create_class('JID_Copy2',r.pid)
        self.assertEqual(d.value(a,d.by_offset[0x1b8]),[['custom'],[]])
        v=d.value(r,d.by_offset[0x1b8]);v[0].append('mutated')
        self.assertEqual(d.value(r,d.by_offset[0x1b8]),[['copy']])
        result=Job(d.build());self.assertEqual(values(result,result.by_pid['JID_Copy2']),values(d,r))

    def test_native_new_self_cycle_pointers_and_null_relocations(self):
        d=self.d;a=d.create_class('JID_A');b=d.create_class('JID_B');old=d.records[0]
        edits=[(old,0x50,a.pid),(a,0x48,old.pid),(a,0x50,b.pid),(a,0x58,a.pid),(b,0x48,a.pid)]
        for r,off,target in edits:d.set(r,d.by_offset[off],target)
        result=Job(d.build())
        for r,off,target in edits:
            row=result.by_pid[r.pid];self.assertEqual(result.original(row,result.by_offset[off]),target)
            self.assertEqual(struct.unpack_from('<Q',result.raw,row.offset+off)[0],result.by_pid[target].offset-32)
            self.assertIn(row.offset+off-32,result.pointers)
        result.set(result.by_pid[a.pid],result.by_offset[0x58],'');again=Job(result.build())
        self.assertNotIn(again.by_pid[a.pid].offset+0x58-32,again.pointers)
        self.assertEqual(again.original(again.by_pid[a.pid],again.by_offset[0x58]),'')

    def test_v2_baseline_forward_cycles_load_before_links(self):
        d=self.d;a=d.create_class('JID_A');b=d.create_class('JID_B')
        d.set(a,d.by_offset[0x50],b.pid);d.set(b,d.by_offset[0x48],a.pid)
        # Bake current links into the definition baselines, as copies can do.
        for r in (a,b):d._seed_values(r.pid,values(d,r))
        project=json.loads(json.dumps(d.project()));self.assertEqual(project['format'],'fw-class-edits-v2')
        project['new_classes'].reverse();other=Job(d.raw);load_suite_project({'Classes':other},project)
        self.assertEqual(other.value(other.by_pid[a.pid],other.by_offset[0x50]),b.pid)
        self.assertEqual(other.value(other.by_pid[b.pid],other.by_offset[0x48]),a.pid)
        self.assertTrue(other.build())

    def test_invalid_ids_fields_and_projects_roll_back(self):
        d=self.d;d.create_class('JID_Before');before=d.project()
        for key in ('JID_','JID_ spaces','JID_A::0','JID_A,B','JID_A!B','JID_A&B','JID_A\0',None,'IID_A',d.records[0].pid,'JID_Before'):
            with self.assertRaises(DataError):d.create_class(key)
            self.assertEqual(d.project(),before)
        for mode in ('source','hash','field','value','target','downgrade','duplicate'):
            bad=deepcopy(before)
            if mode=='source':bad['source_file']='Person.bin'
            elif mode=='hash':bad['source_sha256']='wrong'
            elif mode=='field':del bad['new_classes'][0]['values']['32']
            elif mode=='value':bad['new_classes'][0]['values']['288']=32768
            elif mode=='target':bad['new_classes'][0]['values']['72']='JID_Unknown'
            elif mode=='downgrade':bad['format']='fw-class-edits-v1'
            else:bad['new_classes'].append(deepcopy(bad['new_classes'][0]))
            with self.assertRaises(DataError):d.load_project(bad)
            self.assertEqual(d.project(),before)

    def test_remove_guards_reindex_snapshot_legacy_and_tag_capacity(self):
        d=self.d;legacy=d.project();a=d.create_class('JID_A');b=d.create_class('JID_B');state=d.snapshot_edits()
        d.set(b,d.by_offset[0x48],a.pid)
        with self.assertRaises(DataError):d.remove_class(a.pid)
        with self.assertRaises(DataError):d.remove_class(d.records[0].pid)
        d.set(b,d.by_offset[0x48],'');d.remove_class(a.pid);self.assertEqual(d.by_pid[b.pid].index,2)
        d.restore_edits(state);self.assertEqual(d.by_pid[b.pid].index,3)
        d.load_project(legacy);self.assertEqual(d.build(),d.raw);self.assertFalse(d.modified)
        raw=bytearray(d.raw);struct.pack_into('<H',raw,d.records[-1].offset+22,65535);full=Job(bytes(raw))
        with self.assertRaises(DataError):full.create_class('JID_NoTag')

    def test_current_reference_index_and_chooser_exact_matches(self):
        d=self.d;r=d.create_class('JID_New');d.create_class('JID_NewLonger');p=Person(person_fixture())
        p.set(p.records[0],p.by_offset[0x278],r.pid)
        d.set(d.records[0],d.by_offset[0x1b8],[['!JID_New','JID_NewLonger']])
        docs={'Classes':d,'Characters':p};found=uses(r.pid,docs)
        self.assertEqual(len(found),2);self.assertEqual(found[0].module,'Characters')
        self.assertEqual(found[1].path,'[0][0]')
        app=SimpleNamespace(catalog={},documents=docs);self.assertIn(r.pid,reference_ids(app,'JID_'))
        d.remove_class(r.pid);self.assertNotIn(r.pid,reference_ids(app,'JID_'))

    def test_export_sources_manifest_no_backups_and_reedit(self):
        d=self.d;d.create_class('JID_Export',d.records[0].pid)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'game/romfs/GameData/Job.bin';source.parent.mkdir(parents=True);source.write_bytes(d.raw)
            docs={'Classes':d};export_suite(docs,{'Classes':source},root/'mod')
            target=root/'mod/romfs/GameData/Job.bin';result=Job(target.read_bytes());result.create_class('JID_Reedit')
            self.assertEqual(len(Job(result.build()).records),4)
            manifest=json.loads((root/'mod/suite-edits.json').read_text())
            self.assertEqual(manifest['documents']['Job.bin']['format'],'fw-class-edits-v2')
            export_suite(docs,{'Classes':source},root/'mod');self.assertEqual(len(list(target.parent.glob('*.backup-*'))),0)
            self.assertEqual(source.read_bytes(),d.raw)
            with self.assertRaises(DataError):export_suite(docs,{'Classes':source},root/'game')


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent/fw-game-data'))
@unittest.skipUnless((DATA/'Job.bin').is_file(),'Set FW_GAME_DATA for native class creation tests.')
class RealClassCreationTests(unittest.TestCase):
    def test_all_18358_original_values_auxiliary_bytes_and_indexes_preserved(self):
        d=Job((DATA/'Job.bin').read_bytes());before={(r.pid,f.offset):d.value(r,f) for r in d.records for f in d.fields}
        self.assertEqual(len(before),18358);d.create_class('JID_Blank');d.create_class('JID_Copy',d.records[1].pid)
        result=Job(d.build());self.assertEqual(len(result.records),139)
        for (key,off),value in before.items():self.assertEqual(result.value(result.by_pid[key],result.by_offset[off]),value)
        check_preservation(self,d,result)

    def test_all_134_new_typed_fields_roundtrip(self):
        d=Job((DATA/'Job.bin').read_bytes());r=d.create_class('JID_AllFields')
        for f in d.fields:
            value=(-1 if f.kind.startswith('s') else 1) if f.kind in FORMATS else d.records[0].pid if f.kind=='ref' else [['condition'],[]] if '[,]' in f.kind else ['test'] if f.kind in LIST_TYPES else 'Test_'+str(f.offset)
            d.set(r,f,value)
        result=Job(d.build());self.assertEqual(values(result,result.by_pid[r.pid]),values(d,r))
        self.assertEqual(d.raw,(DATA/'Job.bin').read_bytes())

    def test_character_glid_new_item_new_list_and_class_project_together(self):
        j=Job((DATA/'Job.bin').read_bytes());r=j.create_class('JID_NewIntegrated',j.records[0].pid)
        p=Person((DATA/'Person.bin').read_bytes());p.set(p.by_pid['PID_ディートリヒ'],p.by_offset[0x38],r.pid)
        g=Learning((DATA/'Growth.bin').read_bytes());g.create_list('LID_NewIntegrated')
        v=g.progression;row=next(r for r in v.records if v.value(r,v.by_offset[0x20])==0);v.set(row,v.fields[1],r.pid.removeprefix('JID_'))
        i=Item((DATA/'Item.bin').read_bytes());i.create_item('IID_NewIntegrated')
        docs={'Classes':j,'Characters':p,'Learning tables':g,'Items':i};project=json.loads(json.dumps(suite_project(docs)))
        other={k:type(d)(d.raw) for k,d in docs.items()};load_suite_project(other,project);self.assertEqual(suite_project(other),project)
        found=uses(r.pid,other);self.assertTrue(any(u.module=='Characters' for u in found));self.assertTrue(any(u.module=='GLID progression' for u in found))
        for d in other.values():self.assertTrue(d.build())
        old=deepcopy(project);old['documents']['Job.bin']['new_classes'][0]['values']['72']='JID_Missing'
        with self.assertRaises(DataError):load_suite_project(other,old)
        self.assertEqual(suite_project(other),project)
