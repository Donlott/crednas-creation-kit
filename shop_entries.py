"""Append-only shop inventory rows and isolated, relocation-aware array growth."""
from copy import deepcopy
from bisect import bisect_left
import struct


def create_mixin(Record,DataError):
    class ShopEntries:
        @property
        def added_count(self):return sum(map(len,self.added_entries.values()))

        @property
        def modified(self):return self.owner.modified

        def _index_additions(self):
            self.rows_by_table={key:list(rows) for key,rows in self._source_rows.items()}
            self.names=dict(self._source_names);self._addition_values={}
            for table in self.collections:
                rows=self.rows_by_table[table.pid]
                for values in self.added_entries.get(table.pid,()):
                    row=Record(f'{table.pid}:{len(rows)}',-1-len(self._addition_values),len(rows))
                    rows.append(row);self._addition_values[row.pid]=values
                    self.names[row.pid]=self.names[table.pid]
            self.records=[r for t in self.collections for r in self.rows_by_table[t.pid]]
            self.by_pid={r.pid:r for r in self.records}
            self.row_location={r.pid:(t.pid,r.index) for t in self.collections for r in self.rows_by_table[t.pid]}

        def original(self,row,field):
            if row.pid in self._addition_values:return deepcopy(self._addition_values[row.pid][field.offset])
            return super().original(row,field)

        def snapshot_edits(self):return self.owner.snapshot_edits()
        def restore_edits(self,state):self.owner.restore_edits(state)

        def record_changed(self,pid):return pid in self._addition_values or super().record_changed(pid)

        def table_changed(self,key):return bool(self.added_entries.get(key)) or super().table_changed(key)

        def reset_table(self,key):
            super().reset_table(key);self.added_entries.pop(key,None);self._index_additions()

        def append_entry(self,key,values=None):
            if self.key!='shops' or key not in self.tables_by_id:raise DataError('Choose an existing shop inventory.')
            if len(self.rows_by_table[key])>=65535:raise DataError('Shop inventory exceeds the 16-bit entry-count limit.')
            if maximum_tag(self.owner)+self.owner.added_item_count+self.owner.added_count+1>65535:
                raise DataError('No unused ascending shop-entry header tags remain.')
            check_array(self.owner,self,key,DataError)
            defaults={f.offset:[] if f.kind.endswith('[]') else '' if f.kind in ('string','data') else 0 for f in self.fields}
            defaults[0x6b]=1
            if self._source_rows[key]:defaults[0x20]=self.value(self._source_rows[key][0],self.by_offset[0x20])
            if values is not None and (not isinstance(values,dict) or set(values)!=set(defaults)):
                raise DataError('A new shop entry must provide all nine supported fields.')
            before=self.owner.snapshot_edits()
            try:
                self.added_entries.setdefault(key,[]).append(deepcopy(defaults));self._index_additions()
                row=self.rows_by_table[key][-1]
                for offset,value in (defaults if values is None else values).items():self.set(row,self.by_offset[offset],value)
                self.validate_record(row)
                self.added_entries[key][-1]={f.offset:self.value(row,f) for f in self.fields}
                self.changes={k:v for k,v in self.changes.items() if k[0]!=row.pid}
                self._index_additions();return self.by_pid[row.pid]
            except Exception:self.owner.restore_edits(before);raise

        def duplicate_entry(self,row):
            if row.pid not in self.by_pid:raise DataError('Choose a current shop entry to duplicate.')
            row=self.by_pid[row.pid]
            return self.append_entry(self.row_location[row.pid][0],{f.offset:self.value(row,f) for f in self.fields})

        def remove_last_added(self,key):
            if self.key!='shops' or not self.added_entries.get(key):raise DataError('This shop has no additions to undo.')
            row=self.rows_by_table[key][-1];self.changes={k:v for k,v in self.changes.items() if k[0]!=row.pid}
            self.added_entries[key].pop()
            if not self.added_entries[key]:del self.added_entries[key]
            self._index_additions()

    return ShopEntries


