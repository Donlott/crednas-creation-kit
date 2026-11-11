"""Append-only characters with immutable source slots and creation-time serials."""
from copy import deepcopy
import re
import struct


def create_mixin(Record,DataError,FORMATS,TEXT_TYPES,LIST_TYPES):
    class CharacterCreation:
        def __init__(self,raw):
            self.new_characters={};super().__init__(raw);self._source_records=list(self.records)

        @property
        def added_character_count(self):return len(self.new_characters)

        @property
        def modified(self):return bool(self.changes or self.new_characters)

        def _index_characters(self):
            self.records=[*self._source_records,*[Record(key,-1-i,len(self._source_records)+i) for i,key in enumerate(self.new_characters)]]
            self.by_pid={r.pid:r for r in self.records}

        def original(self,record,field):
            if record.pid in self.new_characters:return deepcopy(self.new_characters[record.pid][field.offset])
            return super().original(record,field)

        def record_changed(self,pid):return pid in self.new_characters or super().record_changed(pid)

        def snapshot_edits(self):return deepcopy((self.changes,self.new_characters))

        def restore_edits(self,state):self.changes,self.new_characters=deepcopy(state);self._index_characters()

        def clear_edits(self):self.changes={};self.new_characters={};self._index_characters()

        def available_serials(self):
            used={self.value(r,self.by_offset[0x30]) for r in self.records}
            return [i for i in range(1,256) if i not in used]

        def _validate_serial(self,serial,key=None):
            if type(serial) is not int or not 0<=serial<=255:raise DataError('Character serial must be an integer from 0 to 255.')
            if serial and any(r.pid!=key and self.value(r,self.by_offset[0x30])==serial for r in self.records):
                raise DataError('That nonzero character serial is already used. Choose an unused serial, or zero for an unnumbered entry.')

        def _seed_character(self,key,values):
            if not isinstance(values,dict) or set(values)!=set(self.by_offset):raise DataError('New characters must provide every supported field.')
            serial=values[0x30];self._validate_serial(serial,key)
            if serial!=self.new_characters[key][0x30]:raise DataError('The creation-time character serial cannot change.')
            row=self.by_pid[key]
            for off,value in values.items():
                if off!=0x30:self.set(row,self.by_offset[off],value)
            self.new_characters[key]={f.offset:self.value(row,f) for f in self.fields}
            self.changes={k:v for k,v in self.changes.items() if k[0]!=key}

        def create_character(self,key,copy_from=None,values=None,serial=None):
            if not isinstance(key,str) or not re.fullmatch(r'''PID_[^\s,;"'!&\x00]+''',key) or '::' in key:
                raise DataError('Enter a unique PID_ ID with a name, no whitespace, nulls, quotes, , ; ! & or :: separators.')
            if key in self.labels or key in self.by_pid:raise DataError('That ID already exists in Person.bin.')
            if len(self.records)>=65536:raise DataError('The character index exceeds the 16-bit format limit.')
            if max(struct.unpack_from('<H',self.raw,r.offset+22)[0] for r in self._source_records)+self.added_character_count+1>65535:
                raise DataError('No unused ascending character-header tags remain.')
            if copy_from is not None:
                if copy_from not in self.by_pid:raise DataError('Choose a current character to duplicate.')
                if values is not None:raise DataError('Choose either a character copy or explicit values.')
                values={f.offset:self.value(self.by_pid[copy_from],f) for f in self.fields};values[0x30]=0 if serial is None else serial
            if serial is None:serial=values.get(0x30,0) if isinstance(values,dict) else 0
            self._validate_serial(serial)
            defaults={}
            for f in self.fields:
                if f.kind in FORMATS:defaults[f.offset]=0
                elif f.kind in TEXT_TYPES:defaults[f.offset]=''
                elif f.kind in LIST_TYPES:defaults[f.offset]=[]
                else:raise DataError('Unsupported new-character field type: '+f.kind)
            defaults[0x30]=serial;before=self.snapshot_edits()
            try:
                self.new_characters[key]=defaults;self._index_characters()
                self._seed_character(key,values if values is not None else defaults)
                return self.by_pid[key]
            except Exception:self.restore_edits(before);raise

        def remove_character(self,key):
            if key not in self.new_characters:raise DataError('Only newly created characters can be removed.')
            self.changes={k:v for k,v in self.changes.items() if k[0]!=key}
            del self.new_characters[key];self._index_characters()

    return CharacterCreation
