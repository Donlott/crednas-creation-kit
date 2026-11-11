"""Experience, automatic grants and difficulty views share their original owners."""
import hashlib
import struct

SECTIONS={
 'exp_curve':('Experience curves','経験値',40,2,2),
 'exp_modifiers':('Experience modifiers','経験補正',40,4,2),
 'exp_calculation':('Experience calculation links','経験計算',48,1,1),
 'auto_exp':('Automatic aptitude experience','自動成長技能経験値',40,2,2),
 'auto_class':('Automatic class decisions','自動成長兵種判定',80,15,1),
 'auto_items':('Automatic item grants','自動成長付与アイテム',128,6,1),
 'hero_items':('Protagonist item grants','自動成長主人公付与アイテム',80,3,1),
 'auto_legions':('Automatic legion grants','自動成長付与軍団兵',128,6,1),
 'part2_items':('Part 2 item supplies','2部支給アイテム',88,4,1),
 'part2_legions':('Part 2 legion supplies','2部支給軍団兵',56,2,1),
 'difficulty':('Difficulty loadouts','難易度差分',176,9,1),
 'auto_gear':('Automatic personal equipment','おまかせ装備',64,2,1),
}
GROWTH_KEYS=tuple(SECTIONS)[:10]
PERSON_KEYS=('difficulty','auto_gear')
EXPECTED={
 'exp_curve':{0x20:('u8',1),0x22:('u16',2)},
 'exp_modifiers':{0x20:('s8',1),**{o:('u16',2) for o in (0x22,0x24,0x26)}},
 'exp_calculation':{0x20:('data',16)},
 'auto_exp':{0x20:('u16',2),0x22:('u16',2)},
 'auto_class':{0x20:('data',16),**{o:('u8',1) for o in range(0x30,0x3d)},0x40:('data',16)},
 'auto_items':{o:('data',16) for o in range(0x20,0x80,16)},
 'hero_items':{0x20:('data',16),0x30:('data[]',16),0x40:('data[]',16)},
 'auto_legions':{o:('data',16) for o in range(0x20,0x80,16)},
 'part2_items':{0x20:('u8',1),0x28:('u8[]',16),0x38:('data[]',16),0x48:('u8[]',16)},
 'part2_legions':{0x20:('u16',2),0x28:('data[]',16)},
 'difficulty':{**{o:('data[]',16) for o in (0x20,0x30,0x50,0x60,0x80,0x90)},**{o:('data[,]',16) for o in (0x40,0x70,0xa0)}},
 'auto_gear':{0x20:('data',16),0x30:('data[]',16)},
}


