"""Facility gameplay sections and separate reward sources; native slots stay fixed."""
import hashlib
import struct

# key: English section, native group, row stride, field count, container kind
SECTIONS={
 'cooking':('Cooking','料理',64,8,1),
 'training':('Training','訓練場',168,24,1),
 'theater':('Theater rewards','劇場報酬',64,5,1),
 'baths':('Baths','テルマエ',112,11,1),
 'temples':('Temples','神殿',320,27,1),
 'exspots':('EX spots','EXスポット',80,4,1),
 'spectating':('Spectating','観戦',96,10,1),
 'inns':('Inns','宿屋',40,1,1),
 'actions':('Individual actions','個別行動',80,13,1),
 'answers':('Perch answers','止まり木回答',40,1,1),
 'questions':('Perch questions','止まり木質問',224,12,1),
 'divination':('Divination','六十四卦',48,2,1),
 'lessons':('Lessons','稽古',144,12,1),
 'challenges':('Challenges','挑戦状',64,3,1),
 'hours':('Opening hours','施設営業時間',64,6,2),
 'statuses':('Facility statuses','施設状況',40,1,2),
 'multipliers':('Reward multipliers','施設報酬倍率',152,15,1),
 'banter':('Facility banter','施設掛け合い',112,9,1),
 'demos':('Facility event triggers','施設起因デモ',72,8,1),
 'guidance':('Facility guidance','施設誘導会話',40,1,1),
 'achievements':('Achievements','実績一覧',104,8,1),
 'causality':('Causality rewards','因果報酬',64,8,1),
 'notices':('Notifications & rewards','通知',192,13,1),
 'renown':('Renown','名声',120,8,1),
}
FACILITY_KEYS=tuple(SECTIONS)[:20]
REWARD_KEYS=tuple(SECTIONS)[20:]


