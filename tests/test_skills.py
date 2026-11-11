"""SID format support, multi-file projects/exports and live reference indexing."""
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest

from fw_editor import (Binary,Skill,SkillP0,SkillP1,Person,Job,Learning,DataError,
                       suite_project,load_suite_project,export_suite,float32,number_text)
from skill_index import SkillIndex,sid_tokens
from fixture import skill_fixture,person_fixture,job_fixture,learning_fixture


def all_values(d):return {(r.pid,f.offset):d.original(r,f) for r in d.records for f in d.fields}


def verify_preserved(test,original,result,edits):
    test.assertEqual(result.labels,original.labels)
    test.assertEqual(all_values(result),{**all_values(original),**edits})
    left=bytearray(original.raw[32:32+original.size]);right=bytearray(result.raw[32:32+original.size])
    changed=set()
    for (pid,offset),value in edits.items():
        row,field=original.edit_target(pid,offset);start=row.offset-32+offset
        changed.update(range(start,start+field.size))
    for at in original.pointers:
        if any(at+i in changed for i in range(8)):continue
        a=struct.unpack_from('<Q',original.raw,at+32)[0];b=struct.unpack_from('<Q',result.raw,at+32)[0]
        if a>=original.pool:test.assertEqual(original.string(a),result.string(b))
        else:test.assertEqual(a,b)
    for at in set(original.pointers)|set(result.pointers):
        if at+8<=original.size:left[at:at+8]=right[at:at+8]=b'\0'*8
    for at in changed:left[at]=right[at]=0
    test.assertEqual(left,right)


class SkillFormatTests(unittest.TestCase):
    def setUp(self):self.doc=Skill(skill_fixture())

    def test_new_types_and_shared_arrays_roundtrip(self):
        d=self.doc;r=d.records[0];self.assertEqual(d.build(),d.raw)
        for row in d.records:
            for f in d.fields:d.set(row,f,d.original(row,f))
        self.assertFalse(d.changes)
        updates={0x88:[['SID_NEW','SID_新規'],[],['SID_SYNTHETIC_A']],0x98:[],
                 0x100:[-32768,1,32767],0x120:[0,255,2,3],0x15c:0.7,
                 0x1f0:['SID_NEW'],0x238:'IID_NEW',0x20:'MSID_NEW',0x14a:-32768}
        for off,value in updates.items():d.set(r,d.by_offset[off],value)
        edits=dict(d.changes);result=Skill(d.build());verify_preserved(self,d,result,edits)
        self.assertEqual(result.size%8,0)
        f=result.by_offset[0x88];at=result.records[0].offset+f.offset
        n,width,res,ptr=struct.unpack_from('<HHIQ',result.raw,at);self.assertEqual((n,width,res),(3,16,7))
        n,width,res,leaf=struct.unpack_from('<HHIQ',result.raw,ptr+32);self.assertEqual((n,width,res),(2,16,0))
        self.assertEqual(struct.unpack_from('<Q',result.raw,leaf+32+8)[0],0)
        self.assertEqual(result.original(result.records[1],f),[['SID_SYNTHETIC_B','SID_SYNTHETIC_A']])
        for off in (0x88,0x100,0x120):result.set(result.records[0],result.by_offset[off],[])
        again=Skill(result.build())
        for off in (0x88,0x100,0x120):self.assertEqual(again.original(again.records[0],again.by_offset[off]),[])
        self.assertEqual(again.original(again.records[1],again.by_offset[0x100]),[-300,0,300])

    def test_float_numeric_array_and_nested_validation(self):
        d=self.doc;r=d.records[0]
        for bad in (float('nan'),float('inf'),-float('inf'),1e100,10**500,True,'1.0'):
            with self.assertRaises(DataError):d.set(r,d.by_offset[0x15c],bad)
        for off,bad in ((0x100,[32768]),(0x100,[-32769]),(0x100,[1.5]),(0x120,[-1]),(0x120,[256]),(0x120,[True]),(0x88,[['']]),(0x88,['flat'])):
            with self.assertRaises(DataError):d.set(r,d.by_offset[off],bad)
        self.assertFalse(d.changes)
        for off in (0x100,0x88):
            d.set(r,d.by_offset[off],[["SID_NEW"]] if off==0x88 else [10])
            copied=d.value(r,d.by_offset[off]);copied[0]=99
            self.assertNotEqual(d.value(r,d.by_offset[off]),copied)
        # Wrong element widths are rejected rather than interpreted as a different layout.
        bad=bytearray(d.raw);struct.pack_into('<H',bad,r.offset+0x100+2,8)
        with self.assertRaises(DataError):Skill(bytes(bad))

    def test_float_display_roundtrips_extremes_without_extra_digits(self):
        for value in (0.7,0.0000001,3.4028234663852886e38,-3.4028234663852886e38,1.401298464324817e-45,1.0):
            normalized=float32(value)
            self.assertEqual(float32(float(number_text(normalized,'float'))),normalized)
        self.assertEqual(number_text(float32(0.7),'float'),'0.7')

    def test_file_specific_project_and_complete_export(self):
        docs={'Characters':Person(person_fixture()),'Classes':Job(job_fixture()),'Learning tables':Learning(learning_fixture()),
              'Skills':self.doc,'Skills · Skill_P0.bin':SkillP0(skill_fixture()),'Skills · Skill_P1.bin':SkillP1(skill_fixture())}
        for i,doc in enumerate(docs.values()):
            if isinstance(doc,Skill):doc.set(doc.records[0],doc.by_offset[0x100],[i])
        project=json.loads(json.dumps(suite_project(docs)));expected={key:dict(d.changes) for key,d in docs.items()}
        broken=json.loads(json.dumps(project));broken['documents']['Skill_P1.bin']['source_file']='Skill.bin'
        with self.assertRaises(DataError):load_suite_project(docs,broken)
        self.assertEqual({key:d.changes for key,d in docs.items()},expected)
        for doc in docs.values():doc.changes={}
        load_suite_project(docs,project);self.assertEqual({key:d.changes for key,d in docs.items()},expected)
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);sources={}
            for key,doc in docs.items():
                p=base/'source'/doc.filename;p.parent.mkdir(exist_ok=True);p.write_bytes(doc.raw);sources[key]=p
            targets=export_suite(docs,sources,base/'mod');self.assertEqual({p.name for p in targets},{d.filename for d in docs.values()})
            for key,doc in docs.items():
                result=type(doc)((base/'mod/romfs/GameData'/doc.filename).read_bytes())
                for (pid,off),value in doc.changes.items():self.assertEqual(result.original(*result.edit_target(pid,off)),value)
                self.assertEqual(sources[key].read_bytes(),doc.raw)
        legacy=docs['Characters'].project();load_suite_project(docs,legacy)
        self.assertFalse(any(doc.changes for doc in docs.values()))
        load_suite_project(docs,project['documents']['Skill_P0.bin'])
        self.assertTrue(docs['Skills · Skill_P0.bin'].changes);self.assertFalse(docs['Skills'].changes)


