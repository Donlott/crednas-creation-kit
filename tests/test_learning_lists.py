"""New indexed LID containers, independent copies and shared exports."""
from copy import deepcopy
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest

from fw_editor import Learning,Person,Job,DataError,suite_project,load_suite_project,export_suite
from skill_index import SkillIndex
from fixture import growth_fixture,job_fixture
from test_learning_entries import emptied,snapshot


def check_original_bytes(test,source,result):
    """Remove parsed NEW objects and compare every original opaque byte/target."""
    native_rows={r.pid for rows in source._source_rows.values() for r in rows}
    native_tables={r.pid for r in source._source_collections}
    ranges=sorted([(r.offset-32,48) for r in result.collections if r.pid not in native_tables]+
                  [(r.offset-32,result.stride) for r in result.records if r.pid not in native_rows])
    def moved(offset):
        for at,size in ranges:
            if at<=offset:offset+=size
        return offset
    for key,at in source.labels.items():test.assertEqual(result.labels[key],moved(at-32)+32)
    for at in source.pointers:
        a=struct.unpack_from('<Q',source.raw,at+32)[0];b=struct.unpack_from('<Q',result.raw,moved(at)+32)[0]
        if any(at==r.offset and not source._source_rows[r.pid] and source.added_entries.get(r.pid) for r in source._source_collections):continue
        if a>=source.pool:test.assertEqual(source.string(a),result.string(b))
        else:test.assertEqual(moved(a),b)
    old=bytearray(source.raw[32:32+source.size]);current=bytearray(result.raw[32:32+result.size])
    for at,size in reversed(ranges):del current[at:at+size]
    current=current[:source.size]
    for at in source.pointers:old[at:at+8]=current[at:at+8]=b'\0'*8
    for table in source._source_collections:
        if source.added_entries.get(table.pid):
            at=table.offset-32+18;old[at:at+2]=current[at:at+2]=b'\0'*2
            if not source._source_rows[table.pid]:
                at=table.offset;old[at:at+8]=current[at:at+8]=b'\0'*8
    test.assertEqual(old,current)


