"""Optional CPU emulation of CCK's own ARM64 helper, with mocked native APIs.

Install Unicorn in a developer environment to execute these tests. They do not
load game instructions or emulate gameplay; their scope is ABI/guard behavior.
"""
import struct
import os
from pathlib import Path
import unittest
import mount_native as native
try:
    import unicorn as uc
    from unicorn.arm64_const import *
except ImportError:uc=None


@unittest.skipIf(uc is None,'Optional Unicorn ARM64 emulator not installed')
class MachineCodeTests(unittest.TestCase):
    def machine(self,offers=None):
        m=uc.Uc(uc.UC_ARCH_ARM64,uc.UC_MODE_ARM)
        m.mem_map(0x800000,0x1b00000);m.mem_map(0x3000000,0x10000)
        for address,raw in (native.patch_records(1356,6) if offers is None else native.catalog_records(offers)):m.mem_write(address,raw)
        for i,register in enumerate((UC_ARM64_REG_X19,UC_ARM64_REG_X20,UC_ARM64_REG_X29)):
            m.reg_write(register,0x3100+i)
        m.reg_write(UC_ARM64_REG_SP,0x300f000);m.reg_write(UC_ARM64_REG_LR,0x3000100)
        return m

    def delivery(self,*,index=1356,free=0,status=2,holder=True,pool=True,array=True,offers=None,occupied=None,unique_lookup=-1):
        m=self.machine(offers);expected={i:(rid,seed,unique) for i,rid,seed,unique in (offers or [(1356,6,1,False),(1357,6,0,False)])};base=0x3001000;stable=0x3002000;records=0x3003000;result=0x300c000;stack=0x300c100
        m.mem_write(stack,struct.pack('<HHI',index,0,1));m.reg_write(UC_ARM64_REG_X1,stack);m.reg_write(UC_ARM64_REG_X8,result)
        m.mem_write(0x22343f8,struct.pack('<Q',base if holder else 0));m.mem_write(base+8,struct.pack('<Q',stable if pool else 0))
        m.mem_write(stable+0x78,struct.pack('<Q',records if array else 0))
        m.mem_write(records,b'\1'+b'\0'*63)
        for i in range(200):m.mem_write(records+i*64,b'\0' if i==free else b'\1')
        for slot,rid in (occupied or {}).items():m.mem_write(records+slot*64,bytes([rid]))
        calls=[]
        def hook(machine,at,size,user):
            if at==0x8a25c0:
                calls.append('ordinary');machine.emu_stop()
            if at==0x94a460:
                calls.append('unique-check');machine.reg_write(UC_ARM64_REG_X0,unique_lookup&0xffffffff);machine.reg_write(UC_ARM64_REG_PC,machine.reg_read(UC_ARM64_REG_LR))
            if at==0x9484a0:
                calls.append('mount');self.assertEqual(machine.reg_read(UC_ARM64_REG_X0),stable)
                self.assertEqual(machine.reg_read(UC_ARM64_REG_X2),0);self.assertEqual(machine.reg_read(UC_ARM64_REG_X3),0)
                temp=machine.reg_read(UC_ARM64_REG_X1);value=machine.mem_read(temp,64)
                self.assertEqual(value[0],expected[index][0]);self.assertEqual(value[1],expected[index][1]);self.assertEqual(value[2:16],b'\0'*14)
                self.assertEqual(struct.unpack_from('<Q',value,16)[0],temp+24);self.assertEqual(value[24:],b'\0'*40)
                output=machine.reg_read(UC_ARM64_REG_X8);machine.mem_write(output,struct.pack('<B3xi',status,free))
                machine.reg_write(UC_ARM64_REG_PC,machine.reg_read(UC_ARM64_REG_LR))
        m.hook_add(uc.UC_HOOK_CODE,hook);m.emu_start(native.DELIVERY,0x3000100,count=10000)
        if index in expected:
            self.assertEqual(m.reg_read(UC_ARM64_REG_SP),0x300f000)
            self.assertEqual(m.reg_read(UC_ARM64_REG_X19),0x3100)
            self.assertEqual(m.reg_read(UC_ARM64_REG_X20),0x3101)
            self.assertEqual(m.reg_read(UC_ARM64_REG_X29),0x3102)
            self.assertEqual(m.reg_read(UC_ARM64_REG_LR),0x3000100)
        return calls,struct.unpack_from('<i',m.mem_read(result,8),4)[0]

    def test_every_free_slot_can_be_granted(self):
        for free in range(200):
            with self.subTest(free=free):self.assertEqual(self.delivery(free=free),(['mount'],free))

    def test_full_stable_never_calls_replacing_native_api(self):self.assertEqual(self.delivery(free=-1),([],-1))

    def test_move_offer_keeps_its_seed_through_slot_search(self):
        for slot in (0,99,199):
            with self.subTest(slot=slot):self.assertEqual(self.delivery(index=1357,free=slot),(['mount'],slot))
        self.assertEqual(self.delivery(index=1357,free=-1),([],-1))

    def test_native_failure_reports_no_delivery(self):
        for status in (0,1,3,4):
            with self.subTest(status=status):self.assertEqual(self.delivery(status=status),(['mount'],-1))

    def test_missing_runtime_state_never_charges(self):
        for kwargs in ({'holder':False},{'pool':False},{'array':False}):
            with self.subTest(kwargs=kwargs):self.assertEqual(self.delivery(**kwargs),([],-1))

    def test_unique_mount_duplicate_and_conversion_protection(self):
        offers=[(2000,24,7,True)]
        self.assertEqual(self.delivery(index=2000,offers=offers),(['unique-check','mount'],0))
        self.assertEqual(self.delivery(index=2000,offers=offers,occupied={199:24}),([],-1))
        self.assertEqual(self.delivery(index=2000,offers=offers,unique_lookup=4),(['unique-check'],-1))
        self.assertEqual(self.delivery(index=2000,offers=offers,free=-1),([],-1))

    def test_maximum_catalog_first_middle_last_and_nonadjacent_indexes(self):
        offers=[(3000+2*i,6+i%22,i,bool(i==100)) for i in range(256)]
        for at in (0,128,255):
            with self.subTest(at=at):self.assertEqual(self.delivery(index=offers[at][0],offers=offers),(['mount'],0))
        self.assertEqual(self.delivery(index=3001,offers=offers)[0],['ordinary'])

    def test_other_items_use_original_function(self):
        for index in (0,1,1355,1358,65535):
            with self.subTest(index=index):self.assertEqual(self.delivery(index=index)[0],['ordinary'])

    def test_destination_hook_keeps_all_other_state(self):
        for index in (1356,1357,1):
            for null in (None,0,1,2):
                with self.subTest(index=index,null=null):
                    m=self.machine();menu=0x3001000;collection=0x3002000;first=0x3003000;entry=0x3004000;item=0x3005000
                    m.reg_write(UC_ARM64_REG_X21,menu);m.reg_write(UC_ARM64_REG_X20,collection)
                    m.mem_write(menu+0x68,struct.pack('<Q',1234))
                    m.mem_write(collection,struct.pack('<Q',first if null!=0 else 0))
                    m.mem_write(first,struct.pack('<Q',entry if null!=1 else 0))
                    m.mem_write(entry+0x30,struct.pack('<Q',item if null!=2 else 0));m.mem_write(item+0x10,struct.pack('<H',index))
                    registers=(UC_ARM64_REG_X8,UC_ARM64_REG_X9,UC_ARM64_REG_X10,UC_ARM64_REG_X11)
                    for i,r in enumerate(registers):m.reg_write(r,0x7770+i)
                    m.reg_write(UC_ARM64_REG_NZCV,0xa0000000)
                    m.emu_start(native.CAVE,native.DESTINATION_HOOK+4,count=100)
                    self.assertEqual(m.reg_read(UC_ARM64_REG_X22),0 if index in (1356,1357) and null is None else 1234)
                    self.assertEqual(m.reg_read(UC_ARM64_REG_NZCV),0xa0000000);self.assertEqual(m.reg_read(UC_ARM64_REG_SP),0x300f000)
                    for i,r in enumerate(registers):self.assertEqual(m.reg_read(r),0x7770+i)


