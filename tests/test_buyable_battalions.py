"""Synthetic projects and optional private source integration; no game assets."""
from copy import deepcopy
import json,os,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fw_editor import Item,Legion,Skill,Job,DataError,messages,suite_project,export_suite
from fixture import legion_fixture,skill_fixture,shop_fixture
from test_buyable_mounts import message_fixture
from message_append import append_messages
import battalion_data as bat
import mount_data as mount
from script_data import load_with_scripts


def synthetic_documents():
    legion=Legion(legion_fixture());r=legion.records[1]
    for off,val in [(0xb0,'VID_軍団兵'),(0x38,'SID_SYNTHETIC_A'),(0x98,700)]:legion.set(r,legion.by_offset[off],val)
    # The general synthetic Item fixture packs its fields more tightly. Give
    # its invented trailing string the native icon-field position for this
    # export fixture; this is not a copy of a game table.
    raw=bytearray(shop_fixture());item=Item(raw);schema=next(g[3] for g in item.groups() if g[0]=='アイテム')
    field=next(i for i,f in enumerate(item.fields) if f.offset==0x148)
    struct.pack_into('<I',raw,schema+field*32+28,0x1c0)
    return {'Items':Item(raw),'Legion':Legion(legion.build()),'Skills':Skill(skill_fixture())}


class BattalionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.main=self.root/'main';self.main.write_bytes(b'CCK invented executable fixture')
        self.bank=self.root/'Item.msbt';self.bank.write_bytes(message_fixture())
        for name,key,value in [('Legion','MLID_SYNTHETIC','Invented Brigade'),('Skill','MSID_SYNTHETIC_0','Invented Gambit')]:
            (self.root/(name+'.msbt')).write_bytes(append_messages(message_fixture(),[(key,value,'MIID_Materials')]))
        for target,value in [('battalion_data.validate_main',None),('battalion_data.SHOP','SHOP_ALPHA')]:
            mock=patch(target,return_value=value) if value is None else patch(target,value)
            mock.start();self.addCleanup(mock.stop)
        self.docs=synthetic_documents();self.doc=bat.BattalionPatch(self.main,self.bank);self.docs[bat.MODULE]=self.doc
        self.offer=bat.catalog_for(self.docs,self.doc)[0]

    def test_catalog_reads_current_stats_and_excludes_noncombat_rows(self):
        self.assertEqual((self.offer.name,self.offer.gambit,self.offer.default_price,self.offer.legion_index),('Invented Brigade','Invented Gambit',700,1))
        legion=self.docs['Legion'];row=legion.records[1];legion.set(row,legion.by_offset[0x98],2222)
        self.assertEqual(bat.catalog_for(self.docs,self.doc)[0].default_price,2222)
        legion.set(row,legion.by_offset[0xb0],'VID_CIVILIAN')
        with self.assertRaises(DataError):bat.catalog_for(self.docs,self.doc)

    def test_project_roundtrip_invalid_values_and_transactionality(self):
        iid=self.offer.iid;self.doc.configure_all(True,{iid:1234},[iid],{iid:2});before=self.doc.project()
        fresh=bat.BattalionPatch(self.main,self.bank);fresh.load_project(before);self.assertEqual(fresh.project(),before)
        for changes in ({'enabled':1},{'prices':{iid:0}},{'prices':{iid:True}},{'limits':{iid:128}},{'limits':{iid:True}},{'limits':None},{'disabled':[iid,iid]},{'disabled':[{}]},{'main_sha256':'bad'}):
            with self.subTest(changes=changes):
                with self.assertRaises(DataError):fresh.load_project({**before,**changes})
                self.assertEqual(fresh.project(),before)

    def test_append_preserves_user_edits_sources_and_stock_identity(self):
        item=self.docs['Items'];row=item.records[1];item.set(row,item.by_offset[0x4c],3456)
        before=suite_project(self.docs);self.doc.configure_all(True,{self.offer.iid:1200},[self.offer.iid],{self.offer.iid:2})
        state=suite_project(self.docs);output=bat.build_outputs(self.docs);self.assertEqual(suite_project(self.docs),state)
        changed=Item(output['romfs/GameData/Item.bin']);self.assertEqual(len(changed.records),len(item.records)+1)
        self.assertEqual(changed.value(changed.by_pid[row.pid],changed.by_offset[0x4c]),3456)
        shops=changed.views['shops'];r=next(r for r in shops.records if shops.value(r,shops.by_offset[0x28])==self.offer.iid)
        self.assertEqual([shops.value(r,shops.by_offset[o]) for o in (0x6b,0x6c)],[2,2])
        self.assertIn('セオドラ篇',shops.value(r,shops.by_offset[0x38]));self.assertIn('!セオドラ篇',shops.value(r,shops.by_offset[0x38]))
        self.assertEqual(messages(output[bat.BANK_OUTPUT])[self.offer.name_key],'Battalion: Invented Brigade')
        self.doc.configure_all(True,{},[],{});unhidden=bat.build_outputs(self.docs)
        self.assertEqual(unhidden[bat.IPS_PATH],output[bat.IPS_PATH])
        self.assertEqual([r.pid for r in Item(unhidden['romfs/GameData/Item.bin']).records],[r.pid for r in changed.records])

    def test_project_reopen_disable_cleanup_and_export_ownership(self):
        self.doc.configure_all(True,{},[],{self.offer.iid:1});p=suite_project(self.docs)
        restored=synthetic_documents();sources={};load_with_scripts(restored,sources,self.root,p)
        self.assertEqual(restored[bat.MODULE].limits,{self.offer.iid:1})
        target=self.root/'mod';export_suite(restored,sources,target)
        self.assertTrue((target/bat.IPS_PATH).is_file());self.assertFalse(list(target.rglob('*.backup-*')))
        restored[bat.MODULE].configure_all(False,{});export_suite(restored,sources,target)
        self.assertFalse((target/bat.IPS_PATH).exists());self.assertFalse((target/bat.BANK_OUTPUT).exists())
        self.assertEqual((target/'romfs/GameData/Item.bin').read_bytes(),restored['Items'].build())
        self.assertEqual(self.main.read_bytes(),b'CCK invented executable fixture')

    def test_missing_sources_do_not_partially_load_or_replace_edits(self):
        folder=self.root/'GameData';folder.mkdir();docs={};sources={}
        for name,doc in self.docs.items():
            if name!=bat.MODULE:(folder/doc.filename).write_bytes(doc.raw)
        (folder/'Skill.bin').unlink()
        with self.assertRaisesRegex(DataError,'Skill.bin'):bat.load_sources(docs,sources,self.root)
        self.assertEqual(docs,{})
        (folder/'Skill.bin').write_bytes(self.docs['Skills'].raw);self.assertEqual(bat.load_sources(docs,sources,self.root),3)
        self.assertNotIn('Classes',docs);original=docs['Items'];original.set(original.records[1],original.by_offset[0x4c],99)
        self.assertEqual(bat.load_sources(docs,sources,None),0);self.assertIs(docs['Items'],original)

    def test_source_and_unknown_offer_guards(self):
        self.doc.configure_all(True,{bat.PREFIX+'missing':999})
        with self.assertRaisesRegex(DataError,'no longer'):bat.build_outputs(self.docs)
        self.doc.configure_all(True,{})
        self.bank.write_bytes(b'edited')
        with self.assertRaisesRegex(DataError,'changed'):bat.build_outputs(self.docs)


