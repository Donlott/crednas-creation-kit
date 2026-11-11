"""Actual serialized script rebuilding, alias caches, restricted edits and mod routing."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from script_bytecode import Module, ScriptError, encoded, OPCODES, INVERSE, LITERALS
from script_data import ScriptDocument, compress, valid_source, load_with_scripts
from fw_editor import Person, suite_project, load_suite_project, export_suite, decompress, DataError
from fixture import person_fixture


def op(name,*args):
    return bytes([next(i for i,(n,layout) in enumerate(OPCODES) if n==name)])+b''.join(encoded(x) for x in args)


def fixture():
    """One function whose name and first runtime string share the serialized cache."""
    s=lambda text:encoded(len(text.encode('utf8'))*2)+text.encode('utf8')
    # New void type; no args; script kind; no receiver or namespace.
    signature=s('SharedName')+b'\0'+encoded(80)+b'\0\0\x01\0\0'
    commands=[op('PGA',0),op('PshC4',5),op('SetV4',1,0x3f800000),op('JZ',1),op('PshC4',0),op('CALLSYS',0),op('RET',0)]
    func=b'f'+signature+b'\0'+encoded(len(commands))+b''.join(commands)+b'\0'
    # Engine call signatures reuse void type index 1.
    system=lambda name:s(name)+b'\x01\0\0\0\0'
    payload=b'\x01\0\0\0\0\0\x01'+func+b'\x01r\0'+b'\0\0\0'+b'\x02'+b'a'+system('Enable')+b'a'+system('Disable')+b'\0'+b'\x02'+b'\x01'+s('日本語')+b'\0'
    header=bytearray(0x2010);header[:4]=b'ASF\0';struct.pack_into('<III',header,4,len(header),len(payload),0)
    return bytes(header)+payload


class ScriptEditorTests(unittest.TestCase):
    def doc(self):return ScriptDocument(compress(fixture()),'Script/cmdbtl/Test.bin.zst')

    def test_reference_fixture_and_untouched_identity(self):
        d=self.doc();self.assertEqual(d.build(),d.raw);self.assertEqual(d.build_raw(),fixture())
        self.assertEqual(len(d.module.functions),1);self.assertEqual(len(d.module.functions[0].instructions),7)
        self.assertEqual([c.text for c in d.module.constants],['SharedName','日本語'])
        self.assertEqual(d.module.used_functions[0].label,'Enable()')
        self.assertIn('string[0]',d.module.describe(d.module.functions[0].instructions[0]))

    def test_signed_variable_encoding_boundaries(self):
        for value in [0,63,64,8191,8192,(1<<20)-1,1<<20,(1<<27)-1,1<<27,1<<34,1<<41,1<<48,(1<<64)-1,-1,-64,-(1<<63)]:
            m=object.__new__(Module);m.raw=encoded(value);m.at=0
            self.assertEqual(m.integer(),value);self.assertEqual(m.at,len(m.raw))
        for invalid in [True,1.0,1<<64,-(1<<63)-1]:
            with self.assertRaises(ScriptError):encoded(invalid)

    def test_variable_length_strings_shared_metadata_and_empty_references(self):
        d=self.doc()
        for value in ['A much longer replacement 日本語','', '日本語', 'SharedName', '短']:
            d.set_string(0,value);result=Module(d.build_raw())
            self.assertEqual(result.constants[0].text,value)
            self.assertEqual(result.functions[0].signature.name,'SharedName')
            self.assertEqual(result.constants[1].text,'日本語')
            self.assertEqual(result.info.payload_size,len(result.raw)-result.info.payload_offset)
            self.assertEqual(result.raw[:8],d.module.raw[:8]);self.assertEqual(result.raw[12:0x2010],d.module.raw[12:0x2010])
        d.set_string(0,'SharedName');self.assertFalse(d.modified);self.assertEqual(d.build(),d.raw)
        with self.assertRaises(ScriptError):d.set_string(1,'bad\0text')
        with self.assertRaises(ScriptError):d.set_string(-1,'bad')

    def test_numeric_literals_branch_inversion_and_compatible_calls(self):
        d=self.doc();ins=d.module.functions[0].instructions
        d.set_instruction(0,1,ins[1].opcode,[-12]);d.set_instruction(0,2,ins[2].opcode,[1,0x40000000])
        inverse=next(i for i,(name,t) in enumerate(OPCODES) if name=='JNZ')
        d.set_instruction(0,3,inverse,ins[3].arguments);d.set_instruction(0,5,ins[5].opcode,[1])
        m=Module(d.build_raw());self.assertEqual(m.functions[0].instructions[1].arguments,(-12,))
        self.assertEqual(m.functions[0].instructions[3].name,'JNZ');self.assertEqual(m.functions[0].instructions[3].arguments,(1,))
        self.assertEqual(m.describe(m.functions[0].instructions[5]),'Disable()')
        self.assertEqual(d.module.call_options(ins[5]),((0,'Enable()'),(1,'Disable()')))
        self.assertEqual(len(m.functions[0].instructions),7)

    def test_unsupported_instruction_changes_cannot_be_saved(self):
        d=self.doc();ins=d.module.functions[0].instructions
        attempts=[(1,ins[1].opcode,[1<<32]),(2,ins[2].opcode,[9,1]),(3,ins[3].opcode,[0]),
                  (5,ins[5].opcode,[99]),(0,ins[0].opcode,[2]),(6,ins[6].opcode,[2]),(1,True,[1])]
        for ii,opcode,args in attempts:
            with self.assertRaises(ScriptError):d.set_instruction(0,ii,opcode,args)
            self.assertFalse(d.modified)
        # Return type mismatch excludes an otherwise existing engine call.
        old=d.module.used_functions[1]
        from dataclasses import replace
        d.module.used_functions[1]=replace(old,result=(68,None,0))
        with self.assertRaises(ScriptError):d.set_instruction(0,5,ins[5].opcode,[1])

    def test_script_project_replay_identity_and_transactional_rejection(self):
        d=self.doc();d.set_string(0,'Changed');project=json.loads(json.dumps(d.project()));fresh=self.doc();fresh.load_project(project)
        self.assertEqual(fresh.build_raw(),d.build_raw());before=d.snapshot_edits()
        for change in ['sha','source','opcode','duplicate','range']:
            bad=deepcopy(project)
            if change=='sha':bad['source_sha256']='wrong'
            if change=='source':bad['source_file']='Script/cmdbtl/Other.bin.zst'
            if change=='opcode':bad['instructions']=[{'function':0,'instruction':3,'opcode':12,'arguments':[0]}]
            if change=='duplicate':bad['strings']*=2
            if change=='range':bad['strings'][0]['index']=-1
            with self.assertRaises((ScriptError,ValueError)):d.load_project(bad)
            self.assertEqual(d.snapshot_edits(),before)

    def test_suite_export_routes_preserves_compression_and_protects_sources(self):
        d=self.doc();d.set_string(1,'New runtime constant');person=Person(person_fixture());docs={'Characters':person,'Scripts · Test':d}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);game=root/'game/romfs';base=game/'GameData';base.mkdir(parents=True);(base/'Person.bin').write_bytes(person.raw)
            source=game/d.filename;source.parent.mkdir(parents=True);source.write_bytes(d.raw);sources={'Characters':base/'Person.bin','Scripts · Test':source}
            targets=export_suite(docs,sources,root/'mod');self.assertEqual(len(targets),2)
            target=root/'mod/romfs'/d.filename;self.assertTrue(target.is_file());self.assertFalse((root/'mod/romfs/GameData'/d.filename).exists())
            fresh=ScriptDocument(target.read_bytes(),d.filename);self.assertEqual(fresh.module.constants[1].text,'New runtime constant')
            self.assertEqual(source.read_bytes(),d.raw)
            export_suite(docs,sources,root/'mod');self.assertEqual(len(list(target.parent.glob('*.backup-*'))),1)
            with self.assertRaises(DataError):export_suite(docs,sources,root/'game')
            project=suite_project(docs);self.assertEqual(project['format'],'fw-hacking-suite-project-v2')
            loaded={'Characters':Person(person.raw)};loaded_sources={'Characters':base/'Person.bin'}
            load_with_scripts(loaded,loaded_sources,base,project)
            self.assertEqual(suite_project(loaded),project)
            self.assertEqual(next(v for v in loaded.values() if isinstance(v,ScriptDocument)).build_raw(),d.build_raw())
            # A later invalid table edit must roll back script edits and membership too.
            before=suite_project(loaded);bad=deepcopy(project);bad['documents']['Person.bin']['source_sha256']='bad'
            with self.assertRaises(ValueError):load_with_scripts(loaded,loaded_sources,base,bad)
            self.assertEqual(suite_project(loaded),before)
            load_suite_project(loaded,person.project());self.assertFalse(any(v.modified for v in loaded.values()))

    def test_path_traversal_and_missing_sources_are_rejected(self):
        for name in ['Script/../Person.bin','../Script/x.bin','Script/a/../../x.bin','Script\\a\\x.bin','/Script/a/x.bin','Script//x.bin','Script/a/C:x.bin']:
            self.assertFalse(valid_source(name))
        with tempfile.TemporaryDirectory() as tmp:
            for name in ['Script/../x.bin','Script/a/missing.bin.zst']:
                with self.assertRaises(ScriptError):load_with_scripts({}, {},Path(tmp)/'GameData',{'format':'fw-hacking-suite-project-v2','documents':{name:{}}})

    def test_loaded_script_string_references_follow_current_edits(self):
        from person_index import uses as person_uses
        from class_index import uses as class_uses
        from item_index import ItemIndex
        from skill_index import SkillIndex
        d=self.doc();docs={'Scripts · Test':d}
        for prefix,finder in [('PID_',person_uses),('JID_',class_uses),('IID_',ItemIndex().uses),('SID_',SkillIndex().uses)]:
            d.set_string(0,prefix+'ScriptTest')
            refs=finder(prefix+'ScriptTest',docs)
            self.assertTrue(any(u.source==d.filename and u.record=='SCRIPT_STRING_0' for u in refs))
            d.set_string(0,'SharedName');self.assertFalse(finder(prefix+'ScriptTest',docs))

    def test_malformed_wrapper_payload_unknown_layout_and_opcode(self):
        raw=fixture();module=Module(raw)
        for bad in [b'',raw[:-1],raw+b'junk']:
            with self.assertRaises(ValueError):Module(bad)
        for where,value in [(0x2010,0),(module.functions[0].instructions[0].start,250)]:
            bad=bytearray(raw);bad[where]=value
            with self.assertRaises(ScriptError):Module(bad)
        bad=bytearray(raw);bad[module.functions[0].instructions[5].end-1]=50
        with self.assertRaises(ScriptError):Module(bad)


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent/fw-game-data'))
@unittest.skipUnless((DATA.parent/'Script').is_dir(),'Set FW_GAME_DATA for native script round trips.')
class NativeScriptTests(unittest.TestCase):
    def test_all_183_native_scripts_parse_rebuild_and_mutate(self):
        paths=sorted((DATA.parent/'Script').rglob('*.bin.zst'));self.assertEqual(len(paths),183);counts=[0,0,0]
        for path in paths:
            original=path.read_bytes();d=ScriptDocument(original,'Script/'+path.relative_to(DATA.parent/'Script').as_posix());m=d.module
            self.assertEqual(d.build(),original)
            unedited=Module(m.rebuild({},{}));self.assertEqual([f.signature for f in unedited.functions],[f.signature for f in m.functions])
            self.assertEqual(unedited.info.imports,m.info.imports)
            if m.constants:d.set_string(0,'FW test longer 日本語 constant')
            changed=False
            for fi,function in enumerate(m.functions):
                for ii,ins in enumerate(function.instructions):
                    if not changed and ins.name in LITERALS:
                        d.set_instruction(fi,ii,ins.opcode,(*ins.arguments[:-1],17));changed=True
            rebuilt=Module(d.build_raw());self.assertEqual(len(rebuilt.functions),len(m.functions))
            if m.constants:self.assertEqual(rebuilt.constants[0].text,'FW test longer 日本語 constant')
            self.assertEqual(path.read_bytes(),original)
            counts[0]+=len(m.functions);counts[1]+=sum(len(f.instructions) for f in m.functions);counts[2]+=len(m.constants)
        self.assertEqual(counts,[10554,490221,11536])
