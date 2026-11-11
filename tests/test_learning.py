"""Learning collections and preserving unrelated Growth.bin content."""
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest

from fw_editor import Learning,Person,Job,DataError,suite_project,load_suite_project,export_suite
from fixture import learning_fixture,person_fixture,job_fixture


class LearningTests(unittest.TestCase):
    def setUp(self):self.doc=Learning(learning_fixture())

    def test_identity_and_numeric_only_edit(self):
        d=self.doc;self.assertEqual(len(d.collections),2);self.assertEqual(len(d.records),3)
        self.assertEqual(d.build(),d.raw)
        row=d.rows_by_table['LID_SYNTHETIC_A'][0];d.set(row,d.by_offset[0x20],19)
        expected=bytearray(d.raw);expected[row.offset+0x20]=19
        self.assertEqual(d.build(),bytes(expected))

    def test_mixed_fields_shared_conditions_and_opaque_progression(self):
        d=self.doc;before={(r.pid,f.offset):d.original(r,f) for r in d.records for f in d.fields};row=d.records[0]
        edits={0x20:255,0x21:12,0x22:7,0x28:'SID_新規テスト',0x38:['new condition','3部']}
        for offset,value in edits.items():d.set(row,d.by_offset[offset],value)
        result=Learning(d.build())
        for r in result.records:
            for f in result.fields:self.assertEqual(result.original(r,f),edits[f.offset] if r.pid==row.pid else before[(r.pid,f.offset)])
        self.assertEqual(result.rows_by_table['LID_SYNTHETIC_A'][0].offset,row.offset)
        self.assertEqual([(r.pid,len(result.rows_by_table[r.pid])) for r in result.collections],[('LID_SYNTHETIC_A',2),('LID_SYNTHETIC_B',1)])
        at=result.labels['GLID_SYNTHETIC'];ptr=struct.unpack_from('<Q',result.raw,at+32)[0]
        self.assertEqual(result.string(ptr),'opaque progression value')
        result.set(result.records[0],result.by_offset[0x38],[])
        again=Learning(result.build());self.assertEqual(again.original(again.records[0],again.by_offset[0x38]),[])

    def test_project_validation_reset_and_joint_export(self):
        d=self.doc;row=d.records[0];d.set(row,d.by_offset[0x28],'SID_REPLACEMENT')
        project=json.loads(json.dumps(d.project()));d.changes={};d.load_project(project)
        self.assertTrue(d.table_changed('LID_SYNTHETIC_A'));self.assertFalse(d.table_changed('LID_SYNTHETIC_B'))
        with self.assertRaises(DataError):d.set(row,d.by_offset[0x20],256)
        with self.assertRaises(DataError):d.set(row,d.by_offset[0x38],[''])
        bad=json.loads(json.dumps(project));bad['changes'][0]['row']=-1;before=dict(d.changes)
        with self.assertRaises(DataError):d.load_project(bad)
        self.assertEqual(d.changes,before)
        docs={'Characters':Person(person_fixture()),'Classes':Job(job_fixture()),'Learning tables':d}
        saved=suite_project(docs);d.reset_table('LID_SYNTHETIC_A');self.assertFalse(d.changes);load_suite_project(docs,saved)
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);sources={}
            for name,doc in docs.items():
                p=base/'source'/doc.filename;p.parent.mkdir(exist_ok=True);p.write_bytes(doc.raw);sources[name]=p
            targets=export_suite(docs,sources,base/'mod')
            self.assertEqual({p.name for p in targets},{'Person.bin','Job.bin','Growth.bin'})
            restored=Learning((base/'mod/romfs/GameData/Growth.bin').read_bytes())
            self.assertEqual(restored.original(restored.records[0],restored.by_offset[0x28]),'SID_REPLACEMENT')
            for name,doc in docs.items():self.assertEqual(sources[name].read_bytes(),doc.raw)
        # Earlier character-only projects remain compatible and clear learning edits.
        load_suite_project(docs,docs['Characters'].project());self.assertFalse(d.changes)


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent/fw-game-data'))
@unittest.skipUnless((DATA/'Growth.bin').is_file(),'Set FW_GAME_DATA for real learning-table tests.')
class RealLearningTests(unittest.TestCase):
    def test_every_entry_and_unrelated_growth_data_preserved(self):
        d=Learning((DATA/'Growth.bin').read_bytes());self.assertEqual(len(d.collections),96);self.assertEqual(len(d.records),4034)
        before={(r.pid,f.offset):d.original(r,f) for r in d.records for f in d.fields}
        for r in d.records:
            for f in d.fields:d.set(r,f,d.original(r,f))
        self.assertFalse(d.changes);self.assertEqual(d.build(),d.raw)
        row=d.rows_by_table['LID_ディートリヒ'][0]
        edits={0x20:17,0x21:12,0x22:9,0x28:'SID_テスト新規',0x38:['test_flag','3部']}
        for offset,value in edits.items():d.set(row,d.by_offset[offset],value)
        result=Learning(d.build())
        self.assertEqual(result.labels,d.labels)
        # References in untouched GLID/experience groups retain their targets,
        # including strings after rebasing to the new string pool.
        changed_locations={row.offset-32+offset for offset in edits}
        for at in d.pointers:
            if at in changed_locations or row.offset-32<=at<row.offset-32+d.stride:continue
            before_ptr=struct.unpack_from('<Q',d.raw,at+32)[0]
            after_ptr=struct.unpack_from('<Q',result.raw,at+32)[0]
            if before_ptr>=d.pool:self.assertEqual(d.string(before_ptr),result.string(after_ptr))
            else:self.assertEqual(before_ptr,after_ptr)
        for r in result.records:
            for f in result.fields:
                self.assertEqual(result.original(r,f),edits[f.offset] if r.pid==row.pid else before[(r.pid,f.offset)],(r.pid,f.offset))
        # Ignore rebased string pointers and the deliberately edited field bytes;
        # every other original byte, including GLID and experience data, must match.
        original=bytearray(d.raw[32:32+d.size]);actual=bytearray(result.raw[32:32+d.size])
        for at in set(d.pointers)|set(result.pointers):
            if at+8<=d.size:original[at:at+8]=b'\0'*8;actual[at:at+8]=b'\0'*8
        for offset in edits:
            at=row.offset-32+offset;size=d.by_offset[offset].size
            original[at:at+size]=b'\0'*size;actual[at:at+size]=b'\0'*size
        self.assertEqual(original,actual)
