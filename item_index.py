"""Current IID links, observed GLID item cells and read-only shop/lottery references."""
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
import struct
from skill_index import Evidence,strings,text_value,document_views

# Pipe characters are literal suffixes in real Item_P1 identifiers. Do not split
# them as operators or collapse an item to a shorter prefix.
IID_PATTERN=re.compile(r'''(?<![\w])(?P<negative>!?)(?P<iid>IID_[^,\s;"'!&]+)''')


def iid_tokens(text):return tuple((m['iid'],bool(m['negative'])) for m in IID_PATTERN.finditer(text))


def reference_ids(app,prefix):
    values={key for key in app.catalog if key.startswith(prefix)}
    if prefix in ('IID_','JID_','PID_'):
        for doc in app.documents.values():
            if doc.prefix==prefix:values.update(doc.by_pid)
    return values


@dataclass(frozen=True)
class ItemUse:
    source:str
    module:str
    record:str
    field:str
    text:str
    path:str=''
    table:str=''
    row:int=-1
    level:int=0
    negative:bool=False


class ItemIndex:
    def __init__(self):
        self.evidence=defaultdict(list);self.static_uses=defaultdict(list)
        self.scanned_files=[];self.errors=[];self.collections=[]

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
                    for iid,negative in set(iid_tokens(text)):
                        index.evidence[iid].append(Evidence(source,ptr+32,text,negative))
                if path.parent==base and path.name in ('Item.bin','Item_P0.bin','Item_P1.bin'):
                    index.add_collections(b,source)
            except (ValueError,struct.error,OSError,UnicodeError) as exc:index.errors.append((source,str(exc)))
        return index

    def add_collections(self,b,source):
        expected={'店':(112,9),'抽選':(72,3)}
        labels={'店':'Shop','抽選':'Lottery'}
        fields_en={'名前':'Name','アイテム':'Item','販売条件':'Sale conditions','交換対象':'Exchange items','条件':'Conditions'}
        for group,stride,count,schema in b.groups():
            if group not in expected:continue
            if (stride,count)!=expected[group]:raise ValueError('Unsupported item collection layout: '+group)
            fields=[]
            for i in range(count):
                n,k,_,size,offset=struct.unpack_from('<QQQII',b.raw,schema+i*32)
                if offset<32 or offset+size>stride:raise ValueError('Shop/lottery field exceeds its row.')
                kind=b.string(k)
                if kind in ('string','data','string[]','data[]'):
                    fields.append((fields_en.get(b.string(n),b.string(n)),kind,offset))
            start=schema+count*32
            for i in range(65536):
                at=start+i*48
                if at+48>32+b.size:break
                number,amount=struct.unpack_from('<HH',b.raw,at+16)
                key=b.string(struct.unpack_from('<Q',b.raw,at+8)[0]) if number==i else ''
                if number!=i or not key or b.labels.get(key)!=at:break
                pointer=struct.unpack_from('<Q',b.raw,at+32)[0]
                if amount and (not pointer or pointer+amount*stride>b.size):raise ValueError('Shop/lottery rows exceed the file.')
                self.collections.append((source,labels[group],key,amount))
                for row in range(amount):
                    leaf=32+pointer+row*stride
                    if struct.unpack_from('<HH',b.raw,leaf+16)!=(row,1):raise ValueError('Unsupported shop/lottery row header.')
                    for name,kind,offset in fields:
                        for path,text in strings(text_value(b,leaf+offset,kind)):
                            for iid,negative in set(iid_tokens(text)):
                                self.static_uses[iid].append(ItemUse(source,'',key,f'{labels[group]} entry {row} · {name} · 0x{offset:X}',text,path,negative=negative))

    def uses(self,iid,documents):
        live={doc.filename for doc in documents.values() if any(v.prefix=='SHOP_' for v in getattr(doc,'views',{}).values())}
        found=[use for use in self.static_uses.get(iid,()) if use.source not in live]
        for module,doc in document_views(documents):
            for record in doc.records:
                table='';row=-1
                if doc.filename=='Growth.bin' or doc.prefix in ('SHOP_','DEPLOY_'):table,row=doc.row_location[record.pid]
                for field in doc.fields:
                    if field.kind not in ('string','data','string[]','data[]','string[,]','data[,]'):continue
                    for path,text in strings(doc.value(record,field)):
                        for reference,negative in set(iid_tokens(text)):
                            if reference==iid:
                                target='Shop & Loot' if doc.prefix=='SHOP_' else 'Facilities & Rewards' if doc.prefix=='FACILITY_' else 'Profiles & Affiliations' if doc.prefix=='PROFILE_' else 'Appearance rules' if doc.prefix=='APPEARANCE_' else 'Skills' if doc.prefix=='SID_' else 'Items' if doc.prefix=='IID_' else module
                                found.append(ItemUse(doc.filename,target,record.pid,f'{field.label} · 0x{field.offset:X}',text,path,table,row,negative=negative))
            progression=getattr(doc,'progression',None)
            if progression is not None:
                bare=iid.removeprefix('IID_')
                for record in progression.records:
                    category=progression.value(record,progression.by_offset[0x20])
                    if category not in range(4,9):continue
                    for level,field in enumerate(progression.fields[1:],1):
                        if progression.value(record,field)==bare:
                            table,row=progression.row_location[record.pid]
                            found.append(ItemUse(doc.filename,'GLID progression',record.pid,f'GLID item-name cell · category {category} · level {"80+" if level==80 else level}',bare,table=table,row=row,level=level))
        return sorted(found,key=lambda u:(u.source.casefold(),u.module,u.record.casefold(),u.field,u.path))
