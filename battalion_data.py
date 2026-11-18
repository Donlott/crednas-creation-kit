"""Opt-in direct battalion purchases, composed with the existing mount export."""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
from pathlib import Path
import struct

from mount_native import MAIN_SHA256,IPS_PATH,validate_main,encode_ips
from mount_data import BANK_OUTPUT,SHOP,digest
from battalion_native import MAX_OFFERS,patch_records

MODULE='Patch · Buyable battalions'
FILENAME='CCK/Buyable-battalions.json'
PREFIX='IID_CCK_BuyBattalion_'


@dataclass(frozen=True)
class BattalionOffer:
    iid:str
    lid:str
    legion_index:int
    name:str
    gambit:str
    troops:int
    command:int
    default_price:int
    @property
    def name_key(self):return 'MIID_'+self.iid.removeprefix('IID_')
    @property
    def help_key(self):return 'MIID_H_'+self.iid.removeprefix('IID_')


def catalog(legion,skills,names):
    from fw_editor import DataError
    result=[]
    for r in legion.records:
        v=lambda o:legion.value(r,legion.by_offset[o])
        # Civilian crowds, no-battalion and empty event placeholders are not
        # recruitable combat battalions. Do not infer eligibility from a name.
        if v(0xb0)!='VID_軍団兵' or not v(0x31) or not v(0x38):continue
        index=struct.unpack_from('<H',legion.raw,r.offset+16)[0]
        if not 1<=index<=255:raise DataError('A battalion index exceeds the native saved-byte range: '+r.pid)
        key=v(0x20)
        if key not in names or not names[key].strip():raise DataError('The English Legion message bank is missing '+key+'.')
        skill=skills.by_pid.get(v(0x38))
        if skill is None:raise DataError('A battalion refers to a missing gambit: '+v(0x38))
        gambit_key=skills.value(skill,skills.by_offset[0x20])
        if gambit_key not in names:raise DataError('The English Skill message bank is missing '+gambit_key+'.')
        iid=PREFIX+hashlib.sha256(r.pid.encode('utf8')).hexdigest()[:16]
        result.append(BattalionOffer(iid,r.pid,index,names[key],names[gambit_key],v(0x31),v(0x32),max(1,v(0x98))))
    if not 1<=len(result)<=MAX_OFFERS:raise DataError('The supported battalion catalog must contain 1 to 100 combat battalions.')
    if len({o.iid for o in result})!=len(result):raise DataError('Battalion offer IDs collide.')
    return result


