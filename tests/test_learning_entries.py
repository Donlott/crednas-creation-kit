"""Structural additions, transactional projects and full-file preservation."""
from copy import deepcopy
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest

from fw_editor import Learning,Job,DataError,suite_project,load_suite_project,export_suite
from skill_index import SkillIndex
from fixture import growth_fixture,job_fixture


def snapshot(doc):
    views=[doc,*doc.views.values()]
    if doc.progression:views.append(doc.progression)
    return {(view.group_name,row.pid,f.offset):view.original(row,f)
            for view in views for row in view.records for f in view.fields}


def emptied(raw,key):
    """Remove a collection's active rows and nullable-pointer relocation."""
    d=Learning(raw);table=d.tables_by_id[key];at=table.offset-32
    body=bytearray(raw[32:32+d.size]);struct.pack_into('<H',body,at+18,0);struct.pack_into('<Q',body,at+32,0)
    order=[p for p in d.pointers if p!=at+32]
    new_pool=d.size+8*len(order)+len(d.label_bytes)
    for p in order:
        value=struct.unpack_from('<Q',body,p)[0]
        if value>=d.pool:struct.pack_into('<Q',body,p,value-d.pool+new_pool)
    pool=raw[32+d.pool:];header=bytearray(raw[:32])
    struct.pack_into('<4I',header,0,32+new_pool+len(pool),d.size,len(order),len(d.label_bytes)//8)
    return bytes(header+body+struct.pack('<'+str(len(order))+'Q',*order)+d.label_bytes+pool)


def check_preservation(test,doc,result):
    """Independently reverse insertion positions and compare opaque source bytes."""
    insertions={}
    first=min((r.offset-32 for rows in doc._source_rows.values() for r in rows),default=doc.collections[-1].offset-32+48)
    allowed=set()
    for table in doc.collections:
        extra=doc.added_entries.get(table.pid,())
        if not extra:continue
        rows=doc._source_rows[table.pid]
        at=rows[-1].offset-32+doc.stride if rows else first
        insertions[at]=insertions.get(at,0)+len(extra)*doc.stride
        allowed.update(range(table.offset-32+18,table.offset-32+20))
    def moved(at):return at+sum(n for pos,n in insertions.items() if pos<=at)
    for name,at in doc.labels.items():test.assertEqual(result.labels[name],moved(at-32)+32)
    for at in doc.pointers:
        original=struct.unpack_from('<Q',doc.raw,32+at)[0]
        current=struct.unpack_from('<Q',result.raw,32+moved(at))[0]
        empty=next((t for t in doc.collections if t.offset==at and not doc._source_rows[t.pid] and doc.added_entries.get(t.pid)),None)
        if empty:continue
        if original>=doc.pool:test.assertEqual(doc.string(original),result.string(current))
        else:test.assertEqual(current,moved(original))
    restored=bytearray(result.raw[32:32+result.size])
    for at,n in sorted(insertions.items(),reverse=True):
        start=at+sum(v for p,v in insertions.items() if p<at)
        del restored[start:start+n]
    restored=restored[:doc.size];old=bytearray(doc.raw[32:32+doc.size])
    for at in doc.pointers:old[at:at+8]=restored[at:at+8]=b'\0'*8
    # Empty collections acquire a previously null/nonrelocated data pointer.
    for table in doc.collections:
        if not doc._source_rows[table.pid] and doc.added_entries.get(table.pid):
            at=table.offset-32+32;old[at:at+8]=restored[at:at+8]=b'\0'*8
    for at in allowed:old[at]=restored[at]=0
    test.assertEqual(old,restored)


class LearningEntryTests(unittest.TestCase):
    def setUp(self):self.doc=Learning(growth_fixture())

    def test_blank_duplicate_and_virtual_values_are_independent(self):
        d=self.doc;key='LID_SYNTHETIC_A';row=d.append_entry(key)
        self.assertTrue(d.modified);self.assertTrue(d.table_changed(key));self.assertEqual(d.added_count,1)
        self.assertEqual([d.value(row,f) for f in d.fields],[1,0,0,'',[]])
        d.set(row,d.by_offset[0x28],'SID_NEW');d.set(row,d.by_offset[0x38],['condition_new'])
        duplicate=d.duplicate_entry(row);self.assertEqual(duplicate.index,3)
        value=d.value(duplicate,d.by_offset[0x38]);value.append('outside mutation')
        self.assertEqual(d.value(duplicate,d.by_offset[0x38]),['condition_new'])
        d.set(duplicate,d.by_offset[0x38],['independent'])
        self.assertEqual(d.value(row,d.by_offset[0x38]),['condition_new'])
        result=Learning(d.build());self.assertEqual(len(result.rows_by_table[key]),4)
        self.assertEqual(result.original(result.by_pid[duplicate.pid],result.by_offset[0x38]),['independent'])
        self.assertEqual(result.original(result.by_pid[row.pid],result.by_offset[0x38]),['condition_new'])

    def test_multiple_lists_tags_labels_and_all_original_bytes(self):
        d=self.doc;before=snapshot(d)
        for key in d.rows_by_table:
            for _ in range(3):d.duplicate_entry(d.rows_by_table[key][0])
        result=Learning(d.build());after=snapshot(result)
        self.assertTrue(all(after[k]==v for k,v in before.items()))
        tags=[struct.unpack_from('<H',result.raw,r.offset+22)[0] for r in [*result.collections,*result.records]]
        self.assertEqual(len(tags),len(set(tags)))
        check_preservation(self,d,result)
        self.assertEqual(d.raw,growth_fixture())

    def test_first_entry_in_empty_list_with_new_relocation(self):
        raw=emptied(growth_fixture(),'LID_SYNTHETIC_B');d=Learning(raw);before=snapshot(d)
        self.assertFalse(d.rows_by_table['LID_SYNTHETIC_B'])
        row=d.append_entry('LID_SYNTHETIC_B');d.set(row,d.by_offset[0x28],'SID_FIRST')
        result=Learning(d.build());after=snapshot(result)
        self.assertTrue(all(after[k]==v for k,v in before.items()))
        self.assertEqual(result.original(result.by_pid[row.pid],result.by_offset[0x28]),'SID_FIRST')
        check_preservation(self,d,result)
        # Entire learning group may also have no active source leaves.
        d=Learning(emptied(raw,'LID_SYNTHETIC_A'));d.append_entry('LID_SYNTHETIC_A');d.append_entry('LID_SYNTHETIC_B')
        result=Learning(d.build());self.assertEqual(len(result.records),2)
        for r in result.records:self.assertEqual(result.original(r,result.by_offset[0x38]),[])

    def test_v3_projects_reopen_and_old_formats_clear_additions(self):
        d=self.doc;legacy=d.project();row=d.duplicate_entry(d.records[0]);d.set(row,d.by_offset[0x28],'SID_NEW')
        d.progression.set(d.progression.records[0],d.progression.fields[1],'New job')
        project=json.loads(json.dumps(d.project()));self.assertEqual(project['format'],'fw-growth-edits-v3')
        restored=Learning(d.raw);load_suite_project({'Growth':restored},project)
        self.assertEqual(restored.project(),project);self.assertEqual(restored.build(),d.build())
        d.load_project(legacy);self.assertFalse(d.modified);self.assertEqual(d.build(),d.raw)
        d.append_entry('LID_SYNTHETIC_A');load_suite_project({'Growth':d,'Classes':Job(job_fixture())},Job(job_fixture()).project())
        self.assertFalse(d.added_count)

    def test_transactional_invalid_additions_and_cross_file_rollback(self):
        d=self.doc;row=d.append_entry('LID_SYNTHETIC_A');d.set(row,d.by_offset[0x28],'SID_BEFORE')
        before=d.project()
        bad_values={f.offset:d.value(row,f) for f in d.fields};bad_values[0x20]=256
        with self.assertRaises(DataError):d.append_entry('LID_SYNTHETIC_A',bad_values)
        self.assertEqual(d.project(),before)
        for patch in ('bad_value','missing_field','unknown_table','wrong_source','downgrade'):
            bad=deepcopy(before)
            if patch=='bad_value':bad['new_entries'][0]['values']['32']=-1
            elif patch=='missing_field':del bad['new_entries'][0]['values']['40']
            elif patch=='unknown_table':bad['new_entries'][0]['table']='LID_UNKNOWN'
            elif patch=='wrong_source':bad['source_file']='Person.bin'
            else:bad['format']='fw-growth-edits-v2'
            with self.assertRaises(DataError):d.load_project(bad)
            self.assertEqual(d.project(),before)
        docs={'Growth':d,'Classes':Job(job_fixture())};project=suite_project(docs)
        project['documents']['Growth.bin']['new_entries'].append(deepcopy(project['documents']['Growth.bin']['new_entries'][0]))
        project['documents']['Job.bin']['source_sha256']='incorrect'
        with self.assertRaises(DataError):load_suite_project(docs,project)
        self.assertEqual(d.project(),before)

    def test_undo_reset_and_original_glid_edits(self):
        d=self.doc;a='LID_SYNTHETIC_A';b='LID_SYNTHETIC_B'
        d.set(d.records[0],d.by_offset[0x20],12)
        d.progression.set(d.progression.records[0],d.progression.fields[1],'Retain GLID')
        d.append_entry(a);last=d.append_entry(a);d.set(last,d.by_offset[0x28],'SID_LAST');d.append_entry(b)
        d.remove_last_added(a);self.assertNotIn(last.pid,d.by_pid);self.assertFalse(any(pid==last.pid for pid,_ in d.changes))
        d.reset_table(a);self.assertFalse(d.added_entries.get(a));self.assertEqual(d.added_count,1)
        self.assertEqual(d.progression.value(d.progression.records[0],d.progression.fields[1]),'Retain GLID')
        d.remove_last_added(b);self.assertFalse(d.added_count)
        with self.assertRaises(DataError):d.remove_last_added(b)
        d.clear_edits();self.assertEqual(d.build(),d.raw)

    def test_capacity_check_preserves_existing_header_tags(self):
        raw=bytearray(growth_fixture());d=Learning(raw)
        struct.pack_into('<H',raw,d.records[-1].offset+22,65535);d=Learning(bytes(raw))
        with self.assertRaises(DataError):d.append_entry('LID_SYNTHETIC_A')
        self.assertFalse(d.modified);self.assertEqual(d.build(),bytes(raw))

    def test_export_manifest_reedit_references_backups_and_sources(self):
        d=self.doc;row=d.append_entry('LID_SYNTHETIC_A');d.set(row,d.by_offset[0x28],'SID_NEW')
        uses=SkillIndex().uses('SID_NEW',{'Learning tables':d})
        self.assertEqual([(u.table,u.row) for u in uses],[('LID_SYNTHETIC_A',2)])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'original/Growth.bin';source.parent.mkdir();source.write_bytes(d.raw)
            with self.assertRaises(DataError):
                export_suite({'Growth':d},{'Growth':root/'mod/romfs/GameData/Growth.bin'},root/'mod')
            export_suite({'Growth':d},{'Growth':source},root/'mod')
            manifest=json.loads((root/'mod/suite-edits.json').read_text());self.assertEqual(manifest['documents']['Growth.bin']['format'],'fw-growth-edits-v3')
            target=root/'mod/romfs/GameData/Growth.bin';reopened=Learning(target.read_bytes())
            reopened.append_entry('LID_SYNTHETIC_A');self.assertEqual(len(Learning(reopened.build()).rows_by_table['LID_SYNTHETIC_A']),4)
            export_suite({'Growth':d},{'Growth':source},root/'mod');self.assertTrue(list(target.parent.glob('Growth.bin.backup-*')))
            self.assertEqual(source.read_bytes(),d.raw)


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent/fw-game-data'))
@unittest.skipUnless((DATA/'Growth.bin').is_file(),'Set FW_GAME_DATA for native expansion regressions.')
class RealLearningEntryTests(unittest.TestCase):
    def test_dietrich_plus_eight_preserves_all_native_values_and_headers(self):
        d=Learning((DATA/'Growth.bin').read_bytes());before=snapshot(d);key='LID_ディートリヒ'
        original_tags={r.pid:struct.unpack_from('<H',d.raw,r.offset+22)[0] for r in [*d.collections,*d.records]}
        for _ in range(8):d.duplicate_entry(d.rows_by_table[key][0])
        result=Learning(d.build());self.assertEqual(len(result.rows_by_table[key]),64)
        after=snapshot(result);self.assertTrue(all(after[k]==v for k,v in before.items()))
        for pid,tag in original_tags.items():
            row=result.tables_by_id.get(pid) or result.by_pid[pid]
            self.assertEqual(struct.unpack_from('<H',result.raw,row.offset+22)[0],tag)
        check_preservation(self,d,result)

    def test_native_shared_auxiliary_glid_edits_projects_and_repeat_export(self):
        d=Learning((DATA/'Growth.bin').read_bytes());row=d.duplicate_entry(d.rows_by_table['LID_ディートリヒ'][0])
        d.set(row,d.by_offset[0x38],['Expansion test']);d.set(d.records[0],d.by_offset[0x20],99)
        d.progression.set(d.progression.records[0],d.progression.fields[1],'Expansion GLID')
        view=d.views['exp_curve'];view.set(view.records[0],view.by_offset[0x22],4321)
        project=json.loads(json.dumps(d.project()));restored=Learning(d.raw);restored.load_project(project)
        self.assertEqual(restored.project(),project)
        result=Learning(restored.build());self.assertEqual(result.original(result.by_pid[row.pid],result.by_offset[0x38]),['Expansion test'])
        self.assertEqual(result.progression.original(result.progression.records[0],result.progression.fields[1]),'Expansion GLID')
        v=result.views['exp_curve'];self.assertEqual(v.original(v.records[0],v.by_offset[0x22]),4321)
        result.duplicate_entry(result.rows_by_table['LID_ディートリヒ'][-1])
        self.assertEqual(len(Learning(result.build()).rows_by_table['LID_ディートリヒ']),58)
