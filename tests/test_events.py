"""Event identities, ordered schedules, cape-rule evidence and wrapper inspection."""
from copy import deepcopy
import hashlib,json,os,struct,tempfile,unittest
from pathlib import Path
from fw_editor import EventData,EVENT_FILES,DataError,Person,suite_project,load_suite_project,export_suite,decompress,read_editable_tables
from event_data import EXPECTED,LAYOUTS
from event_ui import CAPE,EQUIPPED,DIT_EQUIPPED,RECEIVED,LOST
from script_inspector import inspect
from fixture import grouped_fixture,person_fixture
from test_shops import verify,snapshot
from person_index import uses as person_uses


def event_fixture(key='variables'):
    title,native,stride,count,container=LAYOUTS[key]
    fields=[('Event_'+str(off),kind,size,off) for off,(kind,size) in sorted(EXPECTED[key].items())]
    values={}
    for off,(kind,size) in EXPECTED[key].items():
        if kind=='string[,]':values[off]=[['FLAG_A','!FLAG_B'],[]]
        elif kind=='string[]':values[off]=['ARG_A','ARG_B']
        elif kind=='data':values[off]='PID_SYNTHETIC_0'
        elif kind=='string':values[off]='FLAG_NAME' if off==0x20 else 'TEXT_'+str(off)
        else:values[off]=0
    if key=='timeline':rows=[('Timeline_First',[(None,values),(None,values)]),('Timeline_Empty',[])];mode=2
    else:rows=[('First',{**values,**({0x20:'FLAG_FIRST'} if key=='variables' else {})}),('Second',values)];mode=1
    return grouped_fixture([(native,stride,fields,rows,mode),('Opaque event auxiliary',40,[('Opaque','string',8,0x20)],[('AUX_EVENT',{0x20:'retained opaque bytes'})])])


def file_for(key):return {'variables':'Variable.bin','timeline':'Timeline_Com.bin','chapter':'Chapter.bin','situations':'Situation.bin'}[key]


