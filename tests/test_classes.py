"""Class pointer, nested-condition and multi-table project/export regression tests."""
import copy
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from fw_editor import (Job, Person, Binary, DataError, suite_project, load_suite_project, export_suite)
from fixture import job_fixture, person_fixture


class ClassFormatTests(unittest.TestCase):
    def setUp(self):
        self.job=Job(job_fixture());self.a,self.b=self.job.records

    def test_identity_roundtrip_and_direct_links(self):
        self.assertEqual(self.job.build(),self.job.raw)
        self.assertEqual(self.job.value(self.a,self.job.by_offset[0x50]),self.b.pid)
        self.assertEqual(self.job.value(self.b,self.job.by_offset[0x48]),self.a.pid)
        self.job.set(self.a,self.job.by_offset[0x48],self.b.pid)  # null -> direct pointer
        self.job.set(self.a,self.job.by_offset[0x50],'')
        self.job.set(self.a,self.job.by_offset[0x30],7)  # movement type is editable, not a character serial
        result=Job(self.job.build())
        self.assertEqual(result.value(result.records[0],result.by_offset[0x48]),self.b.pid)
        self.assertEqual(result.value(result.records[0],result.by_offset[0x50]),'')
        self.assertEqual(struct.unpack_from('<Q',result.raw,self.a.offset+0x48)[0],self.b.offset-32)
        self.assertEqual(result.value(result.records[0],result.by_offset[0x30]),7)
        for bad in ('JID_missing','PID_SYNTHETIC_0',22):
            with self.assertRaises(DataError):self.job.set(self.a,self.job.by_offset[0x48],bad)

    def test_nested_conditions_copy_on_write_and_reopen(self):
        original={(r.pid,f.offset):self.job.original(r,f) for r in self.job.records for f in self.job.fields}
        edits={0x1b8:[['new condition','日本語'],[],['third']],0x1c8:[['hidden']],
               0x90:['SID_NEW','SID_SECOND'],0x1d8:'IID_NEW',0x228:'AID_NEW',0x219:-128}
        for off,value in edits.items():self.job.set(self.a,self.job.by_offset[off],value)
        raw=self.job.build();result=Job(raw)
        for r in result.records:
            for f in result.fields:
                expected=edits[f.offset] if r.pid==self.a.pid and f.offset in edits else original[(r.pid,f.offset)]
                self.assertEqual(result.original(r,f),expected,(r.pid,f.offset))
        copied=self.job.value(self.a,self.job.by_offset[0x1b8]);copied[0].append('must not leak')
        self.assertNotIn('must not leak',self.job.value(self.a,self.job.by_offset[0x1b8])[0])
        result.set(result.records[0],result.by_offset[0x1b8],[])
        second=Job(result.build());self.assertEqual(second.value(second.records[0],second.by_offset[0x1b8]),[])
        extra=second.labels['SUPPORT_SYNTHETIC'];ptr=struct.unpack_from('<Q',second.raw,extra+32)[0]
        self.assertEqual(second.string(ptr),'opaque retained text')

    def test_nested_validation_and_numeric_boundaries(self):
        for bad in ([['']],['not nested'],[[5]],[['bad\0text']]):
            with self.assertRaises(DataError):self.job.set(self.a,self.job.by_offset[0x1b8],bad)
        for off,bad in ((0x219,128),(0x219,-129),(0x120,32768),(0x30,-1)):
            with self.assertRaises(DataError):self.job.set(self.a,self.job.by_offset[off],bad)

    def test_suite_projects_legacy_compatibility_and_transaction(self):
        person=Person(person_fixture());docs={'Characters':person,'Classes':self.job}
        person.set(person.records[0],person.by_offset[0x1c2],42)
        self.job.set(self.a,self.job.by_offset[0x120],55)
        project=json.loads(json.dumps(suite_project(docs)))
        originals={key:dict(doc.changes) for key,doc in docs.items()}
        broken=copy.deepcopy(project);broken['documents']['Job.bin']['source_sha256']='wrong'
        with self.assertRaises(DataError):load_suite_project(docs,broken)
        self.assertEqual(originals,{key:doc.changes for key,doc in docs.items()})
        person.changes={};self.job.changes={};load_suite_project(docs,project)
        self.assertEqual(originals,{key:doc.changes for key,doc in docs.items()})
        load_suite_project(docs,person.project())
        self.assertEqual(self.job.changes,{})
        self.assertTrue(person.changes)
        with self.assertRaises(DataError):load_suite_project({'Characters':person},project)

    def test_suite_export_guards_backups_and_preflight(self):
        person=Person(person_fixture());docs={'Characters':person,'Classes':self.job}
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);sources={}
            for key,doc in docs.items():
                src=base/'source/romfs/GameData'/doc.filename;src.parent.mkdir(parents=True,exist_ok=True);src.write_bytes(doc.raw);sources[key]=src
            with self.assertRaises(DataError):export_suite(docs,sources,base/'source')
            mod=base/'mod';targets=export_suite(docs,sources,mod)
            self.assertEqual({p.name for p in targets},{'Person.bin','Job.bin'})
            self.job.set(self.a,self.job.by_offset[0x120],88)
            old=(mod/'romfs/GameData/Job.bin').read_bytes()
            with patch.object(self.job,'build',side_effect=DataError('simulated invalid class')):
                with self.assertRaises(DataError):export_suite(docs,sources,mod)
            self.assertEqual((mod/'romfs/GameData/Job.bin').read_bytes(),old)
            export_suite(docs,sources,mod)
            self.assertEqual(next((mod/'romfs/GameData').glob('Job.bin.backup-*')).read_bytes(),old)
            for key,doc in docs.items():self.assertEqual(sources[key].read_bytes(),doc.raw)
            with self.assertRaises(DataError):export_suite({'Characters':person},{'Characters':sources['Characters']},mod)
            unrelated=base/'other/romfs/GameData/Job.bin';unrelated.parent.mkdir(parents=True);unrelated.write_bytes(b'keep')
            with self.assertRaises(DataError):export_suite(docs,sources,base/'other')
            self.assertEqual(unrelated.read_bytes(),b'keep')


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent/fw-game-data'))

