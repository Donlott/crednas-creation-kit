"""CCK-authored shop-to-barracks helper for the verified v1.00 executable.

No executable segments or battalion definitions are distributed. The helper uses
the native 300-slot Legion pool and refuses full-pool replacement.
"""
import struct
from mount_native import branch,DESTINATION_HOOK,DELIVERY_HOOK,CAVE as MOUNT_CAVE,DELIVERY as MOUNT_DELIVERY

CAVE=0x1a45d00
DELIVERY=CAVE+0x80
TABLE=CAVE+0x170
MAX_OFFERS=100
_HELPER=bytes.fromhex("ffc300d1e82700a9ea2f01a90b423bd5eb1300f9b63640f9880240f9280200b4080140f9e80100b4081940f9a80100b4082140790900009029c13991eadd97522b0140791f010b6ba0000054291100914a05007161ffff5402000014f6031faaeb1340f90b421bd5ea2f41a9e82740a9ffc30091560000b43163f9173063f917290040790a0000904ac13991ebdd97524c0140793f010c6ba00000544a1100916b05007161ffff540672b9174c054079ff0301d1fd7b02a9f44f03a9fd030091f30308aaec0300f9693f00f029d541f9c90300b4340540f9940300b4891a40f9490300b48a2580522b014039ab000034292100914a05007181ffff5413000014e00314aae1030091e2031faae8430091d4f3bb97e91740b93fad0471680100548a1a40f94a4d298b4a014039eb0340395f010b6ba1000054690600b949008052690200390400001409008012690600b97f020039f44f43a9fd7b42a9ff030191c0035fd6000000000000000000000000")
DESTINATION_ASSEMBLY="\nsub sp, sp, #0x30\nstp x8, x9, [sp]\nstp x10, x11, [sp, #0x10]\nmrs x11, nzcv\nstr x11, [sp, #0x20]\nldr x22, [x21, #0x68]\nldr x8, [x20]\ncbz x8, done\nldr x8, [x8]\ncbz x8, done\nldr x8, [x8, #0x30]\ncbz x8, done\nldrh w8, [x8, #0x10]\nadrp x9, #27545600\nadd x9, x9, #3696\nmov w10, #0xbeef\nlookup:\nldrh w11, [x9]\ncmp w8, w11\nb.eq match\nadd x9, x9, #4\nsubs w10, w10, #1\nb.ne lookup\nb done\nmatch:\nmov x22, xzr\ndone:\nldr x11, [sp, #0x20]\nmsr nzcv, x11\nldp x10, x11, [sp, #0x10]\nldp x8, x9, [sp]\nadd sp, sp, #0x30\ncbz x22, matched_done\nb #0x189ea3c\nmatched_done:\nb #0x189ea3c\n"
DELIVERY_ASSEMBLY="\nldrh w9, [x1]\nadrp x10, #27545600\nadd x10, x10, #3696\nmov w11, #0xbeef\nlookup:\nldrh w12, [x10]\ncmp w9, w12\nb.eq grant\nadd x10, x10, #4\nsubs w11, w11, #1\nb.ne lookup\nb #0x8a25c0\ngrant:\nldrh w12, [x10, #2]\nsub sp, sp, #0x40\nstp x29, x30, [sp, #0x20]\nstp x20, x19, [sp, #0x30]\nmov x29, sp\nmov x19, x8\nstr x12, [sp]\nadrp x9, #0x2234000\nldr x9, [x9, #0x3a8]\ncbz x9, failed\nldr x20, [x9, #8]\ncbz x20, failed\nldr x9, [x20, #0x30]\ncbz x9, failed\nmov w10, #300\nscan:\nldrb w11, [x9]\ncbz w11, space\nadd x9, x9, #8\nsubs w10, w10, #1\nb.ne scan\nb failed\nspace:\nmov x0, x20\nmov x1, sp\nmov x2, xzr\nadd x8, sp, #0x10\nbl #0x942d60\nldr w9, [sp, #0x14]\ncmp w9, #299\nb.hi failed\nldr x10, [x20, #0x30]\nadd x10, x10, w9, uxtw #3\nldrb w10, [x10]\nldrb w11, [sp]\ncmp w10, w11\nb.ne failed\nstr w9, [x19, #4]\nmov w9, #2\nstrb w9, [x19]\nb done\nfailed:\nmov w9, #-1\nstr w9, [x19, #4]\nstrb wzr, [x19]\ndone:\nldp x20, x19, [sp, #0x30]\nldp x29, x30, [sp, #0x20]\nadd sp, sp, #0x40\nret\n"
COUNT_SLOTS=(60,140)
TAIL_SLOTS=(120,168)


def patch_records(offers,*,mounts=False):
    offers=list(offers)
    if type(mounts) is not bool or not 1<=len(offers)<=MAX_OFFERS:raise ValueError('The battalion patch supports 1 to 100 offers.')
    table=bytearray();seen=set()
    for entry in offers:
        if not isinstance(entry,(tuple,list)) or len(entry)!=2:raise ValueError('Invalid battalion offer.')
        item,legion=entry
        if type(item) is not int or not 1<=item<=65535 or item in seen:raise ValueError('Battalion purchase item indexes must be distinct 16-bit values.')
        if type(legion) is not int or not 1<=legion<=255:raise ValueError('Battalion indexes must fit the saved Legion byte.')
        seen.add(item);table.extend(struct.pack('<HH',item,legion))
    helper=bytearray(_HELPER)
    for slot,register in zip(COUNT_SLOTS,(10,11)):
        struct.pack_into('<I',helper,slot,0x52800000|(len(offers)<<5)|register)
    helper[TAIL_SLOTS[0]:TAIL_SLOTS[0]+4]=branch(CAVE+TAIL_SLOTS[0],MOUNT_CAVE if mounts else 0x189ea3c)
    helper[TAIL_SLOTS[1]:TAIL_SLOTS[1]+4]=branch(CAVE+TAIL_SLOTS[1],MOUNT_DELIVERY if mounts else 0x8a25c0)
    if len(helper)!=TABLE-CAVE or TABLE+len(table)>0x1a46000:raise ValueError('Battalion helper exceeds the verified padding.')
    return [(DESTINATION_HOOK,branch(DESTINATION_HOOK,CAVE)),
            (DELIVERY_HOOK,branch(DELIVERY_HOOK,DELIVERY,True)),(CAVE,bytes(helper+table))]
