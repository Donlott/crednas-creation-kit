"""Current explicit PID references in supported loaded editable fields."""
from dataclasses import dataclass
import re
from skill_index import document_views,strings

PID_PATTERN=re.compile(r'''(?<![\w])!?PID_[^,\s;"'!&]+''')


@dataclass(frozen=True)
class CharacterUse:
    source:str
    module:str
    record:str
    field:str
    text:str
    path:str=''
    table:str=''
    row:int=-1
    level:int=0


def uses(pid,documents):
    found=[]
    modules={'SHOP_':'Shop & Loot','FACILITY_':'Facilities & Rewards','PROFILE_':'Profiles & Affiliations',
             'APPEARANCE_':'Appearance rules','SID_':'Skills','IID_':'Items'}
    for module,doc in document_views(documents):
        for record in doc.records:
            table='';row=-1
            if hasattr(doc,'row_location'):table,row=doc.row_location[record.pid]
            for field in doc.fields:
                if field.kind not in ('string','data','ref','string[]','data[]','string[,]','data[,]'):continue
                for path,text in strings(doc.value(record,field)):
                    if any(m.group().removeprefix('!')==pid for m in PID_PATTERN.finditer(text)):
                        found.append(CharacterUse(doc.filename,modules.get(doc.prefix,module),record.pid,
                            f'{field.label} · 0x{field.offset:X}',text,path,table,row))
    return sorted(found,key=lambda u:(u.module!='Characters',u.source,u.record,u.field,u.path))