class LearningListTests(unittest.TestCase):
    def setUp(self):self.doc=Learning(growth_fixture())

    def test_blank_list_is_indexed_and_counts_as_an_edit(self):
        d=self.doc;table=d.create_list('LID_Custom_新規')
        self.assertTrue(d.modified);self.assertEqual(d.added_list_count,1);self.assertEqual(d.added_count,0)
        self.assertTrue(d.table_changed(table.pid));self.assertFalse(d.changes)
        self.assertEqual(table.index,2);self.assertFalse(d.rows_by_table[table.pid])
        result=Learning(d.build());self.assertEqual(len(result.collections),3)
        r=result.tables_by_id[table.pid];self.assertEqual(result.labels[table.pid],r.offset)
        self.assertEqual(struct.unpack_from('<4H',result.raw,r.offset+16)[:3],(2,0,0))
        self.assertEqual(struct.unpack_from('<Q',result.raw,r.offset+32)[0],0)
        check_original_bytes(self,d,result)

    def test_duplicate_copies_current_values_without_sharing_edits(self):
        d=self.doc;source='LID_SYNTHETIC_A';row=d.rows_by_table[source][0]
        d.set(row,d.by_offset[0x20],33);d.set(row,d.by_offset[0x38],['current condition'])
        d.append_entry(source);table=d.create_list('LID_Copy',source)
        self.assertEqual(len(d.rows_by_table[table.pid]),3)
        copy=d.rows_by_table[table.pid][0]
        self.assertEqual(d.value(copy,d.by_offset[0x20]),33)
        d.set(copy,d.by_offset[0x38],['copy condition'])
        self.assertEqual(d.value(row,d.by_offset[0x38]),['current condition'])
        d.create_list('LID_Second','LID_Copy');self.assertEqual(d.value(d.rows_by_table['LID_Second'][0],d.by_offset[0x38]),['copy condition'])
        result=Learning(d.build());self.assertEqual(len(result.collections),4)
        self.assertEqual(result.original(result.by_pid[copy.pid],result.by_offset[0x38]),['copy condition'])

    def test_invalid_and_duplicate_ids_are_rejected_without_mutation(self):
        d=self.doc;before=d.project()
        for key in ('LID_','LID_   ',' LID_Test','LID_Test ','LID_New\n','LID_New\0ID','LID_New::0','IID_Test',None,42,'LID_SYNTHETIC_A'):
            with self.assertRaises(DataError):d.create_list(key)
            self.assertEqual(d.project(),before)
        with self.assertRaises(DataError):d.create_list('LID_New','LID_Missing')
        d.create_list('LID_New');before=d.project()
        with self.assertRaises(DataError):d.create_list('LID_New')
        self.assertEqual(d.project(),before)

    def test_v4_empty_and_populated_projects_and_transactional_rollback(self):
        d=self.doc;d.create_list('LID_Empty');empty=d.project()
        self.assertEqual(empty['format'],'fw-growth-edits-v4');self.assertEqual(empty['new_entries'],[])
        d.create_list('LID_Copy','LID_SYNTHETIC_A');d.append_entry('LID_Empty');before=json.loads(json.dumps(d.project()))
        restored=Learning(d.raw);load_suite_project({'Growth':restored},before)
        self.assertEqual(restored.project(),before);self.assertEqual(restored.build(),d.build())
        for values in (['LID_Repeat','LID_Repeat'],['LID_SYNTHETIC_A'],['Invalid'],[None],{},None):
            bad=deepcopy(before);bad['new_lists']=values
            with self.assertRaises(DataError):d.load_project(bad)
            self.assertEqual(d.project(),before)
        bad=deepcopy(before);bad['format']='fw-growth-edits-v3'
        with self.assertRaises(DataError):d.load_project(bad)
        docs={'Growth':d,'Classes':Job(job_fixture())};bad=suite_project(docs)
        bad['documents']['Growth.bin']=empty;bad['documents']['Job.bin']['source_sha256']='wrong'
        with self.assertRaises(DataError):load_suite_project(docs,bad)
        self.assertEqual(d.project(),before)
        legacy=Learning(d.raw).project();d.load_project(legacy);self.assertFalse(d.modified)
        self.assertEqual(d.build(),d.raw)

    def test_reset_remove_and_original_indices(self):
        d=self.doc;ids=[(r.pid,r.index) for r in d.collections]
        d.create_list('LID_First','LID_SYNTHETIC_A');d.create_list('LID_Second','LID_First')
        d.reset_table('LID_First');self.assertIn('LID_First',d.tables_by_id);self.assertFalse(d.rows_by_table['LID_First'])
        self.assertEqual(d.added_count,2)
        d.remove_list('LID_First');self.assertNotIn('LID_First',d.tables_by_id)
        self.assertEqual(d.tables_by_id['LID_Second'].index,2)
        self.assertEqual([(r.pid,r.index) for r in d.collections[:2]],ids)
        with self.assertRaises(DataError):d.remove_list('LID_SYNTHETIC_A')
        d.remove_list('LID_Second');self.assertFalse(d.modified);self.assertEqual(d.build(),d.raw)

    def test_headers_rows_strings_and_opaque_bytes_with_multiple_boundaries(self):
        d=self.doc;before=snapshot(d)
        d.create_list('LID_New_新');d.append_entry('LID_New_新');d.create_list('LID_Copy','LID_SYNTHETIC_B')
        d.append_entry('LID_SYNTHETIC_A');d.append_entry('LID_SYNTHETIC_B')
        result=Learning(d.build());after=snapshot(result)
        self.assertTrue(all(after[key]==v for key,v in before.items()))
        self.assertEqual(set(result.labels)-set(d.labels),set(d.new_lists))
        tags=[struct.unpack_from('<H',result.raw,r.offset+22)[0] for r in [*result.collections,*result.records]]
        self.assertEqual(len(tags),len(set(tags)))
        for table in result.collections:
            for row in result.rows_by_table[table.pid]:self.assertEqual(result.string(struct.unpack_from('<Q',result.raw,row.offset+8)[0]),table.pid)
        check_original_bytes(self,d,result)

    def test_entirely_empty_group_capacity_and_reopened_export(self):
        raw=emptied(emptied(growth_fixture(),'LID_SYNTHETIC_A'),'LID_SYNTHETIC_B');d=Learning(raw)
        d.create_list('LID_New');d.append_entry('LID_New');result=Learning(d.build())
        self.assertEqual(len(result.records),1);check_original_bytes(self,d,result)
        result.create_list('LID_Next','LID_New');again=Learning(result.build())
        self.assertEqual(len(again.collections),4);self.assertEqual(len(again.records),2)
        d=Learning(growth_fixture());raw=bytearray(d.raw);struct.pack_into('<H',raw,d.records[-1].offset+22,65535)
        d=Learning(bytes(raw))
        with self.assertRaises(DataError):d.create_list('LID_Full')
        self.assertFalse(d.modified)

    def test_shared_exports_sources_backups_and_live_skill_references(self):
        d=self.doc;d.create_list('LID_Custom');row=d.append_entry('LID_Custom');d.set(row,d.by_offset[0x28],'SID_CUSTOM')
        use=SkillIndex().uses('SID_CUSTOM',{'Learning tables':d})[0]
        self.assertEqual((use.table,use.row,use.record),('LID_Custom',0,row.pid))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'Growth.bin';source.write_bytes(d.raw)
            export_suite({'Growth':d},{'Growth':source},root/'mod')
            target=root/'mod/romfs/GameData/Growth.bin';result=Learning(target.read_bytes())
            self.assertIn('LID_Custom',result.tables_by_id)
            manifest=json.loads((root/'mod/suite-edits.json').read_text(encoding='utf8'))
            self.assertEqual(manifest['documents']['Growth.bin']['new_lists'],['LID_Custom'])
            export_suite({'Growth':d},{'Growth':source},root/'mod');self.assertTrue(list(target.parent.glob('Growth.bin.backup-*')))
            self.assertEqual(source.read_bytes(),d.raw)


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent/fw-game-data'))
@unittest.skipUnless((DATA/'Growth.bin').is_file(),'Set FW_GAME_DATA for native new-list tests.')
class RealLearningListTests(unittest.TestCase):
    def test_new_blank_and_dietrich_copy_preserve_all_original_growth_data(self):
        d=Learning((DATA/'Growth.bin').read_bytes());before=snapshot(d)
        d.create_list('LID_New_空');d.create_list('LID_New_Dietrich','LID_ディートリヒ')
        result=Learning(d.build());self.assertEqual(len(result.collections),98)
        self.assertEqual(len(result.rows_by_table['LID_New_Dietrich']),56)
        after=snapshot(result);self.assertTrue(all(after[k]==v for k,v in before.items()))
        check_original_bytes(self,d,result)
        person=Person((DATA/'Person.bin').read_bytes());row=person.by_pid['PID_ディートリヒ']
        person.set(row,person.by_offset[0x88],['LID_New_Dietrich'])
        project=suite_project({'Characters':person,'Learning tables':d})
        docs={'Characters':Person(person.raw),'Learning tables':Learning(d.raw)};load_suite_project(docs,json.loads(json.dumps(project)))
        built=Person(docs['Characters'].build());self.assertEqual(built.original(built.by_pid[row.pid],built.by_offset[0x88]),['LID_New_Dietrich'])

    def test_native_and_new_rows_glid_auxiliary_edits_roundtrip_together(self):
        d=Learning((DATA/'Growth.bin').read_bytes());d.create_list('LID_WholeCopy','LID_ディートリヒ')
        r=d.rows_by_table['LID_WholeCopy'][0];d.set(r,d.by_offset[0x38],['Independent copy'])
        d.append_entry('LID_ディートリヒ');d.progression.set(d.progression.records[0],d.progression.fields[1],'New class')
        v=d.views['exp_curve'];v.set(v.records[0],v.by_offset[0x22],3210)
        project=json.loads(json.dumps(d.project()));other=Learning(d.raw);other.load_project(project)
        self.assertEqual(other.project(),project);result=Learning(other.build())
        self.assertEqual(result.original(result.by_pid[r.pid],result.by_offset[0x38]),['Independent copy'])
        self.assertEqual(result.progression.original(result.progression.records[0],result.progression.fields[1]),'New class')
        self.assertEqual(result.views['exp_curve'].original(result.views['exp_curve'].records[0],result.views['exp_curve'].by_offset[0x22]),3210)