class EventTests(unittest.TestCase):
    def test_all_four_layouts_noop_and_native_identity_headers(self):
        for key in LAYOUTS:
            d=EventData(event_fixture(key),file_for(key));self.assertEqual(d.build(),d.raw)
            v=d.views[key];self.assertEqual(len(v.collections),2);self.assertEqual(len(v.records),2)
            self.assertEqual(v.names[v.collections[0].pid],'FLAG_FIRST' if key=='variables' else 'Timeline_First' if key=='timeline' else 'First')
            for r in v.records:
                for f in v.fields:v.original(r,f)
            if key=='timeline':self.assertFalse(v.rows_by_table[v.collections[1].pid])

    def test_mixed_fields_dates_arguments_groups_and_opaque_bytes(self):
        for key in LAYOUTS:
            d=EventData(event_fixture(key),file_for(key));v=d.views[key];r=v.records[0]
            for f in v.fields:
                if f.offset in v.locked_offsets:continue
                value=[['FLAG_NEW'],[],['FLAG_新規']] if f.kind=='string[,]' else ['ARG_NEW','ARG_新規'] if f.kind=='string[]' else 'NEW_新規' if f.kind in ('string','data') else -1 if f.kind.startswith('s') or f.kind=='int' else 1
                v.set(r,f,value)
            result=EventData(d.build(),d.filename);verify(self,d,result)
            self.assertEqual(result.views[key].rows_by_table.keys(),v.rows_by_table.keys())

    def test_names_hashes_ranges_and_text_validation(self):
        for key in LAYOUTS:
            d=EventData(event_fixture(key),file_for(key));v=d.views[key];r=v.records[0]
            for off in v.locked_offsets:
                with self.assertRaises(DataError):v.set(r,v.by_offset[off],'rename')
            for f in v.fields:
                if f.offset in v.locked_offsets:continue
                bad=256 if f.kind=='u8' else 65536 if f.kind=='u16' else 128 if f.kind=='s8' else 32768 if f.kind=='s16' else 1<<31 if f.kind=='int' else 'bad\0text' if f.kind in ('data','string') else ['not a nested row'] if f.kind=='string[,]' else ['']
                with self.assertRaises(DataError):v.set(r,f,bad)
            self.assertFalse(d.modified)

    def test_shared_nested_conditions_copy_on_write(self):
        d=EventData(event_fixture(),'Variable.bin');v=d.views['variables'];a,b=v.records
        raw=bytearray(d.raw);pointer=struct.unpack_from('<Q',raw,a.offset+0x58)[0];struct.pack_into('<Q',raw,b.offset+0x58,pointer)
        d=EventData(bytes(raw),'Variable.bin');v=d.views['variables'];a,b=v.records;old=v.value(b,v.by_offset[0x50])
        v.set(a,v.by_offset[0x50],[['ONLY_NEW']]);result=EventData(d.build(),d.filename)
        self.assertEqual(result.views['variables'].value(result.by_pid[b.pid],v.by_offset[0x50]),old)

    def test_source_schema_headers_and_filename_guards(self):
        raw=event_fixture()
        with self.assertRaises(DataError):EventData(raw,'../../Variable.bin')
        with self.assertRaises(DataError):EventData(raw,'Timeline_Com.bin')
        d=EventData(raw,'Variable.bin');g=next(d.groups());broken=bytearray(raw);struct.pack_into('<I',broken,g[3]+28,0x21)
        with self.assertRaises(DataError):EventData(bytes(broken),'Variable.bin')
        broken=bytearray(raw);struct.pack_into('<H',broken,d.records[0].offset+18,2)
        with self.assertRaises(DataError):EventData(bytes(broken),'Variable.bin')

    def test_projects_are_file_specific_transactional_and_replay_lists(self):
        d=EventData(event_fixture(),'Variable.bin');v=d.views['variables'];v.set(v.records[0],v.by_offset[0x50],[['NEW'],[]]);before=d.project()
        other=EventData(d.raw,d.filename);load_suite_project({'Events':other},json.loads(json.dumps(before)));self.assertEqual(other.build(),d.build())
        for mode in ('file','sha','format','lock','value'):
            bad=deepcopy(before)
            if mode=='file':bad['source_file']='Variable_P0.bin'
            elif mode=='sha':bad['source_sha256']='wrong'
            elif mode=='format':bad['format']='unknown'
            elif mode=='lock':bad['changes'].append({'pid':v.records[0].pid,'offset':0x20,'value':'rename'})
            else:bad['changes'].append({'pid':v.records[0].pid,'offset':0x48,'value':256})
            with self.assertRaises(DataError):d.load_project(bad)
            self.assertEqual(d.project(),before)

    def test_suite_rollback_legacy_clear_and_event_pid_references(self):
        p=Person(person_fixture());new=p.create_character('PID_NewEvent');d=EventData(event_fixture(),'Variable.bin');v=d.views['variables']
        v.set(v.records[0],v.by_offset[0x50],[[new.pid]])
        docs={'Characters':p,'Events':d};self.assertTrue(any(u.module=='Events' and u.source=='Variable.bin' for u in person_uses(new.pid,docs)))
        before=suite_project(docs);bad=deepcopy(before);bad['documents']['Variable.bin']['changes'].append({'pid':v.records[0].pid,'offset':0x20,'value':'rename'})
        with self.assertRaises(DataError):load_suite_project(docs,bad)
        self.assertEqual(suite_project(docs),before)
        load_suite_project(docs,Person(p.raw).project());self.assertFalse(d.modified);self.assertFalse(p.new_characters)

    def test_export_source_protection_manifest_no_backup_and_reedit(self):
        d=EventData(event_fixture('timeline'),'Timeline_Com.bin');v=d.views['timeline'];v.set(v.records[0],v.by_offset[0x28],['BD_Custom'])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'game/romfs/GameData'/d.filename;source.parent.mkdir(parents=True);source.write_bytes(d.raw)
            export_suite({'Events':d},{'Events':source},root/'mod');target=root/'mod/romfs/GameData'/d.filename
            result=EventData(target.read_bytes(),d.filename);w=result.views['timeline'];self.assertEqual(w.value(w.records[0],w.by_offset[0x28]),['BD_Custom'])
            w.set(w.records[0],w.by_offset[0x28],[]);self.assertTrue(result.build())
            export_suite({'Events':d},{'Events':source},root/'mod');self.assertEqual(len(list(target.parent.glob('*.backup-*'))),0)
            self.assertEqual(source.read_bytes(),d.raw)
            self.assertEqual(json.loads((root/'mod/suite-edits.json').read_text())['documents'][d.filename]['format'],'fw-event-edits-v1')
            with self.assertRaises(DataError):export_suite({'Events':d},{'Events':source},root/'game')

    def test_asf_wrapper_imports_evidence_and_malformed_bounds(self):
        header=bytearray(176);header[:4]=b'ASF\0';payload=b'NativeFunction\0CALLSYS\0';struct.pack_into('<III',header,4,176,len(payload),1);header[16:27]=b'Script/Test'
        raw=bytes(header)+payload;i=inspect(raw);self.assertEqual(i.imports,('Script/Test',));self.assertIn('NativeFunction',i.identifiers)
        self.assertEqual(i.payload_size,len(payload));self.assertEqual(raw,bytes(header)+payload)
        for invalid in (b'',b'NotASF',raw[:-1],b'ASF\0'+struct.pack('<III',5,0,99)):
            with self.assertRaises(ValueError):inspect(invalid)


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent/fw-game-data'))
@unittest.skipUnless((DATA/'Variable.bin').is_file(),'Set FW_GAME_DATA for native event regressions.')
class RealEventTests(unittest.TestCase):
    def test_all_72545_values_thirteen_sources_and_untouched_bytes(self):
        total=0
        for filename in EVENT_FILES:
            d=EventData((DATA/filename).read_bytes(),filename);v=next(iter(d.views.values()));total+=len(v.records)*len(v.fields)
            self.assertEqual(d.build(),d.raw)
            for f in v.fields:
                if f.offset in v.locked_offsets:continue
                r=v.records[0];old=v.value(r,f)
                value=[['TEST'],[],['FLAG_TEST']] if f.kind=='string[,]' else ['TEST_A','TEST_B'] if f.kind=='string[]' else 'TEST_NEW' if f.kind in ('data','string') else 1
                v.set(r,f,value)
            verify(self,d,EventData(d.build(),filename));self.assertEqual(d.raw,(DATA/filename).read_bytes())
        self.assertEqual(total,72545)

    def test_exact_cape_chain_date_duel_and_condition_patch(self):
        d=EventData((DATA/'Variable.bin').read_bytes(),'Variable.bin');v=d.views['variables']
        get=lambda i,off:v.value(v.records[i],v.by_offset[off])
        self.assertEqual(get(871,0x20),CAPE);self.assertEqual(get(871,0x50),[[EQUIPPED]])
        self.assertEqual(get(1216,0x50),[[RECEIVED,'!'+LOST]]);self.assertEqual(get(1217,0x50),[[LOST]])
        self.assertEqual([get(1486,o) for o in (0x60,0x62,0x63,0x64)],[1449,3,8,1459])
        t=EventData((DATA/'Timeline_Part1_Dit.bin').read_bytes(),'Timeline_Part1_Dit.bin').views['timeline']
        self.assertEqual(t.value(t.by_pid['timeline:0:82'],t.by_offset[0x28]),['BD12_04'])
        self.assertEqual(t.value(t.by_pid['timeline:0:85'],t.by_offset[0x28]),['漆黒のグウェン'])
        v.set(v.records[1216],v.by_offset[0x50],[[RECEIVED]]);result=EventData(d.build(),d.filename);verify(self,d,result)
        self.assertEqual(result.views['variables'].value(result.records[1216],v.by_offset[0x50]),[[RECEIVED]])

    def test_native_all_183_compiled_wrappers_are_read_only(self):
        paths=list((DATA.parent/'Script').rglob('*.bin.zst'));self.assertEqual(len(paths),183)
        for path in paths:
            raw=path.read_bytes();before=hashlib.sha256(raw).digest();info=inspect(decompress(raw))
            self.assertEqual(info.payload_offset,0x2010);self.assertTrue(all(p.startswith('Script/') for p in info.imports))
            self.assertEqual(hashlib.sha256(path.read_bytes()).digest(),before)

    def test_combined_204_file_projects_exports_and_legacy_clear(self):
        docs,sources=read_editable_tables(DATA);self.assertEqual(len(docs),204)
        d=docs['Events'];v=d.views['variables'];v.set(v.records[1216],v.by_offset[0x50],[[RECEIVED]])
        p=docs['Characters'];p.create_character('PID_EventIntegration')
        other,_=read_editable_tables(DATA);load_suite_project(other,json.loads(json.dumps(suite_project(docs))));self.assertEqual(suite_project(other),suite_project(docs))
        with tempfile.TemporaryDirectory() as tmp:
            export_suite(other,sources,Path(tmp)/'mod');self.assertEqual(len(list((Path(tmp)/'mod/romfs/GameData').rglob('*.bin'))),204)
            q=EventData((Path(tmp)/'mod/romfs/GameData/Variable.bin').read_bytes(),'Variable.bin');self.assertEqual(q.views['variables'].value(q.records[1216],q.views['variables'].by_offset[0x50]),[[RECEIVED]])
        legacy=Person(docs['Characters'].raw).project();load_suite_project(other,legacy);self.assertFalse(any(d.modified for d in other.values()))
