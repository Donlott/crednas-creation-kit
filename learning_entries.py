"""Append-only learning entries and relocation-preserving Growth expansion.

New rows use unused header tags; their runtime meaning is not yet established.
Existing tags, collection identities, row ordinals and opaque bytes are preserved.
"""
from bisect import bisect_right
from copy import deepcopy
import struct


def create_mixin(Record, DataError):
    class LearningEntries:
        def __init__(self, raw):
            self.added_entries = {}
            self.new_lists = []
            self._addition_values = {}
            super().__init__(raw)
            self._source_collections = list(self.collections)
            self._source_rows = {key:list(rows) for key,rows in self.rows_by_table.items()}

        @property
        def added_count(self):
            return sum(map(len,self.added_entries.values()))

        @property
        def added_list_count(self):return len(self.new_lists)

        @property
        def modified(self):
            return bool(self.changes or self.added_count or self.new_lists)

        def _index_additions(self):
            self.collections=[*self._source_collections,*[
                Record(key,-1-i,len(self._source_collections)+i) for i,key in enumerate(self.new_lists)]]
            self.tables_by_id={table.pid:table for table in self.collections}
            self.rows_by_table = {key:list(rows) for key,rows in self._source_rows.items()}
            self.rows_by_table.update({key:[] for key in self.new_lists})
            self._addition_values = {}
            for table in self.collections:
                rows=self.rows_by_table[table.pid]
                for values in self.added_entries.get(table.pid,()):
                    row=Record(f'{table.pid}::{len(rows)}',-1-len(self._addition_values),len(rows))
                    rows.append(row);self._addition_values[row.pid]=values
            self.records=[r for table in self.collections for r in self.rows_by_table[table.pid]]
            self.by_pid={r.pid:r for r in self.records}
            self.row_location={r.pid:(table.pid,r.index) for table in self.collections for r in self.rows_by_table[table.pid]}

        def original(self, record, field):
            if record.pid in self._addition_values:
                return deepcopy(self._addition_values[record.pid][field.offset])
            return super().original(record,field)

        def snapshot_edits(self):
            return deepcopy((self.changes,self.added_entries,self.new_lists))

        def restore_edits(self, state):
            self.changes,self.added_entries,self.new_lists=deepcopy(state)
            self._index_additions()

        def clear_edits(self):
            self.changes={};self.added_entries={};self.new_lists=[];self._index_additions()

        def table_changed(self, key):
            return key in self.new_lists or bool(self.added_entries.get(key)) or super().table_changed(key)

        def reset_table(self, key):
            super().reset_table(key)
            self.added_entries.pop(key,None);self._index_additions()

        def _check_tags(self, extra):
            tags=[struct.unpack_from('<H',self.raw,r.offset+22)[0]
                  for r in [*self._source_collections,*[r for rows in self._source_rows.values() for r in rows]]]
            if max(tags,default=0)+self.added_count+self.added_list_count+extra>65535:
                raise DataError('No unused ascending learning-row header tags remain.')

        def _check_capacity(self, key):
            if key not in self.tables_by_id:raise DataError('Choose a current learning list.')
            if len(self.rows_by_table[key])>=65535:raise DataError('The learning-list count exceeds the 16-bit format limit.')
            self._check_tags(1)

        def create_list(self, key, copy_from=None):
            if not isinstance(key,str) or not key.startswith('LID_') or not key[4:].strip() or key!=key.strip() or any(c in key for c in '\0\r\n') or '::' in key:
                raise DataError('Enter a unique LID_ ID with a name, no surrounding whitespace, line breaks or :: separator.')
            if key in self.labels or key in self.tables_by_id:raise DataError('That ID already exists in Growth.bin.')
            if len(self.collections)>=65535:raise DataError('The learning-list index exceeds the 16-bit format limit.')
            if copy_from is not None and copy_from not in self.tables_by_id:raise DataError('Choose a current learning list to duplicate.')
            values=[{f.offset:self.value(row,f) for f in self.fields} for row in self.rows_by_table[copy_from]] if copy_from is not None else []
            self._check_tags(1+len(values));before=self.snapshot_edits()
            try:
                self.new_lists.append(key);self._index_additions()
                for value in values:self.append_entry(key,value)
                return self.tables_by_id[key]
            except Exception:self.restore_edits(before);raise

        def remove_list(self, key):
            if key not in self.new_lists:raise DataError('Only a newly created learning list can be removed.')
            self.changes={k:v for k,v in self.changes.items() if self.row_location.get(k[0],(None,))[0]!=key}
            self.added_entries.pop(key,None);self.new_lists.remove(key);self._index_additions()

        def append_entry(self, key, values=None):
            self._check_capacity(key)
            defaults={0x20:1,0x21:0,0x22:0,0x28:'',0x38:[]}
            if values is not None and (not isinstance(values,dict) or set(values)!=set(defaults)):
                raise DataError('A new learning entry must provide all five supported fields.')
            state=self.snapshot_edits()
            try:
                self.added_entries.setdefault(key,[]).append(deepcopy(defaults))
                self._index_additions();row=self.rows_by_table[key][-1]
                for offset,value in (values or defaults).items():self.set(row,self.by_offset[offset],value)
                self.added_entries[key][-1]={f.offset:self.value(row,f) for f in self.fields}
                for field in self.fields:self.changes.pop((row.pid,field.offset),None)
                self._index_additions()
                return self.by_pid[row.pid]
            except Exception:
                self.restore_edits(state);raise

        def duplicate_entry(self, row):
            if row.pid not in self.by_pid:raise DataError('Choose a current learning entry to duplicate.')
            return self.append_entry(self.row_location[row.pid][0],{f.offset:self.value(row,f) for f in self.fields})

        def remove_last_added(self, key):
            if not self.added_entries.get(key):raise DataError('This list has no additions to undo.')
            row=self.rows_by_table[key][-1]
            self.changes={k:v for k,v in self.changes.items() if k[0]!=row.pid}
            self.added_entries[key].pop()
            if not self.added_entries[key]:del self.added_entries[key]
            self._index_additions()

    return LearningEntries


