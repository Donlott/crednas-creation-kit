"""Select a persisted seed using the native mount-skill selection arithmetic."""
import struct
from skill_index import text_value

DODGE=('SID_共なる喚起','SID_共なる喚起＋')
MOVE=('SID_共なる疾走','SID_共なる疾走＋')


def skill_roll(seed):
    """Return the native selector's unsigned roll (verified for all 256 seeds).

    The selector rebuilds a local PRNG state from a byte saved on the mount. It
    does not consume a fresh random roll whenever its riding skill is displayed.
    """
    if type(seed) is not int or not 0<=seed<=255:raise ValueError('Mount seed must fit in one byte.')
    mask=0xffffffff;mult=0x6c078965
    first=seed*mult&mask
    state=((first^(first>>30))*mult+1)&mask
    state=((state^(state>>30))*mult+2)&mask
    last=((state^(state>>30))*mult+3)&mask
    mixed=(seed*0x3c4b2800&mask)^first
    return (mixed^(mixed>>8)^last^(last>>19))&0x7fffffff


def choose_seeds(first_stage,second_stage):
    from fw_editor import DataError
    if not first_stage or not second_stage:raise DataError('Horse riding-skill lists are empty; guaranteed-skill purchases cannot be generated.')
    result={}
    for name,skills in (('dodge',DODGE),('move',MOVE)):
        for seed in range(256):
            roll=skill_roll(seed)
            if first_stage[roll%len(first_stage)]==skills[0] and second_stage[roll%len(second_stage)]==skills[1]:
                result[name]=seed;break
        else:raise DataError('The edited horse skill lists cannot guarantee '+name+' and its matching upgraded skill with a saved mount seed.')
    return result


def horse_seeds(job,ride):
    from fw_editor import DataError
    group=next((g for g in job.groups() if g[0]=='乗り物'),None)
    if group is None or group[1:3]!=(336,131):raise DataError('Unsupported mount skill-table layout.')
    schema=group[3];found={}
    for i in range(group[2]):
        name,kind,_,size,offset=struct.unpack_from('<QQQII',job.raw,schema+i*32)
        if offset in (0x70,0x80):found[offset]=(job.string(name),job.string(kind),size)
    if found!={0x70:('騎乗スキル1段階','data[]',16),0x80:('騎乗スキル2段階','data[]',16)}:raise DataError('Unsupported mount riding-skill fields.')
    return choose_seeds(text_value(job,ride+0x70,'data[]'),text_value(job,ride+0x80,'data[]'))