def maximum_tag(owner):
    rows=list(owner._source_records)
    for view in owner.views.values():
        rows.extend(view.collections);rows.extend(r for entries in view._source_rows.values() for r in entries)
    return max((struct.unpack_from('<H',owner.raw,r.offset+22)[0] for r in rows),default=0)


def check_array(owner,view,key,DataError):
    """Indexed leaves or unexpected direct references need a different writer."""
    rows=view._source_rows[key]
    if not rows:return
    start=rows[0].offset-32;end=rows[-1].offset-32+view.stride
    if any(start<=at-32<end for at in owner.labels.values()):
        raise DataError('This shop has indexed leaf records; expansion of that layout is unsupported.')
    containers={t.offset-32+32 for t in view.collections}
    for slot in owner.pointers:
        value=struct.unpack_from('<Q',owner.raw,32+slot)[0]
        if start<=value<end and slot not in containers:
            raise DataError('This shop has direct references to its inventory rows; expansion of that layout is unsupported.')


def expanded_raw(owner,additions,DataError):
    """Copy only expanded inventories to new arrays; keep original data in place.

    Other shops, labels, and data-pointer targets retain their offsets. Existing
    array aliases are isolated. Every string pointer is rebased for the new pool.
    """
    view=owner.views.get('shops')
    if view is None:raise DataError('This item source has no supported shops.')
    body=bytearray(owner.raw[32:32+owner.size]);pool=owner.raw[32+owner.pool:]
    pointers={}
    for at in owner.pointers:
        value=struct.unpack_from('<Q',body,at)[0]
        pointers[at]=('string',value-owner.pool) if value>=owner.pool else ('data',value)
    next_tag=maximum_tag(owner)+1
    source_pointers=sorted(owner.pointers)
    if next_tag+sum(map(len,additions.values()))>65536:raise DataError('Shop-entry header tags exceed the format limit.')
    for key,values in additions.items():
        if key not in view.tables_by_id or not values:raise DataError('Invalid shop expansion plan.')
        check_array(owner,view,key,DataError)
        original=view.rows_by_table[key];amount=len(original)+len(values)
        if amount>65535:raise DataError('Shop inventory exceeds the 16-bit entry-count limit.')
        table=view.tables_by_id[key];header=table.offset-32
        body.extend(b'\0'*(-len(body)%8));start=len(body)
        template=original[0] if original else view.records[0] if view.records else None
        source_rows=[*original,*([template]*len(values))]
        for index,row in enumerate(source_rows):
            at=len(body)
            if row is None:
                body.extend(b'\0'*view.stride)
                struct.pack_into('<H',body,at+20,1)
                for offset,width in ((0x38,8),(0x48,16),(0x58,1)):struct.pack_into('<H',body,at+offset+2,width)
            else:
                source=row.offset-32;body.extend(owner.raw[row.offset:row.offset+view.stride])
                for slot in source_pointers[bisect_left(source_pointers,source):bisect_left(source_pointers,source+view.stride)]:
                    pointers[at+slot-source]=pointers[slot]
            if index>=len(original):
                struct.pack_into('<HH',body,at+16,index,1);struct.pack_into('<H',body,at+22,next_tag);next_tag+=1
                # Row header names belong to the destination shop, not the template.
                pointers[at+8]=pointers[header+8]
        struct.pack_into('<H',body,header+18,amount);pointers[header+32]=('data',start)
    order=list(owner.pointers);order.extend(sorted(set(pointers)-set(order)))
    new_pool=len(body)+8*len(order)+len(owner.label_bytes);size=32+new_pool+len(pool)
    if size>=1<<32:raise DataError('Expanded shop data exceeds the file-size limit.')
    for at,(kind,value) in pointers.items():struct.pack_into('<Q',body,at,value+new_pool if kind=='string' else value)
    header=bytearray(owner.raw[:32]);struct.pack_into('<4I',header,0,size,len(body),len(order),len(owner.label_bytes)//8)
    return bytes(header+body+struct.pack('<'+str(len(order))+'Q',*order)+owner.label_bytes+pool)
