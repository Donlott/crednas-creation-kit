"""Bounded reader and fixed-instruction editor for the game's ASF/AngelScript data.

Serializer rules/opcode layouts adapted from AngelScript (2021), not its engine.
This is an altered implementation; see licenses/AngelScript-LICENSE.txt.
No game code is bundled. Unsupported layouts fail closed.
"""
from dataclasses import dataclass
import struct
from script_inspector import inspect
from script_opcodes import OPCODES

MAX_COUNT = 1_000_000
ARG_COUNTS = {'NO_ARG':0, 'W_ARG':1, 'wW_ARG':1, 'rW_ARG':1, 'DW_ARG':1,
 'QW_ARG':1, 'PTR_ARG':1, 'rW_DW_ARG':2, 'wW_DW_ARG':2, 'W_DW_ARG':2,
 'DW_DW_ARG':2, 'wW_rW_rW_ARG':3, 'wW_rW_ARG':2, 'rW_rW_ARG':2,
 'wW_W_ARG':2, 'wW_rW_DW_ARG':3, 'rW_W_DW_ARG':3, 'QW_DW_ARG':2,
 'PTR_DW_ARG':2, 'rW_QW_ARG':2, 'wW_QW_ARG':2, 'wW_PTR_ARG':2,
 'rW_PTR_ARG':2, 'rW_DW_DW_ARG':3}
INVERSE = {'JZ':'JNZ', 'JNZ':'JZ', 'JS':'JNS', 'JNS':'JS', 'JP':'JNP',
           'JNP':'JP', 'JLowZ':'JLowNZ', 'JLowNZ':'JLowZ'}
LITERALS = {'PshC4':32, 'PshC8':64, 'SetV4':32, 'SetV8':64}
JUMPS = set(INVERSE) | {'JMP'}
CALLS = {'CALL', 'CALLSYS', 'CALLINTF', 'Thiscall1', 'CALLBND'}


class ScriptError(ValueError):
    pass


def encoded(value):
    """AngelScript's sign/magnitude, big-endian variable-length integer."""
    if type(value) is not int or not -(1<<63) <= value < (1<<64):
        raise ScriptError('Serialized integer is outside 64-bit bounds.')
    negative = value < 0
    value = abs(value)
    for extra,limit,prefix in ((0,1<<6,0),(1,1<<13,64),(2,1<<20,96),
                               (3,1<<27,112),(4,1<<34,120),(5,1<<41,124),(6,1<<48,126)):
        if value < limit:
            return bytes([(128 if negative else 0) | prefix | (value >> (8*extra))]) + (value & ((1<<(8*extra))-1)).to_bytes(extra,'big')
    return bytes([255 if negative else 127]) + value.to_bytes(8,'big')


@dataclass(frozen=True)
class StringToken:
    start:int
    end:int
    text:str


@dataclass(frozen=True)
class Signature:
    name:str
    kind:int
    result:tuple
    parameters:tuple
    inout:tuple
    object_type:object
    traits:int
    namespace:str
    templates:tuple

    @property
    def shape(self):
        return self.kind,self.result,self.parameters,self.inout,self.object_type,self.traits,self.templates

    @property
    def label(self):
        scope = self.namespace+'::' if self.namespace else ''
        if self.object_type and isinstance(self.object_type[0],str):scope=str(self.object_type[0])+'::'
        return scope+self.name+'('+', '.join(type_name(t) for t in self.parameters)+')'


def type_name(data):
    token,obj,flags=data
    primitive={80:'void',79:'float',92:'double',68:'int',69:'int8',70:'int16',71:'int64',75:'uint',76:'uint8',77:'uint16',78:'uint64',65:'bool'}
    text=str(obj[0] if isinstance(obj,tuple) and len(obj)==2 and isinstance(obj[0],str) else obj) if obj else primitive.get(token,f'type#{token}')
    return text+('@' if flags&1 else '')+('&' if flags&4 else '')


@dataclass(frozen=True)
class Instruction:
    start:int
    end:int
    opcode:int
    arguments:tuple

    @property
    def name(self):
        return OPCODES[self.opcode][0]


@dataclass(frozen=True)
class Function:
    signature:Signature
    start:int
    end:int
    instructions:tuple

    @property
    def label(self):
        return self.signature.label if self.signature.name else f'<global initializer at 0x{self.start:X}>'


