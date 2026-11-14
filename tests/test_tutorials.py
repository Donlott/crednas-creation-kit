"""Native scheduler preservation, reviewed programs, migration and blocked effects."""
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import hashlib,json,os,struct,tempfile,unittest
from fw_editor import EventData,suite_project,load_suite_project,export_suite
from script_data import ScriptDocument,compress,load_with_scripts
from script_bytecode import Module,ScriptError,OPCODES,encoded
from test_events import event_fixture
import tutorial_data as td


def script_fixture():
    s=lambda text:encoded(len(text.encode())*2)+text.encode()
    def op(name,*args):return bytes([next(i for i,(n,_) in enumerate(OPCODES) if n==name)])+b''.join(encoded(x) for x in args)
    sig=s('SyntheticIntro')+b'\0'+encoded(80)+b'\0\0\x01\0\0'
    code=[op('SUSPEND'),op('PGA',0),op('RET',0)]
    fun=b'f'+sig+b'\0'+encoded(len(code))+b''.join(code)+b'\0'
    string_ref=b'\0'+encoded(5)+b'o'+s('string')+b'\0'+bytes([12])
    boolean=b'\0'+encoded(65)+b'\0'
    setter=s('EntryFlag')+b'\x01\x02'+string_ref+boolean+b'\x02\x03\0'+b'\0\0\0'+s('hub')
    jump=s('ReserveJumpNextTimeline')+b'\x01\0\0\0'+s('hub')
    payload=b'\x01\0\0\0\0\0\x01'+fun+b'\x01r\0'+b'\0\0\0'+b'\x02a'+setter+b'a'+jump+b'\0'+b'\x02'+s('SyntheticIntro')+s('日本語')+b'\0'
    header=bytearray(0x2010);header[:4]=b'ASF\0';struct.pack_into('<III',header,4,len(header),len(payload),0)
    return bytes(header)+payload


def fixture():
    d=EventData(event_fixture('timeline'),'Timeline_Com.bin');v=d.views['timeline'];r=v.records[0]
    v.set(r,v.by_offset[0x21],13);v.set(r,v.by_offset[0x28],['スクリプト呼出','SyntheticIntro'])
    d=EventData(d.build(),d.filename);v=d.views['timeline'];r=v.records[0]
    script=ScriptDocument(compress(script_fixture()),'Script/hub/Synthetic.bin.zst')
    p=replace(next(p for p in td.PRESETS if p.key=='cai-trading'),key='synthetic',rows=((d.filename,r.pid,td.row_digest(v,r)),),
              script=script.filename,script_sha=script.sha256,hook='SyntheticIntro',flags=('FLAG_UNLOCK','FLAG_REVEALED'),read_keys=())
    return {'Events':d,'Script':script},p


def execute_program(test,module,fi,args=(),flags=None,reads=()):
    """Bounded opcode interpreter for stack/branch/native-call contracts only."""
    stack=[];flags={} if flags is None else flags;advances=0;grants=[];freed=[];locals_={};result=None;pc=0;steps=0
    code=module.functions[fi].instructions
    while pc<len(code):
        steps+=1;test.assertLess(steps,50000);ins=code[pc];pc+=1
        if ins.name=='SUSPEND':continue
        if ins.name=='PshC4':stack.append(ins.arguments[0])
        elif ins.name=='PGA':
            test.assertEqual(ins.arguments[0]&1,0);stack.append(module.constants[ins.arguments[0]>>1].text)
        elif ins.name=='PshVPtr':stack.append(args[-ins.arguments[0]])
        elif ins.name=='CpyRtoV4':locals_[ins.arguments[0]]=result
        elif ins.name=='CpyVtoR4':result=locals_[ins.arguments[0]]
        elif ins.name=='FREE':
            test.assertEqual(ins.arguments[1],0);freed.append(-ins.arguments[0])
        elif ins.name in ('JLowZ','JLowNZ','JMP'):
            take=ins.name=='JMP' or (ins.name=='JLowZ' and not result) or (ins.name=='JLowNZ' and result)
            if take:pc+=ins.arguments[0]
        elif ins.name=='CALLSYS':
            label=module.used_functions[ins.arguments[0]].label
            if label=='hub::EntryFlag(string&, bool)':
                name=stack.pop();value=stack.pop();test.assertIsInstance(name,str);test.assertIn(value,(0,1));flags[name]=bool(value)
            elif label=='hub::IsActiveFlag(string&)':result=flags.get(stack.pop(),False)
            elif label=='hub::IsAlreadyRead(string&)':result=stack.pop() in reads
            elif label=='string::opEquals(string&)':result=stack.pop()==stack.pop()
            elif label=='hub::ReserveJumpNextTimeline()':test.assertFalse(stack);advances+=1
            elif label=='hub::ui::GainGoldFund(int)':grants.append(('gold',stack.pop()))
            elif label=='hub::ui::RunRecruitResult(string&)':grants.append(('battalion',stack.pop()))
            else:test.fail('Unexpected reviewed native call: '+label)
        else:
            test.assertEqual((ins.name,ins.arguments),('RET',(0,)));test.assertFalse(stack);test.assertEqual(pc,len(code))
    test.assertFalse(stack);test.assertEqual(freed,list(range(len(args))))
    return dict(flags=flags,advances=advances,grants=grants,result=result)


