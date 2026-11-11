"""Editable fixed-order appearance sections with one owner per AssetTable file."""
import hashlib
import struct

SECTIONS={
 'rules':('Appearance rules','アセットテーブル',384,49),
 'info':('Asset information','アセット情報',128,12),
 'variations':('Variations','バリエーション',192,10),
 'voices':('Voice / portrait','容姿情報',80,11),
 'conditions':('Condition sets','条件セット',64,2),
}


def create_models(Binary,EditableTable,Field,Record,DataError,supported_types):
    class AppearanceView(EditableTable):
        prefix='APPEARANCE_';locked_offsets=frozenset()

        def __init__(self,owner,key,group):
            self.owner=owner;self.key=key;self.title=SECTIONS[key][0];self.group_name=group[0]
            self.filename=owner.filename;self.raw=owner.raw;self.size=owner.size;self.pool=owner.pool
            self.multiline_offsets=frozenset((0x40,0x48,0x60)) if key=='info' else frozenset()
            self.labels=owner.labels;self.label_at=owner.label_at
            self.stride,count,schema=group[1:];self.fields=[]
            for i in range(count):
                name,kind,_,size,offset=struct.unpack_from('<QQQII',self.raw,schema+i*32)
                field=Field(self.string(name),self.string(kind),size,offset)
                if offset<32 or offset+size>self.stride or field.kind not in supported_types:
                    raise DataError('Unsupported appearance field layout.')
                self.fields.append(field)
            self.by_offset={f.offset:f for f in self.fields}
            if len(self.by_offset)!=len(self.fields):raise DataError('Duplicate appearance field offsets.')
            self.records=[];self.names={};start=schema+count*32
            for index in range(65536):
                at=start+index*self.stride
                if at+self.stride>32+self.size or struct.unpack_from('<HH',self.raw,at+16)!=(index,1):break
                record=Record(f'{key}:{index}',at,index)
                self.records.append(record);self.names[record.pid]=self.string(struct.unpack_from('<Q',self.raw,at+8)[0])
            if not self.records:raise DataError('Appearance section has no supported records.')
            self.by_pid={r.pid:r for r in self.records}
            for record in self.records:
                for field in self.fields:self.original(record,field)

        @property
        def changes(self):return self.owner.changes

        @changes.setter
        def changes(self,value):self.owner.changes=value

        def build(self):return self.owner.build()

    class Appearance(EditableTable):
        filename='AssetTable.bin';prefix='APPEARANCE_';project_format='fw-appearance-edits-v1';locked_offsets=frozenset()

        def __init__(self,raw):
            Binary.__init__(self,raw);self.fingerprint=hashlib.sha256(raw).hexdigest();self.changes={}
            self.label_at={at:name for name,at in self.labels.items()};self.views={}
            groups={g[0]:g for g in self.groups()}
            if 'アセットテーブル' not in groups:raise DataError('The appearance-rule section is missing.')
            for key,(title,name,stride,count) in SECTIONS.items():
                if name not in groups:continue
                group=groups[name]
                if group[1:3]!=(stride,count):raise DataError('Unsupported appearance layout: '+title)
                self.views[key]=AppearanceView(self,key,group)
            self.records=[r for v in self.views.values() for r in v.records]
            self.by_pid={r.pid:r for r in self.records};self.fields=[];self.by_offset={}

        def edit_target(self,pid,offset):
            view=self.views[pid.partition(':')[0]]
            return view.by_pid[pid],view.by_offset[offset]

        def project(self):
            return {'format':self.project_format,'source_file':self.filename,'source_sha256':self.fingerprint,
                    'changes':[{'section':pid.partition(':')[0],'row':self.by_pid[pid].index,'offset':offset,'value':value}
                               for (pid,offset),value in sorted(self.changes.items())]}

        def load_project(self,project):
            if project.get('format')!=self.project_format or project.get('source_file')!=self.filename or project.get('source_sha256')!=self.fingerprint:
                raise DataError('Appearance project belongs to a different source file.')
            before=dict(self.changes)
            try:
                self.changes={}
                for change in project['changes']:
                    view=self.views[change['section']];index=change['row']
                    if type(index) is not int or not 0<=index<len(view.records):raise DataError('Invalid appearance row index.')
                    view.set(view.records[index],view.by_offset[change['offset']],change['value'])
            except Exception:self.changes=before;raise

    class AppearanceP0(Appearance):filename='AssetTable_P0.bin'
    class AppearanceP1(Appearance):filename='AssetTable_P1.bin'
    return Appearance,AppearanceP0,AppearanceP1,AppearanceView
