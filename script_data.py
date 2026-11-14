"""Script projects and compressed mod output, separate from GameData tables."""
from copy import deepcopy
import ctypes
import ctypes.util
import hashlib
from pathlib import Path, PurePosixPath
import sys
from script_bytecode import Module, ScriptError


def valid_source(filename):
    if not isinstance(filename,str) or '\\' in filename:return False
    path=PurePosixPath(filename)
    return (len(path.parts)>=3 and path.parts[0]=='Script' and all(p not in ('','.', '..') for p in filename.split('/'))
            and not path.is_absolute() and filename.endswith(('.bin.zst','.bin')) and ':' not in filename)


def compress(raw):
    if sys.platform=='win32':
        import zstandard
        return zstandard.ZstdCompressor(level=3).compress(raw)
    lib=ctypes.CDLL(ctypes.util.find_library('zstd') or 'libzstd.so.1')
    lib.ZSTD_compressBound.argtypes=[ctypes.c_size_t];lib.ZSTD_compressBound.restype=ctypes.c_size_t
    lib.ZSTD_compress.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int];lib.ZSTD_compress.restype=ctypes.c_size_t
    lib.ZSTD_isError.argtypes=[ctypes.c_size_t];lib.ZSTD_isError.restype=ctypes.c_uint
    capacity=lib.ZSTD_compressBound(len(raw));output=ctypes.create_string_buffer(capacity);source=ctypes.create_string_buffer(raw)
    size=lib.ZSTD_compress(output,capacity,source,len(raw),3)
    if lib.ZSTD_isError(size):raise ScriptError('Script compression failed.')
    return output.raw[:size]


