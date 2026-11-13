"""Auxiliary shop/lottery/value views share their existing Item.bin owner."""
import struct

SECTIONS={
 'shops':('Shops','店',112,9,2),
 'loot':('Loot lotteries','抽選',72,3,2),
 'values':('Value tiers','価値',40,2,1),
}
EXPECTED={
 'shops':{0x20:('string',8),0x28:('data',16),0x38:('string[]',16),0x48:('data[]',16),0x58:('u8[]',16),0x68:('u16',2),0x6a:('s8',1),0x6b:('u8',1),0x6c:('u8',1)},
 'loot':{0x20:('data',16),0x30:('u16',2),0x38:('string[]',16)},
 'values':{0x20:('u16',2),0x22:('u16',2)},
}


def create_model(CollectionTable,Field,Record,DataError):
    from shop_entries import create_mixin
    ShopEntries=create_mixin(Record,DataError)
    class ShopView(ShopEntries,CollectionTable):
        prefix='SHOP_';locked_offsets=frozenset()
        def __init__(self,owner,key,group):
            self.owner=owner;self.key=key;self.title,self.group_name,_,_,self.container=SECTIONS[key]
            self.filename=owner.filename;self.raw=owner.raw;self.size=owner.size;self.pool=owner.pool
            self.labels=owner.labels;self.label_at=owner.label_at;self.stride,count,schema=group[1:]
            self.fields=[]
            for i in range(count):
                n,k,_,size,offset=struct.unpack_from('<QQQII',self.raw,schema+i*32)
                self.fields.append(Field(self.string(n),self.string(k),size,offset))
            self.by_offset={f.offset:f for f in self.fields}
            if len(self.by_offset)!=count or {f.offset:(f.kind,f.size) for f in self.fields}!=EXPECTED[key]:
                raise DataError('Unsupported '+self.filename+' '+self.title+' layout.')
            self.collections=[];self.records=[];self.names={};self.rows_by_table={};self.row_location={};self.collection_offsets=[]
            self.added_entries={};self._addition_values={}
            start=schema+count*32
            def append(at,index,table):
                if at<32 or at+self.stride>32+self.size or struct.unpack_from('<HH',self.raw,at+16)!=(index,1):
                    raise DataError('Shop/loot entry header differs from the supported layout.')
                pid=f'{table}:{index}' if self.container==2 else f'{key}:{index}'
                row=Record(pid,at,index);self.records.append(row);self.rows_by_table[table].append(row)
                self.names[pid]=self.string(struct.unpack_from('<Q',self.raw,at+8)[0]);self.row_location[pid]=(table,index)
            if self.container==1:
                table=f'{key}:all';self.collections=[Record(table,start,0)];self.names[table]=self.title;self.rows_by_table[table]=[]
                for index in range(65536):
                    at=start+index*self.stride
                    if at+self.stride>32+self.size or struct.unpack_from('<HH',self.raw,at+16)!=(index,1):break
                    append(at,index,table)
            else:
                for index in range(65536):
                    at=start+index*48
                    if at+48>32+self.size or struct.unpack_from('<H',self.raw,at+16)[0]!=index:break
                    amount=struct.unpack_from('<H',self.raw,at+18)[0];pointer=struct.unpack_from('<Q',self.raw,at+32)[0]
                    name=self.string(struct.unpack_from('<Q',self.raw,at+8)[0])
                    if not name or self.labels.get(name)!=at:raise DataError('Shop/loot collection identity differs from the supported layout.')
                    if amount and (not pointer or pointer+amount*self.stride>self.size):raise DataError('Shop/loot entries are outside the data.')
                    table=f'{key}:{index}';self.collections.append(Record(table,at,index));self.collection_offsets.append(at)
                    self.names[table]=name;self.rows_by_table[table]=[]
                    for row in range(amount):append(pointer+32+row*self.stride,row,table)
            if not self.collections:raise DataError('No supported shop/loot collections were found.')
            self.by_pid={r.pid:r for r in self.records};self.tables_by_id={r.pid:r for r in self.collections}
            self._source_rows={key:list(rows) for key,rows in self.rows_by_table.items()};self._source_names=dict(self.names)
            for row in self.records:
                for field in self.fields:self.original(row,field)
        @property
        def changes(self):return self.owner.changes
        @changes.setter
        def changes(self,value):self.owner.changes=value
        def build(self):return self.owner.build()
        def validate_record(self,row):
            if self.key=='shops' and len(self.value(row,self.by_offset[0x48]))!=len(self.value(row,self.by_offset[0x58])):
                raise DataError('Exchange item and quantity lists must have the same number of entries.')
    return ShopView