DATA=os.environ.get('FW_GAME_DATA');BANK=os.environ.get('FW_MESSAGES');MAIN=os.environ.get('FW_MOUNTS_MAIN')
@unittest.skipUnless(DATA and BANK and MAIN,'Optional private sources not configured')
class PrivateBattalionTests(unittest.TestCase):
    def documents(self):
        p=Path(DATA)
        docs={name:kind((p/kind.filename).read_bytes()) for name,kind in [('Items',Item),('Classes',Job),('Legion',Legion),('Skills',Skill)]}
        b=bat.BattalionPatch(MAIN,Path(BANK)/'Item.msbt.zst');b.configure_all(True,{});docs[bat.MODULE]=b
        return docs,b

    def test_all_combat_battalions_and_existing_data_preserved(self):
        docs,b=self.documents();offers=bat.catalog_for(docs,b);self.assertEqual(len(offers),99)
        self.assertEqual({o.legion_index for o in offers},set(range(1,100)))
        before=suite_project(docs);out=bat.build_outputs(docs);self.assertEqual(suite_project(docs),before)
        item=docs['Items'];new=Item(out['romfs/GameData/Item.bin'])
        self.assertEqual(len(new.records),len(item.records)+99)
        for r in item.records:
            for f in item.fields:self.assertEqual(item.value(r,f),new.value(new.by_pid[r.pid],f))
        old_names=messages(Path(BANK,'Item.msbt.zst').read_bytes());names=messages(out[bat.BANK_OUTPUT])
        self.assertTrue(old_names.items()<=names.items());self.assertTrue(all(names[o.name_key]=='Battalion: '+o.name for o in offers))

    def test_joint_mounts_and_battalions_reopen_and_independent_disable(self):
        docs,b=self.documents();m=mount.MountPatch(MAIN,Path(BANK)/'Item.msbt.zst');m.configure(True,1000);docs[mount.MODULE]=m
        offer=bat.catalog_for(docs,b)[0];b.configure_all(True,{offer.iid:2500},[offer.iid],{offer.iid:2})
        before=suite_project(docs);out=mount.build_outputs(docs);self.assertEqual(suite_project(docs),before)
        item=Item(out['romfs/GameData/Item.bin']);self.assertEqual(len(item.records),len(docs['Items'].records)+140)
        names=messages(out[bat.BANK_OUTPUT]);self.assertEqual(names[mount.NAME],'Horse (Dodge)');self.assertIn(offer.name_key,names)
        records=bat.decode_ips(out[bat.IPS_PATH]);self.assertEqual(len(records),4)
        for (a,x),(c,y) in zip(sorted(records),sorted(records)[1:]):self.assertLessEqual(a+len(x),c)
        with tempfile.TemporaryDirectory() as temp:
            export_suite(docs,{},temp);b.configure_all(False,{})
            export_suite(docs,{},temp);only_mounts=Path(temp,bat.IPS_PATH).read_bytes()
            self.assertEqual(only_mounts,mount.build_mount_outputs(docs)[bat.IPS_PATH])
            self.assertNotIn(offer.name_key,messages(Path(temp,bat.BANK_OUTPUT).read_bytes()))
            b.configure_all(True,{});m.configure(False,1000);export_suite(docs,{},temp)
            self.assertNotIn(mount.NAME,messages(Path(temp,bat.BANK_OUTPUT).read_bytes()))
            b.configure_all(False,{});export_suite(docs,{},temp);self.assertFalse(Path(temp,bat.IPS_PATH).exists())
        restored={k:v for k,v in self.documents()[0].items() if k!=bat.MODULE}
        load_with_scripts(restored,{},Path(DATA),before);self.assertEqual(restored[bat.MODULE].limits,{offer.iid:2})
        self.assertTrue(restored[mount.MODULE].enabled)


if __name__=='__main__':unittest.main()
