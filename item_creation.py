"""Virtual primary IID records and relocation-preserving item expansion."""
from copy import deepcopy
import re
import struct


def create_mixin(Record,DataError,FORMATS,TEXT_TYPES,ARRAY_TYPES):
    class ItemCreation:
        def __init__(self,raw):
            self.new_items={}
            super().__init__(raw)
            self._source_records=list(self.records)

        @property
        def added_item_count(self):return len(self.new_items)

        @property
        def modified(self):return bool(self.changes or self.new_items)

        def _index_items(self):
            self.records=[*self._source_records,*[Record(key,-1-i,len(self._source_records)+i) for i,key in enumerate(self.new_items)]]
            self.by_pid={r.pid:r for r in self.records}

        def original(self,record,field):
            if record.pid in self.new_items:return deepcopy(self.new_items[record.pid][field.offset])
            return super().original(record,field)

        def record_changed(self,pid):return pid in self.new_items or super().record_changed(pid)

        def snapshot_edits(self):return deepcopy((self.changes,self.new_items))

        def restore_edits(self,state):
            self.changes,self.new_items=deepcopy(state);self._index_items()

        def clear_edits(self):
            self.changes={};self.new_items={};self._index_items()

        def create_item(self,key,copy_from=None,values=None):
            if not isinstance(key,str) or not key.startswith('IID_') or len(key)==4 or not re.fullmatch(r'''IID_[^\s,;"'!&\x00]+''',key) or '::' in key:
                raise DataError('Enter a unique IID_ ID without whitespace, nulls, quotes, separators (, ; ! &) or ::. Literal pipe suffixes are allowed.')
            if key in self.labels or key in self.by_pid:raise DataError('That ID already exists in this item file.')
            if len(self.records)>=65536:raise DataError('The item index exceeds the 16-bit format limit.')
            tags=[struct.unpack_from('<H',self.raw,r.offset+22)[0] for r in self._source_records]
            if max(tags,default=0)+self.added_item_count+1>65535:raise DataError('No unused ascending item-header tags remain.')
            if copy_from is not None:
                if copy_from not in self.by_pid:raise DataError('Choose a current item to duplicate.')
                if values is not None:raise DataError('Choose either an item copy or explicit values.')
                values={f.offset:self.value(self.by_pid[copy_from],f) for f in self.fields}
            defaults={}
            for f in self.fields:
                if f.kind in FORMATS:defaults[f.offset]=0
                elif f.kind in TEXT_TYPES:defaults[f.offset]=''
                elif f.kind in ARRAY_TYPES:defaults[f.offset]=[]
                else:raise DataError('Unsupported new-item field type: '+f.kind)
            if values is not None and (not isinstance(values,dict) or set(values)!=set(defaults)):
                raise DataError('A new item must provide every supported item field.')
            before=self.snapshot_edits()
            try:
                self.new_items[key]=defaults;self._index_items();record=self.by_pid[key]
                for offset,value in (values or defaults).items():self.set(record,self.by_offset[offset],value)
                self.new_items[key]={f.offset:self.value(record,f) for f in self.fields}
                self.changes={k:v for k,v in self.changes.items() if k[0]!=key};self._index_items()
                return self.by_pid[key]
            except Exception:self.restore_edits(before);raise

        def remove_item(self,key):
            if key not in self.new_items:raise DataError('Only newly created items can be removed.')
            self.changes={k:v for k,v in self.changes.items() if k[0]!=key}
            del self.new_items[key];self._index_items()

    return ItemCreation


def expanded_raw(doc,DataError):
    from record_expansion import expanded_raw as expand_records
    return expand_records(doc,DataError,doc.new_items)
