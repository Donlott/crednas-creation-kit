"""Opt-in export-time mount catalog; loaded source tables remain unchanged."""
from copy import deepcopy
import hashlib
from pathlib import Path
import struct

from mount_native import IPS_PATH,MAIN_SHA256,validate_main,catalog_ips32
from mount_catalog import HORSE_DODGE,HORSE_MOVE,PREFIX,catalog

FILENAME='CCK/Buyable-mounts.json'
MODULE='Patch · Buyable mounts'
IID=HORSE_DODGE;MOVE_IID=HORSE_MOVE
NAME='MIID_CCK_BuyMount_Horse';HELP='MIID_H_CCK_BuyMount_Horse'
MOVE_NAME='MIID_CCK_BuyMount_Horse_Move';MOVE_HELP='MIID_H_CCK_BuyMount_Horse_Move'
BANK_OUTPUT='romfs/Msg/USen/Item.msbt.zst'
GENERATED_PATHS=frozenset((BANK_OUTPUT,IPS_PATH))
SHOP='帝都ダグシオン_道具屋'


def digest(raw):return hashlib.sha256(raw).hexdigest()


class MountPatch:
    filename=FILENAME;records=();fields=();views={};names={};prefix='PATCH_'

    def __init__(self,main_path,message_path):
        from fw_editor import DataError,messages
        self.main_path=Path(main_path).resolve();self.message_path=Path(message_path).resolve()
        validate_main(self.main_path.read_bytes())
        if self.message_path.name not in ('Item.msbt.zst','Item.msbt'):raise DataError('Select the English Item.msbt.zst message bank.')
        raw=self.message_path.read_bytes();self.message_sha256=digest(raw)
        text=messages(raw)
        if 'MIID_Materials' not in text or 'MIID_H_Materials' not in text:raise DataError('The selected Item message bank is missing the required templates.')
        self.catalog_paths={}
        for name in ('Ride','Skill'):
            for suffix in ('.msbt.zst','.msbt'):
                path=self.message_path.parent/(name+suffix)
                if path.is_file():self.catalog_paths[name]=path;break
        self.catalog_hashes={name:digest(path.read_bytes()) for name,path in self.catalog_paths.items()}
        self.enabled=False;self.prices={}

    @property
    def price(self):return self.prices.get(IID,1000)
    @property
    def move_price(self):return self.prices.get(MOVE_IID,3000)
    @property
    def modified(self):return self.enabled
    @property
    def changes(self):return {('buyable-mounts',0):deepcopy(self.prices)} if self.enabled else {}
    def snapshot_edits(self):return self.enabled,deepcopy(self.prices)
    def restore_edits(self,state):self.enabled,self.prices=deepcopy(state)
    def clear_edits(self):self.enabled=False;self.prices={}

    def configure_all(self,enabled,prices):
        from fw_editor import DataError
        if type(enabled) is not bool or not isinstance(prices,dict) or len(prices)>256:raise DataError('Invalid mount catalog settings.')
        if any(not isinstance(key,str) or not key.startswith(PREFIX) or len(key)>96 or type(value) is not int or not 1<=value<=65535 for key,value in prices.items()):raise DataError('Each mount price must be an integer from 1 to 65,535 gold with a valid offer ID.')
        self.enabled=enabled;self.prices=deepcopy(prices)

    def configure(self,enabled,price,move_price=None):
        # Old two-horse projects and API callers retain their price choices.
        if move_price is None:move_price=self.move_price
        self.configure_all(enabled,{**self.prices,IID:price,MOVE_IID:move_price})

    def project(self):
        return {'format':'cck-buyable-mounts-v3','source_file':FILENAME,'main_path':str(self.main_path),
                'main_sha256':MAIN_SHA256,'message_path':str(self.message_path),'message_sha256':self.message_sha256,
                'catalog_message_sha256':dict(self.catalog_hashes),'enabled':self.enabled,'prices':dict(self.prices)}

    def load_project(self,project):
        from fw_editor import DataError
        if not isinstance(project,dict) or project.get('format') not in ('cck-buyable-mounts-v1','cck-buyable-mounts-v2','cck-buyable-mounts-v3') or project.get('source_file')!=FILENAME or project.get('main_sha256')!=MAIN_SHA256 or project.get('message_sha256')!=self.message_sha256 or project.get('main_path')!=str(self.main_path) or project.get('message_path')!=str(self.message_path):raise DataError('Buyable mounts project does not match its original executable/messages.')
        if project['format']=='cck-buyable-mounts-v3':
            if project.get('catalog_message_sha256')!=self.catalog_hashes:raise DataError('The original Ride/Skill message sources differ from the saved mount project.')
            self.configure_all(project.get('enabled'),project.get('prices'));return
        price=project.get('price')
        if project['format']=='cck-buyable-mounts-v2':
            move_price=project.get('move_price')
            if type(move_price) is not int:raise DataError('Missing or invalid Move horse price.')
        else:move_price=min(65535,max(3000,price*3)) if type(price) is int else 3000
        self.configure(project.get('enabled'),price,move_price)

    def catalog_names(self):
        from fw_editor import DataError,messages
        if set(self.catalog_paths)!={'Ride','Skill'}:raise DataError('Keep the English Ride and Skill message banks beside the selected Item message bank.')
        result={}
        for name,path in self.catalog_paths.items():
            raw=path.read_bytes()
            if digest(raw)!=self.catalog_hashes[name]:raise DataError('The original '+name+' message bank changed. Re-select the source files before exporting.')
            result.update(messages(raw))
        return result


