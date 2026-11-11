"""Current explicit JID links and observed bare GLID class-name references."""
from dataclasses import dataclass
import re
from skill_index import document_views,strings

JID_PATTERN=re.compile(r'''(?<![\w])!?JID_[^,\s;"'!&]+''')


@dataclass(frozen=True)
class ClassUse:
    source:str
    module:str
    record:str
    field:str
    text:str
    path:str=''
    table:str=''
    row:int=-1
    level:int=0


def uses(jid,documents):
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
                    if any(match.group().removeprefix('!')==jid for match in JID_PATTERN.finditer(text)):
                        found.append(ClassUse(doc.filename,modules.get(doc.prefix,module),record.pid,
                                              f'{field.label} · 0x{field.offset:X}',text,path,table,row))
        progression=getattr(doc,'progression',None)
        if progression:
            for record in progression.records:
                if progression.value(record,progression.by_offset[0x20])!=0:continue
                for level,field in enumerate(progression.fields[1:],1):
                    if progression.value(record,field)==jid.removeprefix('JID_'):
                        table,row=progression.row_location[record.pid]
                        found.append(ClassUse(doc.filename,'GLID progression',record.pid,
                            f'GLID class-name cell · level {"80+" if level==80 else level}',jid.removeprefix('JID_'),table=table,row=row,level=level))
    return sorted(found,key=lambda u:(u.module!='Characters',u.source,u.record,u.field,u.path))