@unittest.skipUnless(uc is not None and os.environ.get('FW_MOUNTS_MEMORY'),'Optional private native image not configured')
class NativePurchaseCallsiteTests(unittest.TestCase):
    def test_native_payment_loop_for_affordable_full_and_failed_purchases(self):
        image=Path(os.environ['FW_MOUNTS_MEMORY']).read_bytes()
        for index,gold,quantity,full,grant_ok,price in [(1356,2500,3,False,True,1000),(1356,999,1,False,True,1000),(1356,1000,1,True,True,1000),(1356,1000,1,False,False,1000),(1356,3000,3,False,True,1000),(1357,6500,3,False,True,3000),(1357,2999,1,False,True,3000),(1357,3000,1,True,True,3000),(1357,3000,1,False,False,3000)]:
            with self.subTest(gold=gold,quantity=quantity,full=full,grant_ok=grant_ok):
                m=MachineCodeTests().machine();m.mem_write(0x800000,b'\0')
                # Map the verified native image at its actual relative base.
                m.mem_map(0,0x800000);m.mem_write(0,image)
                for address,raw in native.patch_records(1356,6):m.mem_write(address,raw)
                menu=0x3001000;vtable=0x3002000;collection=0x3003000;array=0x3003100;entry=0x3003200;item=0x3003300
                rideholder=0x3004000;pool=0x3005000;rides=0x3006000;wallet=0x300a000;itemholder=0x300b000;itempool=0x300b100
                fileobject=0x300b200;indexarray=0x300b300;pricefunc=0x300e000
                def q(at,value):m.mem_write(at,struct.pack('<Q',value))
                q(menu,vtable);q(vtable+0x260,pricefunc);q(menu+0x78,collection);q(menu+0x68,0x300d000);q(menu+0x70,0)
                m.mem_write(menu+0x54,struct.pack('<I',quantity));q(collection,array);q(collection+8,array+8);q(array,entry);q(entry+0x30,item)
                m.mem_write(item+0x10,struct.pack('<H',index));m.mem_write(item+0x49,b'\x16')
                q(0x22343f8,rideholder);q(rideholder+8,pool);q(pool+0x78,rides)
                for i in range(200):m.mem_write(rides+i*64,b'\1' if full else b'\0')
                q(0x220ab10,wallet);m.mem_write(wallet+0x48,struct.pack('<I',gold))
                itemglobal=struct.unpack_from('<Q',image,0x216afb8)[0];q(itemglobal,itemholder);q(itemholder+8,itempool)
                fileglobal=struct.unpack_from('<Q',image,0x216a8b8)[0];q(fileglobal,fileobject);q(fileobject+0x40,indexarray);q(indexarray+index*8,item)
                calls=[]
                def hook(machine,at,size,user):
                    if at==0x189ea00:machine.reg_write(UC_ARM64_REG_PC,at+4) # PACIBSP does not affect this dataflow test.
                    elif at==pricefunc:
                        machine.reg_write(UC_ARM64_REG_X0,price);machine.reg_write(UC_ARM64_REG_PC,machine.reg_read(UC_ARM64_REG_LR))
                    elif at==0x9484a0:
                        temp=machine.reg_read(UC_ARM64_REG_X1);self.assertEqual(machine.mem_read(temp+1,1)[0],0 if index==1357 else 1)
                        calls.append('grant');slot=len([x for x in calls if x=='grant'])-1
                        machine.mem_write(machine.reg_read(UC_ARM64_REG_X8),struct.pack('<B3xi',2 if grant_ok else 1,slot if grant_ok else -1))
                        if grant_ok:machine.mem_write(rides+slot*64,b'\6')
                        machine.reg_write(UC_ARM64_REG_PC,machine.reg_read(UC_ARM64_REG_LR))
                    elif at==0x8aa0a0:
                        calls.append('stock');machine.reg_write(UC_ARM64_REG_PC,machine.reg_read(UC_ARM64_REG_LR))
                    elif at==0x189edac:machine.emu_stop()
                m.reg_write(UC_ARM64_REG_X0,menu);m.hook_add(uc.UC_HOOK_CODE,hook);m.emu_start(0x189ea00,0x3000100,count=20000)
                successes=min(quantity,gold//price) if grant_ok and not full else 0
                self.assertEqual(len([x for x in calls if x=='stock']),successes)
                self.assertEqual(struct.unpack('<I',m.mem_read(wallet+0x48,4))[0],gold-successes*price)
                if full:self.assertNotIn('grant',calls)


@unittest.skipUnless(uc is not None and os.environ.get('FW_MOUNTS_MEMORY'),'Optional private native image not configured')
class NativeSkillSelectorTests(unittest.TestCase):
    def test_all_saved_seeds_match_the_native_selector_at_both_skill_stages(self):
        from mount_skills import skill_roll
        image=Path(os.environ['FW_MOUNTS_MEMORY']).read_bytes()
        for seed in range(256):
            for level,amount in ((level,amount) for level in (3,4,5) for amount in (1,2,3)):
                with self.subTest(seed=seed,level=level,amount=amount):
                    m=uc.Uc(uc.UC_ARCH_ARM64,uc.UC_MODE_ARM)
                    m.mem_map(0x930000,0x10000);m.mem_write(0x9372c0,image[0x9372c0:0x9373b4])
                    m.mem_map(0x3000000,0x10000);m.mem_map(0x1a41000,0x2000)
                    ride=0x3001000;aux=0x3002000;entries=0x3003000
                    m.mem_write(ride+0x18,struct.pack('<Q',aux));m.mem_write(aux+0x88+level*24,struct.pack('<QQ',entries,entries+4*amount))
                    m.mem_write(entries,struct.pack('<III',0x123,0x456,0x789))
                    def hook(machine,at,size,user):
                        if at in (0x1a41ed0,0x1a41ee0,0x9373b0):machine.reg_write(UC_ARM64_REG_PC,machine.reg_read(UC_ARM64_REG_LR))
                        elif at==0x9372c0:machine.reg_write(UC_ARM64_REG_PC,at+4)
                    m.hook_add(uc.UC_HOOK_CODE,hook)
                    for register,value in ((UC_ARM64_REG_X0,ride),(UC_ARM64_REG_X1,level),(UC_ARM64_REG_X2,seed),(UC_ARM64_REG_SP,0x300f000),(UC_ARM64_REG_LR,0x3000100)):m.reg_write(register,value)
                    m.emu_start(0x9372c0,0x3000100,count=300)
                    self.assertEqual(m.reg_read(UC_ARM64_REG_X0),entries+4*(skill_roll(seed)%amount))

    def test_native_table_builder_maps_first_stage_to_levels_three_four_and_upgrade_to_five(self):
        image=Path(os.environ['FW_MOUNTS_MEMORY']).read_bytes()
        m=uc.Uc(uc.UC_ARCH_ARM64,uc.UC_MODE_ARM);m.mem_map(0x930000,0x10000);m.mem_write(0x938134,image[0x938134:0x938240]);m.mem_map(0x3000000,0x10000)
        ride=0x3001000;aux=0x3002000;first=0x3003000;second=0x3004000;skills=0x3005000
        def q(at,value):m.mem_write(at,struct.pack('<Q',value))
        m.mem_write(ride+0x70,struct.pack('<H',2));q(ride+0x78,first)
        m.mem_write(ride+0x80,struct.pack('<H',2));q(ride+0x88,second)
        for i,number in enumerate((101,102,201,202)):
            at=skills+i*64;m.mem_write(at+0x10,struct.pack('<H',number));q((first if i<2 else second)+(i%2)*16+8,at)
        vectors={}
        for i,offset in enumerate((0xd0,0xe8,0x100)):
            pointer=0x3006000+i*0x100;q(aux+offset,pointer);q(aux+offset+8,pointer);vectors[aux+offset]=pointer
        def hook(machine,at,size,user):
            if at==0x938df0:
                vector=machine.reg_read(UC_ARM64_REG_X0);value=machine.mem_read(machine.reg_read(UC_ARM64_REG_X1),4)
                end=struct.unpack('<Q',machine.mem_read(vector+8,8))[0];machine.mem_write(end,bytes(value));q(vector+8,end+4)
                machine.reg_write(UC_ARM64_REG_PC,machine.reg_read(UC_ARM64_REG_LR))
        m.hook_add(uc.UC_HOOK_CODE,hook)
        for register,value in ((UC_ARM64_REG_X19,ride),(UC_ARM64_REG_X21,aux),(UC_ARM64_REG_X22,aux),(UC_ARM64_REG_X29,0x300f000)):m.reg_write(register,value)
        m.emu_start(0x938134,0x938240,count=500)
        self.assertEqual([struct.unpack('<II',m.mem_read(vectors[aux+off],8)) for off in (0xd0,0xe8,0x100)],[(101,102),(101,102),(201,202)])


@unittest.skipUnless(uc is not None and os.environ.get('FW_GAME_DATA') and os.environ.get('FW_MESSAGES'),'Optional private mount/skill tables not configured')
class CompleteCatalogDeliveryTests(unittest.TestCase):
    def test_every_real_variant_delivers_its_own_type_seed_and_unique_policy(self):
        from fw_editor import Binary,Skill,messages
        from mount_catalog import catalog
        base=Path(os.environ['FW_GAME_DATA']);english=Path(os.environ['FW_MESSAGES']);names={}
        for name in ('Ride','Skill'):names.update(messages((english/(name+'.msbt.zst')).read_bytes()))
        offers=catalog(Binary((base/'Job.bin').read_bytes()),Skill((base/'Skill.bin').read_bytes()),names)
        self.assertEqual(len(offers),41);self.assertEqual(len({o.rid for o in offers}),22)
        rows=[(2000+i,o.ride_index,o.seed,o.unique) for i,o in enumerate(offers)];tester=MachineCodeTests()
        for i,offer in enumerate(offers):
            with self.subTest(rid=offer.rid,skill=offer.skill):
                calls,index=tester.delivery(index=2000+i,offers=rows)
                self.assertEqual((calls,index),((['unique-check'] if offer.unique else [])+['mount'],0))
                if offer.unique:self.assertEqual(tester.delivery(index=2000+i,offers=rows,occupied={199:offer.ride_index}),([],-1))


if __name__=='__main__':unittest.main()