def prepare_project(documents,sources,project):
    from fw_editor import DataError
    payload=project.get('documents',{}) if isinstance(project,dict) else {}
    if not isinstance(payload,dict) or FILENAME not in payload:return
    data=payload[FILENAME]
    if not isinstance(data,dict) or not isinstance(data.get('main_path'),str) or not isinstance(data.get('message_path'),str):raise DataError('Invalid Buyable mounts project sources.')
    patch=MountPatch(data['main_path'],data['message_path']);patch.load_project(data)
    documents[MODULE]=patch;sources[MODULE]=patch.main_path


def source_tables(documents):
    from fw_editor import Item,Job,Skill,DataError
    def find(kind,name):return next((d for d in documents.values() if isinstance(d,kind) and d.filename==name),None)
    item=find(Item,'Item.bin');job=find(Job,'Job.bin');skills=find(Skill,'Skill.bin')
    if item is None or job is None or skills is None:raise DataError('Open the original Item.bin, Job.bin and Skill.bin tables before enabling Buyable mounts.')
    return item,job,skills


def catalog_for(documents,patch):
    from fw_editor import Binary
    _,job,skills=source_tables(documents)
    return catalog(Binary(job.build()),skills,patch.catalog_names())


def build_outputs(documents):
    from fw_editor import Item,DataError
    from message_append import append_messages
    patch=next((d for d in documents.values() if isinstance(d,MountPatch)),None)
    if patch is None or not patch.enabled:return {}
    validate_main(patch.main_path.read_bytes());bank=patch.message_path.read_bytes()
    if digest(bank)!=patch.message_sha256:raise DataError('The original Item message bank changed. Re-select it before exporting Buyable mounts.')
    item_source,_,_=source_tables(documents);offers=catalog_for(documents,patch)
    if set(patch.prices)-{o.iid for o in offers}:raise DataError('Saved prices refer to mount variants no longer present. Reset catalog prices or restore the matching data.')
    for d in documents.values():
        if isinstance(d,Item) and any(pid.startswith(PREFIX) for pid in d.by_pid):raise DataError('Reserved Buyable mounts IIDs already exist. Use original sources and let this patch generate them.')
    item=Item(item_source.build())
    for offer in offers:
        row=item.create_item(offer.iid);price=patch.prices.get(offer.iid,offer.default_price)
        for offset,value in {0x20:offer.name_key,0x30:offer.help_key,0x48:14,0x49:22,0x4c:price,0x50:0,0x150:49,0x1c0:'IconItem_クエスト'}.items():item.set(row,item.by_offset[offset],value)
    shops=item.views.get('shops');matches=[t for t in shops.collections if shops.names[t.pid]==SHOP] if shops else []
    if len(matches)!=1:raise DataError('The supported Dagsion item shop was not found uniquely.')
    table=matches[0];rows=shops.rows_by_table[table.pid]
    if not rows:raise DataError('The Dagsion item-shop layout is unsupported.')
    for offer in offers:
        price=patch.prices.get(offer.iid,offer.default_price)
        shops.append_entry(table.pid,{0x20:shops.value(rows[0],shops.by_offset[0x20]),0x28:offer.iid,
            0x38:['1部','カイ篇','5章以降','機能開放_厩舎'],0x48:[],0x58:[],0x68:price,0x6a:0,0x6b:0,0x6c:0})
    exported=item.build();check=Item(exported);native=[];additions=[]
    for offer in offers:
        index=struct.unpack_from('<H',check.raw,check.by_pid[offer.iid].offset+16)[0]
        native.append((index,offer.ride_index,offer.seed,offer.unique))
        description=offer.skill_name+' / '+offer.upgrade_name+' at the normal bond levels. Delivered to your stable; requires a free slot.'
        if offer.unique:description+=' One owned at a time.'
        additions.extend([(offer.name_key,offer.label,'MIID_Materials'),(offer.help_key,description,'MIID_H_Materials')])
    return {'romfs/GameData/Item.bin':exported,BANK_OUTPUT:append_messages(bank,additions),IPS_PATH:catalog_ips32(native)}