@unittest.skipUnless((DATA/'Job.bin').is_file(),'Set FW_GAME_DATA for the real class-table regression test.')
class RealClassTests(unittest.TestCase):
    def test_every_class_field_and_auxiliary_data_survives_mixed_edit(self):
        j=Job((DATA/'Job.bin').read_bytes());self.assertEqual(len(j.records),137);self.assertEqual(len(j.fields),134)
        self.assertEqual(j.build(),j.raw)
        for r in j.records:
            for f in j.fields:j.set(r,f,j.original(r,f))
        self.assertFalse(j.changes)
        values={(r.pid,f.offset):j.original(r,f) for r in j.records for f in j.fields}
        target=j.by_pid['JID_ソードマスター']
        edits={0x48:'JID_闘士',0x50:'JID_剣士',0x58:'',0x1b8:[['custom','共有_兵種解放_ソードマスター'],[],['third']],
               0x1c8:[],0x90:['SID_NEW_TEST'],0x20:'MJID_NEW_TEST',0x1d8:'IID_NEW_TEST',0x219:-5,0x120:37}
        for off,value in edits.items():j.set(target,j.by_offset[off],value)
        result=Job(j.build())
        self.assertEqual(list(result.labels),list(j.labels))
        self.assertEqual([r.pid for r in j.records],[r.pid for r in result.records])
        for r in result.records:
            for f in result.fields:
                self.assertEqual(result.original(r,f),edits[f.offset] if r.pid==target.pid and f.offset in edits else values[(r.pid,f.offset)],(r.pid,f.offset))
        # Auxiliary mount/support groups remain byte-identical after normalizing relocated string pointers.
        before=bytearray(j.raw[32:32+j.size]);after=bytearray(result.raw[32:32+j.size])
        changed_bytes=set()
        for off in edits:
            size=j.by_offset[off].size;changed_bytes.update(range(target.offset-32+off,target.offset-32+off+size))
        for at in set(j.pointers)|set(result.pointers):
            if at+8<=j.size:
                before[at:at+8]=b'\0'*8;after[at:at+8]=b'\0'*8
        for at in changed_bytes:before[at]=0;after[at]=0
        self.assertEqual(before,after)
