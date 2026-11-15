"""Software-only mount patch, project/export ownership and message append checks."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from fw_editor import DataError,Item,Job,Skill,decompress,messages,export_suite,suite_project
from message_append import append_messages,sections,labels
import mount_data as mounts
import mount_native as native
from script_data import load_with_scripts


def message_fixture():
    names=['MIID_Materials','MIID_H_Materials'];texts=[b'Own test name\0',b'Own test help\0']
    lbl=bytearray(struct.pack('<III',1,2,12))
    for i,name in enumerate(names):
        b=name.encode();lbl.extend(bytes([len(b)])+b+struct.pack('<I',i))
    offsets=[0,4,8,12,16,20,24,28,32,36,40,44,45,49,53,54,55,59,60,61,65,69,70]
    pointers=[a for a,b in zip(offsets,offsets[1:]+[74]) if b-a==4]
    records=bytearray(148)
    for i in range(2):
        for off in pointers:struct.pack_into('<I',records,i*74+off,156+i*5)
        records[i*74+69]=i
    txt=struct.pack('<III',2,12,12+len(texts[0]))+b''.join(texts)
    parts=[(b'LBL1',bytes(lbl)),(b'ATO1',struct.pack('<23I',*offsets)),
           (b'ATR1',struct.pack('<II',2,74)+records+b'attr\0meta\0'),
           (b'TSY1',struct.pack('<II',11,22)),(b'TXT2',txt),(b'AOCM',b'\2\0\xff\xfe')]
    raw=bytearray(32);raw[:10]=b'MsgStdBn\xff\xfe';raw[13]=3;struct.pack_into('<H',raw,14,len(parts))
    for name,payload in parts:
        raw.extend(name+struct.pack('<I',len(payload))+b'\0'*8+payload);raw.extend(b'\xab'*(-len(raw)%16))
    struct.pack_into('<I',raw,18,len(raw));return bytes(raw)


class MessageAppendTests(unittest.TestCase):
    def test_append_preserves_messages_indexes_attributes_and_styles(self):
        old=message_fixture();new=append_messages(old,[('CCK_NAME','Horse','MIID_Materials'),('CCK_HELP','Your stable','MIID_H_Materials')])
        self.assertEqual(messages(new),{**messages(old),'CCK_NAME':'Horse','CCK_HELP':'Your stable'})
        before={n:v for n,h,v,p in sections(old)};after={n:v for n,h,v,p in sections(new)}
        for name in (b'TXT2',):
            count=struct.unpack_from('<I',before[name])[0]
            for i in range(count):
                a=struct.unpack_from('<I',before[name],4+i*4)[0];b=struct.unpack_from('<I',after[name],4+i*4)[0]
                end=before[name].index(0,a)+1
                self.assertEqual(before[name][a:end],after[name][b:b+end-a])
        self.assertEqual(after[b'TSY1'],struct.pack('<4I',11,22,11,22))
        self.assertEqual(after[b'AOCM'],b'\4\0\xff\xfe\xff\xfe')
        self.assertEqual(after[b'ATO1'],before[b'ATO1'])
        for i in range(4):
            for off in (0,40,45,49,55,61,65,70):
                a=struct.unpack_from('<I',before[b'ATR1'],8+(i%2)*74+off)[0]
                b=struct.unpack_from('<I',after[b'ATR1'],8+i*74+off)[0]
                self.assertEqual(b,a+148)
                self.assertEqual(before[b'ATR1'][a:].split(b'\0')[0],after[b'ATR1'][b:].split(b'\0')[0])

    def test_collisions_unknown_template_and_control_text_rejected(self):
        for addition in [('MIID_Materials','new','MIID_Materials'),('NEW','new','absent'),('NEW','bad\ntext','MIID_Materials')]:
            with self.subTest(addition=addition),self.assertRaises(DataError):append_messages(message_fixture(),[addition])

    def test_rejects_bad_sizes_encoding_and_truncation(self):
        raw=message_fixture()
        for changed in [raw[:-1],raw[:12]+b'\1'+raw[13:],raw[:18]+b'\0'*4+raw[22:]]:
            with self.assertRaises(DataError):append_messages(changed,[('NEW','Horse','MIID_Materials')])

    def test_zstandard_and_no_additions(self):
        from script_data import compress
        raw=compress(message_fixture());self.assertEqual(append_messages(raw,[]),raw)
        self.assertEqual(messages(append_messages(raw,[('NEW','Horse','MIID_Materials')]))['NEW'],'Horse')


class NativePatchTests(unittest.TestCase):
    def test_only_known_executable_accepted(self):
        for value in [b'',b'NSO0'+b'\0'*300]:
            with self.assertRaises(DataError):native.validate_main(value)

    def test_ips32_offsets_and_index_immediates(self):
        self.assertEqual(Path(native.IPS_PATH).stem,native.BUILD_ID.upper())
        blob=native.ips32(1356,6);self.assertEqual(blob[:5],b'IPS32');self.assertEqual(blob[-4:],b'EEOF')
        at=5;records=[]
        while at<len(blob)-4:
            address,size=struct.unpack_from('>IH',blob,at);at+=6;records.append((address,blob[at:at+size]));at+=size
        self.assertEqual(records,[(a+0x100,b) for a,b in native.patch_records(1356,6)])
        self.assertLess(native.CAVE+len(records[-1][1]),0x1a46000)
        table=records[-1][1][native.TABLE-native.CAVE:]
        self.assertEqual([struct.unpack_from('<HBBI',table,i*8) for i in range(2)],[(1356,6,1,0),(1357,6,0,0)])
        self.assertEqual((struct.unpack_from('<I',records[-1][1],native.COUNT_SLOTS['dest_count'])[0]>>5)&65535,2)


    def test_index_limits_and_branch_range(self):
        for pair in [(0,6),(65536,6),(1,0),(1,256),(True,6)]:
            with self.assertRaises(ValueError):native.ips32(*pair)
        for target in (1,1<<28):
            with self.assertRaises(ValueError):native.branch(0,target)


class MountProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.main=self.root/'main';self.main.write_bytes(b'own fake executable')
        self.bank=self.root/'Item.msbt';self.bank.write_bytes(message_fixture())
        self.guard=patch('mount_data.validate_main');self.guard.start();self.addCleanup(self.guard.stop)

    def test_price_boolean_and_project_validation(self):
        d=mounts.MountPatch(self.main,self.bank)
        for enabled,price in [(1,1000),(True,0),(True,65536),(True,True)]:
            with self.assertRaises(DataError):d.configure(enabled,price)
        d.configure(True,1000);p=d.project();fresh=mounts.MountPatch(self.main,self.bank);fresh.load_project(p)
        self.assertEqual(fresh.project(),p)
        for key,value in [('format','wrong'),('message_sha256','0'*64),('enabled','yes'),('prices',{mounts.IID:0})]:
            broken={**p,key:value}
            with self.assertRaises(DataError):fresh.load_project(broken)

    def test_two_prices_and_legacy_project_migration(self):
        d=mounts.MountPatch(self.main,self.bank);d.configure(True,1000,5000)
        fresh=mounts.MountPatch(self.main,self.bank);fresh.load_project(d.project())
        self.assertEqual((fresh.price,fresh.move_price),(1000,5000))
        before=fresh.project()
        for value in (0,65536,True,'5000'):
            with self.assertRaises(DataError):fresh.configure(True,1000,value)
            self.assertEqual(fresh.project(),before)
        legacy={**before,'format':'cck-buyable-mounts-v1','price':2000}
        fresh.load_project(legacy);self.assertEqual((fresh.price,fresh.move_price),(2000,6000))
        for broken in ({**before,'format':'cck-buyable-mounts-v2','price':1000,'move_price':None},{**before,'format':'cck-buyable-mounts-v2','price':1000}):
            with self.assertRaises(DataError):fresh.load_project(broken)

    def test_reopen_sources_and_failure_preserves_membership(self):
        d=mounts.MountPatch(self.main,self.bank);d.configure(True,1000)
        docs={mounts.MODULE:d};sources={mounts.MODULE:self.main};project=suite_project(docs)
        new={};src={};load_with_scripts(new,src,self.root/'GameData',project)
        self.assertEqual(suite_project(new),project)
        broken=deepcopy(project);broken['documents'][mounts.FILENAME]['prices']={mounts.IID:0}
        with self.assertRaises(DataError):load_with_scripts(new,src,self.root/'GameData',broken)
        self.assertEqual(suite_project(new),project)

    def test_export_disable_removes_only_owned_outputs(self):
        d=mounts.MountPatch(self.main,self.bank);d.configure(True,1000);docs={mounts.MODULE:d}
        folder=self.root/'mod';outputs={mounts.BANK_OUTPUT:b'own messages',native.IPS_PATH:b'own code'}
        with patch('mount_data.build_outputs',return_value=outputs.copy()):paths=export_suite(docs,{},folder)
        self.assertEqual(len(paths),2);self.assertEqual((folder/native.IPS_PATH).read_bytes(),b'own code')
        (folder/'unrelated.txt').write_text('keep')
        d.configure(False,1000);export_suite(docs,{},folder)
        self.assertFalse((folder/native.IPS_PATH).exists());self.assertFalse((folder/mounts.BANK_OUTPUT).exists())
        self.assertEqual((folder/'unrelated.txt').read_text(),'keep')

    def test_generated_file_collisions_and_outside_edits_refused(self):
        d=mounts.MountPatch(self.main,self.bank);d.configure(True,1000);docs={mounts.MODULE:d};folder=self.root/'mod'
        target=folder/native.IPS_PATH;target.parent.mkdir(parents=True);target.write_bytes(b'external')
        with patch('mount_data.build_outputs',return_value={native.IPS_PATH:b'own code'}),self.assertRaises(DataError):export_suite(docs,{},folder)
        target.unlink()
        with patch('mount_data.build_outputs',return_value={native.IPS_PATH:b'own code'}):export_suite(docs,{},folder)
        target.write_bytes(b'edited');d.configure(False,1000)
        with self.assertRaises(DataError):export_suite(docs,{},folder)
        self.assertEqual(target.read_bytes(),b'edited')

    def test_manifest_cannot_remove_arbitrary_files(self):
        folder=self.root/'mod';folder.mkdir();target=self.root/'keep.txt';target.write_bytes(b'keep')
        manifest={'format':'fw-hacking-suite-project-v1','documents':{},'generated_outputs':{'../keep.txt':hashlib.sha256(b'keep').hexdigest()}}
        (folder/'suite-edits.json').write_text(json.dumps(manifest))
        with self.assertRaises(DataError):export_suite({}, {},folder)
        self.assertEqual(target.read_bytes(),b'keep')


DATA=os.environ.get('FW_GAME_DATA');BANK=os.environ.get('FW_MESSAGES');MAIN=os.environ.get('FW_MOUNTS_MAIN')
@unittest.skipUnless(DATA and BANK and MAIN,'Optional private source files not configured')
class NativeSourceTests(unittest.TestCase):
    def test_overlay_roundtrip_and_all_existing_entries_preserved(self):
        from test_shops import snapshot
        item=Item((Path(DATA)/'Item.bin').read_bytes());job=Job((Path(DATA)/'Job.bin').read_bytes())
        patch=mounts.MountPatch(MAIN,Path(BANK)/'Item.msbt.zst');patch.configure(True,1000)
        docs={'Items':item,'Classes':job,'Skills':Skill((Path(DATA)/'Skill.bin').read_bytes()),mounts.MODULE:patch};before=suite_project(docs)
        result=mounts.build_outputs(docs);self.assertEqual(suite_project(docs),before)
        new=Item(result['romfs/GameData/Item.bin'])
        self.assertEqual(len(new.records),len(item.records)+41)
        for row in item.records:
            for f in item.fields:self.assertEqual(item.value(row,f),new.value(new.by_pid[row.pid],f))
        for key,view in item.views.items():
            for row in view.records:
                for f in view.fields:self.assertEqual(view.value(row,f),new.views[key].value(new.views[key].by_pid[row.pid],f))
        original=messages((Path(BANK)/'Item.msbt.zst').read_bytes());updated=messages(result[mounts.BANK_OUTPUT])
        for key,value in original.items():self.assertEqual(updated[key],value)
        self.assertEqual(updated[mounts.NAME],'Horse (Dodge)');self.assertEqual(updated[mounts.MOVE_NAME],'Horse (Move)')
        with tempfile.TemporaryDirectory() as directory:
            export_suite(docs,{},directory);patch.configure(False,1000);export_suite(docs,{},directory)
            self.assertEqual((Path(directory)/'romfs/GameData/Item.bin').read_bytes(),item.raw)
            self.assertFalse((Path(directory)/native.IPS_PATH).exists())


    def test_user_items_and_shop_edits_survive_dynamic_index_selection(self):
        item=Item((Path(DATA)/'Item.bin').read_bytes());job=Job((Path(DATA)/'Job.bin').read_bytes())
        item.create_item('IID_CCK_OwnTestItem',copy_from=item.records[1].pid)
        row=item.records[1];item.set(row,item.by_offset[0x4c],777)
        shop=item.views['shops'];table=next(t for t in shop.collections if shop.names[t.pid]==mounts.SHOP)
        entry=shop.rows_by_table[table.pid][0];shop.set(entry,shop.by_offset[0x68],321)
        patch=mounts.MountPatch(MAIN,Path(BANK)/'Item.msbt.zst');patch.configure(True,1234)
        docs={'Items':item,'Classes':job,'Skills':Skill((Path(DATA)/'Skill.bin').read_bytes()),mounts.MODULE:patch};before=suite_project(docs);result=mounts.build_outputs(docs)
        self.assertEqual(suite_project(docs),before)
        new=Item(result['romfs/GameData/Item.bin']);self.assertIn('IID_CCK_OwnTestItem',new.by_pid)
        self.assertEqual(new.value(new.by_pid[row.pid],new.by_offset[0x4c]),777)
        self.assertEqual(new.views['shops'].value(new.views['shops'].by_pid[entry.pid],new.views['shops'].by_offset[0x68]),321)
        index=struct.unpack_from('<H',new.raw,new.by_pid[mounts.IID].offset+16)[0]
        self.assertEqual(index,len(item.records)+1)
        offers=mounts.catalog_for(docs,patch)
        rows=[(struct.unpack_from('<H',new.raw,new.by_pid[o.iid].offset+16)[0],o.ride_index,o.seed,o.unique) for o in offers]
        self.assertEqual(result[native.IPS_PATH],native.catalog_ips32(rows))
        self.assertEqual(new.value(new.by_pid[mounts.IID],new.by_offset[0x4c]),1234)
        self.assertEqual(new.value(new.by_pid[mounts.MOVE_IID],new.by_offset[0x4c]),3000)

    def test_changed_messages_and_reserved_item_fail_before_export(self):
        item=Item((Path(DATA)/'Item.bin').read_bytes());job=Job((Path(DATA)/'Job.bin').read_bytes())
        with tempfile.TemporaryDirectory() as directory:
            bank=Path(directory)/'Item.msbt.zst';bank.write_bytes((Path(BANK)/bank.name).read_bytes())
            patch=mounts.MountPatch(MAIN,bank);patch.configure(True,1000);docs={'Items':item,'Classes':job,'Skills':Skill((Path(DATA)/'Skill.bin').read_bytes()),mounts.MODULE:patch}
            bank.write_bytes(b'changed original')
            with self.assertRaises(DataError):mounts.build_outputs(docs)
        patch=mounts.MountPatch(MAIN,Path(BANK)/'Item.msbt.zst');patch.configure(True,1000);docs[mounts.MODULE]=patch
        item.create_item(mounts.IID)
        with self.assertRaises(DataError):mounts.build_outputs(docs)


if __name__=='__main__':unittest.main()
