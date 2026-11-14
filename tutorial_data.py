"""Source-guarded tutorial plans; never substitute a different timeline event type.

Unverified native facility/quest effects deliberately have no executable recipe.
Projects store only reviewed recipe IDs, never arbitrary replacement programs.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from tutorial_catalog import CATALOG


class TutorialError(ValueError):pass


@dataclass(frozen=True)
class Preset:
    group:int
    key:str
    route:str
    chapter:int
    title:str
    rows:tuple
    script:str
    script_sha:str
    hook:str
    flags:tuple
    blocked:str
    description:str
    other_hooks:tuple=()
    off_flags:tuple=()
    read_keys:tuple=()
    read_stages:tuple=()
    advance:bool=True
    native_calls:tuple=()


PRESETS=tuple(Preset(**p) for p in CATALOG)
BY_KEY={p.key:p for p in PRESETS}
LEGACY={'cai-recruitment':(19,'グザラン'), 'dietrich-recruitment':(19,'ヨーカイ'),
        'cai-trading':(31,'機能開放_ヴァンダル商会')}
CONTROLLED=(0x21,0x28,0x48,0x70,0x90,0x98,0xa0,0xb0,0xc0)
BRIDGE_SOURCE='Script/hub/HubXml_Conditions.bin.zst'
BRIDGE_SHA='8b91ea416f320f03c947110fa7477bf848cf60c907e42c9c95148d8d54b8f3a7'
BRIDGE_PREFIX='unlock-bridge:'


def marker(key):return 'CCK_TUTORIAL_DONE_'+key


def read_mappings(preset):
    if preset.read_stages:
        keys=[key for hook,reads in preset.read_stages for key in reads]
        if len(keys)!=len(set(keys)) or set(keys)!=set(preset.read_keys) or {h for h,r in preset.read_stages}!={preset.hook,*preset.other_hooks}:
            raise TutorialError('Inconsistent reviewed tutorial stages.')
        return tuple((key,marker(preset.key+'_stage'+str(i+1))) for i,(hook,reads) in enumerate(preset.read_stages) for key in reads)
    return tuple((key,marker(preset.key)) for key in preset.read_keys)


def row_digest(view,row):
    values={str(f.offset):view.original(row,f) for f in view.fields}
    return hashlib.sha256(json.dumps(values,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def document(documents,filename):
    matches=[d for d in documents.values() if d.filename==filename]
    if len(matches)!=1:raise TutorialError('Load exactly one original source: '+filename)
    return matches[0]


def targets(documents,preset):
    found=[]
    for filename,pid,digest in preset.rows:
        owner=document(documents,filename);view=getattr(owner,'views',{}).get('timeline')
        row=view.by_pid.get(pid) if view else None
        if row is None or row_digest(view,row)!=digest:
            raise TutorialError('The original tutorial row differs from supported game version 1.00: '+preset.title)
        found.append((owner,view,row))
    return found


def legacy_values(preset):
    kind,argument=LEGACY[preset.key]
    return {0x21:kind,0x28:[argument],0x48:[],0x70:'',0x90:'',0x98:0,0xa0:'',0xb0:[],0xc0:''}


def table_state(documents,preset):
    legacy=False
    for _,view,row in targets(documents,preset):
        current={off:view.value(row,view.by_offset[off]) for off in CONTROLLED}
        original={off:view.original(row,view.by_offset[off]) for off in CONTROLLED}
        if current==original:continue
        if preset.key in LEGACY and current==legacy_values(preset):legacy=True
        else:raise TutorialError('The tutorial timeline row has custom action/interval edits. Resolve them in Events first.')
    return 'legacy' if legacy else 'normal'


def checked_functions(doc,filename,sha,labels):
    if doc.filename!=filename or doc.sha256!=sha:
        raise TutorialError('Original script differs from the reviewed version 1.00 source: '+filename)
    found=[]
    for label in labels:
        matches=[i for i,f in enumerate(doc.module.functions) if f.label==label]
        if len(matches)!=1:raise TutorialError('The reviewed entry function is missing or ambiguous: '+label)
        fi=matches[0];function=doc.module.functions[fi]
        if any(key[0]==fi for key in doc.instructions):raise TutorialError('Custom instruction edits overlap the reviewed function.')
        constants={i.arguments[0]>>1 for i in function.instructions if i.name in ('PGA','PshGPtr') and not i.arguments[0]&1}
        if constants&doc.strings.keys():raise TutorialError('Custom string edits overlap the reviewed function.')
        found.append(fi)
    return tuple(found)


def script_targets(doc,preset):
    return checked_functions(doc,preset.script,preset.script_sha,tuple(h+'()' for h in (preset.hook,)+preset.other_hooks))


def script_target(doc,preset):return script_targets(doc,preset)[0]


def bridge_targets(doc):
    return checked_functions(doc,BRIDGE_SOURCE,BRIDGE_SHA,('IsAlreadyRead(string)','IsAlreadyRead(string, string)'))


def inspect_state(documents,preset):
    if preset.blocked:return 'blocked',preset.blocked
    try:
        state=table_state(documents,preset)
        doc=document(documents,preset.script);script_targets(doc,preset)
        bridge=document(documents,BRIDGE_SOURCE) if preset.read_keys else None
        if bridge:bridge_targets(bridge)
        if state=='legacy':return 'legacy','Old event-type replacement: Apply to migrate it, or turn it off to restore the native event.'
        if preset.key in doc.tutorial_programs:
            if bridge and BRIDGE_PREFIX+preset.key not in bridge.tutorial_programs:
                return 'repair','Apply to finish installing persistent facility-access checks.'
            return 'disabled','Guidance bypass enabled. Native scheduling retained; skipped introduction markers preserve facility access.'
        return 'normal','Original sequence. The reviewed completion recipe is available for testing.'
    except (ValueError,AttributeError) as exc:return 'unavailable',str(exc)


def load_sources(documents,sources,base):
    """Read only reviewed original scripts beside GameData, without following escapes."""
    from script_data import ScriptDocument
    root=Path(base).resolve().parent;pending=[]
    names={p.script for p in PRESETS if not p.blocked}
    if any(p.read_keys for p in PRESETS if not p.blocked):names.add(BRIDGE_SOURCE)
    for filename in sorted(names):
        if any(d.filename==filename for d in documents.values()):continue
        source=(root/filename).resolve()
        if not source.is_relative_to(root/'Script') or not source.is_file():continue
        doc=ScriptDocument(source.read_bytes(),filename)
        pending.append(('Scripts · '+filename,doc,source))
    for key,doc,source in pending:documents[key]=doc;sources[key]=source
    return len(pending)


class Assembly:
    """Small private emitter: symbolic forward branches, no user-provided code."""
    def __init__(self):self.code=[];self.labels={}
    def emit(self,name,*args):self.code.append((name,args))
    def label(self,name):
        if name in self.labels:raise TutorialError('Duplicate reviewed program label.')
        self.labels[name]=len(self.code)
    def finish(self):
        from script_bytecode import OPCODES
        ops={name:i for i,(name,_) in enumerate(OPCODES)};output=[]
        for i,(name,args) in enumerate(self.code):
            if name in ('JMP','JLowZ','JLowNZ'):
                target=self.labels[args[0]]
                if target<=i:raise TutorialError('Reviewed programs require forward branches.')
                args=(target-i-1,)
            output.append((ops[name],tuple(args)))
        return tuple(output)


def programs_for_document(doc):
    """Compile registered, source-pinned effects and persistent read compatibility."""
    from script_bytecode import ScriptError,ReviewedProgram
    programs={};extra=[];m=doc.module
    string=(5,('string',''),12);boolean=(65,None,0);void=(80,None,0)
    def constant(value):
        if value not in extra:extra.append(value)
        return (len(m.constants)+extra.index(value))*2
    def api(name,parameters=(),inout=(),result=void,receiver=None,traits=0):
        found=[i for i,s in enumerate(m.used_functions) if s and s.label==name
               and s.kind==0 and s.result==result and s.parameters==parameters and s.inout==inout
               and s.object_type==receiver and not s.templates and s.traits==traits]
        if len(found)!=1:raise ScriptError('Required native API is missing or has a different signature: '+name)
        return found[0]
    def set_flag(a,flag,value):
        a.emit('PshC4',int(value));a.emit('PGA',constant(flag))
        a.emit('CALLSYS',api('hub::EntryFlag(string&, bool)',(string,boolean),(3,0)))
        a.emit('SUSPEND')
    bridges=[]
    for key in sorted(doc.tutorial_programs):
        internal=key.startswith(BRIDGE_PREFIX);public=key[len(BRIDGE_PREFIX):] if internal else key
        preset=BY_KEY.get(public)
        if preset is None or preset.blocked:raise ScriptError('Unknown or unverified tutorial recipe: '+key)
        if internal:
            if not preset.read_keys:raise ScriptError('This recipe has no read compatibility checks.')
            bridge_targets(doc);bridges.append(preset);continue
        for fi in script_targets(doc,preset):
            if fi in programs:raise ScriptError('Tutorial recipes overlap the same function.')
            a=Assembly();a.emit('SUSPEND');hook=m.functions[fi].signature.name
            for n,(call_hook,guard,kind,value) in enumerate(preset.native_calls):
                if call_hook!=hook:continue
                a.emit('PGA',constant(guard));a.emit('CALLSYS',api('hub::IsActiveFlag(string&)',(string,),(3,),boolean))
                a.emit('JLowNZ','reward_done_'+str(n));set_flag(a,guard,True)
                if kind=='gold':
                    a.emit('PshC4',value);a.emit('CALLSYS',api('hub::ui::GainGoldFund(int)',((68,None,0),),(0,)))
                elif kind=='battalion':
                    a.emit('PGA',constant(value));a.emit('CALLSYS',api('hub::ui::RunRecruitResult(string&)',(string,),(3,)))
                else:raise ScriptError('Unregistered tutorial reward kind.')
                a.emit('SUSPEND');a.label('reward_done_'+str(n))
            for flag in preset.flags:set_flag(a,flag,True)
            for flag in preset.off_flags:set_flag(a,flag,False)
            if preset.read_stages:
                read_mappings(preset)
                stage=next(i for i,(h,reads) in enumerate(preset.read_stages) if h==hook)
                set_flag(a,marker(preset.key+'_stage'+str(stage+1)),True)
            elif preset.read_keys:set_flag(a,marker(preset.key),True)
            if preset.advance:a.emit('CALLSYS',api('hub::ReserveJumpNextTimeline()'));a.emit('SUSPEND')
            a.emit('RET',0);programs[fi]=a.finish()
    if bridges:
        equals=api('string::opEquals(string&)',(string,),(1,),boolean,('string',''),1)
        active=api('hub::IsActiveFlag(string&)',(string,),(3,),boolean)
        read=api('hub::IsAlreadyRead(string&)',(string,),(3,),boolean)
        mappings=sorted({pair for p in bridges for pair in read_mappings(p)})
        for fi in bridge_targets(doc):
            count=len(m.functions[fi].signature.parameters);a=Assembly();a.emit('SUSPEND')
            for param in range(count):
                success='param_'+str(param)+'_true'
                for n,(key,flag) in enumerate(mappings):
                    next_pair=f'pair_{param}_{n}_next'
                    a.emit('PGA',constant(key));a.emit('PshVPtr',-param);a.emit('CALLSYS',equals);a.emit('JLowZ',next_pair)
                    a.emit('PGA',constant(flag));a.emit('CALLSYS',active);a.emit('JLowNZ',success);a.label(next_pair)
                a.emit('PshVPtr',-param);a.emit('CALLSYS',read)
                if param<count-1:a.emit('JLowZ','return')
                a.label(success)
            a.label('return');a.emit('CpyRtoV4',4);a.emit('CpyVtoR4',4)
            for param in range(count):a.emit('FREE',-param,0)
            a.emit('RET',0);programs[fi]=ReviewedProgram(a.finish(),4)
    return programs,tuple(extra)


def apply_choices(documents,choices):
    if not isinstance(choices,dict) or any(k not in BY_KEY or type(v) is not bool for k,v in choices.items()):
        raise TutorialError('Unknown tutorial choice.')
    plans=[];snapshots={};changed=0
    for key,disabled in choices.items():
        preset=BY_KEY[key];state,reason=inspect_state(documents,preset)
        if state not in ('normal','disabled','legacy','repair'):raise TutorialError(preset.title+': '+reason)
        doc=document(documents,preset.script)
        if state not in ('legacy','repair') and disabled==(state=='disabled'):continue
        refs=targets(documents,preset);bridge=document(documents,BRIDGE_SOURCE) if preset.read_keys else None
        plans.append((preset,doc,bridge,disabled,state,refs));changed+=1
        for owner in [doc]+([bridge] if bridge else [])+[o for o,v,r in refs]:snapshots.setdefault(owner,owner.snapshot_edits())
    try:
        for preset,doc,bridge,disabled,state,refs in plans:
            for _,view,row in refs:
                if state=='legacy':
                    for off in CONTROLLED:view.set(row,view.by_offset[off],view.original(row,view.by_offset[off]))
            if disabled:
                doc.tutorial_programs.add(preset.key)
                if bridge:bridge.tutorial_programs.add(BRIDGE_PREFIX+preset.key)
            else:doc.tutorial_programs.discard(preset.key)
            # Keep marker-aware guards after disabling. Existing saves must not
            # lose facilities simply because their introduction was omitted.
        for owner in snapshots:owner.build()
    except Exception:
        for owner,state in snapshots.items():owner.restore_edits(state)
        raise
    return changed


def validate_export(documents):
    """Reject obsolete shortcuts and missing unlock guards."""
    for preset in PRESETS:
        if preset.key in LEGACY and any(d.filename==preset.rows[0][0] for d in documents.values()):
            try:state=table_state(documents,preset)
            except TutorialError:state=None
            if state=='legacy':raise TutorialError('An old tutorial event-type bypass is present. Review Tools → Forced tutorials and Apply its migration before exporting: '+preset.title)
        script=next((d for d in documents.values() if d.filename==preset.script),None)
        if script and preset.key in getattr(script,'tutorial_programs',()):
            # Active recipes must include their unchanged, reviewed native rows.
            state=table_state(documents,preset)
            if state!='normal':raise TutorialError('An active tutorial recipe conflicts with its timeline: '+preset.title)
            if preset.read_keys:
                bridge=document(documents,BRIDGE_SOURCE);bridge_targets(bridge)
                if BRIDGE_PREFIX+preset.key not in bridge.tutorial_programs:raise TutorialError('A tutorial recipe is missing persistent facility-access checks: '+preset.title)