class BattalionPatch:
    filename=FILENAME;records=();fields=();views={};names={};prefix='PATCH_'
    def __init__(self,main_path,message_path):
        from fw_editor import DataError,messages
        self.main_path=Path(main_path).resolve();self.message_path=Path(message_path).resolve()
        try:validate_main(self.main_path.read_bytes())
        except DataError as exc:raise DataError(str(exc).replace('Buyable mounts','Buyable battalions')) from exc
        if self.message_path.name not in ('Item.msbt','Item.msbt.zst'):raise DataError('Select the English Item message bank.')
        bank=self.message_path.read_bytes();self.message_sha256=digest(bank);text=messages(bank)
        if not {'MIID_Materials','MIID_H_Materials'}<=text.keys():raise DataError('The Item bank is missing the required templates.')
        self.catalog_paths={}
        for name in ('Legion','Skill'):
            for suffix in ('.msbt.zst','.msbt'):
                path=self.message_path.parent/(name+suffix)
                if path.is_file():self.catalog_paths[name]=path;break
        self.catalog_hashes={k:digest(p.read_bytes()) for k,p in self.catalog_paths.items()}
        self.enabled=False;self.prices={};self.disabled=set();self.limits={}
    @property
    def modified(self):return self.enabled
    @property
    def changes(self):return {('buyable-battalions',0):self.snapshot_edits()} if self.enabled else {}
    def snapshot_edits(self):return self.enabled,deepcopy(self.prices),set(self.disabled),deepcopy(self.limits)
    def restore_edits(self,state):self.enabled,self.prices,self.disabled,self.limits=deepcopy(state)
    def clear_edits(self):self.enabled=False;self.prices={};self.disabled=set();self.limits={}
    def configure_all(self,enabled,prices,disabled=None,limits=None):
        from fw_editor import DataError
        disabled=self.disabled if disabled is None else disabled;limits=self.limits if limits is None else limits
        valid=lambda k:isinstance(k,str) and k.startswith(PREFIX) and len(k)<=96
        if type(enabled) is not bool or not isinstance(prices,dict) or len(prices)>MAX_OFFERS or any(not valid(k) or type(v) is not int or not 1<=v<=65535 for k,v in prices.items()):raise DataError('Battalion prices must be integers from 1 to 65,535 gold.')
        if not isinstance(disabled,(list,tuple,set)) or len(disabled)>MAX_OFFERS or any(not valid(k) for k in disabled):raise DataError('Invalid disabled battalion offers.')
        if not isinstance(limits,dict) or len(limits)>MAX_OFFERS or any(not valid(k) or type(v) is not int or not 1<=v<=127 for k,v in limits.items()):raise DataError('Battalion chapter limits must be 1–127; use 0 in the menu for unlimited.')
        self.enabled=enabled;self.prices=deepcopy(prices);self.disabled=set(disabled);self.limits=deepcopy(limits)
    def project(self):
        return {'format':'cck-buyable-battalions-v1','source_file':FILENAME,'main_path':str(self.main_path),'main_sha256':MAIN_SHA256,
                'message_path':str(self.message_path),'message_sha256':self.message_sha256,'catalog_message_sha256':dict(self.catalog_hashes),
                'enabled':self.enabled,'prices':dict(self.prices),'disabled':sorted(self.disabled),'limits':dict(self.limits)}
    def load_project(self,project):
        from fw_editor import DataError
        expected=self.project()
        keys=('format','source_file','main_path','main_sha256','message_path','message_sha256','catalog_message_sha256')
        if not isinstance(project,dict) or any(project.get(k)!=expected[k] for k in keys):raise DataError('Buyable battalions project does not match its original sources.')
        disabled=project.get('disabled')
        if not isinstance(disabled,list) or any(not isinstance(k,str) for k in disabled) or len(disabled)!=len(set(disabled)) or not isinstance(project.get('limits'),dict):raise DataError('Invalid battalion availability settings.')
        self.configure_all(project.get('enabled'),project.get('prices'),disabled,project.get('limits'))
    def catalog_names(self):
        from fw_editor import DataError,messages
        if set(self.catalog_paths)!={'Legion','Skill'}:raise DataError('Keep the English Legion and Skill message banks beside Item.')
        result={}
        for name,path in self.catalog_paths.items():
            raw=path.read_bytes()
            if digest(raw)!=self.catalog_hashes[name]:raise DataError('The original '+name+' message bank changed. Re-select the sources.')
            result.update(messages(raw))
        return result


def prepare_project(documents,sources,project):
    from fw_editor import DataError
    data=project.get('documents',{}).get(FILENAME) if isinstance(project,dict) and isinstance(project.get('documents',{}),dict) else None
    if data is None:return
    if not isinstance(data,dict) or not isinstance(data.get('main_path'),str) or not isinstance(data.get('message_path'),str):raise DataError('Invalid Buyable battalions project sources.')
    patch=BattalionPatch(data['main_path'],data['message_path']);patch.load_project(data)
    documents[MODULE]=patch;sources[MODULE]=patch.main_path


def source_tables(documents):
    from fw_editor import Item,Legion,Skill,DataError
    result=[]
    for kind in (Item,Legion,Skill):
        found=[d for d in documents.values() if d.filename==kind.filename]
        if len(found)!=1 or not isinstance(found[0],kind):raise DataError('Buyable battalions needs the original '+kind.filename+'. Open the game data folder first.')
        result.append(found[0])
    return tuple(result)


def load_sources(documents,sources,base):
    from fw_editor import Item,Legion,Skill
    from mount_data import load_sources as load
    return load(documents,sources,base,required=(('Items',Item),('Legion',Legion),('Skills',Skill)),label='Buyable battalions')


def catalog_for(documents,patch):
    _,legion,skills=source_tables(documents)
    from fw_editor import Legion
    return catalog(Legion(legion.build()),skills,patch.catalog_names())


def decode_ips(raw):
    from fw_editor import DataError
    if raw[:5]!=b'IPS32' or raw[-4:]!=b'EEOF':raise DataError('Invalid generated vendor patch.')
    records=[];pos=5
    while pos<len(raw)-4:
        if pos+6>len(raw)-4:raise DataError('Truncated generated vendor patch.')
        address,size=struct.unpack_from('>IH',raw,pos);pos+=6
        if not size or address<0x100 or pos+size>len(raw)-4:raise DataError('Unsupported generated vendor patch record.')
        records.append((address-0x100,raw[pos:pos+size]));pos+=size
    if pos!=len(raw)-4:raise DataError('Invalid generated vendor patch end.')
    return records


