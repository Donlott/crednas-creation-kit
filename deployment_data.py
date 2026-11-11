"""Fixed battle deployment groups and unit slots from GameData/Dispos/*.bin."""
from pathlib import PurePosixPath
import hashlib
import struct

EXPECTED={0x20:('data',16),0x30:('u8',1),0x32:('b16',2),
 **{n:('s8',1) for n in (0x34,0x35,0x36,0x37,0x130)},
 **{n:('u8',1) for n in (0x38,0x39,0x3a,0x3b,0x60,0x120,0x121,0x122,0x123,0x124,0x125)},
 **{n:('data',16) for n in (0x40,0x50,0x68,0x80,0x98,0xb0,0xc8)},
 **{n:('b32',4) for n in (0x78,0x90,0xa8,0xc0,0xd8,0x140)},
 **{n:('string',8) for n in (0xe0,0xe8,0xf0,0xf8,0x100,0x108,0x110,0x118,0x128,0x138)}}


def valid_source(name):
    parts=PurePosixPath(name).parts
    return len(parts)==2 and parts[0]=='Dispos' and parts[1].endswith('.bin') and '\\' not in name and parts[1] not in ('.bin','..')


def create_models(Binary,EditableTable,CollectionTable,Field,Record,DataError):
    class DeploymentView(CollectionTable):
        prefix='DEPLOY_';key='units';title='Deployment groups';locked_offsets=frozenset()
        def __init__(self,owner,group):
            self.owner=owner;self.filename=owner.filename;self.raw=owner.raw;self.size=owner.size;self.pool=owner.pool
            self.labels=owner.labels;self.label_at=owner.label_at
            self.group_name,self.stride,count,schema=group;self.fields=[]
            for i in range(count):
                n,k,_,size,offset=struct.unpack_from('<QQQII',self.raw,schema+i*32)
                self.fields.append(Field(self.string(n),self.string(k),size,offset))
            self.by_offset={f.offset:f for f in self.fields}
            if len(self.by_offset)!=count or {f.offset:(f.kind,f.size) for f in self.fields}!=EXPECTED:
                raise DataError('Unsupported deployment unit layout: '+self.filename)
            self.collections=[];self.records=[];self.names={};self.rows_by_table={};self.row_location={};self.collection_offsets=[]
            start=schema+count*32
            for index in range(65536):
                at=start+index*48
                if at+48>32+self.size or struct.unpack_from('<H',self.raw,at+16)[0]!=index:break
                native=self.string(struct.unpack_from('<Q',self.raw,at+8)[0])
                if not native or self.labels.get(native)!=at:raise DataError('Deployment group identity differs: '+self.filename)
                amount=struct.unpack_from('<H',self.raw,at+18)[0];pointer=struct.unpack_from('<Q',self.raw,at+32)[0]
                if amount and (not pointer or pointer+amount*self.stride>self.size):raise DataError('Deployment units are outside the data.')
                table=f'units:{index}';self.collections.append(Record(table,at,index));self.collection_offsets.append(at)
                self.names[table]=native;self.rows_by_table[table]=[]
                for ordinal in range(amount):
                    leaf=32+pointer+ordinal*self.stride
                    if struct.unpack_from('<HH',self.raw,leaf+16)!=(ordinal,1):raise DataError('Deployment unit slot header differs.')
                    row=Record(f'{table}:{ordinal}',leaf,ordinal)
                    self.records.append(row);self.rows_by_table[table].append(row);self.row_location[row.pid]=(table,ordinal)
                    self.names[row.pid]=self.string(struct.unpack_from('<Q',self.raw,leaf+8)[0])
            if not self.collections or set(self.labels)-{self.names[r.pid] for r in self.collections}!={self.group_name}:raise DataError('Unsupported deployment group index: '+self.filename)
            self.by_pid={r.pid:r for r in self.records};self.tables_by_id={r.pid:r for r in self.collections}
            for row in self.records:
                for field in self.fields:self.original(row,field)
        @property
        def changes(self):return self.owner.changes
        @changes.setter
        def changes(self,value):self.owner.changes=value
        def validate_record(self,row):pass
        def build(self):return self.owner.build()

    class Deployment(EditableTable):
        prefix='DEPLOY_';project_format='fw-deployment-edits-v1';locked_offsets=frozenset()
        def __init__(self,raw,filename):
            if not valid_source(filename):raise DataError('Unsupported deployment source filename.')
            self.filename=filename;Binary.__init__(self,raw);groups=list(self.groups())
            if len(groups)!=1 or groups[0][:3]!=('配置',328,42):raise DataError('Unsupported deployment source layout: '+filename)
            schema=groups[0][3]
            headers=[p for p in range(32,32+self.size-31,4) if raw[p:p+4]==b'\x01\x12\x25\x20' and struct.unpack_from('<Q',raw,p+24)[0]+32==schema]
            if len(headers)!=1 or struct.unpack_from('<I',raw,headers[0]+4)[0]!=2:raise DataError('Deployment is not a grouped table.')
            self.fingerprint=hashlib.sha256(raw).hexdigest();self.changes={};self.label_at={at:name for name,at in self.labels.items()}
            self.views={'units':DeploymentView(self,groups[0])};self.fields=[];self.by_offset={}
            self.records=self.views['units'].records;self.by_pid=self.views['units'].by_pid
        def edit_target(self,pid,offset):return self.by_pid[pid],self.views['units'].by_offset[offset]
        def reparse(self,raw):return type(self)(raw,self.filename)
        def project(self):
            return {**super().project(),'source_file':self.filename}
        def load_project(self,project):
            if project.get('format')!=self.project_format or project.get('source_file')!=self.filename or project.get('source_sha256')!=self.fingerprint:
                raise DataError('Deployment project belongs to a different source file.')
            before=dict(self.changes)
            try:
                self.changes={}
                for change in project['changes']:
                    row,field=self.edit_target(change['pid'],change['offset']);self.views['units'].set(row,field,change['value'])
            except Exception:self.changes=before;raise
    return Deployment,DeploymentView


def battle_links(base,binary_type):
    """Read-only exact links from BattleField.bin; never synthesize chapter ownership."""
    from pathlib import Path
    path=Path(base)/'BattleField.bin'
    if not path.is_file():return []
    b=binary_type(path.read_bytes());group=next((g for g in b.groups() if g[0]=='戦場'),None)
    if not group or group[1:3]!=(480,69):raise ValueError('Unsupported BattleField.bin layout.')
    _,stride,count,schema=group;start=schema+count*32;found=[]
    for index in range(65536):
        at=start+index*stride
        if at+stride>32+b.size or struct.unpack_from('<HH',b.raw,at+16)!=(index,1):break
        native=b.string(struct.unpack_from('<Q',b.raw,at+8)[0])
        if b.labels.get(native)!=at:raise ValueError('Battlefield index mismatch.')
        values={key:b.string(struct.unpack_from('<Q',b.raw,at+offset)[0]) for key,offset in
                [('deployment',0x38),('revealed',0x40),('title',0x50),('script',0x48),('terrain',0x20)]}
        found.append(dict(id=native,**values))
    return found
