"""Virtual JID definitions, typed baselines and direct class-link preservation."""
from copy import deepcopy
import re


def create_mixin(Record,DataError,FORMATS,TEXT_TYPES,LIST_TYPES):
    class ClassCreation:
        def __init__(self,raw):
            self.new_classes={}
            super().__init__(raw)
            self._source_records=list(self.records)

        @property
        def added_class_count(self):return len(self.new_classes)

        @property
        def modified(self):return bool(self.changes or self.new_classes)

        def _index_classes(self):
            self.records=[*self._source_records,*[Record(key,-1-i,len(self._source_records)+i) for i,key in enumerate(self.new_classes)]]
            self.by_pid={r.pid:r for r in self.records}

        def original(self,record,field):
            if record.pid in self.new_classes:return deepcopy(self.new_classes[record.pid][field.offset])
            return super().original(record,field)

        def record_changed(self,pid):return pid in self.new_classes or super().record_changed(pid)

        def snapshot_edits(self):return deepcopy((self.changes,self.new_classes))

        def restore_edits(self,state):
            self.changes,self.new_classes=deepcopy(state);self._index_classes()

        def clear_edits(self):
            self.changes={};self.new_classes={};self._index_classes()

        def _seed_values(self,key,values):
            if not isinstance(values,dict) or set(values)!=set(self.by_offset):raise DataError('New classes must provide every supported field.')
            row=self.by_pid[key]
            for offset,value in values.items():self.set(row,self.by_offset[offset],value)
            self.new_classes[key]={f.offset:self.value(row,f) for f in self.fields}
            self.changes={k:v for k,v in self.changes.items() if k[0]!=key}

        def create_class(self,key,copy_from=None,values=None):
            import struct
            if not isinstance(key,str) or not re.fullmatch(r'''JID_[^\s,;"'!&\x00]+''',key) or '::' in key:
                raise DataError('Enter a unique JID_ ID with a name, no whitespace, nulls, quotes, , ; ! & or :: separators.')
            if key in self.labels or key in self.by_pid:raise DataError('That ID already exists in Job.bin.')
            if len(self.records)>=65536:raise DataError('The class index exceeds the 16-bit format limit.')
            if max(struct.unpack_from('<H',self.raw,r.offset+22)[0] for r in self._source_records)+self.added_class_count+1>65535:
                raise DataError('No unused ascending class-header tags remain.')
            if copy_from is not None:
                if copy_from not in self.by_pid:raise DataError('Choose a current class to duplicate.')
                if values is not None:raise DataError('Choose either a class copy or explicit values.')
                values={f.offset:self.value(self.by_pid[copy_from],f) for f in self.fields}
            defaults={}
            for f in self.fields:
                if f.kind in FORMATS:defaults[f.offset]=0
                elif f.kind in TEXT_TYPES:defaults[f.offset]=''
                elif f.kind in LIST_TYPES:defaults[f.offset]=[]
                else:raise DataError('Unsupported new-class field type: '+f.kind)
            before=self.snapshot_edits()
            try:
                self.new_classes[key]=defaults;self._index_classes()
                self._seed_values(key,values if values is not None else defaults)
                return self.by_pid[key]
            except Exception:self.restore_edits(before);raise

        def remove_class(self,key):
            if key not in self.new_classes:raise DataError('Only newly created classes can be removed.')
            if any(self.value(r,f)==key for r in self.records if r.pid!=key for f in self.fields if f.kind=='ref'):
                raise DataError('Other class links refer to this class. Clear those links first.')
            self.changes={k:v for k,v in self.changes.items() if k[0]!=key}
            del self.new_classes[key];self._index_classes()

    return ClassCreation
