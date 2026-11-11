"""Fixed native profile/affiliation slots, sharing one Profile.bin owner."""
import hashlib
import struct
from dataclasses import dataclass

SECTIONS={
 'profiles':('Profiles','プロフィール',328,46),
 'affiliations':('Affiliations','所属',88,5),
 'expressions':('Conversation expressions','会話表情',64,6),
 'limits':('Conversation restrictions','会話制限',48,1),
 'order':('Roster order','キャラ表示順',56,9),
}


def create_models(Binary,EditableTable,Field,Record,DataError,supported_types):
    class ProfileView(EditableTable):
        prefix='PROFILE_';locked_offsets=frozenset()
        def __init__(self,owner,key,group):
            self.owner=owner;self.key=key;self.title=SECTIONS[key][0];self.group_name=group[0]
            self.filename=owner.filename;self.raw=owner.raw;self.size=owner.size;self.pool=owner.pool
            self.labels=owner.labels;self.label_at=owner.label_at
            self.stride,count,schema=group[1:];self.fields=[]
            for i in range(count):
                name,kind,_,size,offset=struct.unpack_from('<QQQII',self.raw,schema+i*32)
                field=Field(self.string(name),self.string(kind),size,offset)
                if offset<32 or offset+size>self.stride or field.kind not in supported_types:
                    raise DataError('Unsupported profile field layout.')
                self.fields.append(field)
            self.by_offset={f.offset:f for f in self.fields}
            if len(self.by_offset)!=len(self.fields):raise DataError('Duplicate profile field offsets.')
            self.records=[];self.names={};start=schema+count*32
            for index in range(65536):
                at=start+index*self.stride
                if at+self.stride>32+self.size or struct.unpack_from('<HH',self.raw,at+16)!=(index,1):break
                record=Record(f'{key}:{index}',at,index)
                self.records.append(record);self.names[record.pid]=self.string(struct.unpack_from('<Q',self.raw,at+8)[0])
            if not self.records:raise DataError('Profile section has no supported records.')
            self.by_pid={r.pid:r for r in self.records}
            for record in self.records:
                for field in self.fields:self.original(record,field)
        @property
        def changes(self):return self.owner.changes
        @changes.setter
        def changes(self,value):self.owner.changes=value
        def build(self):return self.owner.build()
        def validate_record(self,record):
            if self.key=='profiles' and len(self.value(record,self.by_offset[0x68]))!=len(self.value(record,self.by_offset[0x78])):
                raise DataError('History years and history message keys must have the same number of entries.')

    class Profile(EditableTable):
        filename='Profile.bin';prefix='PROFILE_';project_format='fw-profile-edits-v1';locked_offsets=frozenset()
        def __init__(self,raw):
            Binary.__init__(self,raw);self.fingerprint=hashlib.sha256(raw).hexdigest();self.changes={}
            self.label_at={at:name for name,at in self.labels.items()};self.views={};groups={g[0]:g for g in self.groups()}
            for key,(title,name,stride,count) in SECTIONS.items():
                group=groups.get(name)
                if group is None or group[1:3]!=(stride,count):raise DataError('Unsupported Profile.bin layout: '+title)
                self.views[key]=ProfileView(self,key,group)
            self.records=[r for v in self.views.values() for r in v.records]
            self.by_pid={r.pid:r for r in self.records};self.fields=[];self.by_offset={}
        def edit_target(self,pid,offset):
            view=self.views[pid.partition(':')[0]]
            return view.by_pid[pid],view.by_offset[offset]
        def validate(self):
            for view in self.views.values():
                for record in view.records:view.validate_record(record)
        def build(self):
            self.validate()
            return super().build()
        def project(self):
            return {'format':self.project_format,'source_sha256':self.fingerprint,
                    'changes':[{'section':pid.partition(':')[0],'row':self.by_pid[pid].index,'offset':offset,'value':value}
                               for (pid,offset),value in sorted(self.changes.items())]}
        def load_project(self,project):
            if project.get('format')!=self.project_format or project.get('source_sha256')!=self.fingerprint:
                raise DataError('Profile project belongs to a different source file.')
            before=dict(self.changes)
            try:
                self.changes={}
                for change in project['changes']:
                    view=self.views[change['section']];index=change['row']
                    if type(index) is not int or not 0<=index<len(view.records):raise DataError('Invalid profile row index.')
                    view.set(view.records[index],view.by_offset[change['offset']],change['value'])
                self.validate()
            except Exception:self.changes=before;raise
    return Profile,ProfileView


@dataclass(frozen=True)
class Connection:
    module:str
    record:str
    relation:str
    raw:str


def connections(view,record,documents):
    """Direct current field links only; no inherited affiliation or event evaluation."""
    name=view.names[record.pid];found=[];person=documents.get('Characters');owner=view.owner
    if person and view.key in ('profiles','affiliations','order'):
        offset={'profiles':0x118,'affiliations':0x148,'order':0x20}[view.key]
        for row in person.records:
            if person.value(row,person.by_offset[offset])==name:
                found.append(Connection('Characters',row.pid,'Current character reference',row.pid))
    if view.key=='profiles':
        for row in view.records:
            for offset,title in ((0x30,'Profile group reference'),(0x138,'Senior-target reference')):
                value=view.value(row,view.by_offset[offset])
                if value==name or isinstance(value,list) and name in value:
                    found.append(Connection('Profiles & Affiliations',row.pid,title,view.names[row.pid]))
    if view.key=='affiliations':
        for row in view.records:
            if view.value(row,view.by_offset[0x48])==name:
                found.append(Connection('Profiles & Affiliations',row.pid,'Incoming affiliation transition',view.names[row.pid]))
    # Direct outgoing links remain visible alongside owners.
    offsets=(0x30,0x138) if view.key=='profiles' else (0x48,) if view.key=='affiliations' else ()
    for offset in offsets:
        value=view.value(record,view.by_offset[offset]);values=value if isinstance(value,list) else [value]
        for key in values:
            if not key:continue
            for peer in owner.views.values():
                for row in peer.records:
                    if peer.names[row.pid]==key:
                        found.append(Connection('Profiles & Affiliations',row.pid,'Outgoing '+('profile group' if offset==0x30 else 'senior target' if offset==0x138 else 'affiliation transition'),key))
    return found
