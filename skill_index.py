"""SID references from editable tables, read-only item links and original file strings."""
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
import struct

# Brackets, parentheses, fullwidth plus signs and '>' are part of real SID names.
SID_PATTERN=re.compile(r'''(?<![\w])(?P<negative>!?)(?P<sid>SID_[^,\s;"'!&|]+)''')


def sid_tokens(text):
    return tuple((m['sid'],bool(m['negative'])) for m in SID_PATTERN.finditer(text))


def strings(value,path=''):
    if isinstance(value,str):yield path,value
    elif isinstance(value,list):
        for i,entry in enumerate(value):yield from strings(entry,path+f'[{i}]')


@dataclass(frozen=True)
class SkillUse:
    source:str
    module:str
    record:str
    field:str
    text:str
    path:str=''
    table:str=''
    row:int=-1
    negative:bool=False


@dataclass(frozen=True)
class Evidence:
    source:str
    offset:int
    text:str
    negative:bool=False


def text_value(binary,at,kind):
    if kind in ('string','data'):return binary.string(struct.unpack_from('<Q',binary.raw,at)[0])
    nested=kind in ('string[,]','data[,]')
    count,width,_,pointer=struct.unpack_from('<HHIQ',binary.raw,at)
    expected=16 if nested or kind=='data[]' else 8
    if width!=expected or (count and (not pointer or pointer+count*width>binary.size)):
        raise ValueError('Unsupported reference-list layout.')
    if nested:return [text_value(binary,32+pointer+i*width,'data[]' if kind=='data[,]' else 'string[]') for i in range(count)]
    return [text_value(binary,32+pointer+i*width,'data' if kind=='data[]' else 'string') for i in range(count)]


def item_label(name):
    return {'装備スキル':'Equipped skills','所持スキル':'Held skills','使用スキル':'Use skill',
            '付与スキル':'Granted skills','解除スキル':'Removed skills','必要スキル':'Required skills',
            '禁止スキル':'Forbidden skills','レベル１':'Level 1','レベル２':'Level 2','レベル３':'Level 3'}.get(name,name)


def document_views(documents):
    for module,owner in documents.items():
        views=getattr(owner,'views',{})
        if not views or getattr(owner,'fields',()):yield module,owner
        for view in views.values():yield 'Events' if view.prefix=='EVENT_' else 'Progression & Difficulty' if view.prefix=='EXPANDED_' else 'Battle deployment' if view.prefix=='DEPLOY_' else module,view


class SkillIndex:
    def __init__(self):
        self.evidence=defaultdict(list);self.static_uses=defaultdict(list)
        self.scanned_files=[];self.errors=[];self.link_tables=[]

    @classmethod
    def load(cls,base,binary_type):
        index=cls();base=Path(base)
        for path in sorted(base.rglob('*.bin')):
            source=path.relative_to(base).as_posix()
            try:
                b=binary_type(path.read_bytes());index.scanned_files.append(source);seen=set()
                for at in b.pointers:
                    ptr=struct.unpack_from('<Q',b.raw,32+at)[0]
                    if ptr<b.pool or ptr in seen:continue
                    seen.add(ptr);text=b.string(ptr)
                    for sid,negative in set(sid_tokens(text)):
                        index.evidence[sid].append(Evidence(source,ptr+32,text,negative))
                # Item assignments and auxiliary skill groups are read-only. Do not
                # flatten side files or infer an overlay/override order.
                if path.parent==base and path.name in ('Item.bin','Item_P0.bin','Item_P1.bin','Skill.bin','Skill_P0.bin','Skill_P1.bin'):
                    index.add_static_links(b,source)
            except (ValueError,struct.error,OSError,UnicodeError) as exc:index.errors.append((source,str(exc)))
        return index

    def add_static_links(self,binary,source):
        for group,stride,count,schema in binary.groups():
            if group=='スキル':continue # Primary skills are read from live documents instead.
            if source.startswith('Item') and group!='アイテム':continue
            fields=[]
            for i in range(count):
                n,k,_,size,offset=struct.unpack_from('<QQQII',binary.raw,schema+i*32)
                kind=binary.string(k)
                if offset<32 or offset+size>stride:raise ValueError('Reference field exceeds its record.')
                if kind in ('string','data','string[]','data[]','string[,]','data[,]'):
                    fields.append((binary.string(n),kind,offset))
            total=0
            for i in range(65536):
                at=schema+count*32+i*stride
                if at+stride>32+binary.size or struct.unpack_from('<HH',binary.raw,at+16)!=(i,1):break
                key=binary.string(struct.unpack_from('<Q',binary.raw,at+8)[0]);total+=1
                for name,kind,offset in fields:
                    for location,text in strings(text_value(binary,at+offset,kind)):
                        for sid,negative in set(sid_tokens(text)):
                            self.static_uses[sid].append(SkillUse(source,'',key or f'{group} #{i}',f'{item_label(name)} · 0x{offset:X}',text,location,negative=negative))
            self.link_tables.append((source,group,total))

    def uses(self,sid,documents):
        """Current field references, not recursive ownership or runtime activation."""
        found=[]
        # Duck typing keeps this reader independent of the editor entry-point name.
        for module,doc in document_views(documents):
            for record in doc.records:
                table='';row=-1
                if doc.filename=='Growth.bin':
                    table,row=doc.row_location[record.pid]
                for field in doc.fields:
                    if field.kind not in ('string','data','string[]','data[]','string[,]','data[,]'):continue
                    for location,text in strings(doc.value(record,field)):
                        for reference,negative in set(sid_tokens(text)):
                            if reference==sid:
                                found.append(SkillUse(doc.filename,'Shop & Loot' if doc.prefix=='SHOP_' else 'Facilities & Rewards' if doc.prefix=='FACILITY_' else 'Profiles & Affiliations' if doc.prefix=='PROFILE_' else 'Appearance rules' if doc.prefix=='APPEARANCE_' else 'Skills' if doc.filename.startswith('Skill') else 'Items' if doc.filename.startswith('Item') else module,
                                    record.pid,f'{field.label} · 0x{field.offset:X}',text,location,table,row,negative))
        live_items={doc.filename for doc in documents.values() if doc.prefix=='IID_'}
        static=[use for use in self.static_uses.get(sid,()) if use.source not in live_items]
        return sorted([*static,*found],key=lambda u:(u.source.casefold(),u.record.casefold(),u.field,u.path))
