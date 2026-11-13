"""Fixed unit slots, nested source paths, current references and original bytes."""
import copy
import os
from pathlib import Path
import struct
import tempfile
import unittest
from fw_editor import Deployment,DeploymentView,Binary,DataError,read_editable_tables,suite_project,load_suite_project,export_suite
from deployment_data import EXPECTED,battle_links
from fixture import deployment_fixture
from item_index import ItemIndex
from skill_index import SkillIndex
from test_shops import verify,snapshot


class DeploymentTests(unittest.TestCase):
    def setUp(self):self.doc=Deployment(deployment_fixture(),'Dispos/SYNTHETIC.bin');self.view=self.doc.views['units']
    def test_slots_empty_group_and_exact_unchanged_source(self):
        d=self.doc;v=self.view
        self.assertEqual(d.build(),d.raw);self.assertEqual(len(v.fields),42)
        self.assertEqual([len(v.rows_by_table[r.pid]) for r in v.collections],[1,0,2])
        self.assertIs(d.changes,v.changes);self.assertEqual(v.names['units:2'],'Enemy')
        self.assertEqual(v.original(v.records[0],v.by_offset[0x34]),-1)

    def test_exact_numeric_bytes_and_signed_bounds(self):
        d=self.doc;v=self.view;r=v.records[0];expected=bytearray(d.raw)
        for offset,fmt,value in [(0x34,'b',-128),(0x37,'b',127),(0x30,'B',255),(0x32,'H',65535),(0x78,'I',0xffffffff)]:
            v.set(r,v.by_offset[offset],value);struct.pack_into('<'+fmt,expected,r.offset+offset,value)
        self.assertEqual(d.build(),bytes(expected))
        for offset,value in [(0x34,-129),(0x37,128),(0x30,256),(0x32,65536),(0x78,-1),(0x130,128)]:
            with self.assertRaises(DataError):v.set(r,v.by_offset[offset],value)

    def test_every_field_joint_export_reopen_and_opaque_bytes(self):
        d=self.doc;v=self.view;r=v.records[0]
        for f in v.fields:
            value='REFERENCE_'+str(f.offset)+' ★' if f.kind in ('string','data') else -128 if f.kind=='s8' else 3
            v.set(r,f,value)
        result=Deployment(d.build(),d.filename);verify(self,d,result)
        for r in v.records:
            a=d.raw[r.offset:r.offset+32];b=result.raw[r.offset:r.offset+32]
            self.assertEqual(a[:8]+a[16:],b[:8]+b[16:])
        again=result.views['units'];again.set(again.records[0],again.by_offset[0x20],'')
        final=Deployment(result.build(),d.filename)
        self.assertEqual(final.views['units'].original(final.records[0],again.by_offset[0x20]),'')

    def test_projects_source_hash_collision_and_transactional_replacement(self):
        d=self.doc;v=self.view;v.set(v.records[0],v.by_offset[0x3b],99)
        project=d.project();self.assertEqual(project['format'],'fw-deployment-edits-v1')
        other=Deployment(d.raw,'Dispos/OTHER.bin')
        with self.assertRaises(DataError):other.load_project(project)
        for change in [{'source_sha256':'wrong'},{'source_file':'../wrong.bin'},
                       {'changes':project['changes']+[{'pid':'units:0:99','offset':0x20,'value':'bad'}]}]:
            bad=copy.deepcopy(project);bad.update(change);before=copy.deepcopy(d.changes)
            with self.assertRaises((DataError,KeyError)):d.load_project(bad)
            self.assertEqual(d.changes,before)
        docs={'one':d,'two':other};before={k:dict(doc.changes) for k,doc in docs.items()};bad=suite_project(docs)
        bad['documents']['Dispos/OTHER.bin']['source_sha256']='wrong'
        with self.assertRaises(DataError):load_suite_project(docs,bad)
        self.assertEqual(before,{k:doc.changes for k,doc in docs.items()})
        load_suite_project(docs,project);self.assertEqual(d.changes,before['one'])
        empty={**project,'changes':[]};d.load_project(empty);self.assertEqual(d.changes,{})

    def test_reset_group_and_current_item_skill_references(self):
        d=self.doc;v=self.view
        for r in v.records:v.set(r,v.by_offset[0x3b],100)
        v.reset_table('units:0');self.assertEqual(len(d.changes),2)
        row=v.records[0];v.set(row,v.by_offset[0x68],'IID_NEW|||')
        uses=ItemIndex().uses('IID_NEW|||',{'deployment':d})
        self.assertEqual([(u.source,u.module,u.record) for u in uses],[(d.filename,'Battle deployment',row.pid)])
        self.assertFalse(any(u.record==row.pid for u in ItemIndex().uses('IID_SYNTHETIC_A|',{'deployment':d})))
        v.set(row,v.by_offset[0xe8],'SID_NEW');self.assertEqual(SkillIndex().uses('SID_NEW',{'deployment':d})[0].module,'Battle deployment')

    def test_nested_export_no_backups_and_original_protection(self):
        d=self.doc;v=self.view;v.set(v.records[0],v.by_offset[0x20],'PID_NEW')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'romfs/GameData'/d.filename;source.parent.mkdir(parents=True);source.write_bytes(d.raw)
            docs={'Battle deployment':d};sources={'Battle deployment':source}
            with self.assertRaises(DataError):export_suite(docs,sources,root)
            mod=root/'mod';export_suite(docs,sources,mod);target=mod/'romfs/GameData'/d.filename
            verify(self,d,Deployment(target.read_bytes(),d.filename));self.assertEqual(source.read_bytes(),d.raw)
            export_suite(docs,sources,mod);self.assertEqual(len(list(target.parent.glob('*.backup-*'))),0)
            self.assertEqual(set(suite_project(docs)['documents']),{d.filename})
            loaded,_=read_editable_tables(root/'romfs/GameData');self.assertEqual(len(loaded),1)
            self.assertEqual(next(iter(loaded.values())).filename,d.filename)

    def test_schema_and_filename_guards(self):
        for filename in ['SYNTHETIC.bin','../Dispos/a.bin','Dispos/../a.bin','Dispos/a/b.bin','/Dispos/a.bin']:
            with self.assertRaises(DataError):Deployment(self.doc.raw,filename)
        raw=bytearray(self.doc.raw);group=list(Binary(raw).groups())[0]
        struct.pack_into('<I',raw,group[3]+28,0x24)
        with self.assertRaises(DataError):Deployment(bytes(raw),self.doc.filename)


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent/fw-game-data'))
@unittest.skipUnless((DATA/'Dispos').is_dir(),'Set FW_GAME_DATA for private real-data regressions.')
class RealDeploymentTests(unittest.TestCase):
    def test_all_171_sources_roundtrip_and_joint_values(self):
        docs,_=read_editable_tables(DATA);sources=[d for d in docs.values() if isinstance(d,Deployment)]
        self.assertEqual(len(sources),171);self.assertEqual(sum(len(d.records) for d in sources),6715)
        self.assertEqual(sum(len(d.views['units'].collections) for d in sources),1415)
        fields=0
        for d in sources:
            self.assertEqual(d.build(),d.raw);v=d.views['units'];fields+=len(v.records)*42
            if not v.records:continue
            row=v.records[0];v.set(row,v.by_offset[0x20],'PID_SYNTHETIC_TEST');v.set(row,v.by_offset[0x36],-128)
            v.set(row,v.by_offset[0x68],'IID_SYNTHETIC_TEST|||');v.set(row,v.by_offset[0xf8],'synthetic argument')
            verify(self,d,Deployment(d.build(),d.filename))
        self.assertEqual(fields,282030)
    def test_battlefield_links_are_exact_and_read_only(self):
        links=battle_links(DATA,Binary);self.assertEqual(len(links),138)
        self.assertEqual(next(x for x in links if x['id']=='SC00_00')['deployment'],'SC00_00')
        self.assertTrue(all(set(x)=={'id','deployment','revealed','title','script','terrain'} for x in links))
