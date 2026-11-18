"""Execute CCK's own vendor helper with mocked native APIs; no game code."""
import struct
import unittest
import battalion_native as native
import mount_native as mounts
try:
    import unicorn as uc
    from unicorn.arm64_const import *
except ImportError:uc=None


@unittest.skipIf(uc is None,'Optional Unicorn emulator not installed')
class BattalionMachineTests(unittest.TestCase):
    def machine(self,combined=False,offers=None):
        m=uc.Uc(uc.UC_ARCH_ARM64,uc.UC_MODE_ARM);m.mem_map(0x800000,0x1b00000);m.mem_map(0x3000000,0x20000)
        if combined:
            for address,raw in mounts.catalog_records([(5000,6,1,False)]):m.mem_write(address,raw)
        for address,raw in native.patch_records(offers or [(4000,31)],mounts=combined):m.mem_write(address,raw)
        for i,register in enumerate((UC_ARM64_REG_X19,UC_ARM64_REG_X20,UC_ARM64_REG_X29)):m.reg_write(register,0x3100+i)
        m.reg_write(UC_ARM64_REG_SP,0x301f000);m.reg_write(UC_ARM64_REG_LR,0x3000100)
        return m

    def deliver(self,*,index=4000,free=0,combined=False,holder=True,pool=True,array=True,native_slot=None,wrong_id=False):
        m=self.machine(combined);holder_at=0x3001000;pool_at=0x3002000;records=0x3003000;result=0x300e000;input_at=result+0x100
        def q(at,v):m.mem_write(at,struct.pack('<Q',v))
        q(0x22343a8,holder_at if holder else 0);q(holder_at+8,pool_at if pool else 0);q(pool_at+0x30,records if array else 0)
        for i in range(300):m.mem_write(records+i*8,struct.pack('<Q',0 if i==free else 1))
        before=bytes(m.mem_read(records,2400));m.mem_write(input_at,struct.pack('<HHI',index,0,1))
        m.reg_write(UC_ARM64_REG_X1,input_at);m.reg_write(UC_ARM64_REG_X8,result);calls=[]
        def hook(cpu,at,size,_):
            if at in (0x8a25c0,mounts.DELIVERY):calls.append('mount' if at==mounts.DELIVERY else 'ordinary');cpu.emu_stop()
            elif at==0x942d60:
                calls.append('battalion');self.assertEqual(cpu.reg_read(UC_ARM64_REG_X0),pool_at);self.assertEqual(cpu.reg_read(UC_ARM64_REG_X2),0)
                arg=bytes(cpu.mem_read(cpu.reg_read(UC_ARM64_REG_X1),8));self.assertEqual(arg,struct.pack('<Q',31))
                slot=free if native_slot is None else native_slot
                if 0<=slot<300:cpu.mem_write(records+slot*8,struct.pack('<Q',32 if wrong_id else 31))
                cpu.mem_write(cpu.reg_read(UC_ARM64_REG_X8),struct.pack('<B3xi',2,slot))
                cpu.reg_write(UC_ARM64_REG_PC,cpu.reg_read(UC_ARM64_REG_LR))
        m.hook_add(uc.UC_HOOK_CODE,hook);m.emu_start(native.DELIVERY,0x3000100,count=10000)
        if index==4000:
            self.assertEqual(m.reg_read(UC_ARM64_REG_SP),0x301f000)
            for i,register in enumerate((UC_ARM64_REG_X19,UC_ARM64_REG_X20,UC_ARM64_REG_X29)):self.assertEqual(m.reg_read(register),0x3100+i)
            self.assertEqual(m.reg_read(UC_ARM64_REG_LR),0x3000100)
        return calls,struct.unpack_from('<i',m.mem_read(result,8),4)[0],before,bytes(m.mem_read(records,2400))

    def test_every_barracks_slot_delivers(self):
        for free in range(300):
            with self.subTest(slot=free):
                calls,slot,before,after=self.deliver(free=free);self.assertEqual((calls,slot),(['battalion'],free))
                self.assertEqual(after[:free*8],before[:free*8]);self.assertEqual(after[(free+1)*8:],before[(free+1)*8:])

    def test_full_or_missing_barracks_cannot_replace_or_charge(self):
        for kw in ({'free':-1},{'holder':False},{'pool':False},{'array':False}):
            with self.subTest(kw=kw):
                calls,slot,before,after=self.deliver(**kw);self.assertEqual((calls,slot),([],-1));self.assertEqual(before,after)

    def test_failed_or_invalid_native_result_is_not_reported_as_delivery(self):
        for kw in ({'native_slot':-1},{'native_slot':300},{'wrong_id':True}):
            with self.subTest(kw=kw):self.assertEqual(self.deliver(**kw)[:2],(['battalion'],-1))

    def test_other_items_fall_through_and_mounts_chain(self):
        self.assertEqual(self.deliver(index=1)[0],['ordinary'])
        self.assertEqual(self.deliver(index=5000,combined=True)[0],['mount'])
        self.assertEqual(self.deliver(index=1,combined=True)[0],['mount']) # Dispatcher then falls through normally.
        self.assertEqual(self.deliver(combined=True)[:2],(['battalion'],0))

    def test_destination_chaining_and_abi(self):
        for combined in (False,True):
            for index in (4000,5000,1):
                m=self.machine(combined);menu=0x3001000;collection=menu+0x1000;first=menu+0x2000;entry=menu+0x3000;item=menu+0x4000
                def q(at,v):m.mem_write(at,struct.pack('<Q',v))
                q(menu+0x68,0xabcdef);q(collection,first);q(first,entry);q(entry+0x30,item);m.mem_write(item+0x10,struct.pack('<H',index))
                m.reg_write(UC_ARM64_REG_X21,menu);m.reg_write(UC_ARM64_REG_X20,collection);m.reg_write(UC_ARM64_REG_NZCV,0xa0000000)
                saved={r:m.reg_read(r) for r in (UC_ARM64_REG_X8,UC_ARM64_REG_X9,UC_ARM64_REG_X10,UC_ARM64_REG_X11,UC_ARM64_REG_X20,UC_ARM64_REG_X21)}
                m.emu_start(native.CAVE,0x189ea3c,count=10000)
                self.assertEqual(m.reg_read(UC_ARM64_REG_X22),0 if index==4000 or combined and index==5000 else 0xabcdef)
                self.assertEqual(m.reg_read(UC_ARM64_REG_SP),0x301f000);self.assertEqual(m.reg_read(UC_ARM64_REG_NZCV),0xa0000000)
                for reg,value in saved.items():self.assertEqual(m.reg_read(reg),value)

    def test_full_mount_catalog_and_battalions_fit_without_overlap(self):
        records=mounts.catalog_records([(i+1,6,1,False) for i in range(256)])
        bat=native.patch_records([(1000+i,1+i) for i in range(100)],mounts=True)
        self.assertEqual(records[-1][0]+len(records[-1][1]),native.CAVE)
        self.assertEqual(bat[-1][0]+len(bat[-1][1]),0x1a46000)


class BattalionRecordTests(unittest.TestCase):
    def test_invalid_ids_and_extents(self):
        for rows in ([],[(0,1)],[(1,0)],[(1,256)],[(True,1)],[(1,True)],[(1,1),(1,2)],[(i+1,1) for i in range(101)]):
            with self.subTest(rows=rows[:3]):
                with self.assertRaises(ValueError):native.patch_records(rows)


if __name__=='__main__':unittest.main()