class ScriptDocument:
    # Runtime strings participate in explicit reference guards, never as definitions.
    records=();fields=();views={};prefix='SCRIPT_'

    def __init__(self,raw,filename):
        if not valid_source(filename):raise ScriptError('Invalid script source path.')
        from fw_editor import decompress, Field, Record
        self.filename=filename;self.raw=bytes(raw);self.sha256=hashlib.sha256(self.raw).hexdigest()
        self.module=Module(decompress(raw) if filename.endswith('.zst') else raw)
        self.strings={};self.instructions={};self.tutorial_programs=set()
        self.fields=(Field('Runtime string constant','string',8,0x20),)
        self.by_offset={0x20:self.fields[0]}
        self.records=tuple(Record(f'SCRIPT_STRING_{i}',token.start,i) for i,token in enumerate(self.module.constants))
        self.by_pid={r.pid:r for r in self.records};self.names={r.pid:f'String constant #{r.index}' for r in self.records}

    def value(self,record,field):
        return self.strings.get(record.index,self.module.constants[record.index].text)

    @property
    def modified(self):return bool(self.strings or self.instructions or self.tutorial_programs)

    @property
    def changes(self):return {**{('string',i):v for i,v in self.strings.items()},**{('instruction',*k):v for k,v in self.instructions.items()},**{('tutorial',k):True for k in self.tutorial_programs}}

    def clear_edits(self):self.strings={};self.instructions={};self.tutorial_programs=set()
    def snapshot_edits(self):return deepcopy((self.strings,self.instructions,self.tutorial_programs))
    def restore_edits(self,state):
        self.strings,self.instructions=deepcopy(state[:2]);self.tutorial_programs=deepcopy(state[2]) if len(state)>2 else set()

    def set_string(self,index,value):
        if type(index) is not int or not 0<=index<len(self.module.constants):raise ScriptError('Unknown string constant.')
        if not isinstance(value,str) or '\0' in value:raise ScriptError('A string must be text without a NUL character.')
        if len(value.encode('utf8'))*2>1_000_000:raise ScriptError('String exceeds the supported serialized size.')
        if value==self.module.constants[index].text:self.strings.pop(index,None)
        else:self.strings[index]=value

    def instruction(self,fi,ii):
        old=self.module.functions[fi].instructions[ii]
        return self.instructions.get((fi,ii),(old.opcode,old.arguments))

    def set_instruction(self,fi,ii,opcode,args):
        if type(fi) is not int or type(ii) is not int or not 0<=fi<len(self.module.functions) or not 0<=ii<len(self.module.functions[fi].instructions):raise ScriptError('Unknown instruction.')
        old=self.module.functions[fi].instructions[ii];self.module.validate_instruction(old,opcode,args);value=(opcode,tuple(args))
        if value==(old.opcode,old.arguments):self.instructions.pop((fi,ii),None)
        else:self.instructions[(fi,ii)]=value

    def build_raw(self):
        if not self.modified:return self.module.raw
        if self.tutorial_programs:
            from tutorial_data import programs_for_document
            programs,constants=programs_for_document(self)
            return self.module.rebuild(self.strings,self.instructions,reviewed_programs=programs,extra_constants=constants)
        return self.module.rebuild(self.strings,self.instructions)

    def build(self):
        if not self.modified:return self.raw
        raw=self.build_raw()
        return compress(raw) if self.filename.endswith('.zst') else raw

    def project(self):
        project={'format':'fw-script-edits-v1','source_file':self.filename,'source_sha256':self.sha256,
                'strings':[{'index':i,'value':v} for i,v in sorted(self.strings.items())],
                'instructions':[{'function':fi,'instruction':ii,'opcode':op,'arguments':list(args)} for (fi,ii),(op,args) in sorted(self.instructions.items())]}
        if self.tutorial_programs:project.update(format='fw-script-edits-v2',tutorial_programs=sorted(self.tutorial_programs))
        return project

    def load_project(self,project):
        if not isinstance(project,dict) or project.get('format') not in ('fw-script-edits-v1','fw-script-edits-v2') or project.get('source_file')!=self.filename or project.get('source_sha256')!=self.sha256:raise ScriptError('Script project does not match the original source file.')
        fresh=ScriptDocument(self.raw,self.filename);seen=set()
        for item in project.get('strings',[]):
            index=item['index']
            if index in seen:raise ScriptError('Duplicate string edit.')
            seen.add(index);fresh.set_string(index,item['value'])
        seen=set()
        for item in project.get('instructions',[]):
            key=item['function'],item['instruction']
            if key in seen:raise ScriptError('Duplicate instruction edit.')
            seen.add(key);fresh.set_instruction(*key,item['opcode'],item['arguments'])
        if project.get('format')=='fw-script-edits-v2':
            keys=project.get('tutorial_programs')
            if not isinstance(keys,list) or any(not isinstance(k,str) for k in keys) or len(set(keys))!=len(keys):raise ScriptError('Invalid tutorial program list.')
            fresh.tutorial_programs=set(keys)
        elif project.get('tutorial_programs'):raise ScriptError('Tutorial programs require a v2 script project.')
        fresh.build_raw() # Validate the entire round trip before committing.
        self.restore_edits(fresh.snapshot_edits())


def prepare_project(documents,sources,base,project):
    """Load only scripts named by a saved suite; never follow project path traversal."""
    payload=project.get('documents',{}) if isinstance(project,dict) else {}
    if not isinstance(payload,dict):return
    pending=[];root=Path(base).resolve().parent
    for filename in payload:
        if not isinstance(filename,str) or not filename.startswith('Script/'):continue
        if not valid_source(filename):raise ScriptError('Invalid script path in project.')
        if any(d.filename==filename for d in documents.values()):continue
        source=(root/filename).resolve()
        if not source.is_relative_to(root/'Script'):raise ScriptError('Script path escapes the original Script folder.')
        if not source.is_file():raise ScriptError('Original script is missing: '+filename)
        pending.append((filename,source,ScriptDocument(source.read_bytes(),filename)))
    # Fingerprints and all edits must validate before workspace membership changes.
    for filename,source,doc in pending:doc.load_project(payload[filename])
    for filename,source,doc in pending:
        documents['Scripts · '+filename]=doc;sources['Scripts · '+filename]=source
    return [name for name,_,_ in pending]


def load_with_scripts(documents,sources,base,project,loader=None):
    if loader is None:
        from fw_editor import load_suite_project
        loader=load_suite_project
    trial_docs=dict(documents);trial_sources=dict(sources)
    prepare_project(trial_docs,trial_sources,base,project)
    loader(trial_docs,project)
    documents.clear();documents.update(trial_docs)
    sources.clear();sources.update(trial_sources)