class Module:
    def __init__(self,raw):
        self.raw=bytes(raw)
        self.info=inspect(self.raw)
        self.at=self.info.payload_offset
        self.saved_strings=[];self.types=[];self.signatures=[]
        self.string_tokens=[];self.functions=[];self.constants=[]
        self.bindings=[];self.used_functions=[];self.globals=[]
        try:
            self._read_module()
            self.validate_references()
        except (IndexError,UnicodeError,RecursionError,struct.error) as exc:
            raise ScriptError(f'Unsupported or damaged script near 0x{self.at:X}: {exc}') from exc

    def fail(self,message):
        raise ScriptError(f'{message} (at 0x{self.at:X}).')

    def take(self,size):
        if size < 0 or self.at+size>len(self.raw):self.fail('Truncated script')
        value=self.raw[self.at:self.at+size];self.at+=size
        return value

    def byte(self):return self.take(1)[0]

    def integer(self):
        head=self.byte();negative=bool(head&128);head &=127
        if head==127:extra=8;value=0
        elif head>=126:extra=6;value=head&1
        elif head>=124:extra=5;value=head&3
        elif head>=120:extra=4;value=head&7
        elif head>=112:extra=3;value=head&15
        elif head>=96:extra=2;value=head&31
        elif head>=64:extra=1;value=head&63
        else:extra=0;value=head
        value=(value<<(8*extra))|int.from_bytes(self.take(extra),'big')
        return -value if negative else value

    def count(self,limit=MAX_COUNT):
        value=self.integer()
        if not 0<=value<=limit:self.fail('Invalid count or reference index')
        return value

    def string(self):
        start=self.at;size=self.count()
        if size&1:
            value=self.saved_strings[size//2]
        else:
            value=self.take(size//2).decode('utf8')
            if size:self.saved_strings.append(value)
        self.string_tokens.append(StringToken(start,self.at,value))
        return value

    def type_info(self):
        marker=self.byte()
        if marker==0:return None
        if marker==ord('o'):return self.string(),self.string()
        if marker==ord('s'):return ('subtype',self.string())
        if marker==ord('l'):return ('list',self.type_info())
        if marker==ord('c'):return ('child',self.string(),self.type_info())
        if marker==ord('a'):
            name=(self.string(),self.string());subtypes=[]
            for _ in range(self.count(100)):
                tag=self.byte()
                if tag==ord('s'):subtypes.append(self.data_type())
                elif tag==ord('t'):subtypes.append(self.integer())
                else:self.fail('Unknown template subtype marker')
            return name,tuple(subtypes)
        self.fail('Unknown type marker')

    def data_type(self):
        index=self.count()
        if index:return self.types[index-1]
        token=self.integer();slot=len(self.types);self.types.append(None)
        obj=self.type_info() if token==5 else None;flags=self.byte()
        if flags&~15:self.fail('Unknown data type flags')
        self.types[slot]=(token,obj,flags)
        return self.types[slot]

    def signature(self):
        name=self.string();result=self.data_type()
        params=tuple(self.data_type() for _ in range(self.count(256)))
        inout=[0]*len(params)
        if params:
            for i in range(self.count(len(params))):inout[i]=self.count(3)
        kind=self.count(255)
        if params:
            for _ in range(self.count(len(params))):self.string()
        obj=self.type_info()
        traits=self.byte() if obj or name.startswith(('get_','set_')) else 0
        namespace=''
        if not obj:
            if kind&127==4:
                marker=self.byte()
                if marker==ord('o'):obj=self.type_info()
                elif marker!=ord('n'):self.fail('Unknown funcdef scope')
                if marker==ord('n'):namespace=self.string()
            else:namespace=self.string()
        templates=tuple(self.data_type() for _ in range(self.count(256))) if kind&128 else ()
        return Signature(name,kind&127,result,params,tuple(inout),obj,traits,namespace,templates)

    def function(self):
        marker=self.byte()
        if marker==0:return None
        if marker==ord('r'):return self.signatures[self.count()]
        if marker!=ord('f'):self.fail('Unknown function marker')
        sig=self.signature();self.signatures.append(sig)
        if sig.kind==1:
            flags=self.byte()
            if flags&~63:self.fail('Unknown function flags')
            if not flags&4:
                start=self.at;instructions=[]
                for _ in range(self.count()):
                    at=self.at;opcode=self.byte()
                    if opcode>=201:self.fail('Unknown or compiler-only opcode')
                    name,layout=OPCODES[opcode]
                    arguments=tuple(self.integer() for _ in range(ARG_COUNTS[layout]))
                    instructions.append(Instruction(at,self.at,opcode,arguments))
                self.functions.append(Function(sig,start,self.at,tuple(instructions)))
                self.count() # Stack variable space
                if flags&8:
                    count=self.count()
                    for _ in range(count):self.type_info();self.integer()
                    if count:self.count(10000)
                    for _ in range(self.count()):self.count();self.integer();self.count(4)
                if flags&16:
                    for _ in range(self.count()):self.count();self.count()
        elif sig.kind in (2,3):self.count()
        elif sig.kind==4:self.byte()
        elif sig.kind not in (0,5,6):self.fail('Unknown function kind')
        return sig

    def declaration(self):
        name=self.string();flags=int.from_bytes(self.take(4),'big');size=self.count();namespace=self.string()
        external=False
        if flags&(1<<22):
            marker=self.byte()
            if marker not in (32,ord('e')):self.fail('Unknown shared-type marker')
            external=marker==ord('e')
        return name,flags,size,external

    def methods(self,declaration):
        if declaration[3]:return
        self.type_info()
        for _ in range(self.count()):
            self.type_info()
            if declaration[2]:self.count()
        if declaration[2]:
            self.function()
            for _ in range(self.count()):self.function();self.function()
        for _ in range(self.count()):self.function()
        for _ in range(self.count()):self.function()

    def _read_module(self):
        if self.integer()!=1:self.fail('Only the verified stripped-debug script layout is editable')
        for _ in range(self.count()):
            declaration=self.declaration()
            if not declaration[1]&(1<<26):self.fail('Expected an enum declaration')
            if not declaration[3]:
                for _ in range(self.count()):self.string();self.take(4)
        classes=[self.declaration() for _ in range(self.count())]
        for _ in range(self.count()):self.function() # Funcdefs
        for declaration in sorted(classes,key=lambda t:bool(t[2])):self.methods(declaration)
        for declaration in classes:
            if declaration[2] and not declaration[3]:
                for _ in range(self.count()):self.string();self.data_type();self.integer()
        for _ in range(self.count()):self.declaration();self.integer() # Typedefs
        for _ in range(self.count()):self.string();self.string();self.data_type();self.function() # Globals
        for _ in range(self.count()):self.function()
        for _ in range(self.count()):self.function() # Public function references
        for _ in range(self.count()):self.bindings.append((self.function(),self.string()))
        for _ in range(self.count()):self.type_info()
        for _ in range(self.count()):self.data_type()
        for _ in range(self.count()):self.used_functions.append(None if self.byte()==ord('n') else self.signature())
        for _ in range(self.count()):self.globals.append((self.string(),self.string(),self.data_type(),self.byte()))
        for _ in range(self.count()):
            start=self.at;value=self.string();self.constants.append(StringToken(start,self.at,value))
        for _ in range(self.count()):self.type_info();self.string()
        if self.at!=len(self.raw):self.fail('Unparsed bytes remain; this version is unsupported')

    def validate_references(self):
        for function in self.functions:
            for index,ins in enumerate(function.instructions):
                if ins.name in JUMPS:
                    delta=ins.arguments[0]&0xffffffff
                    if delta>=1<<31:delta-=1<<32
                    # AngelScript serialized negative jumps count from the current instruction.
                    target=index+delta+(1 if delta>=0 else 0)
                    if not 0<=target<len(function.instructions):self.fail('Branch target is outside its function')
                if ins.name in CALLS:
                    table=self.bindings if ins.name=='CALLBND' else self.used_functions
                    if not 0<=ins.arguments[0]<len(table):self.fail('Call reference is outside its table')
                if ins.name in ('PGA','PshGPtr'):
                    value=ins.arguments[0]
                    table=self.globals if value&1 else self.constants
                    if value<0 or value>>1>=len(table):self.fail('String/global reference is outside its table')

    def describe(self,ins):
        if ins.name in CALLS:
            sig=self.bindings[ins.arguments[0]][0] if ins.name=='CALLBND' else self.used_functions[ins.arguments[0]]
            return sig.label if sig else '<null function>'
        if ins.name in ('PGA','PshGPtr'):
            value=ins.arguments[0]
            return ('global '+self.globals[value>>1][0]) if value&1 else f'string[{value>>1}]: '+self.constants[value>>1].text
        if ins.name in LITERALS:
            bits=LITERALS[ins.name];value=ins.arguments[-1]&((1<<bits)-1)
            signed=value-(1<<bits) if value&(1<<(bits-1)) else value
            floating=struct.unpack('<f' if bits==32 else '<d',value.to_bytes(bits//8,'little'))[0]
            return f'int {signed} / float {floating:g}'
        return ''

    def call_options(self,ins):
        if ins.name not in CALLS:return ()
        table=[sig for sig,module in self.bindings] if ins.name=='CALLBND' else self.used_functions
        old=table[ins.arguments[0]]
        return tuple((index,sig.label) for index,sig in enumerate(table) if old and sig and sig.shape==old.shape)

    def editable(self,ins):
        if ins.name in LITERALS:return 'literal'
        if ins.name in INVERSE:return 'condition'
        if ins.name in CALLS and self.call_options(ins):return 'call'
        return ''

    def validate_instruction(self,old,opcode,args):
        if type(opcode) is not int or not isinstance(args,(list,tuple)) or any(type(x) is not int for x in args):raise ScriptError('Invalid instruction edit.')
        if not 0<=opcode<201:raise ScriptError('Invalid opcode.')
        args=tuple(args);name=OPCODES[opcode][0]
        if opcode==old.opcode and args==old.arguments:return
        if old.name in LITERALS and opcode==old.opcode and len(args)==len(old.arguments) and args[:-1]==old.arguments[:-1]:
            bits=LITERALS[old.name]
            if -(1<<(bits-1))<=args[-1]<(1<<bits):return
        if old.name in INVERSE and name==INVERSE[old.name] and args==old.arguments:return
        if old.name in CALLS and opcode==old.opcode and len(args)==1 and args[0] in dict(self.call_options(old)):return
        raise ScriptError('Unsupported change. Edit literal values, invert a conditional branch, or select an existing call with an identical signature. Instruction count, stack slots and branch destinations stay fixed.')

    def rebuild(self,strings,instructions):
        """Rewrite parsed tokens; reindex string caches and preserve opaque bytes."""
        replacements=[];cache={}
        constant_positions={token.start:index for index,token in enumerate(self.constants)}
        for token in self.string_tokens:
            value=strings.get(constant_positions.get(token.start),token.text)
            data=value.encode('utf8')
            if len(data)*2>MAX_COUNT:raise ScriptError('String exceeds the supported serialized size.')
            if not data:output=b'\0'
            elif value in cache:output=encoded(cache[value]*2+1)
            else:
                output=encoded(len(data)*2)+data;cache[value]=len(cache)
            replacements.append((token.start,token.end,output))
        for (fi,ii),(opcode,args) in instructions.items():
            old=self.functions[fi].instructions[ii];self.validate_instruction(old,opcode,args)
            replacements.append((old.start,old.end,bytes([opcode])+b''.join(encoded(x) for x in args)))
        data=bytearray();at=0
        for start,end,value in sorted(replacements):
            if start<at:raise ScriptError('Overlapping serialized edits.')
            data.extend(self.raw[at:start]);data.extend(value);at=end
        data.extend(self.raw[at:]);struct.pack_into('<I',data,8,len(data)-self.info.payload_offset)
        rebuilt=Module(data)
        # Check semantic round-trip, including metadata strings that share the cache.
        expected=[strings.get(constant_positions.get(t.start),t.text) for t in self.string_tokens]
        if [t.text for t in rebuilt.string_tokens]!=expected:raise ScriptError('String cache round-trip mismatch.')
        if len(rebuilt.functions)!=len(self.functions):raise ScriptError('Function count changed.')
        for fi,(old,new) in enumerate(zip(self.functions,rebuilt.functions)):
            expected=[instructions.get((fi,ii),(ins.opcode,ins.arguments)) for ii,ins in enumerate(old.instructions)]
            actual=[(ins.opcode,ins.arguments) for ins in new.instructions]
            if actual!=expected:raise ScriptError('Instruction round-trip mismatch.')
        return bytes(data)