class SkillReferenceTests(unittest.TestCase):
    def test_sid_identity_brackets_negation_and_reserved_names(self):
        text='SID_[e]テスト[効果], !SID_テスト(後), SID_>予約 | SID_テスト_plus MSID_テスト'
        self.assertEqual(sid_tokens(text),(('SID_[e]テスト[効果]',False),('SID_テスト(後)',True),('SID_>予約',False),('SID_テスト_plus',False)))
        self.assertNotIn(('SID_テスト',False),sid_tokens(text))

    def test_live_references_replace_original_assignments_and_link_locations(self):
        index=SkillIndex();skill=Skill(skill_fixture());job=Job(job_fixture());learning=Learning(learning_fixture())
        docs={'Skills':skill,'Classes':job,'Learning tables':learning}
        sid='SID_SYNTHETIC_B';uses=index.uses(sid,docs)
        self.assertTrue(any(u.source=='Skill.bin' and u.path=='[0][0]' and '0x88' in u.field for u in uses))
        row=learning.records[0];learning.set(row,learning.by_offset[0x28],sid)
        job.set(job.records[0],job.by_offset[0x90],[sid])
        uses=index.uses(sid,docs)
        self.assertTrue(any(u.module=='Learning tables' and u.table=='LID_SYNTHETIC_A' and u.row==0 for u in uses))
        self.assertTrue(any(u.module=='Classes' for u in uses))
        learning.set(row,learning.by_offset[0x28],'SID_OTHER');job.set(job.records[0],job.by_offset[0x90],[])
        self.assertFalse(any(u.module in ('Classes','Learning tables') for u in index.uses(sid,docs)))
        before=skill.raw
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);(base/'Skill.bin').write_bytes(before)
            index=SkillIndex.load(base,Binary)
            self.assertIn('Skill.bin',index.scanned_files)
            self.assertTrue(index.evidence[sid]);self.assertEqual((base/'Skill.bin').read_bytes(),before)


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent'))
@unittest.skipUnless((DATA/'Skill.bin').is_file(),'Set FW_GAME_DATA for real skill regression.')
class RealSkillTests(unittest.TestCase):
    def test_all_452945_fields_and_unrelated_bytes_in_all_three_files(self):
        for kind,count in ((Skill,2854),(SkillP0,28),(SkillP1,3)):
            with self.subTest(file=kind.filename):
                d=kind((DATA/kind.filename).read_bytes());self.assertEqual((len(d.records),len(d.fields)),(count,157))
                self.assertEqual(d.size%8,0)
                self.assertEqual(d.build(),d.raw)
                for r in d.records:
                    for f in d.fields:d.set(r,f,d.original(r,f))
                self.assertFalse(d.changes)
                r=d.records[0]
                for off,v in ((0x88,[['SID_TEST'],[],['SID_新規']]),(0x98,[]),(0x100,[-32768,77,32767]),(0x120,[0,255]),(0x15c,0.73),(0x238,'IID_TEST'),(0x14a,-32768),(0x1f0,['SID_TEST'])):d.set(r,d.by_offset[off],v)
                result=kind(d.build());verify_preserved(self,d,result,dict(d.changes))
                # Reopen, edit and export again with the new numeric/nested arrays.
                result.set(result.records[-1],result.by_offset[0x100],[1,2,3]);again=kind(result.build())
                self.assertEqual(again.original(again.records[-1],again.by_offset[0x100]),[1,2,3])

    def test_real_usage_primary_and_side_files_item_links_and_learning_owners(self):
        from fw_editor import read_editable_tables
        docs,_=read_editable_tables(DATA);index=SkillIndex.load(DATA,Binary)
        for kind in (Skill,SkillP0,SkillP1):self.assertIn(kind.filename,index.scanned_files)
        self.assertIn('Item.bin',{source for source,_,_ in index.link_tables})
        self.assertTrue(any(index.static_uses.values()))
        sid='SID_主人公用輸送隊';uses=index.uses(sid,docs)
        self.assertTrue(any(u.record.startswith('PID_') for u in uses))
        growth=docs['Learning tables'];field=growth.by_offset[0x28]
        sid=next(growth.value(row,field) for row in growth.records if growth.value(row,field))
        self.assertTrue(any(u.module=='Learning tables' for u in index.uses(sid,docs)))