def create_models(Binary,EditableTable,CollectionTable,Field,Record,DataError):
    class ExpandedView(CollectionTable):
        prefix='EXPANDED_';locked_offsets=frozenset()
        def __init__(self,owner,key,group):
            self.owner=owner;self.key=key;self.title,self.group_name,_,_,self.container=SECTIONS[key]
            self.filename=owner.filename;self.raw=owner.raw;self.size=owner.size;self.pool=owner.pool
            self.labels=owner.labels;self.label_at=owner.label_at;self.stride,count,schema=group[1:]
            self.fields=[]
            for i in range(count):
                n,k,_,size,offset=struct.unpack_from('<QQQII',self.raw,schema+i*32)
                self.fields.append(Field(self.string(n),self.string(k),size,offset))
            self.by_offset={f.offset:f for f in self.fields}
            if len(self.by_offset)!=count or {f.offset:(f.kind,f.size) for f in self.fields}!=EXPECTED[key]:
                raise DataError('Unsupported '+self.filename+' '+self.title+' field layout.')
            self.collections=[];self.records=[];self.names={};self.rows_by_table={};self.row_location={};self.collection_offsets=[]
            start=schema+count*32
            def append(at,native_index,table,pid):
                if at<32 or at+self.stride>32+self.size or struct.unpack_from('<HH',self.raw,at+16)!=(native_index,1):
                    raise DataError('Expanded progression entry header differs.')
                row=Record(pid,at,native_index);self.records.append(row);self.rows_by_table[table].append(row)
                self.names[pid]=self.string(struct.unpack_from('<Q',self.raw,at+8)[0]);self.row_location[pid]=(table,native_index)
            for i in range(65536):
                at=start+i*(48 if self.container==2 else self.stride)
                if at+32>32+self.size or struct.unpack_from('<H',self.raw,at+16)[0]!=i:break
                table=f'{key}:{i}';native=self.string(struct.unpack_from('<Q',self.raw,at+8)[0])
                if self.container==1:
                    if struct.unpack_from('<H',self.raw,at+18)[0]!=1:break
                    self.collections.append(Record(table,at,i));self.names[table]=native;self.rows_by_table[table]=[]
                    append(at,i,table,table+':0')
                else:
                    if at+48>32+self.size or not native or self.labels.get(native)!=at:raise DataError('Expanded progression collection identity differs.')
                    count=struct.unpack_from('<H',self.raw,at+18)[0];pointer=struct.unpack_from('<Q',self.raw,at+32)[0]
                    if count and (not pointer or pointer+count*self.stride>self.size):raise DataError('Expanded progression entries are outside the data.')
                    self.collections.append(Record(table,at,i));self.collection_offsets.append(at)
                    self.names[table]=native;self.rows_by_table[table]=[]
                    for j in range(count):append(32+pointer+j*self.stride,j,table,f'{table}:{j}')
            if not self.collections:raise DataError('No supported '+self.title+' records were found.')
            self.by_pid={r.pid:r for r in self.records};self.tables_by_id={r.pid:r for r in self.collections}
            for row in self.records:
                for field in self.fields:self.original(row,field)
        @property
        def changes(self):return self.owner.changes
        @changes.setter
        def changes(self,value):self.owner.changes=value
        def build(self):return self.owner.build()
        def validate_record(self,row):
            # Native supply lists may contain alternatives with a single quantity,
            # or no quantity at all. Their relationship is not established.
            pass

    def attach(owner,keys):
        groups={g[0]:g for g in owner.groups()};views={};kinds={}
        pos=32
        while True:
            pos=owner.raw.find(b'\x01\x12\x25\x20',pos,32+owner.size)
            if pos<0:break
            if pos+32<=32+owner.size:kinds[struct.unpack_from('<Q',owner.raw,pos+24)[0]+32]=struct.unpack_from('<I',owner.raw,pos+4)[0]
            pos+=4
        for key in keys:
            title,native,stride,count,container=SECTIONS[key];group=groups.get(native)
            if group is None:continue
            if group[1:3]!=(stride,count) or kinds.get(group[3])!=container:raise DataError('Unsupported '+owner.filename+' '+title+' layout.')
            views[key]=ExpandedView(owner,key,group)
        return views

    class GrowthSide(EditableTable):
        filename='Growth_P0.bin';prefix='EXPANDED_';project_format='fw-expanded-side-edits-v1';locked_offsets=frozenset()
        def __init__(self,raw):
            Binary.__init__(self,raw);self.fingerprint=hashlib.sha256(raw).hexdigest();self.changes={}
            self.label_at={at:name for name,at in self.labels.items()};self.views=attach(self,('part2_items',))
            if not self.views:raise DataError('No supported supplies in Growth_P0.bin.')
            self.records=[r for view in self.views.values() for r in view.records];self.by_pid={r.pid:r for r in self.records};self.fields=[];self.by_offset={}
        def edit_target(self,pid,offset):
            view=self.views[pid.partition(':')[0]];return view.by_pid[pid],view.by_offset[offset]
        def build(self):
            for view in self.views.values():
                for row in view.records:view.validate_record(row)
            return super().build()
        def project(self):return {**super().project(),'source_file':self.filename}
        def load_project(self,project):
            if project.get('format')!=self.project_format or project.get('source_file')!=self.filename or project.get('source_sha256')!=self.fingerprint:
                raise DataError('Expanded progression project belongs to a different source file.')
            before=dict(self.changes)
            try:
                self.changes={}
                for change in project['changes']:
                    pid=change['pid'];view=self.views[pid.partition(':')[0]];view.set(*self.edit_target(pid,change['offset']),change['value'])
                for view in self.views.values():
                    for row in view.records:view.validate_record(row)
            except Exception:self.changes=before;raise
    return ExpandedView,GrowthSide,attach


def validate_views(owner):
    for view in owner.views.values():
        for row in view.records:view.validate_record(row)
