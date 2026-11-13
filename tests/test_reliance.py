"""One Reliance document: directed matrix, seven layouts and shared-array isolation."""
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from fw_editor import Reliance,Person,DataError,suite_project,load_suite_project,export_suite
from fixture import reliance_fixture,person_fixture


def snapshot(doc):return {(r.pid,f.offset):v.original(r,f) for v in doc.views.values() for r in v.records for f in v.fields}


def compare(test,d,result,edits):
    test.assertEqual(snapshot(result),{**snapshot(d),**edits})
    test.assertEqual(result.labels,d.labels);test.assertEqual(result.label_bytes,d.label_bytes)
    test.assertEqual({k:len(v.records) for k,v in result.views.items()},{k:len(v.records) for k,v in d.views.items()})
    left=bytearray(d.raw[32:32+d.size]);right=bytearray(result.raw[32:32+d.size]);changed=set()
    for (pid,off),value in edits.items():
        r,f=d.edit_target(pid,off);at=r.offset-32+off;changed.update(range(at,at+f.size))
    for at in d.pointers:
        if any(at+i in changed for i in range(8)):continue
        a=struct.unpack_from('<Q',d.raw,at+32)[0];b=struct.unpack_from('<Q',result.raw,at+32)[0]
        if a>=d.pool:test.assertEqual(d.string(a),result.string(b))
        else:test.assertEqual(a,b)
    for at in set(d.pointers)|set(result.pointers):
        if at+8<=d.size:left[at:at+8]=right[at:at+8]=b'\0'*8
    for at in changed:left[at]=right[at]=0
    test.assertEqual(left,right)


