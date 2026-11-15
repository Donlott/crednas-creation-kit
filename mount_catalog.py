"""Build purchasable mount/skill pairs from the user's current tables and names."""
from dataclasses import dataclass
import hashlib
import struct
from skill_index import text_value
from mount_skills import DODGE,MOVE,skill_roll

HORSE_DODGE='IID_CCK_BuyMount_Horse'
HORSE_MOVE='IID_CCK_BuyMount_Horse_Move'
PREFIX='IID_CCK_BuyMount_'


@dataclass(frozen=True)
class MountOffer:
    iid:str
    rid:str
    ride_index:int
    seed:int
    unique:bool
    mount_name:str
    skill:str
    upgrade:str
    skill_name:str
    upgrade_name:str
    default_price:int

    @property
    def name_key(self):return 'MIID_'+self.iid.removeprefix('IID_')
    @property
    def help_key(self):return 'MIID_H_'+self.iid.removeprefix('IID_')
    @property
    def label(self):
        if self.iid==HORSE_DODGE:return 'Horse (Dodge)'
        if self.iid==HORSE_MOVE:return 'Horse (Move)'
        return self.mount_name+' ('+self.skill_name+')'


def variant_seeds(first,second):
    """All skill pairs reachable by a saved byte, preserving current list order."""
    if not first and not second:return []
    pairs={}
    for seed in range(256):
        roll=skill_roll(seed);a=first[roll%len(first)] if first else '';b=second[roll%len(second)] if second else ''
        pairs.setdefault((a,b),seed)
    order_a={s:i for i,s in reversed(list(enumerate(first)))};order_b={s:i for i,s in reversed(list(enumerate(second)))}
    return [(a,b,pairs[a,b]) for a,b in sorted(pairs,key=lambda p:(order_a.get(p[0],0),order_b.get(p[1],0)))]


def default_price(value,skill):
    base=1000*max(1,value)
    if skill.startswith(('SID_再移動','SID_飛行再移動')):base*=4
    elif skill.startswith(('SID_共なる疾走','SID_共なる大移動')):base*=3
    return min(65535,base)


def catalog(job,skills,names):
    from fw_editor import DataError
    group=next((g for g in job.groups() if g[0]=='乗り物'),None)
    if group is None or group[1:3]!=(336,131):raise DataError('Unsupported mount table layout.')
    fields={}
    for i in range(group[2]):
        name,kind,_,width,offset=struct.unpack_from('<QQQII',job.raw,group[3]+i*32)
        fields[offset]=(job.string(name),job.string(kind),width)
    for offset,field in {0x28:('名前','string',8),0x6c:('固有','u8',1),0x6e:('価値','u8',1),
                         0x70:('騎乗スキル1段階','data[]',16),0x80:('騎乗スキル2段階','data[]',16)}.items():
        if fields.get(offset)!=field:raise DataError('Unsupported mount catalog fields.')
    def skill_name(sid):
        if not sid:return 'No skill'
        row=skills.by_pid.get(sid)
        if row is None:raise DataError('Mount refers to a missing skill: '+sid)
        name=skills.value(row,skills.by_offset[0x20]);suffix=skills.value(row,skills.by_offset[0x28])
        if name not in names:raise DataError('The English Skill message bank is missing a mount skill name: '+name)
        return names[name]+(names.get(suffix,'+' if sid.endswith('＋') else '') if suffix else '')
    result=[];seen=set();start=group[3]+group[2]*32
    for index in range(256):
        at=start+index*group[1]
        if at+group[1]>32+job.size:break
        number,amount=struct.unpack_from('<HH',job.raw,at+16)
        if (number,amount)!=(index,1):break
        rid=job.string(struct.unpack_from('<Q',job.raw,at+8)[0])
        if not rid.startswith('RID_') or job.labels.get(rid)!=at:raise DataError('Unsupported mount record index.')
        first=text_value(job,at+0x70,'data[]');second=text_value(job,at+0x80,'data[]')
        pairs=variant_seeds(first,second)
        if not pairs:continue # Engine default/no-mount placeholders have no traits.
        if not index or not 1<=job.raw[at+0x20]<=5:raise DataError('Unsupported purchasable mount type: '+rid)
        key=text_value(job,at+0x28,'string')
        if key not in names:raise DataError('The English Ride message bank is missing a mount name: '+key)
        mount_name=names[key]
        for a,b,seed in pairs:
            if rid=='RID_馬' and (a,b)==DODGE:iid=HORSE_DODGE
            elif rid=='RID_馬' and (a,b)==MOVE:iid=HORSE_MOVE
            else:iid=PREFIX+hashlib.sha256((rid+'\0'+a+'\0'+b).encode('utf8')).hexdigest()[:16]
            if iid in seen:raise DataError('Duplicate mount offer ID.')
            seen.add(iid);result.append(MountOffer(iid,rid,index,seed,bool(job.raw[at+0x6c]),mount_name,a,b,skill_name(a),skill_name(b),default_price(job.raw[at+0x6e],a)))
    if not result:raise DataError('No purchasable mount skill variants were found.')
    if len(result)>256:raise DataError('The executable patch supports at most 256 mount/skill offers.')
    return result
