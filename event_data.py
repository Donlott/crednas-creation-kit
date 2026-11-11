"""Fixed native event rules and ordered timeline entries; no script-bytecode rewriting."""
import hashlib
import struct

VARIABLE_FILES=('Variable.bin','Variable_P0.bin','Variable_P1.bin')
TIMELINE_FILES=('Timeline_Com.bin','Timeline_Part0_Ism.bin','Timeline_Part1_Dit.bin','Timeline_Part1_Kai.bin',
                'Timeline_Part1_Led.bin','Timeline_Part1_Seo.bin','Timeline_Part2.bin','Timeline_Part3_Ism.bin')
EVENT_FILES=VARIABLE_FILES+TIMELINE_FILES+('Chapter.bin','Situation.bin')
# key, title, native schema, stride, fields, container width (0 = flat primary rows)
LAYOUTS={
 'variables':('Variable rules','変数',104,13,0),
 'timeline':('Timeline events','タイムライン',216,21,48),
 'chapter':('Chapter flag permissions','フラグ開放',88,7,0),
 'situations':('Situation rules','状況',96,8,0),
}
EXPECTED={
 'variables':{0x20:('string',8),**{o:('int',4) for o in (0x28,0x2c,0x30)},0x38:('string[]',16),
              0x48:('u8',1),0x49:('u8',1),0x50:('string[,]',16),0x60:('u16',2),
              0x62:('u8',1),0x63:('u8',1),0x64:('u16',2),0x66:('u8',1)},
 'timeline':{0x20:('u8',1),0x21:('u8',1),0x28:('string[]',16),0x38:('string[,]',16),0x48:('string[]',16),
             0x58:('s8',1),0x59:('s8',1),0x5a:('s16',2),0x5c:('s8',1),0x5d:('s8',1),0x5e:('s16',2),
             0x60:('string',8),0x68:('u8',1),0x70:('data',16),0x80:('data',16),0x90:('string',8),
             0x98:('u8',1),0xa0:('data',16),0xb0:('string[]',16),0xc0:('data',16),0xd0:('string',8)},
 'chapter':{**{o:('u8',1) for o in (0x20,0x21,0x22,0x23)},**{o:('string[]',16) for o in (0x28,0x38,0x48)}},
 'situations':{0x20:('string[,]',16),0x30:('u16',2),0x32:('u8',1),0x33:('u8',1),0x34:('u8',1),
               0x38:('data',16),0x48:('string',8),0x50:('data',16)},
}


def create_models(Binary,EditableTable,CollectionTable,Field,Record,DataError):
    class EventView(CollectionTable):
        prefix='EVENT_'
        def __init__(self,owner,key,group):
            self.owner=owner;self.key=key;self.title,self.group_name,_,_,container=LAYOUTS[key]
            self.filename=owner.filename;self.raw=owner.raw;self.size=owner.size;self.pool=owner.pool
            self.labels=owner.labels;self.label_at=owner.label_at;self.stride,count,schema=group[1:]
            self.fields=[]
            for i in range(count):
                n,k,_,size,offset=struct.unpack_from('<QQQII',self.raw,schema+32*i)
                self.fields.append(Field(self.string(n),self.string(k),size,offset))
            self.by_offset={f.offset:f for f in self.fields}
            if len(self.by_offset)!=count or {f.offset:(f.kind,f.size) for f in self.fields}!=EXPECTED[key]:raise DataError('Unsupported event field schema: '+self.filename)
            self.locked_offsets=frozenset({0x20} if key=='variables' else {0xd0} if key=='timeline' else ())
            self.collections=[];self.records=[];self.rows_by_table={};self.row_location={};self.names={}
            start=schema+count*32
            for i in range(65536):
                at=start+i*(container or self.stride)
                if at+32>32+self.size or struct.unpack_from('<H',self.raw,at+16)[0]!=i:break
                table=f'{key}:{i}';number,amount=struct.unpack_from('<HH',self.raw,at+16)
                if container:
                    if at+container>32+self.size:raise DataError('Event container is outside the data.')
                    pointer=struct.unpack_from('<Q',self.raw,at+32)[0]
                    if amount and (not pointer or pointer+amount*self.stride>self.size):raise DataError('Event array is outside the data.')
                    leaves=[(32+pointer+j*self.stride,j) for j in range(amount)]
                else:
                    if amount!=1:break
                    leaves=[(at,i)]
                self.collections.append(Record(table,at,i));self.rows_by_table[table]=[]
                self.names[table]=self.string(struct.unpack_from('<Q',self.raw,at+8)[0])
                for j,(offset,ordinal) in enumerate(leaves):
                    if offset<32 or offset+self.stride>32+self.size or struct.unpack_from('<HH',self.raw,offset+16)!=(ordinal,1):raise DataError('Event row header/order differs.')
                    row=Record(table+f':{j}',offset,ordinal);self.records.append(row);self.rows_by_table[table].append(row)
                    self.row_location[row.pid]=(table,j)
                if key=='variables':self.names[table]=self.original(self.rows_by_table[table][0],self.by_offset[0x20])
            if not self.collections:raise DataError('No supported event rows: '+self.filename)
            self.by_pid={r.pid:r for r in self.records};self.tables_by_id={r.pid:r for r in self.collections}
            for row in self.records:
                for field in self.fields:self.original(row,field)
        @property
        def changes(self):return self.owner.changes
        @changes.setter
        def changes(self,value):self.owner.changes=value
        def set(self,record,field,value):
            if field.offset in self.locked_offsets:raise DataError('Event variable names and timeline hash keys are fixed to preserve existing references.')
            super().set(record,field,value)
        def build(self):return self.owner.build()
        def validate_record(self,row):pass

    class EventData(EditableTable):
        prefix='EVENT_';locked_offsets=frozenset();project_format='fw-event-edits-v1'
        def __init__(self,raw,filename):
            if filename not in EVENT_FILES:raise DataError('Unsupported event source filename.')
            self.filename=filename;Binary.__init__(self,raw);self.fingerprint=hashlib.sha256(raw).hexdigest();self.changes={}
            self.label_at={offset:key for key,offset in self.labels.items()}
            key='variables' if filename in VARIABLE_FILES else 'timeline' if filename in TIMELINE_FILES else 'chapter' if filename=='Chapter.bin' else 'situations'
            title,native,stride,count,_=LAYOUTS[key];group=next((g for g in self.groups() if g[0]==native),None)
            if not group or group[1:3]!=(stride,count):raise DataError('Unsupported event layout; this editor targets version 1.00.')
            self.views={key:EventView(self,key,group)};self.fields=[];self.by_offset={}
            self.records=[r for v in self.views.values() for r in v.records];self.by_pid={r.pid:r for r in self.records}
        def edit_target(self,pid,offset):
            view=self.views[pid.partition(':')[0]];return view.by_pid[pid],view.by_offset[offset]
        def reparse(self,raw):return EventData(raw,self.filename)
        def project(self):return {**super().project(),'source_file':self.filename}
        def load_project(self,project):
            if project.get('format')!=self.project_format or project.get('source_file')!=self.filename or project.get('source_sha256')!=self.fingerprint:
                raise DataError('Event project belongs to a different original source file.')
            before=self.snapshot_edits()
            try:
                self.clear_edits()
                for change in project['changes']:
                    row,field=self.edit_target(change['pid'],change['offset']);self.views[change['pid'].partition(':')[0]].set(row,field,change['value'])
            except Exception:self.restore_edits(before);raise
    return EventData,EventView
