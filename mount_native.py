"""CCK-authored AArch64 vendor hooks for the verified v1.00 executable.

No executable segments are distributed here. The helper is our own code. See
docs/Buyable-mounts.md for ABI, offset and failure-handling details.
"""
import hashlib
import struct

BUILD_ID = 'db93b0125f4850601d61c3edde012f8eb2ecfe77000000000000000000000000'
MAIN_SHA256 = '616e7d906936ea4c2d908d0553cf69779e60242d769c40722267ee8bcb98e79a'
CAVE = 0x1a45300
DELIVERY = 0x1a45380
TABLE = 0x1a45500
MAX_OFFERS = 256
DESTINATION_HOOK = 0x189ea38
DELIVERY_HOOK = 0x189ec80
# Eden's patch collector compares build-ID filenames case-sensitively against
# Common::HexToString's uppercase representation, even on Linux.
IPS_PATH = 'exefs/'+BUILD_ID.upper()+'.ips'

# CCK-authored helper and lookup table. Only the two offer-count immediates
# change in the code; each eight-byte table row is (item u16, RID u8, seed u8,
# unique u32). All table values are derived from the user's exported data.
_HELPER = bytes.fromhex(
    'ffc300d1e82700a9ea2f01a90b423bd5eb1300f9b63640f9880240f9280200b4080140f9e80100b4081940f9a80100b4'
    '082140790900009029011491eadd97522b0140791f010b6ba0000054292100914a05007161ffff5402000014f6031faa'
    'eb1340f90b421bd5ea2f41a9e82740a9ffc30091b265f9170000000000000000290040790a0000904a011491ebdd9752'
    '4c0140793f010c6ba00000544a2100916b05007161ffff548674b9174c0540794d0540b9ff0302d1fd7b06a9f44f07a9'
    'fd030091f30308aa693f00f029fd41f9a90500b4340540f9740500b4893e40f9290500b40a198052ee031f2a8f1d0012'
    '2b0140397f010071ce158e1a6d0000347f010f6b00040054290101914a05007101ffff548e030034ff7f00a9ff7f01a9'
    'ff7f02a9ff7f03a9e9630091e90b00f9ec030079cd000034e00314aae10300910814bc974000f8370f000014e00314aa'
    'e1030091e2031faae3031f2ae8030191100cbc97e90341393f090071c1000054e94740b9690600b94900805269020039'
    '0400001409008012690600b97f020039f44f47a9fd7b46a9ff030291c0035fd600000000000000000000000000000000'
    '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000'
)
COUNT_SLOTS = {'dest_count': 60, 'delivery_count': 140}
DESTINATION_ASSEMBLY = r"""
sub sp, sp, #0x30
stp x8, x9, [sp]
stp x10, x11, [sp, #0x10]
mrs x11, nzcv
str x11, [sp, #0x20]
ldr x22, [x21, #0x68]
ldr x8, [x20]
cbz x8, dest_done
ldr x8, [x8]
cbz x8, dest_done
ldr x8, [x8, #0x30]
cbz x8, dest_done
ldrh w8, [x8, #0x10]
adrp x9, #27545600
add x9, x9, #1280
mov w10, #0xbeef
dest_loop:
ldrh w11, [x9]
cmp w8, w11
b.eq dest_mount
add x9, x9, #8
subs w10, w10, #1
b.ne dest_loop
b dest_done
dest_mount:
mov x22, xzr
dest_done:
ldr x11, [sp, #0x20]
msr nzcv, x11
ldp x10, x11, [sp, #0x10]
ldp x8, x9, [sp]
add sp, sp, #0x30
b #0x189ea3c
"""
DELIVERY_ASSEMBLY = r"""
ldrh w9, [x1]
adrp x10, #27545600
add x10, x10, #1280
mov w11, #0xbeef
delivery_loop:
ldrh w12, [x10]
cmp w9, w12
b.eq mount
add x10, x10, #8
subs w11, w11, #1
b.ne delivery_loop
b #0x8a25c0
mount:
ldrh w12, [x10, #2]
ldr w13, [x10, #4]
sub sp, sp, #0x80
stp x29, x30, [sp, #0x60]
stp x20, x19, [sp, #0x70]
mov x29, sp
mov x19, x8
adrp x9, #0x2234000
ldr x9, [x9, #0x3f8]
cbz x9, failed
ldr x20, [x9, #8]
cbz x20, failed
ldr x9, [x20, #0x78]
cbz x9, failed
mov w10, #200
mov w14, wzr
and w15, w12, #0xff
scan:
ldrb w11, [x9]
cmp w11, #0
cinc w14, w14, eq
cbz w13, next
cmp w11, w15
b.eq failed
next:
add x9, x9, #0x40
subs w10, w10, #1
b.ne scan
cbz w14, failed
stp xzr, xzr, [sp]
stp xzr, xzr, [sp, #0x10]
stp xzr, xzr, [sp, #0x20]
stp xzr, xzr, [sp, #0x30]
add x9, sp, #0x18
str x9, [sp, #0x10]
strh w12, [sp]
cbz w13, grant
mov x0, x20
mov x1, sp
bl #0x94a460
tbnz w0, #31, grant
b failed
grant:
mov x0, x20
mov x1, sp
mov x2, xzr
mov w3, wzr
add x8, sp, #0x40
bl #0x9484a0
ldrb w9, [sp, #0x40]
cmp w9, #2
b.ne failed
ldr w9, [sp, #0x44]
str w9, [x19, #4]
mov w9, #2
strb w9, [x19]
b done
failed:
mov w9, #-1
str w9, [x19, #4]
strb wzr, [x19]
done:
ldp x20, x19, [sp, #0x70]
ldp x29, x30, [sp, #0x60]
add sp, sp, #0x80
ret
"""


