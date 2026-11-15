"""Optional native stock decrement/restock checks; no game code is distributed."""
from pathlib import Path
import os,struct,unittest
try:
    import unicorn as uc
    from unicorn.arm64_const import *
except ImportError:uc=None


@unittest.skipUnless(uc and os.environ.get('FW_MOUNTS_MEMORY'),'Optional native image/Unicorn not configured')
class NativeStockTests(unittest.TestCase):
    def test_caps_refill_do_not_accumulate_and_saved_counter_survives_reload(self):
        image=Path(os.environ['FW_MOUNTS_MEMORY']).read_bytes()
        def machine(limit,saved=0x80):
            m=uc.Uc(uc.UC_ARCH_ARM64,uc.UC_MODE_ARM);m.mem_map(0,0x2400000);m.mem_write(0,image);m.mem_map(0x3000000,0x20000)
            collection=0x3001000;array=0x3001100;entry=0x3001200;aux=0x3001400;user=0x3001600;store=0x3001700;node=0x3001800
            def q(at,val):m.mem_write(at,struct.pack('<Q',val))
            q(collection,array);q(collection+8,array+8);q(array,entry);q(entry+0x18,aux)
            m.mem_write(entry+0x6b,bytes([limit,limit]));q(0x220ab10,user);q(user+0x30,store);m.mem_write(node+0x20,struct.pack('<I',saved))
            def hook(cpu,at,size,data):
                if at in (0x8a9f20,0x8aa0a0,0x8b1da0,0x8aa38c,0x8b2154):cpu.reg_write(UC_ARM64_REG_PC,at+4)
                elif at in (0x8aa08c,0x8aa31c,0x8b20e4):cpu.reg_write(UC_ARM64_REG_PC,cpu.reg_read(UC_ARM64_REG_LR))
                elif at==0x65cd00:
                    self.assertEqual(cpu.reg_read(UC_ARM64_REG_X1),aux+0x20)
                    cpu.reg_write(UC_ARM64_REG_X0,node);cpu.reg_write(UC_ARM64_REG_PC,cpu.reg_read(UC_ARM64_REG_LR))
                elif at==0x719980:
                    self.assertEqual(cpu.reg_read(UC_ARM64_REG_X0),aux+0x20)
                    cpu.mem_write(node+0x20,struct.pack('<I',cpu.reg_read(UC_ARM64_REG_W1)));cpu.reg_write(UC_ARM64_REG_PC,cpu.reg_read(UC_ARM64_REG_LR))
            m.hook_add(uc.UC_HOOK_CODE,hook)
            def call(address):
                for reg,val in ((UC_ARM64_REG_X0,collection),(UC_ARM64_REG_X1,collection),(UC_ARM64_REG_SP,0x301f000),(UC_ARM64_REG_LR,0x3000100)):m.reg_write(reg,val)
                m.emu_start(address,0x3000100,count=5000);return m.reg_read(UC_ARM64_REG_W0)
            def state():return struct.unpack('<I',m.mem_read(node+0x20,4))[0]
            return call,state
        for limit in (1,2,7,127):
            with self.subTest(limit=limit):
                call,state=machine(limit);self.assertEqual(call(0x8a9f20),limit)
                for expected in range(limit-1,-1,-1):
                    call(0x8aa0a0);self.assertEqual(call(0x8a9f20),expected)
                saved=state();self.assertEqual(saved,0x80|limit)
                call,state=machine(limit,saved);self.assertEqual(call(0x8a9f20),0)
                call(0x8b1da0);self.assertEqual(call(0x8a9f20),limit);self.assertEqual(state(),0x80)
                call(0x8b1da0);self.assertEqual(call(0x8a9f20),limit)
        call,state=machine(0);self.assertEqual(call(0x8a9f20),0xffffffff)
        call(0x8aa0a0);self.assertEqual(call(0x8a9f20),0xffffffff)


if __name__=='__main__':unittest.main()