def build_outputs(documents):
    """Compose both opt-in patches into ONE item table, message bank and IPS."""
    from fw_editor import Item,DataError
    from mount_data import build_mount_outputs,MountPatch
    from mount_native import DESTINATION_HOOK,DELIVERY_HOOK
    from message_append import append_messages
    output=build_mount_outputs(documents)
    patch=next((d for d in documents.values() if isinstance(d,BattalionPatch)),None)
    if patch is None or not patch.enabled:return output
    validate_main(patch.main_path.read_bytes())
    original=patch.message_path.read_bytes()
    if digest(original)!=patch.message_sha256:raise DataError('The original Item message bank changed. Re-select the sources.')
    mount=next((d for d in documents.values() if isinstance(d,MountPatch) and d.enabled),None)
    if mount and (mount.main_path!=patch.main_path or mount.message_sha256!=patch.message_sha256 or mount.message_path!=patch.message_path):raise DataError('Buyable mounts and battalions must use the same original executable and Item message bank.')
    item_source,_,_=source_tables(documents);offers=catalog_for(documents,patch)
    if (set(patch.prices)|patch.disabled|set(patch.limits))-{o.iid for o in offers}:raise DataError('Saved settings refer to battalions no longer in the source catalog.')
    if any(pid.startswith(PREFIX) for doc in documents.values() if isinstance(doc,Item) for pid in doc.by_pid):raise DataError('Reserved battalion purchase items already exist. Use original sources.')
    path='romfs/GameData/Item.bin';item=Item(output.get(path,item_source.build()))
    if not {0x20,0x30,0x48,0x49,0x4c,0x50,0x150,0x1c0}<=item.by_offset.keys():raise DataError('The item table does not have the supported purchase-item fields.')
    shops=item.views.get('shops');tables=[t for t in shops.collections if shops.names[t.pid]==SHOP] if shops else []
    if len(tables)!=1 or not shops.rows_by_table[tables[0].pid]:raise DataError('The supported Dagsion item shop was not found uniquely.')
    table=tables[0];shop_name=shops.value(shops.rows_by_table[table.pid][0],shops.by_offset[0x20])
    additions=[]
    for offer in offers:
        row=item.create_item(offer.iid);price=patch.prices.get(offer.iid,offer.default_price)
        for offset,value in {0x20:offer.name_key,0x30:offer.help_key,0x48:14,0x49:22,0x4c:price,0x50:0,0x150:49,0x1c0:'IconItem_クエスト'}.items():item.set(row,item.by_offset[offset],value)
        conditions=['1部','セオドラ篇','4章以降','機能開放_軍団兵舎']
        if offer.iid in patch.disabled:conditions.append('!セオドラ篇')
        limit=patch.limits.get(offer.iid,0)
        shops.append_entry(table.pid,{0x20:shop_name,0x28:offer.iid,0x38:conditions,0x48:[],0x58:[],0x68:price,0x6a:0,0x6b:limit,0x6c:limit})
        additions.extend([(offer.name_key,'Battalion: '+offer.name,'MIID_Materials'),
                          (offer.help_key,f'{offer.gambit}. Delivered directly to your barracks; requires a free battalion slot. Normal command and equipment requirements still apply.','MIID_H_Materials')])
    exported=item.build();check=Item(exported)
    native=[(struct.unpack_from('<H',check.raw,check.by_pid[o.iid].offset+16)[0],o.legion_index) for o in offers]
    hooks=patch_records(native,mounts=bool(mount))
    records=decode_ips(output[IPS_PATH]) if IPS_PATH in output else []
    records=[r for r in records if r[0] not in (DESTINATION_HOOK,DELIVERY_HOOK)]+hooks
    ordered=sorted(records)
    if any(a+len(raw)>b for (a,raw),(b,_) in zip(ordered,ordered[1:])):raise DataError('Generated mount and battalion code overlaps.')
    output.update({path:exported,BANK_OUTPUT:append_messages(output.get(BANK_OUTPUT,original),additions),IPS_PATH:encode_ips(ordered)})
    return output