def validate_main(raw):
    from fw_editor import DataError
    if len(raw)<256 or raw[:4]!=b'NSO0' or raw[0x40:0x60].hex()!=BUILD_ID or hashlib.sha256(raw).hexdigest()!=MAIN_SHA256:
        raise DataError('Buyable mounts supports only the verified, unmodified Fortune’s Weave v1.00 main executable. Select the original exefs/main.')


def branch(at,target,link=False):
    offset=target-at
    if offset%4 or not -(1<<27)<=offset<(1<<27):raise ValueError('AArch64 branch exceeds its range.')
    return struct.pack('<I',(0x94000000 if link else 0x14000000)|((offset//4)&0x3ffffff))


def catalog_records(offers):
    offers=list(offers)
    if not 1<=len(offers)<=MAX_OFFERS:raise ValueError('The native patch needs 1 to 256 mount offers.')
    seen=set();table=bytearray()
    for entry in offers:
        if not isinstance(entry,(tuple,list)) or len(entry)!=4:raise ValueError('Invalid mount offer row.')
        index,ride,seed,unique=entry
        if type(index) is not int or not 1<=index<=65535 or index in seen:raise ValueError('Purchase indexes must be distinct 16-bit integers.')
        if type(ride) is not int or not 1<=ride<=255:raise ValueError('Invalid mount index.')
        if type(seed) is not int or not 0<=seed<=255:raise ValueError('Invalid saved mount seed.')
        if type(unique) not in (bool,int) or unique not in (0,1):raise ValueError('Invalid unique-mount flag.')
        seen.add(index);table.extend(struct.pack('<HBBI',index,ride,seed,int(unique)))
    helper=bytearray(_HELPER)
    for slot,register in (('dest_count',10),('delivery_count',11)):
        struct.pack_into('<I',helper,COUNT_SLOTS[slot],0x52800000|(len(offers)<<5)|register)
    if len(helper)!=TABLE-CAVE or TABLE+len(table)>0x1a46000:raise ValueError('Mount lookup table exceeds the verified code-cave page.')
    return [(DESTINATION_HOOK,branch(DESTINATION_HOOK,CAVE)),
            (DELIVERY_HOOK,branch(DELIVERY_HOOK,DELIVERY,True)),(CAVE,bytes(helper+table))]


def encode_ips(records):
    result=bytearray(b'IPS32')
    for address,raw in records:
        result.extend(struct.pack('>IH',address+0x100,len(raw)));result.extend(raw)
    return bytes(result+b'EEOF')


def catalog_ips32(offers):return encode_ips(catalog_records(offers))


def patch_records(item_index,ride_index,move_index=None,dodge_seed=1,move_seed=0):
    # Compatibility for the original two-offer helper API and its regressions.
    if type(item_index) is not int:raise ValueError('Invalid purchase item index.')
    if move_index is None:move_index=item_index+1
    return catalog_records([(item_index,ride_index,dodge_seed,False),(move_index,ride_index,move_seed,False)])


def ips32(item_index,ride_index,move_index=None,dodge_seed=1,move_seed=0):
    return encode_ips(patch_records(item_index,ride_index,move_index,dodge_seed,move_seed))