def create_models(Binary,EditableTable,Field,Record,DataError,supported_types):
    class FacilityView(EditableTable):
        prefix='FACILITY_';locked_offsets=frozenset()
        def __init__(self,owner,key,group):
            self.owner=owner;self.key=key;self.title,self.group_name,_,_,self.container=SECTIONS[key]
            self.filename=owner.filename;self.raw=owner.raw;self.size=owner.size;self.pool=owner.pool
            self.labels=owner.labels;self.label_at=owner.label_at;self.stride,count,schema=group[1:]
            self.fields=[]
            for i in range(count):
                n,k,_,size,offset=struct.unpack_from('<QQQII',self.raw,schema+i*32)
                field=Field(self.string(n),self.string(k),size,offset)
                if offset<32 or offset+size>self.stride or field.kind not in supported_types:
                    raise DataError('Unsupported facility/reward field layout.')
                self.fields.append(field)
            self.by_offset={f.offset:f for f in self.fields}
            if len(self.by_offset)!=len(self.fields):raise DataError('Duplicate facility field offsets.')
            self.records=[];self.names={};self.locations={};self.collection_names=[];self.collection_offsets=[]
            start=schema+count*32
            def append(at,native_index,collection=None):
                if at<32 or at+self.stride>32+self.size or struct.unpack_from('<HH',self.raw,at+16)!=(native_index,1):
                    raise DataError('Facility/reward record header differs from the supported layout.')
                key_id=f'{key}:{native_index}' if collection is None else f'{key}:{collection}:{native_index}'
                record=Record(key_id,at,len(self.records));self.records.append(record)
                self.names[key_id]=self.string(struct.unpack_from('<Q',self.raw,at+8)[0]);self.locations[key_id]=(collection,native_index)
            for index in range(65536):
                at=start+index*(48 if self.container==2 else self.stride)
                if at+32>32+self.size or struct.unpack_from('<H',self.raw,at+16)[0]!=index:break
                if self.container==1:
                    if struct.unpack_from('<H',self.raw,at+18)[0]!=1:break
                    append(at,index)
                else:
                    if at+48>32+self.size:raise DataError('Facility collection header is outside the data.')
                    amount=struct.unpack_from('<H',self.raw,at+18)[0];pointer=struct.unpack_from('<Q',self.raw,at+32)[0]
                    if amount and (not pointer or pointer+amount*self.stride>self.size):raise DataError('Facility collection entries are outside the data.')
                    self.collection_names.append(self.string(struct.unpack_from('<Q',self.raw,at+8)[0]));self.collection_offsets.append(at)
                    for leaf in range(amount):append(pointer+32+leaf*self.stride,leaf,index)
            if not self.records:raise DataError('Facility/reward section has no supported records.')
            self.by_pid={r.pid:r for r in self.records}
            for record in self.records:
                for field in self.fields:self.original(record,field)
        @property
        def changes(self):return self.owner.changes
        @changes.setter
        def changes(self,value):self.owner.changes=value
        def build(self):return self.owner.build()
        def group_label(self,record):
            group,_=self.locations[record.pid]
            return self.collection_names[group] if group is not None else ''
        def validate_record(self,record):
            if self.key=='baths' and len(self.value(record,self.by_offset[0x48]))!=len(self.value(record,self.by_offset[0x58])):
                raise DataError('Bath skill and weight lists must have the same number of entries.')

    class Facility(EditableTable):
        filename='Facility.bin';prefix='FACILITY_';project_format='fw-facility-edits-v1';locked_offsets=frozenset();section_keys=FACILITY_KEYS
        def __init__(self,raw):
            Binary.__init__(self,raw);self.fingerprint=hashlib.sha256(raw).hexdigest();self.changes={}
            self.label_at={at:name for name,at in self.labels.items()};self.views={};groups={g[0]:g for g in self.groups()}
            kinds={}
            pos=32
            while True:
                pos=raw.find(b'\x01\x12\x25\x20',pos,32+self.size)
                if pos<0:break
                if pos+32<=32+self.size:
                    kind=struct.unpack_from('<I',raw,pos+4)[0];schema=struct.unpack_from('<Q',raw,pos+24)[0]+32
                    kinds[schema]=kind
                pos+=4
            for key in self.section_keys:
                title,name,stride,count,container=SECTIONS[key];group=groups.get(name)
                if group is None or group[1:3]!=(stride,count) or kinds.get(group[3])!=container:
                    raise DataError('Unsupported '+self.filename+' layout: '+title)
                self.views[key]=FacilityView(self,key,group)
            self.records=[r for v in self.views.values() for r in v.records];self.by_pid={r.pid:r for r in self.records};self.fields=[];self.by_offset={}
        def edit_target(self,pid,offset):
            view=self.views[pid.partition(':')[0]];return view.by_pid[pid],view.by_offset[offset]
        def validate(self):
            for view in self.views.values():
                for record in view.records:view.validate_record(record)
        def build(self):self.validate();return super().build()
        def project(self):
            return {'format':self.project_format,'source_file':self.filename,'source_sha256':self.fingerprint,
                'changes':[{'section':pid.partition(':')[0],'row':self.by_pid[pid].index,'offset':offset,'value':value}
                           for (pid,offset),value in sorted(self.changes.items())]}
        def load_project(self,project):
            if project.get('format')!=self.project_format or project.get('source_file')!=self.filename or project.get('source_sha256')!=self.fingerprint:
                raise DataError('Facility/reward project belongs to a different source file.')
            before=dict(self.changes)
            try:
                self.changes={}
                for change in project['changes']:
                    view=self.views[change['section']];index=change['row']
                    if type(index) is not int or not 0<=index<len(view.records):raise DataError('Invalid facility/reward row index.')
                    view.set(view.records[index],view.by_offset[change['offset']],change['value'])
                self.validate()
            except Exception:self.changes=before;raise
    class Reward(Facility):filename='Reward.bin';section_keys=REWARD_KEYS
    class RewardP0(Reward):filename='Reward_P0.bin';section_keys=('notices',)
    class RewardP1(Reward):filename='Reward_P1.bin';section_keys=('notices',)
    return Facility,Reward,RewardP0,RewardP1,FacilityView
