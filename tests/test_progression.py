"""Joint LID/GLID edits must preserve every other Growth.bin field and header."""
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from fw_editor import Learning,DataError,suite_project,load_suite_project,export_suite
from fixture import growth_fixture


def values(document):
    return {(r.pid,f.offset):view.original(r,f) for view in (document,document.progression) if view for r in view.records for f in view.fields}


class ProgressionTests(unittest.TestCase):
    def setUp(self):self.doc=Learning(growth_fixture())

    def test_category_and_last_level_edit_exact_bytes_and_shared_state(self):
        d=self.doc;p=d.progression;r=p.records[0]
        self.assertEqual(d.build(),d.raw)
        self.assertIs(d.changes,p.changes)
        p.set(r,p.by_offset[0x20],255)
        expected=bytearray(d.raw);expected[r.offset+0x20]=255
        self.assertEqual(d.build(),bytes(expected))
        p.set(r,p.by_offset[0x2a0],'Unicode 最終レベル')
        q=Learning(d.build()).progression
        self.assertEqual(q.original(q.records[0],q.by_offset[0x2a0]),'Unicode 最終レベル')
        self.assertEqual(q.original(q.records[1],q.by_offset[0x2a0]),'80+ raw')
        # Reset one module/table never removes the other's edits.
        d.set(d.records[0],d.by_offset[0x20],23)
        p.reset_table('GLID_SYNTHETIC_A')
        self.assertEqual(len(d.changes),1);self.assertIs(d.changes,p.changes)
        p.set(r,p.by_offset[0x28],'new class')
        d.reset_table('LID_SYNTHETIC_A')
        self.assertEqual(len(d.changes),1);self.assertTrue(p.table_changed('GLID_SYNTHETIC_A'))
        self.assertFalse(d.table_changed('LID_SYNTHETIC_A'))

    def test_combined_save_export_legacy_and_rollback(self):
        d=self.doc;p=d.progression;r=p.records[0]
        d.set(d.records[0],d.by_offset[0x38],['new condition','2部'])
        p.set(r,p.by_offset[0x28],'new bare class');p.set(r,p.by_offset[0x2a0],'')
        expected=dict(d.changes);project=json.loads(json.dumps(suite_project({'Learning tables':d})))
        d.changes={};load_suite_project({'Learning tables':d},project);self.assertEqual(d.changes,expected)
        invalid=json.loads(json.dumps(project));invalid['documents']['Growth.bin']['changes'].append({'table':'GLID_SYNTHETIC_A','row':-1,'offset':0x28,'value':'x'})
        with self.assertRaises(DataError):load_suite_project({'Learning tables':d},invalid)
        self.assertEqual(d.changes,expected);self.assertIs(d.changes,p.changes)
        with self.assertRaises(DataError):p.set(r,p.by_offset[0x20],256)
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);source=base/'Growth.bin';source.write_bytes(d.raw)
            targets=export_suite({'Learning tables':d},{'Learning tables':source},base/'mod')
            self.assertEqual(len(targets),1)
            q=Learning(targets[0].read_bytes());self.assertEqual(values(q),{**values(d),**expected})
            self.assertEqual(source.read_bytes(),d.raw)
        # 0.5/0.5.1 standalone and wrapped learning projects both remain loadable.
        legacy={'format':'fw-learning-edits-v1','source_sha256':d.fingerprint,'changes':[{'lid':'LID_SYNTHETIC_A','row':0,'offset':0x20,'value':99}]}
        load_suite_project({'Learning tables':d},legacy)
        self.assertEqual(d.changes,{('LID_SYNTHETIC_A::0',0x20):99})
        wrapped={'format':'fw-hacking-suite-project-v1','documents':{'Growth.bin':legacy}}
        load_suite_project({'Learning tables':d},wrapped)
        self.assertEqual(d.value(d.records[0],d.by_offset[0x20]),99)

    def test_all_values_opaque_bytes_and_pointer_targets(self):
        d=self.doc;p=d.progression;before=values(d)
        edits={(p.records[0].pid,0x28):'新しいクラス',(p.records[1].pid,0x2a0):'new 80+',
               (p.records[2].pid,0x20):2,(d.records[0].pid,0x38):['nonshared','new'],(d.records[1].pid,0x28):'SID_NEW'}
        for (key,offset),value in edits.items():
            view=p if key.startswith('GLID_') else d
            view.set(*d.edit_target(key,offset),value)
        result=Learning(d.build());self.assertEqual(values(result),{**before,**edits})
        self.assertEqual(result.labels,d.labels)
        original=bytearray(d.raw[32:32+d.size]);actual=bytearray(result.raw[32:32+d.size])
        changed_bytes=set()
        for key,offset in edits:
            row,field=d.edit_target(key,offset);start=row.offset-32+offset
            changed_bytes.update(range(start,start+field.size))
        for at in d.pointers:
            if any(at+i in changed_bytes for i in range(8)):continue
            oldptr=struct.unpack_from('<Q',d.raw,at+32)[0];newptr=struct.unpack_from('<Q',result.raw,at+32)[0]
            if oldptr>=d.pool:self.assertEqual(d.string(oldptr),result.string(newptr))
            else:self.assertEqual(oldptr,newptr)
        for at in set(d.pointers)|set(result.pointers):
            if at+8<=d.size:original[at:at+8]=actual[at:at+8]=b'\0'*8
        for at in changed_bytes:original[at]=actual[at]=0
        self.assertEqual(original,actual)
        # Every GLID collection and leaf header, including native IDs and unused fields, stays exact.
        for view in (d,p):
            restored=result if view is d else result.progression
            self.assertEqual([(r.pid,len(view.rows_by_table[r.pid])) for r in view.collections],[(r.pid,len(restored.rows_by_table[r.pid])) for r in restored.collections])
            for row in view.records:
                self.assertEqual(d.raw[row.offset:row.offset+8],result.raw[row.offset:row.offset+8])
                self.assertEqual(d.raw[row.offset+16:row.offset+32],result.raw[row.offset+16:row.offset+32])


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent'))
@unittest.skipUnless((DATA/'Growth.bin').is_file(),'Set FW_GAME_DATA for real GLID regression.')
class RealProgressionTests(ProgressionTests):
    def setUp(self):self.doc=Learning((DATA/'Growth.bin').read_bytes())
    # The full preservation test is reusable; fixture-specific tests above are excluded here.
    test_category_and_last_level_edit_exact_bytes_and_shared_state=None
    test_combined_save_export_legacy_and_rollback=None
    def test_original_identities_counts_and_class_path(self):
        d=self.doc;p=d.progression
        self.assertEqual((len(p.collections),len(p.records),len(p.fields)),(206,1630,81))
        self.assertEqual(d.build(),d.raw)
        for r in p.records:
            for f in p.fields:p.set(r,f,p.original(r,f))
        self.assertFalse(d.changes)
        row=p.rows_by_table['GLID_ディートリヒ'][0]
        self.assertEqual([(i,p.original(row,f)) for i,f in enumerate(p.fields[1:],1) if p.original(row,f)],[(1,'無職'),(5,'闘士'),(20,'剣士'),(35,'シドー'),(45,'ソードマスター'),(55,'ザ・ブレイド')])