def run_program(test,module,fi):
    result=execute_program(test,module,fi)
    return result['flags'],result['advances']


class TutorialTests(unittest.TestCase):
    def test_timeline_bytes_unchanged_and_emitted_flags_stack_and_metadata(self):
        docs,p=fixture();table=docs['Events'];script=docs['Script'];v=table.views['timeline'];r=v.records[0]
        v.set(r,v.by_offset[0x5e],1850);v.set(r,v.by_offset[0x38],[['CUSTOM_CONDITION']]);before=table.build()
        with patch.dict(td.BY_KEY,{p.key:p}):
            self.assertEqual(td.inspect_state(docs,p)[0],'normal');self.assertEqual(td.apply_choices(docs,{p.key:True}),1)
            self.assertEqual(table.build(),before);rebuilt=Module(script.build_raw())
            self.assertEqual(run_program(self,rebuilt,0),({'FLAG_UNLOCK':True,'FLAG_REVEALED':True},1))
            self.assertEqual(rebuilt.constants[0].text,'SyntheticIntro');self.assertEqual(rebuilt.constants[1].text,'日本語')
            self.assertEqual(rebuilt.function_layouts[0][2]&24,0);self.assertEqual(rebuilt.types,script.module.types)
            self.assertEqual(td.apply_choices(docs,{p.key:True}),0)
            self.assertEqual(td.apply_choices(docs,{p.key:False}),1);self.assertEqual(script.build(),script.raw)
            self.assertEqual(table.build(),before)

    def test_source_custom_edits_and_unreviewed_programs_fail_closed(self):
        docs,p=fixture();script=docs['Script']
        with patch.dict(td.BY_KEY,{p.key:p}):
            self.assertEqual(td.inspect_state(docs,replace(p,script_sha='bad'))[0],'unavailable')
            script.set_string(0,'CUSTOM');self.assertEqual(td.inspect_state(docs,p)[0],'unavailable');before=script.snapshot_edits()
            with self.assertRaises(td.TutorialError):td.apply_choices(docs,{p.key:True})
            self.assertEqual(script.snapshot_edits(),before);script.clear_edits()
            for key in ('unknown',next(p.key for p in td.PRESETS if p.blocked)):
                script.tutorial_programs={key}
                with self.assertRaises((ScriptError,td.TutorialError)):script.build_raw()
            script.clear_edits()
            for choices in ({'bad':True},{p.key:1},{p.key:'yes'},[]):
                with self.assertRaises(td.TutorialError):td.apply_choices(docs,choices)

    def test_transactional_writer_failure_and_preserving_unrelated_string_edits(self):
        docs,p=fixture();script=docs['Script'];script.set_string(1,'Other text');before={k:d.snapshot_edits() for k,d in docs.items()}
        with patch.dict(td.BY_KEY,{p.key:p}),patch.object(script,'build',side_effect=ScriptError('Rejected output')):
            with self.assertRaises(ScriptError):td.apply_choices(docs,{p.key:True})
        self.assertEqual({k:d.snapshot_edits() for k,d in docs.items()},before)
        with patch.dict(td.BY_KEY,{p.key:p}):
            td.apply_choices(docs,{p.key:True});self.assertEqual(Module(script.build_raw()).constants[1].text,'Other text')

    def test_project_v2_ids_only_replay_path_guards_and_rollback(self):
        docs,p=fixture();script=docs['Script']
        with patch.dict(td.BY_KEY,{p.key:p}):
            td.apply_choices(docs,{p.key:True});payload=json.loads(json.dumps(script.project()))
            self.assertEqual(payload['format'],'fw-script-edits-v2');self.assertEqual(payload['tutorial_programs'],[p.key])
            fresh=ScriptDocument(script.raw,script.filename);fresh.load_project(payload);self.assertEqual(fresh.build(),script.build())
            before=fresh.snapshot_edits()
            for keys in ([p.key,p.key],['unknown'],[0],None):
                bad={**payload,'tutorial_programs':keys}
                with self.assertRaises((ScriptError,td.TutorialError)):fresh.load_project(bad)
                self.assertEqual(fresh.snapshot_edits(),before)
            project=suite_project(docs)
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp);base=root/'original/romfs/GameData';base.mkdir(parents=True)
                (base/docs['Events'].filename).write_bytes(docs['Events'].raw)
                source=base.parent/script.filename;source.parent.mkdir(parents=True);source.write_bytes(script.raw)
                loaded={'Events':EventData(docs['Events'].raw,docs['Events'].filename)};sources={'Events':base/docs['Events'].filename}
                load_with_scripts(loaded,sources,base,json.loads(json.dumps(project)))
                self.assertEqual(suite_project(loaded),project)
                export_suite(loaded,sources,root/'mod');output=root/'mod/romfs'/script.filename
                self.assertEqual(output.read_bytes(),script.build());self.assertEqual(source.read_bytes(),script.raw)
                self.assertEqual((root/'mod/romfs/GameData'/docs['Events'].filename).read_bytes(),docs['Events'].raw)
                self.assertFalse(list(root.rglob('*.backup-*')))

    def test_all_unverified_catalog_entries_cannot_be_activated_from_projects_or_ui(self):
        self.assertEqual({p.group for p in td.PRESETS},set(range(1,29)))
        docs,p=fixture();before={k:d.snapshot_edits() for k,d in docs.items()}
        for preset in td.PRESETS:
            if not preset.blocked:continue
            self.assertEqual(td.inspect_state(docs,preset)[0],'blocked')
            with self.assertRaises(td.TutorialError):td.apply_choices(docs,{preset.key:True})
            self.assertEqual({k:d.snapshot_edits() for k,d in docs.items()},before)

    def test_source_loading_shows_wrong_versions_and_rejects_symlink_escapes(self):
        docs,p=fixture();original=docs.pop('Script');table=docs['Events']
        with tempfile.TemporaryDirectory() as temp,patch.object(td,'PRESETS',(p,)):
            root=Path(temp);base=root/'game/romfs/GameData';base.mkdir(parents=True)
            source=base.parent/p.script;source.parent.mkdir(parents=True)
            original.set_string(1,'Modified original');source.write_bytes(original.build());before=source.read_bytes()
            self.assertEqual(td.load_sources(docs,{},base),1)
            self.assertEqual(td.inspect_state(docs,p)[0],'unavailable');self.assertIn('differs',td.inspect_state(docs,p)[1])
            self.assertEqual(source.read_bytes(),before);self.assertFalse(next(d for d in docs.values() if d.filename==p.script).modified)
            if os.name!='nt':
                outside=root/'outside.bin.zst';outside.write_bytes(before);source.unlink();source.symlink_to(outside)
                clean={'Events':table};self.assertEqual(td.load_sources(clean,{},base),0)
                self.assertEqual(list(clean),['Events'])


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent/fw-game-data'))
@unittest.skipUnless((DATA/'Timeline_Part1_Kai.bin').is_file(),'Set FW_GAME_DATA for native tutorial checks.')
class NativeTutorialTests(unittest.TestCase):
    def docs(self):
        names={ref[0] for p in td.PRESETS for ref in p.rows}
        docs={n:EventData((DATA/n).read_bytes(),n) for n in names};sources={n:DATA/n for n in names}
        td.load_sources(docs,sources,DATA);return docs,sources

    def test_all_reviewed_recipes_preserve_native_timeline_bytes_and_unrelated_functions(self):
        docs,sources=self.docs();ready=[p for p in td.PRESETS if not p.blocked]
        self.assertEqual(len(ready),20)
        original={k:d.raw for k,d in docs.items()}
        td.apply_choices(docs,{p.key:True for p in ready});td.validate_export(docs)
        for key,d in docs.items():
            if isinstance(d,EventData):self.assertEqual(d.build(),original[key]);continue
            rebuilt=Module(d.build_raw())
            changed=set(td.bridge_targets(d)) if d.filename==td.BRIDGE_SOURCE else {fi for p in ready if p.script==d.filename for fi in td.script_targets(d,p)}
            for fi,(a,b) in enumerate(zip(d.module.functions,rebuilt.functions)):
                if fi not in changed:self.assertEqual([(i.opcode,i.arguments) for i in a.instructions],[(i.opcode,i.arguments) for i in b.instructions])
                elif d.filename!=td.BRIDGE_SOURCE:
                    p=next(p for p in ready if p.script==d.filename and fi in td.script_targets(d,p))
                    effect=execute_program(self,rebuilt,fi)
                    for flag in p.flags:self.assertTrue(effect['flags'][flag])
                    for flag in p.off_flags:self.assertFalse(effect['flags'][flag])
                    self.assertEqual(effect['advances'],int(p.advance))
                    self.assertEqual(rebuilt.function_layouts[fi][2]&24,0)
            self.assertEqual([t.text for t in rebuilt.constants[:len(d.module.constants)]],[t.text for t in d.module.constants])
        project=suite_project(docs);fresh,_=self.docs();load_suite_project(fresh,json.loads(json.dumps(project)))
        self.assertEqual(suite_project(fresh),project)
        td.apply_choices(docs,{p.key:False for p in ready});td.validate_export(docs)
        for key,d in docs.items():
            if d.filename==td.BRIDGE_SOURCE:self.assertTrue(d.modified);self.assertEqual(len(d.tutorial_programs),20)
            else:self.assertEqual(d.build(),original[key])
        # Re-exporting restores old scene files and keeps access guards; no stale bypass payloads.
        with tempfile.TemporaryDirectory() as temp:
            export_suite(fresh,sources,temp);export_suite(docs,sources,temp)
            for d in docs.values():
                target=Path(temp)/'romfs'/d.filename if isinstance(d,ScriptDocument) else Path(temp)/'romfs/GameData'/d.filename
                self.assertEqual(target.read_bytes(),d.build())

    def test_read_guards_exact_keys_native_fallback_two_argument_and_semantics(self):
        docs,_=self.docs();ready=[p for p in td.PRESETS if not p.blocked]
        td.apply_choices(docs,{p.key:True for p in ready})
        d=td.document(docs,td.BRIDGE_SOURCE);m=Module(d.build_raw());one,two=td.bridge_targets(d)
        mappings={key:flag for p in ready for key,flag in td.read_mappings(p)}
        for key,flag in mappings.items():
            self.assertFalse(execute_program(self,m,one,(key,))['result'])
            self.assertTrue(execute_program(self,m,one,(key,),reads={key})['result'])
            self.assertTrue(execute_program(self,m,one,(key,),flags={flag:True})['result'])
        a,fa=next(iter(mappings.items()));b='UNRELATED_STORY_SCENE'
        for marker_on in (False,True):
            for read_a in (False,True):
                for read_b in (False,True):
                    flags={fa:marker_on};reads={key for key,on in ((a,read_a),(b,read_b)) if on}
                    expected=(marker_on or read_a) and read_b
                    for args in ((a,b),(b,a)):
                        self.assertEqual(execute_program(self,m,two,args,flags,reads)['result'],expected)
        self.assertFalse(execute_program(self,m,one,(b,),flags={f:True for f in mappings.values()})['result'])
        self.assertTrue(execute_program(self,m,one,(b,),reads={b})['result'])

    def test_drink_vendor_and_unlock_flags_persist_when_guidance_is_reenabled(self):
        docs,_=self.docs();p=td.BY_KEY['leda-drinks'];td.apply_choices(docs,{p.key:True})
        d=td.document(docs,p.script);m=Module(d.build_raw());effect=execute_program(self,m,td.script_target(d,p))
        self.assertTrue(effect['flags']['機能開放_飲み物係']);self.assertEqual(effect['advances'],0)
        td.apply_choices(docs,{p.key:False});self.assertEqual(d.build(),d.raw)
        bridge=td.document(docs,td.BRIDGE_SOURCE);m=Module(bridge.build_raw());one,_=td.bridge_targets(bridge)
        read_key='MID_LGV_1LED_TG14_003_m03'
        # Positive guard enables the regular vendor; the inverted guard hides the tutorial-only vendor.
        regular=execute_program(self,m,one,(read_key,),effect['flags'])['result']
        self.assertTrue(regular);self.assertFalse(not regular)
        fresh,_=self.docs();load_suite_project(fresh,json.loads(json.dumps(suite_project(docs))))
        self.assertEqual(td.document(fresh,td.BRIDGE_SOURCE).build(),bridge.build())
        td.validate_export(fresh)

    def test_city_stages_do_not_complete_later_inn_or_story_conversation_early(self):
        docs,_=self.docs();p=td.BY_KEY['cai-city'];td.apply_choices(docs,{p.key:True})
        d=td.document(docs,p.script);m=Module(d.build_raw());first,inn=td.script_targets(d,p)
        state=execute_program(self,m,first);self.assertEqual(state['grants'],[('gold',1500)]);self.assertEqual(state['advances'],1)
        self.assertFalse(execute_program(self,m,first,flags=state['flags'])['grants'])
        b=td.document(docs,td.BRIDGE_SOURCE);bm=Module(b.build_raw());one,_=td.bridge_targets(b)
        def read(k):return execute_program(self,bm,one,(k,),state['flags'])['result']
        self.assertTrue(read(p.hook));self.assertFalse(read('MID_LGV_1KAI_TG11_101_m03'))
        self.assertFalse(read('MID_LGV_1KAI_c02_LG11_002_m02'))
        effect=execute_program(self,m,inn,flags=state['flags']);self.assertFalse(effect['grants']);self.assertEqual(effect['advances'],1)
        self.assertTrue(read('MID_LGV_1KAI_TG11_101_m03'))

    def test_battalion_reward_is_native_and_original_first_visit_flag_prevents_duplicates(self):
        docs,_=self.docs();p=td.BY_KEY['theodora-gambits'];td.apply_choices(docs,{p.key:True})
        d=td.document(docs,p.script);m=Module(d.build_raw());fi=td.script_target(d,p)
        initial=execute_program(self,m,fi);self.assertEqual(initial['grants'],[('battalion','LID_駆け出し傭兵団E')])
        self.assertTrue(initial['flags']['機能開放_軍団兵舎']);self.assertEqual(initial['advances'],1)
        self.assertFalse(execute_program(self,m,fi,flags=initial['flags'])['grants'])
        original_flag='拠点_セオドラ篇1部4章_軍団兵チュートリアル'
        self.assertFalse(execute_program(self,m,fi,flags={original_flag:True})['grants'])

    def test_missing_read_guard_old_recipe_repair_and_transactional_rollback(self):
        docs,_=self.docs();p=td.BY_KEY['cai-trading'];scene=td.document(docs,p.script);scene.tutorial_programs.add(p.key)
        self.assertEqual(td.inspect_state(docs,p)[0],'repair')
        with self.assertRaisesRegex(td.TutorialError,'facility-access'):td.validate_export(docs)
        bridge=td.document(docs,td.BRIDGE_SOURCE);before={k:d.snapshot_edits() for k,d in docs.items()}
        with patch.object(bridge,'build',side_effect=ScriptError('Rejected guard')):
            with self.assertRaises(ScriptError):td.apply_choices(docs,{p.key:True})
        self.assertEqual({k:d.snapshot_edits() for k,d in docs.items()},before)
        td.apply_choices(docs,{p.key:True});td.validate_export(docs);self.assertEqual(td.inspect_state(docs,p)[0],'disabled')
        scene.tutorial_programs.clear();scene.tutorial_programs.add(td.BRIDGE_PREFIX+p.key)
        with self.assertRaises(td.TutorialError):scene.build_raw()
        scene.tutorial_programs.clear();bridge.tutorial_programs={td.BRIDGE_PREFIX+'cai-exam'}
        with self.assertRaises(ScriptError):bridge.build_raw()

    def test_legacy_migration_restore_and_export_rejection(self):
        docs,sources=self.docs();keys=list(td.LEGACY)
        for key in keys:
            p=td.BY_KEY[key]
            for _,v,r in td.targets(docs,p):
                v.set(r,v.by_offset[0x5e],1830)
                for off,value in td.legacy_values(p).items():v.set(r,v.by_offset[off],value)
            self.assertEqual(td.inspect_state(docs,p)[0],'legacy')
        before={k:d.snapshot_edits() for k,d in docs.items()}
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'mod'
            with self.assertRaisesRegex(td.TutorialError,'old tutorial'):export_suite(docs,sources,output)
            self.assertFalse(output.exists())
        doc=td.document(docs,td.BY_KEY[keys[-1]].script)
        with patch.object(doc,'build',side_effect=ScriptError('Rejected migration')):
            with self.assertRaises(ScriptError):td.apply_choices(docs,{key:True for key in keys})
        self.assertEqual({k:d.snapshot_edits() for k,d in docs.items()},before)
        td.apply_choices(docs,{key:True for key in keys});td.validate_export(docs)
        for key in keys:
            p=td.BY_KEY[key];self.assertEqual(td.inspect_state(docs,p)[0],'disabled')
            for _,v,r in td.targets(docs,p):
                self.assertEqual(v.value(r,v.by_offset[0x21]),13);self.assertEqual(v.value(r,v.by_offset[0x5e]),1830)
                for off in td.CONTROLLED:self.assertEqual(v.value(r,v.by_offset[off]),v.original(r,v.by_offset[off]))
        td.apply_choices(docs,{key:False for key in keys})
        for d in docs.values():
            if isinstance(d,ScriptDocument) and d.filename!=td.BRIDGE_SOURCE:self.assertEqual(d.build(),d.raw)


if __name__=='__main__':unittest.main()
