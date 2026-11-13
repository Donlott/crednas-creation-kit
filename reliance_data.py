"""Fixed-row Reliance.bin views sharing one editable document and export."""
import hashlib
import struct

# IDs are editor-only keys. Native names (including duplicate/empty names), order
# and headers stay intact; all seven sections are exported together.
SECTIONS={
 'matrix':('Compatibility','支援一覧',48,1),
 'special':('Pair bonuses','特殊支援',88,12),
 'talks':('Support conditions','支援会話',136,24),
 'scout':('Recruitment','スカウト',160,14),
 'assist':('Wings of Salvation','支援援護',48,1),
 'voices':('Linked voices','連携掛合',96,5),
 'drinks':('Tobias items','トビヤススカウト',48,1),
}


def create_models(Binary,EditableTable,Field,Record,DataError,supported_types):
    """Inject the entry point's model classes, avoiding a second __main__ import."""
    class RelianceView(EditableTable):
        filename='Reliance.bin';prefix='SUPPORT_';locked_offsets=frozenset()

        def __init__(self,owner,key,group):
            self.owner=owner;self.key=key;self.title=SECTIONS[key][0]
            self.raw=owner.raw;self.size=owner.size;self.pool=owner.pool
            self.labels=owner.labels;self.label_at=owner.label_at
            self.stride,self.fields_count,schema=group[1:]
            self.fields=[]
            for i in range(self.fields_count):
                name,kind,_,size,offset=struct.unpack_from('<QQQII',self.raw,schema+i*32)
                field=Field(self.string(name),self.string(kind),size,offset)
                if offset<32 or offset+size>self.stride or field.kind not in supported_types:
                    raise DataError('Unsupported Reliance field layout.')
                self.fields.append(field)
            self.by_offset={f.offset:f for f in self.fields}
            if len(self.by_offset)!=len(self.fields):raise DataError('Duplicate Reliance field offsets.')
            self.records=[];self.names={};self.anchors={};anchor=''
            start=schema+self.fields_count*32
            for index in range(65536):
                at=start+index*self.stride
                if at+self.stride>32+self.size or struct.unpack_from('<HH',self.raw,at+16)!=(index,1):break
                name=self.string(struct.unpack_from('<Q',self.raw,at+8)[0])
                record=Record(f'{key}:{index}',at,index)
                self.records.append(record);self.names[record.pid]=name
                if name:anchor=name
                self.anchors[record.pid]=anchor
            if not self.records:raise DataError('Reliance section has no supported rows: '+self.title)
            self.by_pid={r.pid:r for r in self.records}
            for row in self.records:
                for field in self.fields:self.original(row,field)
            if key=='matrix':
                if len(set(self.names.values()))!=len(self.records) or not all(v.startswith('RID_') for v in self.names.values()):
                    raise DataError('Unsupported compatibility row identifiers.')
                if set(self.by_offset)!={0x20} or self.by_offset[0x20].kind!='u8[]':raise DataError('Unsupported compatibility vector.')
                if any(len(self.original(r,self.by_offset[0x20]))!=len(self.records) for r in self.records):
                    raise DataError('Compatibility row and column counts differ.')

        @property
        def changes(self):return self.owner.changes

        @changes.setter
        def changes(self,value):self.owner.changes=value

        def set(self,record,field,value):
            if self.key in ('matrix','assist') and field.kind=='u8[]':
                if not isinstance(value,list) or len(value)!=len(self.original(record,field)):
                    raise DataError('This vector has a fixed length; existing row/column order is preserved.')
            super().set(record,field,value)

        def build(self):return self.owner.build()

        def guard_rates(self,record):
            if self.key!='assist' or set(self.by_offset)!={0x20} or self.by_offset[0x20].kind!='u8[]':
                raise DataError('This section is not the supported Wings of Salvation rate table.')
            values=self.value(record,self.by_offset[0x20])
            if len(values)!=5:raise DataError('Wings of Salvation requires five support-level rate columns.')
            return values

        def set_guard_rates(self,record,values):
            self.guard_rates(record)
            if not isinstance(values,list) or len(values)!=5 or any(type(v) is not int or not 0<=v<=100 for v in values):
                raise DataError('Wings of Salvation rates must be five whole-number percentages from 0 to 100.')
            self.set(record,self.by_offset[0x20],values)

    class Reliance(EditableTable):
        filename='Reliance.bin';prefix='SUPPORT_';project_format='fw-reliance-edits-v1';locked_offsets=frozenset()

        def __init__(self,raw):
            Binary.__init__(self,raw);self.changes={};self.fingerprint=hashlib.sha256(raw).hexdigest()
            self.label_at={offset:name for name,offset in self.labels.items()}
            groups={g[0]:g for g in self.groups()};self.views={}
            for key,(title,name,stride,count) in SECTIONS.items():
                group=groups.get(name)
                if group is None or group[1:3]!=(stride,count):raise DataError('Unsupported Reliance.bin section: '+title)
                self.views[key]=RelianceView(self,key,group)
            self.records=[r for view in self.views.values() for r in view.records]
            self.by_pid={r.pid:r for r in self.records}
            self.fields=[];self.by_offset={}

        def edit_target(self,pid,offset):
            view=self.views[pid.partition(':')[0]]
            return view.by_pid[pid],view.by_offset[offset]

        def project(self):
            return {'format':self.project_format,'source_sha256':self.fingerprint,
                    'changes':[{'section':pid.partition(':')[0],'row':self.by_pid[pid].index,'offset':offset,'value':value}
                               for (pid,offset),value in sorted(self.changes.items())]}

        def load_project(self,project):
            if project.get('format')!=self.project_format or project.get('source_sha256')!=self.fingerprint:
                raise DataError('This project belongs to a different source Reliance.bin.')
            before=dict(self.changes)
            try:
                self.changes={}
                for change in project['changes']:
                    view=self.views[change['section']];index=change['row']
                    if type(index) is not int or not 0<=index<len(view.records):raise DataError('Invalid Reliance row index.')
                    view.set(view.records[index],view.by_offset[change['offset']],change['value'])
            except Exception:self.changes=before;raise

    return Reliance,RelianceView