def expanded_raw(doc, DataError):
    """Insert new headers and rows once, preserving all original indexed objects."""
    source=doc.raw[32:32+doc.size];pool=bytearray(doc.raw[32+doc.pool:])
    originals=[r for rows in doc._source_rows.values() for r in rows]
    header_end=doc._source_collections[-1].offset-32+48
    first_leaf=min((r.offset-32 for r in originals),default=header_end)
    last_leaf=max((r.offset-32+doc.stride for r in originals),default=header_end)
    template=originals[0] if originals else None
    template_at=template.offset-32 if template else None
    template_bytes=source[template_at:template_at+doc.stride] if template else bytes(doc.stride)
    container_at=doc._source_collections[0].offset-32
    container_bytes=source[container_at:container_at+48]
    def slots(at,width):return [p for p in doc.pointers if at is not None and at<=p<at+width]
    template_pointers=slots(template_at,doc.stride);container_pointers=slots(container_at,48)
    next_tag=max((struct.unpack_from('<H',doc.raw,r.offset+22)[0] for r in [*doc._source_collections,*originals]),default=0)+1
    names={};plans={}
    # Headers must remain contiguous immediately after the original header array.
    for key in doc.new_lists:
        names[key]=len(pool);pool.extend(key.encode('utf8')+b'\0')
        plans.setdefault(header_end,[]).append(('table',doc.tables_by_id[key],next_tag));next_tag+=1
    for table in doc.collections:
        additions=doc.added_entries.get(table.pid,())
        if not additions:continue
        rows=doc._source_rows.get(table.pid,())
        at=last_leaf if table.pid in doc.new_lists else rows[-1].offset-32+doc.stride if rows else first_leaf
        for i,_ in enumerate(additions):
            plans.setdefault(at,[]).append(('row',(table,len(rows)+i),next_tag));next_tag+=1
    if next_tag>65536:raise DataError('New learning header tags exceed the 16-bit format limit.')
    positions=sorted(plans);totals=[];total=0
    for at in positions:
        total+=sum(48 if kind=='table' else doc.stride for kind,_,_ in plans[at]);totals.append(total)
    def moved(at):
        n=bisect_right(positions,at)
        return at+(totals[n-1] if n else 0)
    body=bytearray();cursor=0;starts={};new_headers=[];new_rows=[]
    for at in positions:
        body.extend(source[cursor:at])
        for kind,entry,tag in plans[at]:
            start=len(body)
            if kind=='table':
                table=entry;starts[table.pid]=start;new_headers.append((table,start))
                body.extend(container_bytes)
                struct.pack_into('<4H',body,start+16,table.index,len(doc.rows_by_table[table.pid]),0,tag)
                struct.pack_into('<Q',body,start+32,0)
            else:
                table,index=entry;starts[f'{table.pid}::{index}']=start;new_rows.append((table,start))
                body.extend(template_bytes);struct.pack_into('<4H',body,start+16,index,1,1,tag)
                if template is None:struct.pack_into('<HHIQ',body,start+0x38,0,8,0,0)
        cursor=at
    body.extend(source[cursor:]);pointers={}
    def target(at):
        value=struct.unpack_from('<Q',source,at)[0]
        return ('string',value-doc.pool) if value>=doc.pool else ('data',moved(value))
    for at in doc.pointers:pointers[moved(at)]=target(at)
    def name_target(table):
        return ('string',names[table.pid]) if table.pid in names else target(table.offset-32+8)
    for table,start in new_headers:
        for at in container_pointers:pointers[start+at-container_at]=target(at)
        pointers[start+8]=name_target(table);pointers.pop(start+32,None)
        if doc.rows_by_table[table.pid]:pointers[start+32]=('data',starts[f'{table.pid}::0'])
    for table,start in new_rows:
        for at in template_pointers:pointers[start+at-template_at]=target(at)
        pointers[start+8]=name_target(table)
    for table in doc._source_collections:
        additions=doc.added_entries.get(table.pid,())
        if not additions:continue
        rows=doc._source_rows[table.pid];at=moved(table.offset-32)
        struct.pack_into('<H',body,at+18,len(rows)+len(additions))
        if not rows:pointers[at+32]=('data',starts[f'{table.pid}::0'])
    order=[moved(at) for at in doc.pointers];order.extend(sorted(set(pointers)-set(order)))
    labels=[];inserted=False
    additions=[(starts[key],names[key]) for key in doc.new_lists]
    for at,name in struct.iter_unpack('<II',doc.label_bytes):
        if not inserted and at>=header_end:labels.extend(additions);inserted=True
        labels.append((moved(at),name))
    if not inserted:labels.extend(additions)
    new_pool=len(body)+len(order)*8+len(labels)*8;total_size=32+new_pool+len(pool)
    if total_size>=1<<32:raise DataError('Expanded Growth.bin exceeds the format size limit.')
    for at,(kind,value) in pointers.items():struct.pack_into('<Q',body,at,value+new_pool if kind=='string' else value)
    header=bytearray(doc.raw[:32]);struct.pack_into('<4I',header,0,total_size,len(body),len(order),len(labels))
    return bytes(header+body+struct.pack('<'+str(len(order))+'Q',*order)+b''.join(struct.pack('<II',*label) for label in labels)+pool)