class RelianceTests(unittest.TestCase):
    def setUp(self):self.doc=Reliance(reliance_fixture())

    def test_guard_percentages_validate_and_roundtrip_without_changing_other_data(self):
        d=self.doc;v=d.views['assist'];r=v.records[0]
        v.set_guard_rates(r,[0,25,50,75,100]);before=dict(d.changes)
        for bad in ([0,1],[-1,0,0,0,0],[101,0,0,0,0],[True,0,0,0,0],[1.5,0,0,0,0],['20',0,0,0,0]):
            with self.assertRaises(DataError):v.set_guard_rates(r,bad)
            self.assertEqual(d.changes,before)
        with self.assertRaises(DataError):d.views['matrix'].guard_rates(d.views['matrix'].records[0])
        outside=v.guard_rates(r);outside[0]=99;self.assertEqual(v.guard_rates(r)[0],0)
        result=Reliance(d.build());compare(self,d,result,before)
        restored=Reliance(d.raw);restored.load_project(json.loads(json.dumps(d.project())))
        self.assertEqual(restored.views['assist'].guard_rates(restored.views['assist'].records[0]),[0,25,50,75,100])
        self.assertEqual(restored.build(),result.raw)

    def test_directed_matrix_and_fixed_dimensions(self):
        d=self.doc;m=d.views['matrix'];self.assertEqual(d.build(),d.raw)
        r=m.records[0];values=m.value(r,m.by_offset[0x20]);values[1]=9;m.set(r,m.by_offset[0x20],values)
        result=Reliance(d.build());compare(self,d,result,dict(d.changes))
        reverse=result.views['matrix'];self.assertEqual(reverse.original(reverse.records[1],reverse.by_offset[0x20]),[4,0])
        for bad in ([1],[1,2,3],[1,256],[True,1]):
            with self.assertRaises(DataError):m.set(r,m.by_offset[0x20],bad)
        a=d.views['assist']
        with self.assertRaises(DataError):a.set(a.records[0],a.by_offset[0x20],[1])

    def test_mixed_seven_sections_unnamed_duplicate_headers_and_reedit(self):
        d=self.doc;before=snapshot(d)
        updates=[('matrix',0,0x20,[3,2]),('special',1,0x40,-32768),('talks',0,0x58,['new_flag','日本語']),
                 ('scout',1,0x22,65535),('scout',1,0x50,'IID_新規'),('assist',0,0x20,[0,1,2,3,255]),
                 ('voices',0,0x40,'new_voice'),('drinks',1,0x20,['IID_NEW','IID_SECOND'])]
        for section,index,offset,value in updates:
            view=d.views[section];view.set(view.records[index],view.by_offset[offset],value)
        result=Reliance(d.build());compare(self,d,result,dict(d.changes))
        self.assertEqual(result.views['scout'].names['scout:1'],'')
        self.assertEqual(result.views['scout'].anchors['scout:1'],'PID_SYNTH_0')
        self.assertEqual(result.views['talks'].names['talks:0'],result.views['talks'].names['talks:1'])
        talk=result.views['talks'];talk.set(talk.records[0],talk.by_offset[0x58],[])
        again=Reliance(result.build());self.assertEqual(again.views['talks'].original(again.views['talks'].records[0],talk.by_offset[0x58]),[])
        self.assertEqual(again.views['talks'].original(again.views['talks'].records[1],talk.by_offset[0x58]),['shared_flag'])

    def test_project_rollback_export_and_old_project_replacement(self):
        d=self.doc;v=d.views['scout'];v.set(v.records[1],v.by_offset[0x50],'IID_TEST')
        docs={'Supports & Recruitment':d,'Characters':Person(person_fixture())};project=json.loads(json.dumps(suite_project(docs)))
        before=dict(d.changes);d.changes={};load_suite_project(docs,project);self.assertEqual(d.changes,before)
        self.assertIs(d.changes,v.changes)
        bad=json.loads(json.dumps(project));bad['documents']['Reliance.bin']['changes'].append({'section':'matrix','row':-1,'offset':0x20,'value':[1,2]})
        with self.assertRaises(DataError):load_suite_project(docs,bad)
        self.assertEqual(d.changes,before);self.assertIs(d.changes,v.changes)
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);sources={}
            for name,doc in docs.items():
                p=base/'source'/doc.filename;p.parent.mkdir(exist_ok=True);p.write_bytes(doc.raw);sources[name]=p
            paths=export_suite(docs,sources,base/'mod');self.assertEqual(len(paths),2)
            r=Reliance((base/'mod/romfs/GameData/Reliance.bin').read_bytes());compare(self,d,r,before)
            self.assertEqual(sources['Supports & Recruitment'].read_bytes(),d.raw)
        load_suite_project(docs,docs['Characters'].project());self.assertFalse(d.changes)
        load_suite_project(docs,project['documents']['Reliance.bin']);self.assertTrue(d.changes)


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent'))
@unittest.skipUnless((DATA/'Reliance.bin').is_file(),'Set FW_GAME_DATA for real Reliance regression.')
class RealRelianceTests(unittest.TestCase):
    def test_all_guard_activation_rows_and_levels_preserve_native_data(self):
        d=Reliance((DATA/'Reliance.bin').read_bytes());v=d.views['assist']
        self.assertEqual(len(v.records),8)
        for index,r in enumerate(v.records):v.set_guard_rates(r,[index,20,40,60,100])
        result=Reliance(d.build());compare(self,d,result,dict(d.changes))
        other=Reliance(d.raw);other.load_project(json.loads(json.dumps(d.project())))
        self.assertEqual(other.build(),result.raw)

    def test_every_section_field_matrix_cell_and_native_byte_preserved(self):
        d=Reliance((DATA/'Reliance.bin').read_bytes());self.assertEqual({k:len(v.records) for k,v in d.views.items()},
            {'matrix':73,'special':314,'talks':515,'scout':214,'assist':8,'voices':165,'drinks':3})
        self.assertEqual(len(snapshot(d)),20033);self.assertEqual(d.build(),d.raw)
        for view in d.views.values():
            for row in view.records:
                for field in view.fields:view.set(row,field,view.original(row,field))
        self.assertFalse(d.changes)
        updates=[('matrix',4,0x20,[7]*73),('special',0,0x20,'PID_マジーデ'),('special',0,0x40,-32768),
                 ('talks',0,0x58,['test_flag','2部']),('scout',1,0x21,0),('scout',1,0x50,'IID_試作品１号|||'),
                 ('assist',1,0x20,[0,1,2,3,4]),('voices',0,0x40,'test_voice'),('drinks',1,0x20,['IID_傷薬'])]
        for section,index,offset,value in updates:
            v=d.views[section];v.set(v.records[index],v.by_offset[offset],value)
        result=Reliance(d.build());compare(self,d,result,dict(d.changes))
        # Directional cell replacement must never silently mirror another row.
        m=d.views['matrix'];rm=result.views['matrix']
        self.assertEqual(m.original(m.records[5],m.by_offset[0x20]),rm.original(rm.records[5],rm.by_offset[0x20]))
        v=result.views['drinks'];v.set(v.records[0],v.by_offset[0x20],[])
        again=Reliance(result.build());self.assertEqual(again.views['drinks'].original(again.views['drinks'].records[0],v.by_offset[0x20]),[])
