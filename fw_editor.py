#!/usr/bin/env python3
"""Fortune's Weave 1.00 hacking suite. Original implementation; no game data bundled."""
from __future__ import annotations

import ctypes
import ctypes.util
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime

from branding import APP_NAME
from localization import Translator, JAPANESE
from asset_index import AssetIndex
from item_index import reference_ids

VERSION = '1.00'
MESSAGE_TABLES = ('Person','Job','Skill','Item','Clan','Roster','ScoutInfo','System_Facility','System_Notice','System_Hub','System_Gmap','System_Dungeon','System','BattleTitle','Spot','Divination','Shop','Legion')
FORMATS = {'u8': 'B', 's8': 'b', 'b8': 'B', 'bool': 'B', 'u16': 'H',
           's16': 'h', 'b16': 'H', 'u32': 'I', 's32': 'i', 'b32': 'I', 'int':'i'}
LIMITS = {t: ((-(1 << (struct.calcsize(f) * 8 - 1)), (1 << (struct.calcsize(f) * 8 - 1)) - 1)
              if f.islower() else (0, (1 << (struct.calcsize(f) * 8)) - 1))
          for t, f in FORMATS.items()}
LIMITS['bool'] = (0, 1)
TEXT_TYPES = {'string', 'data', 'ref'}
ARRAY_TYPES = {'string[]', 'data[]'}
NESTED_TYPES = {'string[,]','data[,]'}
FLOAT_TYPES = {'float','f32'}
NUMERIC_ARRAYS = {'s16[]':'h','u8[]':'B'}
LIST_TYPES = ARRAY_TYPES | NESTED_TYPES
TRANSLATIONS = {
    '名前': 'Name key', '識別子': 'Short identifier', '通し番号': 'Character serial',
    'フラグ': 'Flags', '死亡タイプ': 'Death type', '死亡台詞': 'Death dialogue', '身分': 'Status',
    '兵種': 'Class', '前期デフォルト兵種': 'Early default classes', '後期デフォルト兵種': 'Later default classes',
    '自動騎乗': 'Automatic mount', '初期アイテム': 'Initial items', '技能習得': 'Learning tables',
    '強制スキル': 'Forced skills', '除外スキル': 'Excluded skills', '強制魔法': 'Forced magic',
    '除外魔法': 'Excluded magic', '強制戦技': 'Forced combat arts', '除外戦技': 'Excluded combat arts',
    '強制猛撃': 'Forced special attacks', '支援関係': 'Support reference', 'プロフィール': 'Profile reference',
    '成長リスト': 'Automatic progression table', '難易度差分': 'Difficulty variation', '所属': 'Affiliation',
    '捕獲': 'Capture reference', '落下アイテム': 'Drop items', '落下アイテム3部': 'Later drop items',
    '抽選落下': 'Random drop reference', '固有アイテム': 'Personal items', '固有アイテム条件': 'Personal item conditions',
    'カテゴリ': 'Category', '性別': 'Gender value', '固定成長': 'Fixed growth level', '相対成長': 'Relative growth level',
    '最低成長': 'Minimum growth level', '固定表示': 'Fixed display level', '相対表示': 'Relative display level',
    '固定経験': 'Fixed experience level', '相対経験': 'Relative experience level', '撃破名声': 'Defeat renown',
    'HP': 'HP', '力': 'Strength', '魔力': 'Magic', '技': 'Dexterity', '速さ': 'Speed', '幸運': 'Luck',
    '守備': 'Defense', '魔防': 'Resistance', '魅力': 'Charm', '視界': 'Sight', '移動': 'Movement',
    '剣': 'Sword', '槍': 'Lance', '斧': 'Axe', '弓': 'Bow', '格闘': 'Brawling', '黒魔': 'Black magic',
    '白魔': 'White magic', '特殊': 'Special', '歩兵': 'Infantry', '騎馬': 'Mounted', '騎兵': 'Cavalry',
    '重装': 'Armor', '飛行': 'Flying', '指揮': 'Command', '自動成長適用技能': 'Auto-progression skill flags',
    'アセット流用': 'Reuse assets from character', 'アセットフラグ': 'Asset flag', 'バリエーション': 'Variation',
    'プリセット': 'Preset', '帰還エフェクト': 'Return effect', '戦闘BGM': 'Battle music', 'オリジナル': 'Original character',
    '3部前': 'Later phase: before', '3部後': 'Later phase: after',
    'レベル':'Level','技能タイプ':'Skill type code','技能レベル':'Skill level code',
    'スキル':'Skill reference','必要条件':'Required conditions',
}


TRANSLATIONS.update({
    'ヘルプ':'Description key', '移動タイプ':'Movement type', 'ランク':'Class rank',
    '思考':'AI behavior', '支援効果':'Support effect', '下級職':'Lower class link',
    '上級職':'Upper class link', '下馬先':'Dismounted class', '配備':'Deployment value',
    '乗り物':'Mount reference', '補正率':'Adjustment rate', '専用装備':'Exclusive equipment',
    '所持スキル':'Class skills', '味方スキル':'Ally skills', '敵軍スキル':'Enemy skills',
    '味方猛撃スキル':'Ally special-attack skills', '敵軍猛撃スキル':'Enemy special-attack skills',
    '戦技スキル':'Combat-art skills', '属性スキル':'Attribute skills', 'マスタースキル':'Mastery skills',
    '成長経験':'Growth experience', '戦闘経験':'Battle experience', '継続ターン':'Duration turns',
    '占有サイズ':'Occupancy size', '戦闘範囲小':'Small battle range', '戦闘範囲大':'Large battle range',
    '共有１':'Shared value 1', '共有２':'Shared value 2', '共有３':'Shared value 3',
    'CC必要条件':'Promotion conditions', 'CC秘匿条件':'Hidden promotion conditions',
    'CC必要アイテム':'Required promotion item', 'CC禁止キャラ':'Barred characters',
    '不合格係数':'Failure coefficient', '返還試験':'Return-exam value',
    'アイコン名':'Icon name', 'CC表示武器':'Promotion display weapon', '系統':'Class family',
})


class DataError(ValueError):
    pass


def edit_summary(doc):
    added=getattr(doc,'added_count',0)
    lists=getattr(doc,'added_list_count',0)
    items=getattr(doc,'added_item_count',0)
    characters=getattr(doc,'added_character_count',0)
    classes=getattr(doc,'added_class_count',0)
    return f'{len(doc.changes)} edited fields'+(f' · {added} added entries' if added else '')+(f' · {lists} new lists' if lists else '')+(f' · {items} new items' if items else '')+(f' · {classes} new classes' if classes else '')+(f' · {characters} new characters' if characters else '')


def float32(value):
    if type(value) not in (int,float):raise DataError('Enter a finite decimal number.')
    try:
        result=struct.unpack('<f',struct.pack('<f',value))[0]
    except (OverflowError,struct.error) as exc:raise DataError('Decimal exceeds the 32-bit float range.') from exc
    if not math.isfinite(result):raise DataError('Enter a finite decimal number within the 32-bit float range.')
    return result


def raw_color(value):
    if not isinstance(value,str) or not re.fullmatch(r'#?[0-9a-fA-F]{8}',value):
        raise DataError('Enter four raw bytes as #XXXXXXXX (eight hexadecimal digits).')
    return '#'+value.removeprefix('#').upper()


def number_text(value,kind):
    if kind in FLOAT_TYPES and math.isfinite(value):
        for precision in range(1,10):
            text=format(value,f'.{precision}g')
            try:
                if float32(float(text))==value:return text
            except DataError:continue
    return str(value)


class Binary:
    def __init__(self, raw: bytes):
        self.raw = bytes(raw)
        if len(raw) < 32:
            raise DataError('File is too short.')
        total, self.size, count, labels = struct.unpack_from('<4I', raw)
        self.pool = self.size + 8 * count + 8 * labels
        if total != len(raw) or self.size < 32 or 32 + self.pool > total:
            raise DataError('Invalid table header or file length.')
        self.pointers = list(struct.unpack_from(f'<{count}Q', raw, 32 + self.size))
        if len(set(self.pointers)) != count:
            raise DataError('Duplicate relocation entries.')
        for offset in self.pointers:
            if offset + 8 > self.size:
                raise DataError('Relocation lies outside the data section.')
            pointer = struct.unpack_from('<Q', raw, offset + 32)[0]
            if pointer + 32 >= total or self.size <= pointer < self.pool:
                raise DataError('Invalid relocation target.')
        label_start = 32 + self.size + count * 8
        self.label_bytes = raw[label_start:label_start + labels * 8]
        self.labels = {}
        for i in range(labels):
            offset, string = struct.unpack_from('<II', self.label_bytes, i * 8)
            if offset >= self.size:
                raise DataError('Label points outside the data section.')
            label = self.cstring(32 + self.pool + string)
            self.labels[label] = offset + 32

    def cstring(self, absolute: int) -> str:
        if not 32 <= absolute < len(self.raw):
            raise DataError('String offset is outside the file.')
        end = self.raw.find(b'\0', absolute)
        if end < 0:
            raise DataError('Unterminated string.')
        try:
            return self.raw[absolute:end].decode('utf-8')
        except UnicodeDecodeError as exc:
            raise DataError('Invalid UTF-8 string.') from exc

    def string(self, pointer: int) -> str:
        return self.cstring(pointer + 32) if pointer else ''

    def groups(self):
        pos = 32
        while True:
            pos = self.raw.find(b'\x01\x12\x25\x20', pos, 32 + self.size)
            if pos < 0:
                break
            if pos + 32 <= 32 + self.size:
                name, width, count, schema = struct.unpack_from('<QIIQ', self.raw, pos + 8)
                if 0 < count < 512 and 32 <= width < 8192 and schema + 32 + count * 32 <= pos:
                    yield self.string(name), width, count, schema + 32
            pos += 4


@dataclass(frozen=True)
class Field:
    name: str
    kind: str
    size: int
    offset: int

    @property
    def label(self):
        return TRANSLATIONS.get(self.name, self.name)


@dataclass(frozen=True)
class Record:
    pid: str
    offset: int
    index: int


class EditableTable(Binary):
    group_name = ''
    layout = (0, 0)
    prefix = ''
    filename = ''
    project_format = ''
    locked_offsets = frozenset()
    multiline_offsets = frozenset()

    def __init__(self, raw: bytes):
        super().__init__(raw)
        group = next((g for g in self.groups() if g[0] == self.group_name), None)
        if not group or group[1:3] != self.layout:
            raise DataError(f'Unsupported {self.filename} layout. This editor targets version 1.00.')
        _, self.stride, count, schema = group
        self.fields = []
        for i in range(count):
            name, kind, _, size, offset = struct.unpack_from('<QQQII', raw, schema + i * 32)
            field = Field(self.string(name), self.string(kind), size, offset)
            if offset < 32 or offset + size > self.stride:
                raise DataError('Invalid character field layout.')
            self.fields.append(field)
        self.by_offset = {f.offset: f for f in self.fields}
        if self.prefix == 'PID_' and self.by_offset[0x30].name != '通し番号':
            raise DataError('Character serial layout differs.')
        self.records = []
        start = schema + count * 32
        for index in range(65536):
            offset = start + index * self.stride
            if offset + self.stride > 32 + self.size:
                break
            number, amount = struct.unpack_from('<HH', raw, offset + 16)
            if number != index or amount != 1:
                break
            pid = self.string(struct.unpack_from('<Q', raw, offset + 8)[0])
            if not pid.startswith(self.prefix) or self.labels.get(pid) != offset:
                raise DataError('Character label/index mismatch.')
            self.records.append(Record(pid, offset, index))
        if not self.records or len({r.pid for r in self.records}) != len(self.records):
            raise DataError('Invalid character index.')
        self.by_pid = {r.pid: r for r in self.records}
        self.label_at = {offset: label for label, offset in self.labels.items()}
        self.changes = {}
        self.fingerprint = hashlib.sha256(raw).hexdigest()

    def original(self, record: Record, field: Field):
        at = record.offset + field.offset
        if field.kind=='color':return '#'+self.raw[at:at+4].hex().upper()
        if field.kind in FLOAT_TYPES:
            return struct.unpack_from('<f',self.raw,at)[0]
        if field.kind in NUMERIC_ARRAYS:
            count,width,_,pointer=struct.unpack_from('<HHIQ',self.raw,at)
            fmt=NUMERIC_ARRAYS[field.kind];expected=struct.calcsize(fmt)
            if width!=expected or (count and (not pointer or pointer+count*width>self.size)):
                raise DataError('Unsupported numeric-array layout.')
            return list(struct.unpack_from('<'+str(count)+fmt,self.raw,pointer+32)) if count else []
        if field.kind in FORMATS:
            return struct.unpack_from('<' + FORMATS[field.kind], self.raw, at)[0]
        if field.kind == 'ref':
            pointer = struct.unpack_from('<Q', self.raw, at)[0]
            if not pointer: return ''
            key = self.label_at.get(pointer + 32)
            if key not in self.by_pid:
                raise DataError('Direct class reference does not point to an indexed class.')
            return key
        if field.kind in TEXT_TYPES:
            return self.string(struct.unpack_from('<Q', self.raw, at)[0])
        if field.kind in ARRAY_TYPES:
            count, width, _, pointer = struct.unpack_from('<HHIQ', self.raw, at)
            expected = 8 if field.kind == 'string[]' else 16
            if width != expected or (count and (not pointer or pointer + count * width > self.size)):
                raise DataError('Unsupported character array layout.')
            return [self.string(struct.unpack_from('<Q', self.raw, pointer + 32 + i * width)[0])
                    for i in range(count)]
        if field.kind in NESTED_TYPES:
            count, width, _, pointer = struct.unpack_from('<HHIQ', self.raw, at)
            if width != 16 or (count and (not pointer or pointer + count*16 > self.size)):
                raise DataError('Unsupported nested condition layout.')
            rows = []
            leaf_width=16 if field.kind=='data[,]' else 8
            for i in range(count):
                n, w, _, ptr = struct.unpack_from('<HHIQ', self.raw, pointer+32+i*16)
                if w != leaf_width or (n and (not ptr or ptr+n*leaf_width > self.size)):
                    raise DataError('Unsupported nested condition row.')
                rows.append([self.string(struct.unpack_from('<Q', self.raw, ptr+32+j*leaf_width)[0]) for j in range(n)])
            return rows
        raise DataError('Unsupported field type: ' + field.kind)

    def value(self, record, field):
        value = self.changes.get((record.pid, field.offset), self.original(record, field))
        return [list(v) if isinstance(v,list) else v for v in value] if isinstance(value,list) else value

    def set(self, record, field, value):
        if field.offset in self.locked_offsets:
            raise DataError('The character serial is fixed to preserve the slot.')
        if field.kind=='color':
            value=raw_color(value)
        elif field.kind in FLOAT_TYPES:
            value=float32(value)
        elif field.kind in NUMERIC_ARRAYS:
            low,high=(-32768,32767) if field.kind=='s16[]' else (0,255)
            if not isinstance(value,list) or len(value)>65535 or any(type(v) is not int or not low<=v<=high for v in value):
                raise DataError(f'Enter a list of integers between {low} and {high} (maximum 65535).')
            value=list(value)
        elif field.kind in FORMATS:
            if type(value) is not int:
                raise DataError('Enter a whole number.')
            low, high = LIMITS[field.kind]
            if not low <= value <= high:
                raise DataError(f'Value must be between {low} and {high}.')
        elif field.kind == 'ref':
            if not isinstance(value,str) or (value and value not in self.by_pid):
                raise DataError('Choose an existing class ID or leave the link empty.')
        elif field.kind in TEXT_TYPES:
            if not isinstance(value, str) or '\0' in value or (field.offset not in self.multiline_offsets and ('\n' in value or '\r' in value)):
                raise DataError('Enter one text/reference value without null characters.')
        elif field.kind in ARRAY_TYPES:
            if not isinstance(value, list) or len(value) > 65535 or any(
                    not isinstance(v, str) or not v or '\0' in v or '\n' in v or '\r' in v for v in value):
                raise DataError('Enter one non-empty reference per line (maximum 65535).')
            value = list(value)
        elif field.kind in NESTED_TYPES:
            if not isinstance(value,list) or len(value)>65535 or any(
                    not isinstance(row,list) or len(row)>65535 or any(
                        not isinstance(v,str) or not v or any(c in v for c in '\0\n\r') for v in row)
                    for row in value):
                raise DataError('Enter nested condition rows as JSON lists of non-empty strings.')
            value = [list(row) for row in value]
        else:
            raise DataError('Unsupported field type.')
        key = record.pid, field.offset
        if value == self.original(record, field):
            self.changes.pop(key, None)
        else:
            self.changes[key] = value

    def project(self):
        return {'format': self.project_format, 'source_sha256': self.fingerprint,
                'changes': [{'pid': pid, 'offset': offset, 'value': value}
                            for (pid, offset), value in sorted(self.changes.items())]}

    def load_project(self, project):
        if project.get('format') != self.project_format or project.get('source_sha256') != self.fingerprint:
            raise DataError(f'This project belongs to a different source {self.filename}.')
        before = dict(self.changes)
        try:
            self.changes = {}
            for change in project['changes']:
                self.set(self.by_pid[change['pid']], self.by_offset[change['offset']], change['value'])
        except Exception:
            self.changes = before
            raise

    def edit_target(self, pid, offset):
        return self.by_pid[pid], self.by_offset[offset]

    @property
    def modified(self):return bool(self.changes)

    def record_changed(self,pid):return any(key==pid for key,_ in self.changes)

    def snapshot_edits(self):return deepcopy(self.changes)

    def restore_edits(self,state):self.changes=deepcopy(state)

    def clear_edits(self):self.changes={}

    def reparse(self, raw):
        return type(self)(raw)

    def build(self):
        if not self.changes:
            return self.raw
        body = bytearray(self.raw[32:32 + self.size])
        pool = bytearray(self.raw[32 + self.pool:])
        pointers = {}
        for at in self.pointers:
            target = struct.unpack_from('<Q', body, at)[0]
            pointers[at] = ('string', target - self.pool) if target >= self.pool else ('data', target)
        strings = {}
        for at, (kind, target) in pointers.items():
            if kind == 'string':
                strings.setdefault(self.cstring(32 + self.pool + target), target)

        def assign(at, value):
            pointers.pop(at, None)
            struct.pack_into('<Q', body, at, 0)
            if value:
                if value not in strings:
                    strings[value] = len(pool)
                    pool.extend(value.encode('utf-8') + b'\0')
                pointers[at] = ('string', strings[value])

        for (pid, offset), value in sorted(self.changes.items()):
            record, field = self.edit_target(pid, offset)
            at = record.offset + offset - 32
            if field.kind=='color':
                body[at:at+4]=bytes.fromhex(value[1:])
            elif field.kind in FLOAT_TYPES:
                struct.pack_into('<f',body,at,value)
            elif field.kind in NUMERIC_ARRAYS:
                fmt=NUMERIC_ARRAYS[field.kind];width=struct.calcsize(fmt)
                _,_,reserved,_=struct.unpack_from('<HHIQ',body,at);pointer=0
                if value:
                    body.extend(b'\0'*(-len(body)%8));pointer=len(body)
                    body.extend(struct.pack('<'+str(len(value))+fmt,*value))
                    body.extend(b'\0'*(-len(body)%8))
                struct.pack_into('<HHIQ',body,at,len(value),width,reserved,pointer)
                pointers.pop(at+8,None)
                if value:pointers[at+8]=('data',pointer)
            elif field.kind in FORMATS:
                struct.pack_into('<' + FORMATS[field.kind], body, at, value)
            elif field.kind == 'ref':
                pointers.pop(at,None)
                target = self.by_pid[value].offset - 32 if value else 0
                struct.pack_into('<Q',body,at,target)
                if value: pointers[at]=('data',target)
            elif field.kind in TEXT_TYPES:
                assign(at, value)
                if field.kind == 'data':
                    struct.pack_into('<Q', body, at + 8, 0)
                    pointers.pop(at + 8, None)
            elif field.kind in NESTED_TYPES:
                _, _, reserved, _ = struct.unpack_from('<HHIQ',body,at)
                pointer = 0
                if value:
                    body.extend(b'\0' * (-len(body)%8))
                    pointer = len(body); body.extend(b'\0'*(16*len(value)))
                    leaf_width=16 if field.kind=='data[,]' else 8
                    for i,row in enumerate(value):
                        leaf = len(body) if row else 0
                        body.extend(b'\0'*(leaf_width*len(row)))
                        for j,entry in enumerate(row):assign(leaf+j*leaf_width,entry)
                        cell = pointer+i*16
                        struct.pack_into('<HHIQ',body,cell,len(row),leaf_width,0,leaf)
                        if row:pointers[cell+8]=('data',leaf)
                struct.pack_into('<HHIQ',body,at,len(value),16,reserved,pointer)
                pointers.pop(at+8,None)
                if value:pointers[at+8]=('data',pointer)
            else:
                width = 8 if field.kind == 'string[]' else 16
                _, _, reserved, _ = struct.unpack_from('<HHIQ', body, at)
                pointer = 0
                if value:
                    body.extend(b'\0' * (-len(body) % 8))
                    pointer = len(body)
                    body.extend(b'\0' * (width * len(value)))
                    for i, entry in enumerate(value):
                        assign(pointer + i * width, entry)
                struct.pack_into('<HHIQ', body, at, len(value), width, reserved, pointer)
                pointers.pop(at + 8, None)
                if value:
                    pointers[at + 8] = ('data', pointer)

        order = [at for at in self.pointers if at in pointers]
        known = set(order)
        order.extend(sorted(set(pointers) - known))
        new_pool = len(body) + len(order) * 8 + len(self.label_bytes)
        for at, (kind, target) in pointers.items():
            struct.pack_into('<Q', body, at, target + new_pool if kind == 'string' else target)
        header = bytearray(self.raw[:32])
        total = 32 + new_pool + len(pool)
        if total >= 1 << 32:
            raise DataError('Output exceeds the format size limit.')
        struct.pack_into('<4I', header, 0, total, len(body), len(order), len(self.label_bytes) // 8)
        result = bytes(header + body + struct.pack(f'<{len(order)}Q', *order) + self.label_bytes + pool)
        checked = self.reparse(result)
        if [r.pid for r in checked.records] != [r.pid for r in self.records]:
            raise DataError('Export changed the character index.')
        for record in self.records:
            for offset in self.locked_offsets:
                if checked.original(checked.by_pid[record.pid], checked.by_offset[offset]) != self.original(record,self.by_offset[offset]):
                    raise DataError('Export changed a locked field.')
        for (pid, offset), value in self.changes.items():
            if checked.original(*checked.edit_target(pid, offset)) != value:
                raise DataError('Export verification failed.')
        return result


from person_creation import create_mixin as create_character_creation
CharacterCreation=create_character_creation(Record,DataError,FORMATS,TEXT_TYPES,LIST_TYPES)


class Person(CharacterCreation,EditableTable):
    group_name = '個人'
    layout = (704, 143)
    prefix = 'PID_'
    filename = 'Person.bin'
    project_format = 'fw-character-edits-v1'
    locked_offsets = frozenset({0x30})

    def __init__(self,raw):
        super().__init__(raw)
        self.views=attach_expanded(self,PERSON_EXPANDED_KEYS)

    def edit_target(self,pid,offset):
        section=pid.partition(':')[0]
        if section in self.views:
            view=self.views[section];return view.by_pid[pid],view.by_offset[offset]
        return super().edit_target(pid,offset)

    def build(self):
        validate_expanded(self)
        if self.added_character_count:
            raw=bytearray(expand_records(self,DataError,self.new_characters))
            start=self._source_records[-1].offset+self.stride
            for i,key in enumerate(self.new_characters):
                struct.pack_into('<B',raw,start+i*self.stride+0x30,self.new_characters[key][0x30])
            expanded=Person(bytes(raw))
            for (pid,offset),value in self.changes.items():
                if pid not in self.new_characters:
                    section=pid.partition(':')[0];target=expanded.views.get(section,expanded)
                    target.set(*expanded.edit_target(pid,offset),value)
            for pid in self.new_characters:
                for field in self.fields:
                    if field.offset!=0x30:expanded.set(expanded.by_pid[pid],field,self.value(self.by_pid[pid],field))
            return expanded.build()
        return super().build()

    def project(self):
        project=super().project()
        if any(pid.partition(':')[0] in self.views for pid,_ in self.changes):
            project.update(format='fw-character-edits-v2',source_file=self.filename)
        if self.added_character_count:
            project.update(format='fw-character-edits-v3',source_file=self.filename,new_characters=[
                {'pid':key,'values':{str(offset):deepcopy(value) for offset,value in values.items()}} for key,values in self.new_characters.items()])
        return project

    def load_project(self,project):
        fmt=project.get('format')
        if fmt not in ('fw-character-edits-v1','fw-character-edits-v2','fw-character-edits-v3') or project.get('source_sha256')!=self.fingerprint or fmt!='fw-character-edits-v1' and project.get('source_file')!=self.filename:
            raise DataError('This project belongs to a different source Person.bin.')
        if fmt!='fw-character-edits-v3' and project.get('new_characters'):raise DataError('New characters require the character v3 project format.')
        before=self.snapshot_edits()
        try:
            self.clear_edits()
            if fmt=='fw-character-edits-v3':
                additions=project.get('new_characters')
                if not isinstance(additions,list):raise DataError('New characters must be a list.')
                for entry in additions:
                    if not isinstance(entry,dict) or set(entry)!={'pid','values'} or not isinstance(entry['values'],dict):raise DataError('Invalid new character definition.')
                    if set(entry['values'])!={str(f.offset) for f in self.fields}:raise DataError('New characters must include every supported field.')
                    self.create_character(entry['pid'],values={int(offset):value for offset,value in entry['values'].items()})
            for change in project['changes']:
                pid=change['pid'];section=pid.partition(':')[0]
                if section in self.views:
                    if fmt not in ('fw-character-edits-v2','fw-character-edits-v3'):raise DataError('Difficulty/equipment edits require the character v2 format.')
                    self.views[section].set(*self.edit_target(pid,change['offset']),change['value'])
                else:self.set(*self.edit_target(pid,change['offset']),change['value'])
            validate_expanded(self)
        except Exception:self.restore_edits(before);raise


from class_creation import create_mixin as create_class_creation
from record_expansion import expanded_raw as expand_records
ClassCreation=create_class_creation(Record,DataError,FORMATS,TEXT_TYPES,LIST_TYPES)


class Job(ClassCreation,EditableTable):
    group_name = '兵種'
    layout = (560, 134)
    prefix = 'JID_'
    filename = 'Job.bin'
    project_format = 'fw-class-edits-v1'

    def build(self):
        if self.added_class_count:
            expanded=Job(expand_records(self,DataError,self.new_classes))
            for (pid,offset),value in self.changes.items():
                if pid not in self.new_classes:expanded.set(*expanded.edit_target(pid,offset),value)
            for pid in self.new_classes:
                for field in self.fields:expanded.set(expanded.by_pid[pid],field,self.value(self.by_pid[pid],field))
            return expanded.build()
        return super().build()

    def project(self):
        project=super().project()
        if self.added_class_count:
            project.update(format='fw-class-edits-v2',source_file=self.filename,new_classes=[
                {'jid':key,'values':{str(offset):deepcopy(value) for offset,value in values.items()}} for key,values in self.new_classes.items()])
        return project

    def load_project(self,project):
        fmt=project.get('format')
        if fmt not in ('fw-class-edits-v1','fw-class-edits-v2') or project.get('source_sha256')!=self.fingerprint or (fmt=='fw-class-edits-v2' and project.get('source_file')!=self.filename):
            raise DataError('This project belongs to a different source Job.bin.')
        if fmt!='fw-class-edits-v2' and project.get('new_classes'):raise DataError('New classes require the class v2 project format.')
        before=self.snapshot_edits()
        try:
            self.clear_edits()
            if fmt=='fw-class-edits-v2':
                entries=project.get('new_classes')
                if not isinstance(entries,list):raise DataError('New classes must be a list.')
                for entry in entries:
                    if not isinstance(entry,dict) or set(entry)!={'jid','values'} or not isinstance(entry['values'],dict):raise DataError('Invalid new class definition.')
                    if set(entry['values'])!={str(f.offset) for f in self.fields}:raise DataError('New classes must include every supported field.')
                    self.create_class(entry['jid'])
                # Register all IDs before resolving forward links or class cycles.
                for entry in entries:self._seed_values(entry['jid'],{int(offset):value for offset,value in entry['values'].items()})
            for change in project['changes']:self.set(*self.edit_target(change['pid'],change['offset']),change['value'])
        except Exception:self.restore_edits(before);raise


from legion_data import create_model as create_legion_model
Legion=create_legion_model(EditableTable,DataError)


class Skill(EditableTable):
    group_name='スキル';layout=(904,157);prefix='SID_'
    filename='Skill.bin';project_format='fw-skill-edits-v1'

    def __init__(self,raw):
        super().__init__(raw)
        supported=set(FORMATS)|TEXT_TYPES|LIST_TYPES|FLOAT_TYPES|set(NUMERIC_ARRAYS)
        if any(f.kind not in supported for f in self.fields):raise DataError('Unsupported skill field type.')
        for row in self.records:
            for field in self.fields:self.original(row,field)

    def project(self):
        return {**super().project(),'source_file':self.filename}

    def load_project(self,project):
        if project.get('source_file')!=self.filename:raise DataError('Skill project belongs to a different source file.')
        super().load_project(project)


class SkillP0(Skill):filename='Skill_P0.bin'
class SkillP1(Skill):filename='Skill_P1.bin'
SKILL_TABLES=(Skill,SkillP0,SkillP1)


from item_creation import create_mixin as create_item_creation,expanded_raw as expand_item_raw
ItemCreation=create_item_creation(Record,DataError,FORMATS,TEXT_TYPES,ARRAY_TYPES)


class Item(ItemCreation,EditableTable):
    group_name='アイテム';layout=(456,80);prefix='IID_'
    filename='Item.bin';project_format='fw-item-edits-v1'

    def __init__(self,raw):
        super().__init__(raw)
        if any(f.kind not in set(FORMATS)|TEXT_TYPES|ARRAY_TYPES for f in self.fields):
            raise DataError('Unsupported item field type.')
        for row in self.records:
            for field in self.fields:self.original(row,field)
        self.views={}
        from shop_data import SECTIONS as shop_sections
        groups={g[0]:g for g in self.groups()}
        for key,(title,native,stride,count,container) in shop_sections.items():
            group=groups.get(native)
            if group is None:continue
            if group[1:3]!=(stride,count):raise DataError('Unsupported item auxiliary layout: '+title)
            self.views[key]=ShopView(self,key,group)

    def edit_target(self,pid,offset):
        section=pid.partition(':')[0]
        if section in self.views:return self.views[section].by_pid[pid],self.views[section].by_offset[offset]
        return super().edit_target(pid,offset)

    def validate(self):
        for view in self.views.values():
            for row in view.records:view.validate_record(row)

    def build(self):
        self.validate()
        if self.added_item_count:
            expanded=type(self)(expand_item_raw(self,DataError))
            for (pid,offset),value in self.changes.items():
                if pid not in self.new_items:expanded.set(*expanded.edit_target(pid,offset),value)
            for pid in self.new_items:
                for field in self.fields:expanded.set(expanded.by_pid[pid],field,self.value(self.by_pid[pid],field))
            return expanded.build()
        return super().build()

    def project(self):
        project={**super().project(),'source_file':self.filename}
        if any(pid.partition(':')[0] in self.views for pid,_ in self.changes):project['format']='fw-item-edits-v2'
        if self.added_item_count:
            project.update(format='fw-item-edits-v3',new_items=[{'iid':key,'values':{str(offset):deepcopy(value) for offset,value in values.items()}} for key,values in self.new_items.items()])
        return project

    def load_project(self,project):
        if project.get('source_file')!=self.filename or project.get('format') not in ('fw-item-edits-v1','fw-item-edits-v2','fw-item-edits-v3') or project.get('source_sha256')!=self.fingerprint:
            raise DataError('Item project belongs to a different source file.')
        if project.get('format')!='fw-item-edits-v3' and project.get('new_items'):raise DataError('New items require the item v3 project format.')
        before=self.snapshot_edits()
        try:
            self.clear_edits()
            if project.get('format')=='fw-item-edits-v3':
                additions=project.get('new_items')
                if not isinstance(additions,list):raise DataError('New items must be a list.')
                for entry in additions:
                    if not isinstance(entry,dict) or set(entry)!={'iid','values'} or not isinstance(entry['values'],dict):raise DataError('Invalid new item definition.')
                    if set(entry['values'])!={str(f.offset) for f in self.fields}:raise DataError('New items must include every supported field.')
                    self.create_item(entry['iid'],values={int(offset):value for offset,value in entry['values'].items()})
            for change in project['changes']:
                pid=change['pid'];record,field=self.edit_target(pid,change['offset'])
                section=pid.partition(':')[0]
                if section in self.views:
                    if project['format'] not in ('fw-item-edits-v2','fw-item-edits-v3'):raise DataError('Shop/loot changes require the item v2 project format.')
                    self.views[section].set(record,field,change['value'])
                else:self.set(record,field,change['value'])
            self.validate()
        except Exception:self.restore_edits(before);raise


class ItemP0(Item):filename='Item_P0.bin'
class ItemP1(Item):filename='Item_P1.bin'
ITEM_TABLES=(Item,ItemP0,ItemP1)


def validate_new_item_ids(documents):
    items=[d for d in documents.values() if isinstance(d,Item)]
    for doc in items:
        for key in doc.new_items:
            if any(key in other.by_pid for other in items if other is not doc):
                raise DataError('New item ID exists in more than one loaded file: '+key)


class CollectionTable(EditableTable):
    """Fixed collection/leaf headers, with editable fields in each existing leaf."""
    filename='Growth.bin'
    locked_offsets=frozenset()

    def __init__(self,raw):
        Binary.__init__(self,raw)
        group=next((g for g in self.groups() if g[0]==self.group_name),None)
        if not group or group[1:3]!=self.layout:
            raise DataError(f'Unsupported Growth.bin {self.prefix} layout. This module targets version 1.00.')
        _,self.stride,count,schema=group
        self.fields=[]
        for i in range(count):
            n,k,_,size,offset=struct.unpack_from('<QQQII',raw,schema+i*32)
            self.fields.append(Field(self.string(n),self.string(k),size,offset))
        if {f.offset:(f.kind,f.size) for f in self.fields}!=self.expected_fields:
            raise DataError(f'Unsupported {self.prefix} entry field layout.')
        self.by_offset={f.offset:f for f in self.fields};self.collections=[];self.rows_by_table={};self.records=[]
        entries=sorted(((key,at) for key,at in self.labels.items() if key.startswith(self.prefix)),key=lambda pair:pair[1])
        if not entries:raise DataError(f'No {self.prefix} collections were found in Growth.bin.')
        collection_start=schema+count*32
        for index,(key,at) in enumerate(entries):
            if at!=collection_start+index*48 or at+48>32+self.size:
                raise DataError(f'{self.prefix} collection headers differ from the supported layout.')
            number,amount=struct.unpack_from('<HH',raw,at+16)
            if number!=index or self.string(struct.unpack_from('<Q',raw,at+8)[0])!=key:
                raise DataError(f'{self.prefix} collection identity mismatch.')
            pointer=struct.unpack_from('<Q',raw,at+32)[0]
            if amount and (not pointer or pointer+amount*self.stride>self.size):
                raise DataError(f'{self.prefix} entry array is outside the data section.')
            collection=Record(key,at,index);self.collections.append(collection);rows=[]
            for i in range(amount):
                offset=32+pointer+i*self.stride
                if struct.unpack_from('<HH',raw,offset+16)!=(i,1):
                    raise DataError(f'{self.prefix} row order/header mismatch.')
                row=Record(f'{key}::{i}',offset,i);rows.append(row);self.records.append(row)
            self.rows_by_table[key]=rows
        self.tables_by_id={r.pid:r for r in self.collections}
        self.by_pid={r.pid:r for r in self.records}
        self.row_location={r.pid:(key,r.index) for key,rows in self.rows_by_table.items() for r in rows}
        self.label_at={at:key for key,at in self.labels.items()}
        self.changes={};self.fingerprint=hashlib.sha256(raw).hexdigest()
        for row in self.records:
            for field in self.fields:self.original(row,field)

    def table_changed(self,key):
        return any(self.row_location.get(pid,(None,))[0]==key for pid,_ in self.changes)

    def reset_table(self,key):
        self.changes={k:v for k,v in self.changes.items() if self.row_location.get(k[0],(None,))[0]!=key}


class Progression(CollectionTable):
    """GLID view of the same Growth document; never exported as a second file."""
    group_name='成長リスト';layout=(680,81);prefix='GLID_'
    expected_fields={0x20:('u8',1),**{0x28+i*8:('string',8) for i in range(80)}}

    def __init__(self,raw,owner):
        self.owner=owner
        # CollectionTable initializes changes; do not clear the owner's edits here.
        before=owner.changes
        super().__init__(raw)
        owner.changes=before
        if [f.name for f in self.fields[1:]]!=[str(i) for i in range(1,80)]+['80～']:
            raise DataError('Unsupported GLID level-column order.')

    @property
    def changes(self):return self.owner.changes

    @changes.setter
    def changes(self,value):self.owner.changes=value

    @staticmethod
    def reference_prefix(category):
        # Observed names in the supplied 1.00 data; other categories stay raw.
        return 'JID_' if category==0 else 'IID_' if category in range(4,9) else None

    def build(self):return self.owner.build()


from learning_entries import create_mixin as create_learning_entries,expanded_raw as expand_learning_raw
LearningEntries=create_learning_entries(Record,DataError)


class Learning(LearningEntries,CollectionTable):
    """One Growth.bin document containing LID and optional GLID editing views."""
    group_name='技能習得';layout=(72,5);prefix='LID_'
    project_format='fw-growth-edits-v1'
    expected_fields={0x20:('u8',1),0x21:('u8',1),0x22:('u8',1),0x28:('data',16),0x38:('string[]',16)}

    def __init__(self,raw):
        super().__init__(raw)
        self.progression=Progression(raw,self) if any(g[0]=='成長リスト' for g in self.groups()) else None
        self.views=attach_expanded(self,GROWTH_EXPANDED_KEYS)

    def edit_target(self,pid,offset):
        if pid.partition(':')[0] in self.views:
            view=self.views[pid.partition(':')[0]];return view.by_pid[pid],view.by_offset[offset]
        view=self.progression if pid.startswith('GLID_') else self
        if view is None:raise DataError('This Growth.bin has no supported GLID group.')
        return view.by_pid[pid],view.by_offset[offset]

    def build(self):
        validate_expanded(self)
        if self.added_count or self.added_list_count:
            expanded=Learning(expand_learning_raw(self,DataError))
            for (pid,offset),value in self.changes.items():
                if pid not in self._addition_values:
                    expanded.set(*expanded.edit_target(pid,offset),value)
            for pid in self._addition_values:
                row=self.by_pid[pid]
                for field in self.fields:expanded.set(expanded.by_pid[pid],field,self.value(row,field))
            return expanded.build()
        return super().build()

    def project(self):
        changes=[];auxiliary=[]
        for (key,offset),value in sorted(self.changes.items()):
            if key.partition(':')[0] in self.views:
                auxiliary.append({'pid':key,'offset':offset,'value':value});continue
            view=self.progression if key.startswith('GLID_') else self
            table,row=view.row_location[key]
            changes.append({'table':table,'row':row,'offset':offset,'value':value})
        project={'format':self.project_format,'source_sha256':self.fingerprint,'changes':changes}
        if auxiliary:project.update(format='fw-growth-edits-v2',source_file=self.filename,aux_changes=auxiliary)
        if self.added_count or self.added_list_count:
            project.update(format='fw-growth-edits-v3',source_file=self.filename,new_entries=[
                {'table':table.pid,'values':{str(offset):deepcopy(value) for offset,value in values.items()}}
                for table in self.collections for values in self.added_entries.get(table.pid,())])
        if self.added_list_count:project.update(format='fw-growth-edits-v4',new_lists=list(self.new_lists))
        return project

    def load_project(self,project):
        legacy=project.get('format')=='fw-learning-edits-v1'
        if project.get('format') not in (self.project_format,'fw-learning-edits-v1','fw-growth-edits-v2','fw-growth-edits-v3','fw-growth-edits-v4') or project.get('source_sha256')!=self.fingerprint:
            raise DataError('This project belongs to a different source Growth.bin.')
        if project.get('format') in ('fw-growth-edits-v2','fw-growth-edits-v3','fw-growth-edits-v4') and project.get('source_file')!=self.filename:raise DataError('Growth project belongs to a different source file.')
        if project.get('format') not in ('fw-growth-edits-v2','fw-growth-edits-v3','fw-growth-edits-v4') and project.get('aux_changes'):raise DataError('Expanded changes require the Growth v2 format.')
        if project.get('format') not in ('fw-growth-edits-v3','fw-growth-edits-v4') and project.get('new_entries'):raise DataError('New learning entries require the Growth v3 format.')
        if project.get('format')!='fw-growth-edits-v4' and project.get('new_lists'):raise DataError('New learning lists require the Growth v4 format.')
        before=self.snapshot_edits()
        try:
            self.clear_edits()
            if project.get('format')=='fw-growth-edits-v4':
                lists=project.get('new_lists')
                if not isinstance(lists,list):raise DataError('New learning lists must be a list of unique LID_ IDs.')
                for key in lists:self.create_list(key)
            if project.get('format') in ('fw-growth-edits-v3','fw-growth-edits-v4'):
                additions=project.get('new_entries')
                if not isinstance(additions,list):raise DataError('New learning entries must be a list.')
                for entry in additions:
                    if not isinstance(entry,dict) or set(entry)!= {'table','values'} or not isinstance(entry['values'],dict):raise DataError('Invalid new learning entry.')
                    if set(entry['values'])!={str(f.offset) for f in self.fields}:raise DataError('New learning entries must include all five fields.')
                    self.append_entry(entry['table'],{int(offset):value for offset,value in entry['values'].items()})
            for change in project['changes']:
                key=change['lid' if legacy else 'table']
                view=self.progression if key.startswith('GLID_') and not legacy else self
                if view is None:raise DataError('No supported GLID data in this source file.')
                rows=view.rows_by_table[key];index=change['row']
                if type(index) is not int or not 0<=index<len(rows):raise DataError('Invalid collection entry index.')
                view.set(rows[index],view.by_offset[change['offset']],change['value'])
            for change in project.get('aux_changes',[]):
                pid=change['pid'];view=self.views[pid.partition(':')[0]]
                view.set(*self.edit_target(pid,change['offset']),change['value'])
            validate_expanded(self)
        except Exception:self.restore_edits(before);raise


from reliance_data import create_models,SECTIONS as RELIANCE_SECTIONS
Reliance,RelianceView=create_models(Binary,EditableTable,Field,Record,DataError,
    set(FORMATS)|TEXT_TYPES|LIST_TYPES|FLOAT_TYPES|set(NUMERIC_ARRAYS))


from appearance_data import create_models as create_appearance_models,SECTIONS as APPEARANCE_SECTIONS
Appearance,AppearanceP0,AppearanceP1,AppearanceView=create_appearance_models(Binary,EditableTable,Field,Record,DataError,
    set(FORMATS)|TEXT_TYPES|LIST_TYPES|FLOAT_TYPES|{'color'})
APPEARANCE_TABLES=(Appearance,AppearanceP0,AppearanceP1)

from profile_data import create_models as create_profile_models, SECTIONS as PROFILE_SECTIONS
Profile,ProfileView=create_profile_models(Binary,EditableTable,Field,Record,DataError,
    set(FORMATS)|TEXT_TYPES|LIST_TYPES|set(NUMERIC_ARRAYS))


from facility_data import create_models as create_facility_models
Facility,Reward,RewardP0,RewardP1,FacilityView=create_facility_models(Binary,EditableTable,Field,Record,DataError,
    set(FORMATS)|TEXT_TYPES|LIST_TYPES|FLOAT_TYPES|set(NUMERIC_ARRAYS))
FACILITY_TABLES=(Facility,Reward,RewardP0,RewardP1)

from shop_data import create_model as create_shop_model,SECTIONS as SHOP_SECTIONS
ShopView=create_shop_model(CollectionTable,Field,Record,DataError)

from deployment_data import create_models as create_deployment_models
Deployment,DeploymentView=create_deployment_models(Binary,EditableTable,CollectionTable,Field,Record,DataError)

from expanded_data import create_models as create_expanded_models,PERSON_KEYS as PERSON_EXPANDED_KEYS,GROWTH_KEYS as GROWTH_EXPANDED_KEYS,validate_views as validate_expanded
ExpandedView,GrowthSide,attach_expanded=create_expanded_models(Binary,EditableTable,CollectionTable,Field,Record,DataError)


from event_data import create_models as create_event_models,EVENT_FILES
EventData,EventView=create_event_models(Binary,EditableTable,CollectionTable,Field,Record,DataError)


def suite_project(documents):
    return {'format':'fw-hacking-suite-project-v2' if any(doc.filename.startswith('Script/') for doc in documents.values()) else 'fw-hacking-suite-project-v1',
            'documents':{doc.filename:doc.project() for doc in documents.values()}}


def load_suite_project(documents, project):
    by_name = {doc.filename:doc for doc in documents.values()}
    if project.get('format') in ('fw-hacking-suite-project-v1','fw-hacking-suite-project-v2'):
        payload = project.get('documents')
        if not isinstance(payload,dict) or not payload:
            raise DataError('Project has no table data.')
    else:
        filename = {'fw-character-edits-v1':'Person.bin','fw-class-edits-v1':'Job.bin','fw-class-edits-v2':'Job.bin','fw-learning-edits-v1':'Growth.bin','fw-growth-edits-v1':'Growth.bin','fw-reliance-edits-v1':'Reliance.bin','fw-profile-edits-v1':'Profile.bin','fw-legion-edits-v1':'Legion.bin','fw-character-edits-v2':'Person.bin','fw-character-edits-v3':'Person.bin','fw-growth-edits-v2':'Growth.bin','fw-growth-edits-v3':'Growth.bin','fw-growth-edits-v4':'Growth.bin','fw-expanded-side-edits-v1':'Growth_P0.bin'}.get(project.get('format'))
        if project.get('format')=='fw-skill-edits-v1':
            filename=project.get('source_file')
            if filename not in {kind.filename for kind in SKILL_TABLES}:raise DataError('Unsupported skill source file.')
        if project.get('format') in ('fw-item-edits-v1','fw-item-edits-v2','fw-item-edits-v3'):
            filename=project.get('source_file')
            if filename not in {kind.filename for kind in ITEM_TABLES}:raise DataError('Unsupported item source file.')
        if project.get('format')=='fw-appearance-edits-v1':
            filename=project.get('source_file')
            if filename not in {kind.filename for kind in APPEARANCE_TABLES}:raise DataError('Unsupported appearance source file.')
        if project.get('format')=='fw-facility-edits-v1':
            filename=project.get('source_file')
            if filename not in {kind.filename for kind in FACILITY_TABLES}:raise DataError('Unsupported facility/reward source file.')
        if project.get('format')=='fw-deployment-edits-v1':
            from deployment_data import valid_source
            filename=project.get('source_file')
            if not isinstance(filename,str) or not valid_source(filename):raise DataError('Unsupported deployment source file.')
        if project.get('format')=='fw-event-edits-v1':
            filename=project.get('source_file')
            if filename not in EVENT_FILES:raise DataError('Unsupported event source file.')
        if filename is None:raise DataError('Unsupported project format.')
        payload = {filename:project}
    missing = set(payload)-set(by_name)
    if missing:raise DataError('Open the source tables first: '+', '.join(sorted(missing)))
    before = {name:doc.snapshot_edits() for name,doc in by_name.items()}
    try:
        for name,doc in by_name.items():
            if name not in payload:doc.clear_edits()
        for name,content in payload.items():by_name[name].load_project(content)
        validate_new_item_ids(documents)
    except Exception:
        for name,state in before.items():by_name[name].restore_edits(state)
        raise


def export_suite(documents, sources, directory):
    validate_new_item_ids(documents)
    directory = Path(directory)
    manifest = directory/'suite-edits.json'
    owned = set()
    if manifest.exists():
        try:
            content=json.loads(manifest.read_text(encoding='utf8'))
            if content.get('format') not in ('fw-hacking-suite-project-v1','fw-hacking-suite-project-v2'):raise ValueError()
            owned=set(content['documents'])
        except (OSError,ValueError,KeyError,TypeError):
            raise DataError('The existing suite manifest is invalid. Choose a separate output folder.')
    elif (directory/'character-edits.json').is_file():
        owned={'Person.bin'}
    if owned-{doc.filename for doc in documents.values()}:
        raise DataError('This mod contains sources that are not loaded. Open its suite project, load the required GameData/scripts, or choose a new output folder.')
    planned=[]
    for module,doc in documents.items():
        from script_data import ScriptDocument, valid_source as valid_script_source
        if isinstance(doc,ScriptDocument):
            if not valid_script_source(doc.filename):raise DataError('Invalid script output path.')
            target=directory/'romfs'/doc.filename
        else:target=directory/'romfs/GameData'/doc.filename
        if any(target.resolve()==Path(source).resolve() for source in sources.values()):
            raise DataError('Choose a separate mod folder, not the original game folder.')
        if target.exists() and doc.filename not in owned:
            raise DataError(f'{doc.filename} already exists and is not owned by this editor export.')
        planned.append((target,doc.build()))
    # Validate and build every table before changing any output file.
    for target,raw in planned:
        if target.exists():
            shutil.copy2(target,target.with_name(target.name+'.backup-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')))
        atomic_write(target,raw)
    atomic_write(manifest,json.dumps(suite_project(documents),ensure_ascii=False,indent=2).encode('utf8'))
    return [target for target,_ in planned]


def decompress(raw):
    if raw.startswith(b'MsgStdBn'):
        return raw
    if sys.platform == 'win32':
        from platform_support import decompress_windows
        try:
            return decompress_windows(raw)
        except ValueError as exc:
            raise DataError(str(exc)) from exc
    lib = ctypes.CDLL(ctypes.util.find_library('zstd') or 'libzstd.so.1')
    lib.ZSTD_getFrameContentSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    lib.ZSTD_getFrameContentSize.restype = ctypes.c_uint64
    lib.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
    lib.ZSTD_decompress.restype = ctypes.c_size_t
    lib.ZSTD_isError.argtypes = [ctypes.c_size_t]
    lib.ZSTD_isError.restype = ctypes.c_uint
    lib.ZSTD_getErrorName.argtypes = [ctypes.c_size_t]
    lib.ZSTD_getErrorName.restype = ctypes.c_char_p
    source = ctypes.create_string_buffer(raw)
    size = lib.ZSTD_getFrameContentSize(source, len(raw))
    if size == 0xFFFFFFFFFFFFFFFE:
        raise DataError('Invalid Zstandard message file.')
    capacity = max(65536, len(raw) * 4) if size == 0xFFFFFFFFFFFFFFFF else size
    while capacity <= 64 * 1024 * 1024:
        output = ctypes.create_string_buffer(capacity)
        result = lib.ZSTD_decompress(output, capacity, source, len(raw))
        if not lib.ZSTD_isError(result):
            return output.raw[:result]
        error = lib.ZSTD_getErrorName(result).decode()
        if 'too small' not in error.lower():
            raise DataError(error)
        capacity *= 2
    raise DataError('Decompressed message file exceeds 64 MiB.')


def messages(raw):
    raw = decompress(raw)
    if raw[:8] != b'MsgStdBn' or raw[8:10] != b'\xff\xfe' or raw[12] not in (0, 1):
        raise DataError('Unsupported message format.')
    sections, at = {}, 32
    for _ in range(struct.unpack_from('<H', raw, 14)[0]):
        size = struct.unpack_from('<I', raw, at + 4)[0]
        if at + 16 + size > len(raw):
            raise DataError('Invalid message section.')
        sections[raw[at:at + 4]] = raw[at + 16:at + 16 + size]
        at = (at + 16 + size + 15) & ~15
    labels, data = {}, sections[b'LBL1']
    for i in range(struct.unpack_from('<I', data)[0]):
        count, offset = struct.unpack_from('<II', data, 4 + i * 8)
        for _ in range(count):
            length = data[offset]
            label = data[offset + 1:offset + 1 + length].decode('utf-8')
            index = struct.unpack_from('<I', data, offset + 1 + length)[0]
            labels[index] = label
            offset += length + 5
    data = sections[b'TXT2']
    count = struct.unpack_from('<I', data)[0]
    offsets = list(struct.unpack_from(f'<{count}I', data, 4)) + [len(data)]
    result = {}
    for i in range(count):
        part = data[offsets[i]:offsets[i + 1]]
        if raw[12] == 0:
            clean, j = bytearray(), 0
            while j < len(part) and part[j]:
                if part[j] == 0x0E and j + 7 <= len(part):
                    length = struct.unpack_from('<H', part, j + 5)[0]
                    j += 7 + length
                elif part[j] == 0x0F:
                    j += 5
                else:
                    clean.append(part[j]); j += 1
            value = clean.decode('utf-8', errors='replace')
        else:
            value = part.decode('utf-16le', errors='replace').rstrip('\0')
        if i in labels:
            result[labels[i]] = value
    return result


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name + '.')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class RecentPaths:
    """Small local preference file; no game bytes or unsaved edits are stored."""
    def __init__(self,path):
        self.path=Path(path);self.values={}
        try:
            raw=json.loads(self.path.read_text(encoding='utf8'))
            if isinstance(raw,dict):
                for key in ('last_data','last_names','last_export'):
                    if isinstance(raw.get(key),str) and raw[key]:self.values[key]=raw[key]
                project=raw.get('last_project')
                if isinstance(project,dict) and all(isinstance(project.get(key),str) and project[key] for key in ('path','data')):
                    self.values['last_project']={key:project[key] for key in ('path','data','names','module','skill_source','item_source','support_section','appearance_source','appearance_section','profile_section','facility_source','facility_section','shop_source','shop_section','deployment_source','expanded_source','expanded_section','event_source') if isinstance(project.get(key),str)}
        except (OSError,ValueError):pass

    def update(self,**values):
        updated=dict(self.values);updated.update(values)
        atomic_write(self.path,json.dumps(updated,ensure_ascii=False,indent=2).encode('utf8'))
        self.values=updated

    def initial_dir(self,key):
        value=self.values.get(key)
        if key=='last_project':value=self.values.get(key,{}).get('path')
        if not value:return str(Path.home())
        path=Path(value).expanduser()
        if key=='last_project' or path.is_file():path=path.parent
        return str(path) if path.is_dir() else str(Path.home())


def read_editable_tables(base):
    documents={};sources={}
    for name,kind in (('Characters',Person),('Classes',Job),('Learning tables',Learning),('Legion',Legion)):
        source=Path(base)/kind.filename
        if source.is_file():documents[name]=kind(source.read_bytes());sources[name]=source.resolve()
    for kind in SKILL_TABLES:
        source=Path(base)/kind.filename
        name='Skills' if kind is Skill else 'Skills · '+kind.filename
        if source.is_file():documents[name]=kind(source.read_bytes());sources[name]=source.resolve()
    for kind in ITEM_TABLES:
        source=Path(base)/kind.filename
        name='Items' if kind is Item else 'Items · '+kind.filename
        if source.is_file():documents[name]=kind(source.read_bytes());sources[name]=source.resolve()
    source=Path(base)/'Reliance.bin'
    if source.is_file():documents['Supports & Recruitment']=Reliance(source.read_bytes());sources['Supports & Recruitment']=source.resolve()
    source=Path(base)/'Profile.bin'
    if source.is_file():documents['Profiles & Affiliations']=Profile(source.read_bytes());sources['Profiles & Affiliations']=source.resolve()
    for kind in APPEARANCE_TABLES:
        source=Path(base)/kind.filename
        name='Appearance rules' if kind is Appearance else 'Appearance rules · '+kind.filename
        if source.is_file():documents[name]=kind(source.read_bytes());sources[name]=source.resolve()
    for kind in FACILITY_TABLES:
        source=Path(base)/kind.filename
        name='Facilities & Rewards' if kind is Facility else 'Facilities & Rewards · '+kind.filename
        if source.is_file():documents[name]=kind(source.read_bytes());sources[name]=source.resolve()
    source=Path(base)/GrowthSide.filename
    if source.is_file():documents['Progression & Difficulty · '+GrowthSide.filename]=GrowthSide(source.read_bytes());sources['Progression & Difficulty · '+GrowthSide.filename]=source.resolve()
    for source in sorted((Path(base)/'Dispos').glob('*.bin')):
        filename='Dispos/'+source.name;name='Battle deployment · '+source.name
        documents[name]=Deployment(source.read_bytes(),filename);sources[name]=source.resolve()
    for filename in EVENT_FILES:
        source=Path(base)/filename;name='Events' if filename=='Variable.bin' else 'Events · '+filename
        if source.is_file():documents[name]=EventData(source.read_bytes(),filename);sources[name]=source.resolve()
    return documents,sources


def export_mod(document, source, directory):
    target = Path(directory) / 'romfs/GameData/Person.bin'
    if target.resolve() == Path(source).resolve():
        raise DataError('Choose a separate mod folder, not the original game folder.')
    if target.exists() and not (Path(directory) / 'character-edits.json').is_file():
        raise DataError('That folder already contains character data. Choose an empty mod folder or an earlier editor export.')
    result = document.build()
    if target.exists():
        shutil.copy2(target, target.with_name('Person.bin.backup-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f')))
    atomic_write(target, result)
    atomic_write(Path(directory) / 'character-edits.json', json.dumps(document.project(), ensure_ascii=False, indent=2).encode('utf-8'))
    return target


def main():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    class Editor(tk.Tk):
        number_text=staticmethod(number_text)
        def __init__(self):
            super().__init__()
            self.title(f"{APP_NAME} {VERSION}")
            self.geometry('1180x780'); self.minsize(1000, 680)
            self.doc = None; self.source = None; self.current = None
            self.saved_state = None
            self.documents = {}; self.sources = {}; self.module_tabs = {}
            self.module = tk.StringVar(value='Characters')
            self.active_module = 'Characters'
            self.asset_index=None;self.current_aid=None;self.data_directory=None
            self.learning_row=None;self.learning_clipboard=None
            self.aid_source=tk.StringVar(value='All files');self.aid_group_files=tk.BooleanVar(value=True)
            self.current_aid_source=None;self.aid_tree_map={}
            self.skill_source=tk.StringVar(value='Skill.bin');self.skill_index=None
            self.item_source=tk.StringVar(value='Item.bin');self.item_index=None
            self.support_section=tk.StringVar(value='matrix');self.support_commit=None;self.support_dirty=None
            self.appearance_source=tk.StringVar(value='AssetTable.bin');self.appearance_section=tk.StringVar(value='rules');self.appearance_clipboard=None
            self.profile_section=tk.StringVar(value='profiles')
            self.facility_source=tk.StringVar(value='Facility.bin');self.facility_section=tk.StringVar(value='cooking');self.facility_group_index=-1
            self.shop_source=tk.StringVar(value='Item.bin');self.shop_section=tk.StringVar(value='shops');self.shop_clipboard=None
            self.deployment_source=tk.StringVar(value='');self.deployment_clipboard=None;self.battle_links=[]
            self.expanded_source=tk.StringVar(value='Growth.bin');self.expanded_section=tk.StringVar(value='exp_curve');self.expanded_clipboard=None
            self.event_source=tk.StringVar(value='Variable.bin');self.event_clipboard=None
            self.legion_clipboard=None
            self.names = {}; self.catalog = {}; self.widgets = {}; self.suggestion_cache = {};self.live_item_names={};self.live_class_names={};self.live_character_names={}
            self.previews = {}; self.pending_previews = {}; self.preview_bindings = []
            from platform_support import config_directory
            self.glossary_path = config_directory() / 'translations.json'
            self.preferences=RecentPaths(self.glossary_path.with_name('recent-paths.json'))
            self.names_directory=None;self.project_path=None
            self.custom_translations = {}
            try:
                candidate = json.loads(self.glossary_path.read_text(encoding='utf8'))
                if isinstance(candidate, dict):
                    self.custom_translations = {k:v for k,v in candidate.items()
                                                if isinstance(k,str) and k and isinstance(v,str) and v}
            except (OSError, ValueError): pass
            self.translator = Translator(overrides=self.custom_translations)
            self.search = tk.StringVar(); self.variants = tk.BooleanVar(value=False)
            self.status = tk.StringVar(value='Open your extracted game folder to begin. Translations work offline.')
            self.heading = tk.StringVar(value='Select a character')
            self.details = tk.StringVar(value='Fortune’s Weave 1.00 · Character data')
            self.translation_status = tk.StringVar(value='Load English names for game translations')
            style = ttk.Style(self); style.theme_use('clam')
            style.configure('.', font=('DejaVu Sans', 9), background='#f4f5f7')
            style.configure('TButton', padding=(7, 3))
            style.configure('TNotebook.Tab', padding=(10, 5))
            style.configure('Treeview', rowheight=23, background='white', fieldbackground='white')
            style.configure('Treeview.Heading', padding=(4, 4))
            style.configure('Title.TLabel', font=('DejaVu Sans', 15, 'bold'))
            style.configure('Hint.TLabel', foreground='#596776', font=('DejaVu Sans', 8))
            style.configure('English.TLabel', foreground='#145868', background='#edf5f5', padding=(6, 3))
            style.configure('Missing.TLabel', foreground='#89612c', background='#fff7e8', padding=(6, 3))
            style.configure('Accent.TButton', foreground='white', background='#286b78')
            menu = tk.Menu(self)
            file_menu = tk.Menu(menu, tearoff=False)
            for label, action in [('Open last project',self.open_last_project),('Open game data…', self.open_data), ('Load English names…', self.load_names),
                                  ('Open project…', self.load_project), ('Save project…', self.save_project),
                                  ('Export mod…', self.export)]:
                file_menu.add_command(label=label, command=action)
            menu.add_cascade(label='File', menu=file_menu)
            tools_menu = tk.Menu(menu, tearoff=False)
            tools_menu.add_command(label='Translation glossary…', command=self.glossary)
            tools_menu.add_command(label='Script editor…', command=lambda:__import__('script_ui').open_editor(self))
            menu.add_cascade(label='Tools', menu=tools_menu)
            self.configure(menu=menu)
            top = ttk.Frame(self, padding=(8, 6)); top.pack(fill='x')
            ttk.Label(top, text=APP_NAME, font=('DejaVu Sans', 10, 'bold')).pack(side='left', padx=(0, 14))
            self.open_last_button=ttk.Button(top,text='Open last project',command=self.open_last_project,
                                             state='normal' if self.preferences.values.get('last_project') else 'disabled')
            self.open_last_button.pack(side='left',padx=2)
            for label, action in [('Open data…', self.open_data), ('English names…', self.load_names),
                                  ('Save project…', self.save_project), ('Glossary…', self.glossary)]:
                ttk.Button(top, text=label, command=action).pack(side='left', padx=2)
            ttk.Button(top, text='Export mod…', command=self.export, style='Accent.TButton').pack(side='right')
            pane = ttk.Panedwindow(self, orient='horizontal'); pane.pack(fill='both', expand=True, padx=8)
            left = ttk.Frame(pane, width=245, padding=(0, 0, 7, 0)); pane.add(left, weight=0)
            module_row=ttk.Frame(left); module_row.pack(fill='x',pady=(0,6))
            ttk.Label(module_row,text='Module').pack(side='left',padx=(0,5))
            self.module_choice=ttk.Combobox(module_row,textvariable=self.module,values=('Characters','Classes','AIDs','Learning tables','GLID progression','Skills','Items','Supports & Recruitment','Appearance rules','Profiles & Affiliations','Facilities & Rewards','Shop & Loot','Battle deployment','Legion','Progression & Difficulty','Events'),state='readonly',width=17)
            self.module_choice.pack(side='left',fill='x',expand=True)
            self.module_choice.bind('<<ComboboxSelected>>',lambda _:self.switch_module())
            search_row = ttk.Frame(left); search_row.pack(fill='x', pady=(0, 4))
            ttk.Label(search_row, text='Find').pack(side='left', padx=(0, 5))
            entry = ttk.Entry(search_row, textvariable=self.search); entry.pack(side='left', fill='x', expand=True)
            ttk.Button(search_row, text='×', width=2, command=lambda:self.search.set('')).pack(side='right', padx=(3,0))
            self.aid_controls=ttk.Frame(left)
            source_row=ttk.Frame(self.aid_controls);source_row.pack(fill='x')
            ttk.Label(source_row,text='Source').pack(side='left',padx=(0,5))
            self.aid_source_choice=ttk.Combobox(source_row,textvariable=self.aid_source,values=('All files',),state='readonly',width=17)
            self.aid_source_choice.pack(side='left',fill='x',expand=True)
            self.aid_source_choice.bind('<<ComboboxSelected>>',lambda _:self.filter_aids())
            ttk.Checkbutton(self.aid_controls,text='Group by file',variable=self.aid_group_files,command=self.filter_aids).pack(anchor='w',pady=(3,0))
            self.skill_controls=ttk.Frame(left)
            ttk.Label(self.skill_controls,text='Source').pack(side='left',padx=(0,5))
            self.skill_source_choice=ttk.Combobox(self.skill_controls,textvariable=self.skill_source,state='readonly',width=17)
            self.skill_source_choice.pack(side='left',fill='x',expand=True)
            self.skill_source_choice.bind('<<ComboboxSelected>>',lambda _:self.switch_module('Skills',source_file=self.skill_source.get()))
            self.item_controls=ttk.Frame(left)
            ttk.Label(self.item_controls,text='Source').pack(side='left',padx=(0,5))
            self.item_source_choice=ttk.Combobox(self.item_controls,textvariable=self.item_source,state='readonly',width=17)
            self.item_source_choice.pack(side='left',fill='x',expand=True)
            self.item_source_choice.bind('<<ComboboxSelected>>',lambda _:self.switch_module('Items',source_file=self.item_source.get()))
            self.support_controls=ttk.Frame(left)
            ttk.Label(self.support_controls,text='Section').pack(side='left',padx=(0,5))
            self.support_section_choice=ttk.Combobox(self.support_controls,state='readonly',width=17,
                values=[spec[0] for spec in RELIANCE_SECTIONS.values()])
            self.support_section_choice.pack(side='left',fill='x',expand=True)
            self.support_section_choice.bind('<<ComboboxSelected>>',lambda _:self.switch_module('Supports & Recruitment',
                section=list(RELIANCE_SECTIONS)[self.support_section_choice.current()]))
            self.appearance_controls=ttk.Frame(left)
            for label,var,attribute in [('Source',self.appearance_source,'appearance_source_choice'),('Section',self.appearance_section,'appearance_section_choice')]:
                row=ttk.Frame(self.appearance_controls);row.pack(fill='x',pady=(0,3))
                ttk.Label(row,text=label,width=7).pack(side='left')
                choice=ttk.Combobox(row,state='readonly',width=16);choice.pack(side='left',fill='x',expand=True)
                setattr(self,attribute,choice)
            self.appearance_source_choice.configure(textvariable=self.appearance_source)
            self.appearance_source_choice.bind('<<ComboboxSelected>>',lambda _:self.switch_module('Appearance rules',source_file=self.appearance_source.get()))
            self.appearance_section_choice.bind('<<ComboboxSelected>>',lambda _:self.switch_module('Appearance rules',
                section=next(key for key,v in self.doc.owner.views.items() if v.title==self.appearance_section_choice.get())))
            self.profile_controls=ttk.Frame(left)
            ttk.Label(self.profile_controls,text='Section',width=7).pack(side='left')
            self.profile_section_choice=ttk.Combobox(self.profile_controls,state='readonly',width=16,values=[s[0] for s in PROFILE_SECTIONS.values()])
            self.profile_section_choice.pack(side='left',fill='x',expand=True)
            self.profile_section_choice.bind('<<ComboboxSelected>>',lambda _:self.switch_module('Profiles & Affiliations',
                section=list(PROFILE_SECTIONS)[self.profile_section_choice.current()]))
            self.facility_controls=ttk.Frame(left)
            for label,attribute in [('Source','facility_source_choice'),('Section','facility_section_choice'),('Group','facility_group_choice')]:
                row=ttk.Frame(self.facility_controls);row.pack(fill='x',pady=(0,3))
                ttk.Label(row,text=label,width=7).pack(side='left')
                choice=ttk.Combobox(row,state='readonly',width=16);choice.pack(side='left',fill='x',expand=True)
                setattr(self,attribute,choice)
                if label=='Group':self.facility_group_row=row
            self.facility_source_choice.configure(textvariable=self.facility_source)
            self.facility_source_choice.bind('<<ComboboxSelected>>',lambda _:self.switch_module('Facilities & Rewards',source_file=self.facility_source.get()))
            self.facility_section_choice.bind('<<ComboboxSelected>>',lambda _:self.switch_module('Facilities & Rewards',
                section=list(self.doc.owner.views)[self.facility_section_choice.current()]))
            self.facility_group_choice.bind('<<ComboboxSelected>>',lambda _:self.change_facility_group())
            self.shop_controls=ttk.Frame(left)
            for label,attribute in [('Source','shop_source_choice'),('Section','shop_section_choice')]:
                row=ttk.Frame(self.shop_controls);row.pack(fill='x',pady=(0,3));ttk.Label(row,text=label,width=7).pack(side='left')
                choice=ttk.Combobox(row,state='readonly',width=16);choice.pack(side='left',fill='x',expand=True);setattr(self,attribute,choice)
            self.deployment_controls=ttk.Frame(left)
            ttk.Label(self.deployment_controls,text='Deployment file').pack(anchor='w')
            self.deployment_source_choice=ttk.Combobox(self.deployment_controls,textvariable=self.deployment_source,state='readonly')
            self.deployment_source_choice.pack(fill='x')
            self.deployment_source_choice.bind('<<ComboboxSelected>>',lambda _:self.switch_module('Battle deployment',source_file=self.deployment_source.get()))
            self.expanded_controls=ttk.Frame(left)
            for label,attribute in [('Source','expanded_source_choice'),('Section','expanded_section_choice')]:
                row=ttk.Frame(self.expanded_controls);row.pack(fill='x',pady=(0,3));ttk.Label(row,text=label,width=7).pack(side='left')
                choice=ttk.Combobox(row,state='readonly');choice.pack(side='left',fill='x',expand=True);setattr(self,attribute,choice)
            self.expanded_source_choice.configure(textvariable=self.expanded_source)
            self.expanded_source_choice.bind('<<ComboboxSelected>>',lambda _:self.switch_module('Progression & Difficulty',source_file=self.expanded_source.get()))
            self.expanded_section_choice.bind('<<ComboboxSelected>>',lambda _:self.switch_module('Progression & Difficulty',section=list(self.doc.owner.views)[self.expanded_section_choice.current()]))
            self.shop_source_choice.configure(textvariable=self.shop_source)
            self.shop_source_choice.bind('<<ComboboxSelected>>',lambda _:self.switch_module('Shop & Loot',source_file=self.shop_source.get()))
            self.shop_section_choice.bind('<<ComboboxSelected>>',lambda _:self.switch_module('Shop & Loot',section=list(self.doc.owner.views)[self.shop_section_choice.current()]))
            self.event_controls=ttk.Frame(left)
            ttk.Label(self.event_controls,text='Event source').pack(anchor='w')
            self.event_source_choice=ttk.Combobox(self.event_controls,textvariable=self.event_source,state='readonly')
            self.event_source_choice.pack(fill='x')
            self.event_source_choice.bind('<<ComboboxSelected>>',lambda _:self.switch_module('Events',source_file=self.event_source.get()))
            self.variant_button=ttk.Checkbutton(left,text='Scenario / test records',variable=self.variants,command=self.filter)
            self.variant_button.pack(anchor='w',pady=(0,4))
            listing = ttk.Frame(left); listing.pack(fill='both', expand=True)
            self.tree = ttk.Treeview(listing, columns=('serial', 'id'), displaycolumns=('serial',), show='tree headings', selectmode='browse')
            self.tree.heading('#0', text='Character'); self.tree.heading('serial', text='Slot'); self.tree.heading('id', text='Internal ID')
            self.tree.column('#0', width=173); self.tree.column('serial', width=40, stretch=False); self.tree.column('id', width=0, stretch=False)
            scroll = ttk.Scrollbar(listing, orient='vertical', command=self.tree.yview)
            self.tree.configure(yscrollcommand=scroll.set); self.tree.pack(side='left', fill='both', expand=True); scroll.pack(side='right', fill='y')
            self.count_label = ttk.Label(left, text='No data loaded', style='Hint.TLabel'); self.count_label.pack(anchor='w', pady=4)
            right = ttk.Frame(pane, padding=(7, 0, 0, 0)); pane.add(right, weight=1)
            header = ttk.Frame(right); header.pack(fill='x', pady=(0, 5))
            ttk.Label(header, textvariable=self.heading, style='Title.TLabel').pack(anchor='w')
            ttk.Label(header, textvariable=self.details, style='Hint.TLabel').pack(anchor='w', pady=(2,0))
            self.notebook = ttk.Notebook(right); self.notebook.pack(fill='both', expand=True)
            bottom = ttk.Frame(right); bottom.pack(fill='x', pady=5)
            self.apply_button=ttk.Button(bottom,text='Apply edits',command=self.apply,style='Accent.TButton')
            self.apply_button.pack(side='left')
            self.reset_button=ttk.Button(bottom,text='Reset entry',command=self.reset)
            self.reset_button.pack(side='left',padx=5)
            self.copy_item_button=ttk.Button(bottom,text='Copy IID',command=self.copy_item)
            self.copy_skill_button=ttk.Button(bottom,text='Copy SID',command=self.copy_skill)
            self.copy_aid_button=ttk.Button(bottom,text='Copy AID',command=self.copy_aid)
            self.readonly_hint=ttk.Label(bottom,text='AID browser · open a rule to edit its appearance settings',style='Hint.TLabel')
            ttk.Label(bottom, textvariable=self.translation_status, style='Hint.TLabel').pack(side='right')
            self.path_label = ttk.Label(self, text='Original files stay unchanged. Export writes a separate mod.', style='Hint.TLabel', padding=(8,2))
            self.path_label.pack(fill='x')
            ttk.Label(self, textvariable=self.status, padding=(8,5), relief='sunken', anchor='w').pack(fill='x')
            self.after_idle(lambda:pane.sashpos(0, 245))
            self.search.trace_add('write', lambda *_: self.filter())
            self.tree.bind('<<TreeviewSelect>>', self.select)
            self.bind('<Control-o>', lambda _: self.open_data())
            self.bind('<Control-s>', lambda _: self.save_project())
            self.protocol('WM_DELETE_WINDOW', self.close)
            if len(sys.argv)>1:
                self.after(100,lambda:self.open_data(sys.argv[1]))
            elif self.preferences.values.get('last_project'):
                self.status.set('Last project: '+Path(self.preferences.values['last_project']['path']).name+' · choose Open last project to resume.')

        def error(self, exc):
            messagebox.showerror(APP_NAME, str(exc), parent=self)

        def remember_paths(self, **values):
            try:self.preferences.update(**values)
            except OSError as exc:self.error('Your data is open, but the last-used paths could not be saved: '+str(exc))
            self.open_last_button.configure(state='normal' if self.preferences.values.get('last_project') else 'disabled')

        def remember_project(self, path):
            self.project_path=Path(path).resolve()
            context={'path':str(self.project_path),'data':str(self.data_directory),
                     'names':str(self.names_directory) if self.names_directory else '', 'module':self.active_module,'skill_source':self.skill_source.get(),'item_source':self.item_source.get(),'support_section':self.support_section.get(),'appearance_source':self.appearance_source.get(),'appearance_section':self.appearance_section.get(),'profile_section':self.profile_section.get(),'facility_source':self.facility_source.get(),'facility_section':self.facility_section.get(),'shop_source':self.shop_source.get(),'shop_section':self.shop_section.get(),'deployment_source':self.deployment_source.get(),'expanded_source':self.expanded_source.get(),'expanded_section':self.expanded_section.get(),'event_source':self.event_source.get()}
            self.remember_paths(last_project=context)

        def open_last_project(self):
            context=dict(self.preferences.values.get('last_project',{}))
            if not context:self.status.set('Save or open a project first to enable reopening it.');return False
            try:
                project_path=Path(context['path']);base=Path(context['data'])
                if not project_path.is_file():raise DataError('Last project was not found: '+str(project_path)+'\nUse File → Open project to select its new location.')
                if not base.is_dir():raise DataError('The project data folder is unavailable: '+str(base)+'\nMount its drive or use Open data to select the folder again.')
                project=json.loads(project_path.read_text(encoding='utf8'))
                documents,sources=read_editable_tables(base)
                if not documents:raise DataError('No editable source tables were found in '+str(base))
                # Validate every project fingerprint before replacing the current workspace.
                from script_data import load_with_scripts
                load_with_scripts(documents,sources,base,project,load_suite_project)
                if not self.open_data(base,prepared=(documents,sources)):return False
                note=''
                if context.get('names'):
                    if Path(context['names']).is_dir():
                        try:self.read_names(Path(context['names']))
                        except Exception as exc:note=' · English names could not be restored; choose English names…'
                    else:note=' · Saved English folder is unavailable; choose English names…'
                module=context.get('module','Characters')
                if module not in self.documents and module not in ('AIDs','GLID progression','Skills','Items','Supports & Recruitment','Appearance rules','Profiles & Affiliations','Facilities & Rewards','Shop & Loot','Battle deployment','Legion','Progression & Difficulty','Events'):module=next(iter(self.documents))
                self.switch_module(module,source_file=context.get('event_source') if module=='Events' else context.get('expanded_source') if module=='Progression & Difficulty' else context.get('deployment_source') if module=='Battle deployment' else context.get('shop_source') if module=='Shop & Loot' else context.get('facility_source') if module=='Facilities & Rewards' else context.get('appearance_source') if module=='Appearance rules' else context.get('item_source') if module=='Items' else context.get('skill_source'),section=context.get('expanded_section') if module=='Progression & Difficulty' else context.get('shop_section') if module=='Shop & Loot' else context.get('facility_section') if module=='Facilities & Rewards' else context.get('appearance_section') if module=='Appearance rules' else context.get('profile_section') if module=='Profiles & Affiliations' else context.get('support_section'))
                self.saved_state=self.session_state();self.remember_project(project_path)
                self.status.set('Reopened '+str(project_path)+note)
                return True
            except Exception as exc:self.error(exc);return False

        def display(self, record):
            if isinstance(self.doc,EventView):
                from event_ui import collection_name
                return collection_name(self,record)
            if isinstance(self.doc,ExpandedView):
                from expanded_ui import collection_name
                return collection_name(self,record)
            if isinstance(self.doc,Legion):
                from legion_ui import row_name
                return row_name(self,record)
            if isinstance(self.doc,DeploymentView):
                from deployment_ui import collection_name
                return collection_name(self,record)
            if isinstance(self.doc,ShopView):
                from shop_ui import collection_name
                return collection_name(self,record)
            if isinstance(self.doc,FacilityView):
                from facility_ui import row_name
                return row_name(self,record)
            if isinstance(self.doc,ProfileView):
                from profile_ui import row_name
                return row_name(self,record)
            if isinstance(self.doc,AppearanceView):
                from appearance_ui import row_name
                return row_name(self,record)
            if isinstance(self.doc,RelianceView):
                from supports_ui import row_name
                return row_name(self,record)
            if isinstance(self.doc,CollectionTable):
                result=self.translator.resolve(record.pid)
                return result.text.removeprefix('Learning: ').removeprefix('Progression: ') if result.source!='Untranslated' else record.pid.removeprefix(self.doc.prefix)
            key = self.doc.value(record, self.doc.by_offset[0x20])
            if self.names.get(key):return self.names[key]
            result=self.translator.resolve(record.pid)
            return result.text if result.source not in ('Untranslated','Identifier') else record.pid.removeprefix(self.doc.prefix)

        def switch_aids(self, aid=None):
            if self.asset_index is None:
                self.module.set(self.active_module);self.error('Open your GameData folder first.');return False
            if not self.apply(True):
                self.module.set(self.active_module)
                if isinstance(self.doc,EventView):self.event_source.set(self.doc.filename)
                if isinstance(self.doc,Skill):self.skill_source.set(self.doc.filename)
                if isinstance(self.doc,Item):self.item_source.set(self.doc.filename)
                if isinstance(self.doc,RelianceView):self.support_section_choice.set(self.doc.title)
                if isinstance(self.doc,ProfileView):self.profile_section_choice.set(self.doc.title)
                if isinstance(self.doc,ExpandedView):self.expanded_source.set(self.doc.filename);self.expanded_section_choice.set(self.doc.title)
                if isinstance(self.doc,DeploymentView):self.deployment_source.set(self.doc.filename)
                if isinstance(self.doc,ShopView):self.shop_source.set(self.doc.filename);self.shop_section_choice.set(self.doc.title)
                if isinstance(self.doc,FacilityView):
                    self.facility_source.set(self.doc.filename);self.facility_section_choice.set(self.doc.title)
                if isinstance(self.doc,AppearanceView):
                    self.appearance_source.set(self.doc.filename);self.appearance_section_choice.set(self.doc.title)
                return False
            if self.notebook.tabs():self.module_tabs[self.active_module]=self.notebook.index('current')
            self.clear_previews();self.widgets={};self.current=None;self.doc=None
            for tab in self.notebook.tabs():self.nametowidget(tab).destroy()
            self.skill_controls.pack_forget();self.item_controls.pack_forget();self.support_controls.pack_forget();self.appearance_controls.pack_forget();self.profile_controls.pack_forget();self.facility_controls.pack_forget();self.shop_controls.pack_forget();self.deployment_controls.pack_forget();self.expanded_controls.pack_forget();self.event_controls.pack_forget();self.copy_skill_button.pack_forget();self.copy_item_button.pack_forget()
            self.active_module='AIDs';self.module.set('AIDs');self.current_aid=aid
            self.apply_button.pack_forget();self.reset_button.pack_forget()
            self.copy_aid_button.pack(side='left');self.readonly_hint.pack(side='left',padx=7)
            self.variant_button.pack_forget()
            self.aid_controls.pack(before=self.tree.master,fill='x',pady=(0,4))
            self.tree.configure(displaycolumns=('serial','id'))
            self.tree.heading('#0',text='AID / English');self.tree.column('#0',width=137)
            self.tree.heading('serial',text='Users');self.tree.column('serial',width=48)
            self.tree.heading('id',text='Rows');self.tree.column('id',width=48)
            self.path_label.configure(text=str(self.data_directory)+' · AID sources and current appearance edits')
            self.search.set('');self.filter_aids()
            if self.notebook.tabs():self.notebook.select(min(self.module_tabs.get('AIDs',0),len(self.notebook.tabs())-1))
            self.status.set('AIDs: direct owners, conditional references and linked appearance records. Appearance rows reflect current edits.')
            return True

        def aid_item(self,aid,source=None):
            return next((item for item,(key,file) in self.aid_tree_map.items()
                         if key==aid and (source is None or source==file)),None)

        def select_aid(self,aid,source=None):
            item=self.aid_item(aid,source)
            if item is None:return False
            self.tree.selection_set(item)
            parent=self.tree.parent(item)
            if parent:self.tree.item(parent,open=True)
            self.tree.see(item)
            self.current_aid_source=self.aid_tree_map[item][1]
            self.show_aid(aid)
            return True

        def filter_aids(self):
            if self.asset_index is None or self.active_module!='AIDs':return
            self.asset_index.refresh_users(self.documents)
            files=self.asset_index.source_files()
            self.aid_source_choice.configure(values=['All files']+files)
            if self.aid_source.get() not in ['All files']+files:self.aid_source.set('All files')
            source=self.aid_source.get();query=self.search.get().casefold().strip()
            visible=[]
            for aid in self.asset_index.aids:
                if source!='All files' and source not in self.asset_index.sources_for(aid):continue
                result=self.translator.resolve(aid)
                title=result.text.removeprefix('Appearance: ') if result.source!='Untranslated' else aid.removeprefix('AID_')
                if query and query not in (aid+' '+title).casefold():continue
                visible.append((aid,title))
            visible.sort(key=lambda row:(row[1].casefold(),row[0].casefold()))
            expanded={item.removeprefix('file:') for item in self.tree.get_children() if item.startswith('file:') and self.tree.item(item,'open')}
            self.tree.delete(*self.tree.get_children());self.aid_tree_map={}
            if self.aid_group_files.get():
                grouped={file:[] for file in files if source=='All files' or file==source}
                for aid,title in visible:
                    for file in self.asset_index.sources_for(aid):
                        if file in grouped:grouped[file].append((aid,title))
                for file,rows in grouped.items():
                    if not rows:continue
                    parent='file:'+file
                    self.tree.insert('','end',iid=parent,text=f'{file} · {len(rows)}',open=file in expanded)
                    for aid,title in rows:
                        item='aid:'+json.dumps([file,aid],ensure_ascii=False)
                        self.aid_tree_map[item]=(aid,file)
                        self.tree.insert(parent,'end',iid=item,text=title,values=(self.asset_index.direct_count(aid),len(self.asset_index.rows_by_aid.get(aid,[]))))
            else:
                for aid,title in visible:
                    self.aid_tree_map[aid]=(aid,source if source!='All files' else None)
                    self.tree.insert('','end',iid=aid,text=title,values=(self.asset_index.direct_count(aid),len(self.asset_index.rows_by_aid.get(aid,[]))))
            self.count_label.configure(text=f'{len(visible)} / {len(self.asset_index.aids)} AIDs')
            if visible:
                aid=self.current_aid if self.aid_item(self.current_aid) else 'AID_ディートリヒ' if self.aid_item('AID_ディートリヒ') else visible[0][0]
                item=self.aid_item(aid,self.current_aid_source) or self.aid_item(aid)
                selected_source=self.aid_tree_map[item][1]
                view_state=(aid,selected_source,self.session_state())
                changed=view_state!=getattr(self,'aid_view_state',None)
                self.aid_view_state=view_state
                self.tree.selection_set(item)
                parent=self.tree.parent(item)
                if parent:self.tree.item(parent,open=True)
                self.tree.see(item);self.current_aid_source=selected_source
                if changed or not self.notebook.tabs():self.show_aid(aid)
            else:
                self.current_aid=None;self.current_aid_source=None
                for tab in self.notebook.tabs():self.nametowidget(tab).destroy()
                self.heading.set('No matching AIDs');self.details.set('Try another source file, English name or raw AID.')

        def show_aid(self, aid):
            if self.asset_index is None or aid not in self.asset_index.aids:return
            from aid_ui import show_aid
            show_aid(self,aid)

        def copy_item(self):
            if not isinstance(self.doc,Item) or not self.current:return
            self.clipboard_clear();self.clipboard_append(self.current.pid);self.status.set('Copied '+self.current.pid)

        def copy_skill(self):
            if not isinstance(self.doc,Skill) or not self.current:return
            self.clipboard_clear();self.clipboard_append(self.current.pid);self.status.set('Copied '+self.current.pid)

        def copy_aid(self):
            if not self.current_aid:return
            self.clipboard_clear();self.clipboard_append(self.current_aid)
            self.status.set('Copied '+self.current_aid)

        def dirty_widgets(self):
            if not self.current:
                return False
            record=self.learning_row if isinstance(self.doc,CollectionTable) else self.current
            if record is None:return False
            if isinstance(self.doc,RelianceView) and self.support_dirty and self.support_dirty():return True
            return any(self.widget_value(f, w) != self.doc.value(record, f)
                       for f, w in self.widgets.values())

        def multiline_text(self,field):
            return field.kind=='string' and self.doc is not None and field.offset in self.doc.multiline_offsets

        def widget_value(self, field, widget):
            raw = widget.get('1.0', 'end-1c') if field.kind in LIST_TYPES or field.kind in NUMERIC_ARRAYS or self.multiline_text(field) else widget.get()
            if field.kind=='color':return raw_color(raw)
            if field.kind in FLOAT_TYPES:
                try:return float32(float(raw))
                except ValueError as exc:raise DataError(f'{field.label}: enter a decimal number.') from exc
            if field.kind in NUMERIC_ARRAYS:
                try:return json.loads(raw) if raw.strip() else []
                except ValueError as exc:raise DataError(f'{field.label}: enter a JSON list such as [1, 2, 3].') from exc
            if field.kind in FORMATS:
                try: return int(raw, 10)
                except ValueError: raise DataError(f'{field.label}: enter a whole number.')
            if field.kind in NESTED_TYPES:
                try:rows=[json.loads(line) for line in raw.splitlines() if line.strip()]
                except ValueError as exc:raise DataError(field.label+': use one JSON list of strings per line.') from exc
                return rows
            return [line.strip() for line in raw.splitlines() if line.strip()] if field.kind in LIST_TYPES else raw

        def apply(self, quiet=False):
            if not self.current:
                return True
            record=self.learning_row if isinstance(self.doc,CollectionTable) else self.current
            if record is None:return True
            before = dict(self.doc.changes)
            try:
                if isinstance(self.doc,RelianceView) and self.support_commit:self.support_commit()
                for field, widget in self.widgets.values():
                    if field.offset not in self.doc.locked_offsets:
                        self.doc.set(record, field, self.widget_value(field, widget))
                if isinstance(self.doc,(ProfileView,FacilityView,ShopView,DeploymentView,ExpandedView,EventView)):self.doc.validate_record(record)
            except Exception as exc:
                self.doc.changes = before; self.error(exc); return False
            if isinstance(self.doc,Item) and record.pid in self.doc.new_items:
                if self.live_item_names.get(record.pid)!=self.doc.value(record,self.doc.by_offset[0x20]):self.rebuild_translator()
            if isinstance(self.doc,Person) and record.pid in self.doc.new_characters:
                if self.live_character_names.get(record.pid)!=self.doc.value(record,self.doc.by_offset[0x20]):self.rebuild_translator()
            if isinstance(self.doc,Job) and record.pid in self.doc.new_classes:
                if self.live_class_names.get(record.pid)!=self.doc.value(record,self.doc.by_offset[0x20]):self.rebuild_translator()
            if isinstance(self.doc,(Legion,Item,Job)) and self.tree.exists(str(record.index)):
                self.tree.set(str(record.index),'serial',str(self.doc.value(record,self.doc.by_offset[0x31 if isinstance(self.doc,Job) else 0x48 if isinstance(self.doc,Item) else 0x30])))
            if isinstance(self.doc,RelianceView) and self.doc.key=='matrix':
                from supports_ui import refresh_matrix
                refresh_matrix(self)
            if isinstance(self.doc,ExpandedView):
                from expanded_ui import refresh_entries
                refresh_entries(self)
            if isinstance(self.doc,DeploymentView):
                from deployment_ui import refresh_entries
                refresh_entries(self)
            if isinstance(self.doc,ShopView):
                from shop_ui import refresh_entries
                refresh_entries(self)
            if isinstance(self.doc,EventView):
                from event_ui import refresh_entries
                refresh_entries(self)
            if isinstance(self.doc,Progression):
                from progression_ui import refresh_levels
                refresh_levels(self)
            elif isinstance(self.doc,Learning):
                from learning_ui import refresh_entries
                refresh_entries(self)
            if not quiet:
                self.status.set(f'Applied edits · {edit_summary(self.doc)}. Save a project or export a mod.')
                self.heading.set(self.display(self.current))
                if self.tree.exists(str(self.current.index)):
                    changed=self.doc.table_changed(self.current.pid) if isinstance(self.doc,CollectionTable) else self.doc.record_changed(self.current.pid)
                    self.tree.item(str(self.current.index), text=self.display(self.current) + (' *' if changed else ''))
                self.count_label.configure(text=f'{len(self.tree.get_children())} shown · {edit_summary(self.doc)}')
            return True

        def session_state(self):
            return json.dumps(suite_project(self.documents),sort_keys=True)

        def switch_module(self, name=None, record_id=None, source_file=None, section=None):
            name=name or self.module.get();entry_target=None
            if name.startswith('Scripts · '):
                from script_ui import open_editor
                source=source_file or self.documents[name].filename
                editor=open_editor(self,source.removeprefix('Script/'))
                if editor and record_id and record_id.startswith('SCRIPT_STRING_'):
                    editor.tabs.select(1);editor.constant_search.set('')
                    if editor.constant_tree.exists(record_id.removeprefix('SCRIPT_STRING_')):
                        editor.constant_tree.selection_set(record_id.removeprefix('SCRIPT_STRING_'));editor.select_constant()
                return bool(editor)
            if name=='AIDs':return self.switch_aids(record_id)
            growth=self.documents.get('Learning tables')
            document=growth.progression if name=='GLID progression' and growth else self.documents.get(name)
            if name=='Skills':
                choices=[doc for doc in self.documents.values() if isinstance(doc,Skill)]
                document=next((doc for doc in choices if doc.filename==(source_file or self.skill_source.get())),choices[0] if choices else None)
            if name=='Items':
                choices=[doc for doc in self.documents.values() if isinstance(doc,Item)]
                document=next((doc for doc in choices if doc.filename==(source_file or self.item_source.get())),choices[0] if choices else None)
                if source_file is None and record_id and document and record_id not in document.by_pid:
                    document=next((doc for doc in choices if record_id in doc.by_pid),document)
            if name=='Events':
                choices=[d for d in self.documents.values() if isinstance(d,EventData)]
                owner=next((d for d in choices if d.filename==(source_file or self.event_source.get())),choices[0] if choices else None)
                document=next(iter(owner.views.values())) if owner else None
                if document and record_id in document.row_location:entry_target=record_id;record_id=document.row_location[record_id][0]
            if name=='Progression & Difficulty':
                choices=[d for d in self.documents.values() if any(isinstance(v,ExpandedView) for v in getattr(d,'views',{}).values())]
                owner=next((d for d in choices if d.filename==(source_file or self.expanded_source.get())),choices[0] if choices else None)
                if owner:
                    if section is None and record_id:
                        if record_id.partition(':')[0] in owner.views:section=record_id.partition(':')[0]
                        else:section=next((k for k,v in owner.views.items() if any(v.names[r.pid]==record_id for r in v.collections)),None)
                    document=owner.views.get(section or self.expanded_section.get(),next(iter(owner.views.values())))
                    if record_id in document.row_location:entry_target=record_id;record_id=document.row_location[record_id][0]
                    elif record_id and record_id not in document.tables_by_id:record_id=next((r.pid for r in document.collections if document.names[r.pid]==record_id),record_id)
                else:document=None
            if name=='Battle deployment':
                choices=[d for d in self.documents.values() if isinstance(d,Deployment)]
                owner=next((d for d in choices if d.filename==(source_file or self.deployment_source.get())),choices[0] if choices else None)
                document=owner.views['units'] if owner else None
                if document and record_id in document.row_location:entry_target=record_id;record_id=document.row_location[record_id][0]
            if name=='Shop & Loot':
                choices=[doc for doc in self.documents.values() if isinstance(doc,Item) and doc.views]
                owner=next((d for d in choices if d.filename==(source_file or self.shop_source.get())),choices[0] if choices else None)
                if owner:
                    if section is None and record_id and record_id.partition(':')[0] in owner.views:section=record_id.partition(':')[0]
                    document=owner.views.get(section or self.shop_section.get(),next(iter(owner.views.values())))
                    if record_id in document.row_location:entry_target=record_id;record_id=document.row_location[record_id][0]
                    elif record_id and record_id not in document.tables_by_id:
                        record_id=next((r.pid for r in document.collections if document.names[r.pid]==record_id),record_id)
                else:document=None
            if name=='Supports & Recruitment' and document is not None:
                if section is None and record_id and record_id.partition(':')[0] in document.views:section=record_id.partition(':')[0]
                document=document.views.get(section or self.support_section.get(),document.views['matrix'])
            if name=='Profiles & Affiliations' and document is not None:
                if section is None and record_id and record_id.partition(':')[0] in document.views:section=record_id.partition(':')[0]
                document=document.views.get(section or self.profile_section.get(),document.views['profiles'])
            if name=='Facilities & Rewards':
                choices=[doc for doc in self.documents.values() if isinstance(doc,Facility)]
                owner=next((d for d in choices if d.filename==(source_file or self.facility_source.get())),choices[0] if choices else None)
                if owner:
                    if section is None and record_id and record_id.partition(':')[0] in owner.views:section=record_id.partition(':')[0]
                    document=owner.views.get(section or self.facility_section.get(),next(iter(owner.views.values())))
                else:document=None
            if name=='Appearance rules':
                choices=[doc for doc in self.documents.values() if isinstance(doc,Appearance)]
                owner=next((d for d in choices if d.filename==(source_file or self.appearance_source.get())),choices[0] if choices else None)
                if owner:
                    if section is None and record_id and record_id.partition(':')[0] in owner.views:section=record_id.partition(':')[0]
                    document=owner.views.get(section or self.appearance_section.get(),owner.views['rules'])
                else:document=None
            if document is None:
                self.module.set(self.active_module)
                if self.documents:self.error('Open GameData containing '+{'Classes':'Job.bin','Characters':'Person.bin','Learning tables':'Growth.bin','GLID progression':'Growth.bin','Skills':'Skill.bin','Items':'Item.bin','Supports & Recruitment':'Reliance.bin','Appearance rules':'AssetTable.bin','Profiles & Affiliations':'Profile.bin','Facilities & Rewards':'Facility.bin or Reward*.bin','Shop & Loot':'Item.bin containing shop or lottery tables','Battle deployment':'Dispos/*.bin','Legion':'Legion.bin','Progression & Difficulty':'Growth.bin, Growth_P0.bin or Person.bin','Events':'Variable*.bin, Timeline*.bin, Chapter.bin or Situation.bin'}.get(name,'the requested table')+' first.')
                return False
            if not self.apply(True):
                self.module.set(self.active_module)
                if isinstance(self.doc,EventView):self.event_source.set(self.doc.filename)
                if isinstance(self.doc,Skill):self.skill_source.set(self.doc.filename)
                if isinstance(self.doc,Item):self.item_source.set(self.doc.filename)
                if isinstance(self.doc,RelianceView):self.support_section_choice.set(self.doc.title)
                if isinstance(self.doc,ProfileView):self.profile_section_choice.set(self.doc.title)
                if isinstance(self.doc,ExpandedView):self.expanded_source.set(self.doc.filename);self.expanded_section_choice.set(self.doc.title)
                if isinstance(self.doc,DeploymentView):self.deployment_source.set(self.doc.filename)
                if isinstance(self.doc,ShopView):self.shop_source.set(self.doc.filename);self.shop_section_choice.set(self.doc.title)
                if isinstance(self.doc,FacilityView):
                    self.facility_source.set(self.doc.filename);self.facility_section_choice.set(self.doc.title)
                if isinstance(self.doc,AppearanceView):
                    self.appearance_source.set(self.doc.filename);self.appearance_section_choice.set(self.doc.title)
                return False
            if self.notebook.tabs():self.module_tabs[self.active_module]=self.notebook.index('current')
            self.clear_previews();self.widgets={};self.current=None;self.learning_row=None
            for tab in self.notebook.tabs():self.nametowidget(tab).destroy()
            self.active_module=name;self.module.set(name);self.doc=document;self.source=next(self.sources[key] for key,doc in self.documents.items() if doc is (document.owner if isinstance(document,(RelianceView,AppearanceView,ProfileView,FacilityView,ShopView,DeploymentView,ExpandedView,EventView)) else growth if name=='GLID progression' else document))
            self.aid_controls.pack_forget();self.skill_controls.pack_forget();self.item_controls.pack_forget();self.support_controls.pack_forget();self.appearance_controls.pack_forget();self.profile_controls.pack_forget();self.facility_controls.pack_forget();self.shop_controls.pack_forget();self.deployment_controls.pack_forget();self.expanded_controls.pack_forget();self.event_controls.pack_forget()
            if isinstance(self.doc,EventView):
                self.event_source.set(self.doc.filename)
                self.event_source_choice.configure(values=[d.filename for d in self.documents.values() if isinstance(d,EventData)])
                self.event_controls.pack(before=self.tree.master,fill='x',pady=(0,5))
            if isinstance(self.doc,Skill):
                self.skill_source.set(self.doc.filename)
                self.skill_source_choice.configure(values=[doc.filename for doc in self.documents.values() if isinstance(doc,Skill)])
                self.skill_controls.pack(before=self.tree.master,fill='x',pady=(0,5))
            if isinstance(self.doc,Item):
                self.item_source.set(self.doc.filename)
                self.item_source_choice.configure(values=[doc.filename for doc in self.documents.values() if isinstance(doc,Item)])
                self.item_controls.pack(before=self.tree.master,fill='x',pady=(0,5))
            if isinstance(self.doc,RelianceView):
                self.support_section.set(self.doc.key);self.support_section_choice.set(self.doc.title)
                self.support_controls.pack(before=self.tree.master,fill='x',pady=(0,5))
            if isinstance(self.doc,ExpandedView):
                self.expanded_source.set(self.doc.filename);self.expanded_section.set(self.doc.key)
                self.expanded_source_choice.configure(values=[d.filename for d in self.documents.values() if any(isinstance(v,ExpandedView) for v in getattr(d,'views',{}).values())])
                self.expanded_section_choice.configure(values=[v.title for v in self.doc.owner.views.values()]);self.expanded_section_choice.set(self.doc.title)
                self.expanded_controls.pack(before=self.tree.master,fill='x',pady=(0,5))
            if isinstance(self.doc,DeploymentView):
                self.deployment_source.set(self.doc.filename)
                self.deployment_source_choice.configure(values=[d.filename for d in self.documents.values() if isinstance(d,Deployment)])
                self.deployment_controls.pack(before=self.tree.master,fill='x',pady=(0,5))
            if isinstance(self.doc,ShopView):
                self.shop_source.set(self.doc.filename);self.shop_section.set(self.doc.key)
                self.shop_source_choice.configure(values=[d.filename for d in self.documents.values() if isinstance(d,Item) and d.views])
                self.shop_section_choice.configure(values=[v.title for v in self.doc.owner.views.values()]);self.shop_section_choice.set(self.doc.title)
                self.shop_controls.pack(before=self.tree.master,fill='x',pady=(0,5))
            if isinstance(self.doc,FacilityView):
                from facility_ui import group_title
                self.facility_source.set(self.doc.filename);self.facility_section.set(self.doc.key);self.facility_group_index=-1
                self.facility_source_choice.configure(values=[doc.filename for doc in self.documents.values() if isinstance(doc,Facility)])
                self.facility_section_choice.configure(values=[v.title for v in self.doc.owner.views.values()]);self.facility_section_choice.set(self.doc.title)
                self.facility_group_choice.configure(values=['All groups']+[f'{i}: {group_title(self,name)}' for i,name in enumerate(self.doc.collection_names)])
                self.facility_group_choice.current(0)
                if self.doc.container==2:self.facility_group_row.pack(fill='x',pady=(0,3))
                else:self.facility_group_row.pack_forget()
                self.facility_controls.pack(before=self.tree.master,fill='x',pady=(0,5))
            if isinstance(self.doc,ProfileView):
                self.profile_section.set(self.doc.key);self.profile_section_choice.set(self.doc.title)
                self.profile_controls.pack(before=self.tree.master,fill='x',pady=(0,5))
            if isinstance(self.doc,AppearanceView):
                self.appearance_source.set(self.doc.filename);self.appearance_section.set(self.doc.key)
                self.appearance_source_choice.configure(values=[d.filename for d in self.documents.values() if isinstance(d,Appearance)])
                self.appearance_section_choice.configure(values=[v.title for v in self.doc.owner.views.values()]);self.appearance_section_choice.set(self.doc.title)
                self.appearance_controls.pack(before=self.tree.master,fill='x',pady=(0,5))
            self.copy_aid_button.pack_forget();self.copy_skill_button.pack_forget();self.copy_item_button.pack_forget();self.readonly_hint.pack_forget()
            self.apply_button.pack(side='left');self.reset_button.pack(side='left',padx=5)
            if isinstance(self.doc,Skill):self.copy_skill_button.pack(side='left',padx=3)
            if isinstance(self.doc,Item):self.copy_item_button.pack(side='left',padx=3)
            self.reset_button.configure(text='Reset row' if isinstance(self.doc,(RelianceView,AppearanceView,ProfileView,FacilityView)) else 'Reset table' if isinstance(self.doc,CollectionTable) else 'Reset entry')
            if name=='Characters' and record_id in self.doc.by_pid:
                target=self.doc.by_pid[record_id]
                if not self.doc.original(target,self.doc.by_offset[0x30]) and record_id not in self.doc.new_characters:self.variants.set(True)
            self.path_label.configure(text=str(self.source))
            self.tree.column('#0',width=173)
            self.tree.configure(displaycolumns=('serial',))
            self.tree.heading('#0',text=self.doc.title if isinstance(self.doc,(RelianceView,AppearanceView,ProfileView,FacilityView,ShopView,DeploymentView,ExpandedView,EventView)) else 'Legion' if name=='Legion' else 'Item' if name=='Items' else 'Skill' if name=='Skills' else 'Progression table' if name=='GLID progression' else 'Learning table' if name=='Learning tables' else 'Class' if name=='Classes' else 'Character')
            self.tree.heading('serial',text='#' if isinstance(self.doc,(RelianceView,AppearanceView,ProfileView,FacilityView)) else 'Type' if isinstance(self.doc,(Skill,Item)) else 'Rows' if isinstance(self.doc,CollectionTable) else 'Level' if name=='Legion' else 'Rank' if name=='Classes' else 'Slot')
            self.tree.column('serial',width=48 if name in ('Classes','Learning tables','GLID progression','Skills','Items','Supports & Recruitment','Appearance rules','Profiles & Affiliations','Facilities & Rewards','Shop & Loot','Battle deployment','Legion','Progression & Difficulty','Events') else 40)
            if name in ('Classes','Learning tables','GLID progression','Skills','Items','Supports & Recruitment','Appearance rules','Profiles & Affiliations','Facilities & Rewards','Shop & Loot','Battle deployment','Legion','Progression & Difficulty','Events'):self.variant_button.pack_forget()
            elif not self.variant_button.winfo_manager():self.variant_button.pack(before=self.tree.master,anchor='w',pady=(0,4))
            self.search.set('');self.filter()
            records=self.doc.collections if isinstance(self.doc,CollectionTable) else self.doc.records
            mapping=self.doc.tables_by_id if isinstance(self.doc,CollectionTable) else self.doc.by_pid
            first=mapping.get(record_id) if record_id else None
            if first is None:
                first=next((r for r in records if self.display(r)==('Gladiator' if name=='Classes' else 'Dietrich')),records[0])
            if not self.tree.exists(str(first.index)):
                first=next((r for r in records if self.tree.exists(str(r.index))),records[0])
            self.tree.selection_set(str(first.index));self.tree.see(str(first.index));self.show(first)
            self.notebook.select(min(self.module_tabs.get(name,0),len(self.notebook.tabs())-1))
            if isinstance(self.doc,EventView) and entry_target:
                from event_ui import show_entry
                show_entry(self,self.doc.by_pid[entry_target]);self.notebook.select(0)
            if isinstance(self.doc,ExpandedView) and entry_target:
                from expanded_ui import show_entry
                show_entry(self,self.doc.by_pid[entry_target]);self.notebook.select(0)
            if isinstance(self.doc,DeploymentView) and entry_target:
                from deployment_ui import show_entry
                show_entry(self,self.doc.by_pid[entry_target]);self.notebook.select(0)
            if isinstance(self.doc,ShopView) and entry_target:
                from shop_ui import show_entry
                show_entry(self,self.doc.by_pid[entry_target]);self.notebook.select(0)
            return True

        def open_data(self,path=None,prepared=None):
            if self.documents:
                if not self.apply(True):return
                if self.session_state()!=self.saved_state and not messagebox.askyesno('Open data','Open another source and discard unsaved edits?',parent=self):return
            if path is None:
                path=filedialog.askdirectory(title='Choose the game folder or GameData folder',initialdir=self.preferences.initial_dir('last_data'),parent=self)
                if not path:return
            path=Path(path)
            bases=[path.parent.parent] if path.is_file() and path.parent.name=='Dispos' else [path.parent] if path.is_file() else [path.parent,path] if path.name=='Dispos' else [path,path/'GameData',path/'romfs/GameData']
            base=next((p for p in bases if (p/'Person.bin').is_file() or (p/'Job.bin').is_file() or (p/'Growth.bin').is_file() or (p/'Reliance.bin').is_file() or (p/'Profile.bin').is_file() or (p/'Legion.bin').is_file() or (p/'Growth_P0.bin').is_file() or any((p/kind.filename).is_file() for kind in (*SKILL_TABLES,*ITEM_TABLES,*FACILITY_TABLES)) or any(p.glob('AssetTable*.bin')) or any((p/name).is_file() for name in EVENT_FILES) or any((p/'Dispos').glob('*.bin'))),None)
            if base is None:self.error('No supported tables were found. Select GameData containing Person.bin, Job.bin, Growth.bin, Reliance.bin, Profile.bin, Skill*.bin, Item*.bin, AssetTable*.bin, Facility.bin, Reward*.bin, Legion.bin, Growth_P0.bin or Dispos/*.bin.');return
            try:
                documents,sources=prepared if prepared is not None else read_editable_tables(base)
                self.clear_previews();self.widgets={};self.current=None
                self.documents=documents;self.sources=sources;self.doc=None
                self.data_directory=base.resolve();self.current_aid=None;self.current_aid_source=None
                self.project_path=None;self.names_directory=None;self.learning_row=None
                from deployment_data import battle_links
                try:self.battle_links=battle_links(base,Binary)
                except (ValueError,struct.error):self.battle_links=[]
                self.asset_index=AssetIndex.load(base,Binary)
                from skill_index import SkillIndex
                self.skill_index=SkillIndex.load(base,Binary)
                from item_index import ItemIndex
                self.item_index=ItemIndex.load(base,Binary)
                self.names={};self.suggestion_cache={};self.catalog={}
                self.translation_status.set('English names not loaded · click English names…')
                for filename in ('Person','Job','Skill','Skill_P0','Skill_P1','Item','Item_P0','Item_P1','Growth','Profile','Reliance','AssetTable','AssetTable_P0','AssetTable_P1','Facility','Reward','Reward_P0','Reward_P1','Legion','Growth_P0'):
                    p=base/(filename+'.bin')
                    if not p.is_file():continue
                    table=next((doc for doc in documents.values() if doc.filename==p.name),None)
                    if table is None:table=Binary(p.read_bytes())
                    for key,offset in table.labels.items():
                        hint=''
                        try:
                            pointer=struct.unpack_from('<Q',table.raw,offset+32)[0]
                            if pointer>=table.pool:
                                candidate=table.string(pointer)
                                if candidate.startswith(('MPID_','MJID_','MSID_','MIID_')) or isinstance(table,Legion) and candidate.startswith('MLID_') or isinstance(table,Facility) and candidate.startswith('MID_'):hint=candidate
                        except (DataError,struct.error):pass
                        if key not in self.catalog or not self.catalog[key]:self.catalog[key]=hint
                for parent in (base.parent,base.parent.parent):
                    for relative in ('Msg/USen','romfs/Msg/USen','USen'):
                        directory=parent/relative
                        if any((directory/(name+suffix)).is_file() for name in MESSAGE_TABLES for suffix in ('.msbt.zst','.msbt')):
                            self.read_names(directory);break
                    if self.names:break
                last_names=self.preferences.values.get('last_names')
                if not self.names and last_names and Path(last_names).is_dir():
                    try:self.read_names(Path(last_names))
                    except (OSError,ValueError):pass
                self.rebuild_translator();self.saved_state=self.session_state()
                chosen=('Events' if path.name in EVENT_FILES or all(isinstance(d,EventData) for d in documents.values()) else 'Progression & Difficulty' if path.name=='Growth_P0.bin' or all(isinstance(d,GrowthSide) for d in documents.values()) else 'Legion' if path.name=='Legion.bin' or all(isinstance(d,Legion) for d in documents.values()) else 'Battle deployment' if path.name=='Dispos' or path.parent.name=='Dispos' or all(isinstance(d,Deployment) for d in documents.values()) else 'Appearance rules' if path.name.startswith('AssetTable') else 'AIDs' if not documents else
                        'Facilities & Rewards' if path.name in {kind.filename for kind in FACILITY_TABLES} else 'Profiles & Affiliations' if path.name=='Profile.bin' else 'Supports & Recruitment' if path.name=='Reliance.bin' else 'Items' if path.name in {kind.filename for kind in ITEM_TABLES} or all(isinstance(doc,Item) for doc in documents.values()) else 'Skills' if path.name in {kind.filename for kind in SKILL_TABLES} or all(isinstance(doc,Skill) for doc in documents.values()) else 'Learning tables' if path.name=='Growth.bin' else 'Classes' if path.name=='Job.bin' else next(iter(documents)))
                self.switch_module(chosen,source_file=('Dispos/'+path.name if path.parent.name=='Dispos' else path.name) if path.is_file() else None)
                self.remember_paths(last_data=str(self.data_directory))
                summary=[f'{len(doc.collections) if isinstance(doc,Learning) else len(doc.records)} {name.lower()}' for name,doc in documents.items() if not isinstance(doc,(Skill,Item,Deployment,GrowthSide))]
                deployments=[d for d in documents.values() if isinstance(d,Deployment)]
                if deployments:summary.append(f'{sum(len(d.records) for d in deployments)} deployment units ({len(deployments)} files)')
                skills=[doc for doc in documents.values() if isinstance(doc,Skill)]
                if skills:summary.append(f'{sum(len(doc.records) for doc in skills)} skills ({len(skills)} files)')
                items=[doc for doc in documents.values() if isinstance(doc,Item)]
                if items:summary.append(f'{sum(len(doc.records) for doc in items)} items ({len(items)} files)')
                self.status.set('Loaded '+', '.join(summary+[f'{len(self.asset_index.aids)} AIDs'])+'. Original files stay unchanged.')
                return True
            except Exception as exc:self.error(exc);return False

        def read_names(self, directory):
            directory = Path(directory)
            directory = next((d for d in (directory, directory/'USen', directory/'Msg/USen',
                                         directory/'romfs/Msg/USen')
                              if any((d/(name+suffix)).is_file() for name in MESSAGE_TABLES for suffix in ('.msbt.zst','.msbt'))), directory)
            loaded = {}
            for name in MESSAGE_TABLES:
                p = directory/(name+'.msbt.zst')
                if not p.exists(): p = directory/(name+'.msbt')
                if p.is_file(): loaded.update(messages(p.read_bytes()))
            if not loaded: raise DataError('No supported message files found. Choose USen containing Person, Item, System_Facility or other supported tables.')
            self.names = loaded
            self.names_directory=directory.resolve()
            self.remember_paths(last_names=str(self.names_directory))
            if self.project_path:self.remember_project(self.project_path)
            self.translation_status.set(f'{len(loaded):,} English entries · ≈ glossary')
            self.suggestion_cache.clear()
            self.rebuild_translator()

        def load_names(self):
            if not self.documents and self.asset_index is None:self.error('Open your game data first.');return
            directory = filedialog.askdirectory(title='Choose USen or another language folder',initialdir=self.preferences.initial_dir('last_names'),parent=self)
            if not directory: return
            if not self.apply(True): return
            try:
                self.read_names(Path(directory)); self.filter()
                if self.current:self.show(self.current)
                elif self.active_module=='AIDs' and self.current_aid:self.show_aid(self.current_aid)
                self.status.set('Localized names loaded; search by name or internal ID.')
            except Exception as exc: self.error(exc)

        def filter(self):
            if self.active_module=='AIDs':return self.filter_aids()
            if not self.doc: return
            if self.current and not self.apply(True): return
            query = self.search.get().casefold().strip()
            self.tree.delete(*self.tree.get_children())
            count = 0
            records=self.doc.collections if isinstance(self.doc,CollectionTable) else self.doc.records
            for record in records:
                serial=record.index if isinstance(self.doc,(RelianceView,AppearanceView,ProfileView,FacilityView)) else len(self.doc.rows_by_table[record.pid]) if isinstance(self.doc,CollectionTable) else self.doc.value(record,self.doc.by_offset[0x30]) if isinstance(self.doc,Legion) else self.doc.value(record,self.doc.by_offset[0x48]) if isinstance(self.doc,Item) else self.doc.value(record,self.doc.by_offset[0x31]) if isinstance(self.doc,Job) else self.doc.original(record,self.doc.by_offset[0x68 if isinstance(self.doc,Skill) else 0x30])
                if isinstance(self.doc,Person) and not self.variants.get() and not serial and record.pid not in self.doc.new_characters:continue
                if isinstance(self.doc,FacilityView) and self.facility_group_index>=0 and self.doc.locations[record.pid][0]!=self.facility_group_index:continue
                name = self.display(record)
                extra=''
                if isinstance(self.doc,RelianceView):
                    from supports_ui import search_text
                    extra=search_text(self,record)
                if query and isinstance(self.doc,EventView):
                    from event_ui import search_text
                    extra=search_text(self,record)
                if query and isinstance(self.doc,ExpandedView):
                    from expanded_ui import search_text
                    extra=search_text(self,record)
                if query and isinstance(self.doc,Legion):
                    from legion_ui import search_text
                    extra=search_text(self,record)
                if query and isinstance(self.doc,DeploymentView):
                    from deployment_ui import search_text
                    extra=search_text(self,record)
                if query and isinstance(self.doc,ShopView):
                    from shop_ui import search_text
                    extra=search_text(self,record)
                if query and isinstance(self.doc,FacilityView):
                    from facility_ui import search_text
                    extra=search_text(self,record)
                if query and isinstance(self.doc,ProfileView):
                    from profile_ui import search_text
                    extra=search_text(self,record)
                if query and isinstance(self.doc,AppearanceView):
                    from appearance_ui import search_text
                    extra=search_text(self,record)
                if query and query not in (extra+' '+name+' '+record.pid+' '+self.translator.resolve(record.pid).text+' '+str(serial)).casefold(): continue
                changed=self.doc.table_changed(record.pid) if isinstance(self.doc,CollectionTable) else self.doc.record_changed(record.pid)
                self.tree.insert('', 'end', iid=str(record.index), text=name + (' *' if changed else ''), values=(serial, record.pid))
                count += 1
            self.count_label.configure(text=f'{count} shown · {edit_summary(self.doc)}')
            if self.current and self.tree.exists(str(self.current.index)):
                self.tree.selection_set(str(self.current.index))

        def change_facility_group(self):
            selected=self.facility_group_choice.current()-1
            if not self.apply(True):self.facility_group_choice.current(self.facility_group_index+1);return
            self.facility_group_index=selected;self.filter()
            rows=self.tree.get_children()
            if rows and (self.current is None or not self.tree.exists(str(self.current.index))):
                self.tree.selection_set(rows[0]);self.show(self.doc.records[int(rows[0])])

        def select(self, event=None):
            selection = self.tree.selection()
            if not selection: return
            if self.active_module=='AIDs':
                selected=self.aid_tree_map.get(selection[0])
                if selected is None:return
                aid,self.current_aid_source=selected
                return self.show_aid(aid)
            record=(self.doc.collections if isinstance(self.doc,CollectionTable) else self.doc.records)[int(selection[0])]
            if self.current and self.current.pid == record.pid: return
            if not self.apply(True):
                self.tree.selection_set(str(self.current.index)); return
            self.show(record)

        def rebuild_translator(self):
            self.live_item_names={key:doc.value(doc.by_pid[key],doc.by_offset[0x20])
                                  for doc in self.documents.values() if isinstance(doc,Item) for key in doc.new_items}
            self.live_class_names={key:doc.value(doc.by_pid[key],doc.by_offset[0x20])
                                   for doc in self.documents.values() if isinstance(doc,Job) for key in doc.new_classes}
            self.live_character_names={key:doc.value(doc.by_pid[key],doc.by_offset[0x20])
                                       for doc in self.documents.values() if isinstance(doc,Person) for key in doc.new_characters}
            self.translator = Translator(self.names, {**self.catalog,**self.live_item_names,**self.live_class_names,**self.live_character_names}, self.custom_translations)
            for offset in list(self.previews):
                self.update_preview(offset)
            if self.active_module=='AIDs' and self.current_aid and self.asset_index:
                self.filter_aids();self.show_aid(self.current_aid)

        def clear_previews(self):
            for job in self.pending_previews.values():
                self.after_cancel(job)
            self.pending_previews.clear()
            self.previews = {}; self.preview_bindings = []

        def queue_preview(self, offset):
            previous = self.pending_previews.pop(offset, None)
            if previous: self.after_cancel(previous)
            self.pending_previews[offset] = self.after(120, lambda:self.update_preview(offset))

        def translate_value(self,raw,field=None):
            if isinstance(self.doc,EventView):
                from event_ui import translate
                return translate(self,raw)
            if raw in self.custom_translations:return self.translator.resolve(raw)
            if isinstance(self.doc,FacilityView) and field:
                prefix='SID_' if self.doc.key=='exspots' and field.offset==0x30 else 'PCHA_' if self.doc.key=='questions' and field.offset>=0x40 else ''
                if prefix and prefix+raw in self.catalog:return self.translator.resolve(prefix+raw)
            if isinstance(self.doc,AppearanceView) and self.doc.key=='rules' and field and field.offset==0x158:
                if 'FID_'+raw in self.catalog:return self.translator.resolve('FID_'+raw)
            if isinstance(self.doc,Progression) and self.learning_row:
                category=self.doc.value(self.learning_row,self.doc.by_offset[0x20])
                if 0x20 in self.widgets:
                    try:category=self.widget_value(*self.widgets[0x20])
                    except DataError:pass
                prefix=self.doc.reference_prefix(category)
                if prefix and prefix+raw in reference_ids(self,prefix):return self.translator.resolve(prefix+raw)
            return self.translator.resolve(raw)

        def update_preview(self, offset):
            job = self.pending_previews.pop(offset, None)
            if job: self.after_cancel(job)
            if offset not in self.previews: return
            field, widget = self.widgets[offset]
            preview, source_label = self.previews[offset]
            badges = {'English text':'English', 'Glossary':'≈ glossary', 'Partial glossary':'≈ partial',
                      'Untranslated':'Unknown', 'Custom':'Custom', 'Identifier':'ID', 'Empty':''}
            raw = widget.get('1.0', 'end-1c') if field.kind in LIST_TYPES or self.multiline_text(field) else widget.get()
            if field.kind in LIST_TYPES or self.multiline_text(field):
                lines = raw.split('\n')
                if field.kind in NESTED_TYPES:
                    texts=[];results=[]
                    for line in lines:
                        try:
                            row=json.loads(line) if line.strip() else []
                            if not isinstance(row,list) or not all(isinstance(v,str) for v in row):raise ValueError()
                            translated=[self.translate_value(v,field) for v in row];results.extend(translated)
                            texts.append(json.dumps([r.text for r in translated],ensure_ascii=False))
                        except ValueError:texts.append('Use a JSON list of strings on this line')
                    text='\n'.join(texts)
                else:
                    results=[self.translate_value(line.strip(),field) for line in lines]
                    text='\n'.join(result.text.replace('\n',' ') for result in results)
                preview.configure(state='normal'); preview.delete('1.0','end'); preview.insert('1.0',text)
                preview.configure(state='disabled')
                preview.yview_moveto(widget.yview()[0])
                types = sorted({r.source for r in results if r.source!='Empty'})
                source_label.set(' / '.join(badges.get(t,t) for t in types))
            else:
                result = self.translate_value(raw,field)
                preview.configure(text=result.text,
                    style='Missing.TLabel' if result.source in ('Partial glossary','Untranslated') else 'English.TLabel')
                source_label.set(badges.get(result.source,result.source))

        def reference_row(self, body, row, field, record):
            value = self.doc.value(record,field)
            label = ttk.Label(body, text=field.label, width=20, wraplength=152)
            label.grid(row=row,column=0,sticky='nw',padx=(0,6),pady=3)
            raw_frame = ttk.Frame(body); raw_frame.grid(row=row,column=1,sticky='nsew',pady=3)
            english_frame = ttk.Frame(body); english_frame.grid(row=row,column=2,sticky='nsew',padx=(6,0),pady=3)
            source_label = tk.StringVar()
            if field.kind in LIST_TYPES or self.multiline_text(field):
                height = max(2,min(4,len(value)))
                widget = tk.Text(raw_frame,height=height,width=18,font=('DejaVu Sans',9),undo=True,
                                 wrap='none',relief='solid',borderwidth=1,highlightthickness=0)
                widget.insert('1.0',value if self.multiline_text(field) else '\n'.join(json.dumps(row,ensure_ascii=False) for row in value) if field.kind in NESTED_TYPES else '\n'.join(value))
                widget.pack(side='left',fill='both',expand=True)
                preview = tk.Text(english_frame,height=height,width=18,font=('DejaVu Sans',9),
                                  wrap='none',background='#edf5f5',foreground='#145868',
                                  relief='flat',highlightthickness=0,padx=5,state='disabled')
                preview.pack(fill='both',expand=True)
                def scroll(*args):
                    widget.yview(*args); preview.yview(*args)
                bar = ttk.Scrollbar(raw_frame,orient='vertical',command=scroll)
                bar.pack(side='right',fill='y')
                def scrolled(first,last):
                    bar.set(first,last)
                    preview.yview_moveto(first)
                widget.configure(yscrollcommand=scrolled)
                def modified(event=None, w=widget, off=field.offset):
                    if w.edit_modified():
                        w.edit_modified(False); self.queue_preview(off)
                widget.edit_modified(False)
                widget.bind('<<Modified>>',modified)
                def english_wheel(event):
                    scroll('scroll',-1 if getattr(event,'num',0)==4 or getattr(event,'delta',0)>0 else 1,'units')
                    return 'break'
                for event in ('<MouseWheel>','<Button-4>','<Button-5>'):
                    preview.bind(event,english_wheel)
            else:
                variable = tk.StringVar(value=str(value))
                widget = ttk.Entry(raw_frame,textvariable=variable,width=18)
                widget.pack(fill='x')
                callback = variable.trace_add('write',lambda *_,off=field.offset:self.queue_preview(off))
                self.preview_bindings.append((variable,callback))
                preview = ttk.Label(english_frame,style='English.TLabel',wraplength=260)
                preview.pack(fill='x')
            actions = ttk.Frame(body); actions.grid(row=row,column=3,sticky='n',padx=(6,0),pady=3)
            ttk.Label(actions,textvariable=source_label,style='Hint.TLabel',width=9,wraplength=65).pack(side='left',padx=(0,3))
            ttk.Button(actions,text='…' if field.kind in NESTED_TYPES else '+' if field.kind in LIST_TYPES else '…',width=2,
                       command=lambda:self.edit_conditions(field,widget) if field.kind in NESTED_TYPES else self.pick(field,widget)).pack(side='right',anchor='n')
            self.widgets[field.offset]=(field,widget)
            self.previews[field.offset]=(preview,source_label)
            self.update_preview(field.offset)
            preview.bind('<Enter>', lambda _:self.status.set(
                self.translate_value(widget.get('insert linestart','insert lineend').strip()
                    if field.kind in LIST_TYPES or self.multiline_text(field) else widget.get()).text))
            def glossary(event=None):
                raw = widget.get('insert linestart','insert lineend') if field.kind in LIST_TYPES or self.multiline_text(field) else widget.get()
                self.glossary(raw.strip())
                return 'break'
            preview.bind('<Double-1>',glossary)
            label.bind('<Enter>',lambda _,f=field:self.status.set(f'{f.name} · {f.kind} · 0x{f.offset:03X}'))

        def numeric_row(self, body, row, field, record):
            ttk.Label(body,text=field.label,width=24).grid(row=row,column=0,sticky='w',pady=3)
            widget = ttk.Entry(body,width=9)
            widget.insert(0,number_text(self.doc.value(record,field),field.kind))
            widget.grid(row=row,column=1,sticky='w',pady=3)
            if field.offset in self.doc.locked_offsets: widget.configure(state='readonly')
            else: self.widgets[field.offset]=(field,widget)
            ttk.Label(body,text=f'{field.name} · {field.kind} · 0x{field.offset:03X}',style='Hint.TLabel').grid(row=row,column=2,columnspan=2,sticky='w',padx=(6,0))

        def edit_conditions(self, field, widget, description=None):
            try:
                groups=self.widget_value(field,widget)
                if not isinstance(groups,list) or any(not isinstance(row,list) or any(not isinstance(v,str) for v in row) for row in groups):
                    raise DataError('Use one JSON list of strings per row, or clear the field before opening this editor.')
            except Exception as exc:self.error(exc);return
            groups=[list(row) for row in groups]
            dialog=tk.Toplevel(self);dialog.title(field.label);dialog.geometry('900x460');dialog.transient(self)
            ttk.Label(dialog,text=description or 'Each group contains condition IDs. Boolean group semantics are not yet verified.',
                      style='Hint.TLabel').pack(anchor='w',padx=10,pady=8)
            tools=ttk.Frame(dialog,padding=(10,0));tools.pack(fill='x')
            choice=ttk.Combobox(tools,state='readonly',width=20);choice.pack(side='left')
            area=ttk.Frame(dialog,padding=10);area.pack(fill='both',expand=True)
            area.columnconfigure(0,weight=1);area.columnconfigure(1,weight=1);area.rowconfigure(1,weight=1)
            ttk.Label(area,text='Raw IDs · one per line').grid(row=0,column=0,sticky='w')
            ttk.Label(area,text='English / explanation').grid(row=0,column=1,sticky='w',padx=(8,0))
            raw=tk.Text(area,wrap='none',width=30,undo=True,font=('DejaVu Sans',9))
            preview=tk.Text(area,wrap='none',width=30,state='disabled',background='#edf5f5',font=('DejaVu Sans',9))
            raw.grid(row=1,column=0,sticky='nsew');preview.grid(row=1,column=1,sticky='nsew',padx=(8,0))
            for col,text in ((0,raw),(1,preview)):
                scroll=ttk.Scrollbar(area,orient='horizontal',command=text.xview)
                scroll.grid(row=2,column=col,sticky='ew',padx=(8,0) if col else 0);text.configure(xscrollcommand=scroll.set)
            current=[None]
            def translated(event=None):
                if raw.edit_modified():raw.edit_modified(False)
                lines=raw.get('1.0','end-1c').splitlines()
                preview.configure(state='normal');preview.delete('1.0','end')
                preview.insert('1.0','\n'.join(self.translate_value(line.strip(),field).text for line in lines))
                preview.configure(state='disabled')
            def commit():
                if current[0] is not None:
                    groups[current[0]]=[line.strip() for line in raw.get('1.0','end-1c').splitlines() if line.strip()]
            def display(index):
                current[0]=index;choice.configure(values=[f'Group {i+1}' for i in range(len(groups))])
                choice.set(f'Group {index+1}' if index is not None else '')
                raw.configure(state='normal');raw.delete('1.0','end')
                if index is not None:raw.insert('1.0','\n'.join(groups[index]))
                else:raw.configure(state='disabled')
                translated()
            def selected(event=None):
                commit();display(choice.current())
            def add():
                commit();groups.append([]);display(len(groups)-1)
            def remove():
                if current[0] is None:return
                groups.pop(current[0]);display(min(current[0],len(groups)-1) if groups else None)
            def save():
                commit()
                if len(groups)>65535 or any(len(row)>65535 or any('\0' in value for value in row) for row in groups):
                    self.error('Too many conditions or a null character was entered.');return
                widget.delete('1.0','end');widget.insert('1.0','\n'.join(json.dumps(row,ensure_ascii=False) for row in groups))
                self.update_preview(field.offset);dialog.destroy()
            ttk.Button(tools,text='Add group',command=add).pack(side='left',padx=5)
            ttk.Button(tools,text='Remove group',command=remove).pack(side='left')
            bottom=ttk.Frame(dialog,padding=10);bottom.pack(fill='x')
            ttk.Label(bottom,text='No groups = clear conditions. An empty group is preserved as [].',style='Hint.TLabel').pack(side='left')
            ttk.Button(bottom,text='Use groups',command=save,style='Accent.TButton').pack(side='right')
            ttk.Button(bottom,text='Cancel',command=dialog.destroy).pack(side='right',padx=5)
            choice.bind('<<ComboboxSelected>>',selected);raw.bind('<<Modified>>',translated)
            display(0 if groups else None)

        def class_stat_grid(self, body, record):
            ttk.Label(body,text='Class stats · identified columns are named; remaining blocks retain their original numbers.',style='Hint.TLabel').pack(anchor='w',pady=(0,6))
            tables=ttk.Frame(body);tables.pack(fill='x')
            stats=ttk.Frame(tables);stats.pack(side='left',anchor='n',padx=(0,10))
            starts=(0x120,0x136,0x14c,0x162,0x178,0x219)
            for col,start in enumerate(starts,1):
                label={2:'Class\nbases',5:'Class growth\nbonuses',6:'Minimum\nstats'}.get(col,f'Block {col}')
                ttk.Label(stats,text=label,style='Hint.TLabel').grid(row=0,column=col,padx=2)
                ttk.Label(stats,text=f'0x{start:X}',style='Hint.TLabel').grid(row=1,column=col,pady=(0,4))
            for i in range(11):
                field=self.doc.by_offset[0x120+i*2]
                ttk.Label(stats,text=field.label,width=11).grid(row=i+2,column=0,sticky='w')
                for col,start in enumerate(starts,1):
                    offset=start+i*(2 if col<6 else 1);f=self.doc.by_offset[offset]
                    widget=ttk.Entry(stats,width=5,justify='right');widget.insert(0,str(self.doc.value(record,f)))
                    widget.grid(row=i+2,column=col,padx=2,pady=2);self.widgets[offset]=(f,widget)
            apt=ttk.Frame(tables);apt.pack(side='left',anchor='n')
            for col,label in enumerate(('Aptitudes','Signed','Unsigned')):
                ttk.Label(apt,text=label,style='Hint.TLabel').grid(row=0,column=col,padx=2,sticky='w')
            for col,start in ((1,0x18e),(2,0x1a4)):
                ttk.Label(apt,text=f'0x{start:X}',style='Hint.TLabel').grid(row=1,column=col,pady=(0,4))
            for i in range(13):
                field=self.doc.by_offset[0x18e+i]
                ttk.Label(apt,text=field.label,width=12).grid(row=i+2,column=0,sticky='w')
                for col,start in ((1,0x18e),(2,0x1a4)):
                    f=self.doc.by_offset[start+i];widget=ttk.Entry(apt,width=5,justify='right')
                    widget.insert(0,str(self.doc.value(record,f)));widget.grid(row=i+2,column=col,padx=2,pady=2)
                    self.widgets[f.offset]=(f,widget)
            ttk.Label(body,text='Minimum stats are signed 8-bit numbers. Class aptitude columns preserve their original signedness.',
                      style='Hint.TLabel',wraplength=700).pack(anchor='w',pady=8)

        def class_uses(self, body, record):
            from class_ui import usage
            return usage(self,body,record)

        def show_class(self, record):
            active=self.notebook.index('current') if self.notebook.tabs() else 0
            self.clear_previews();self.current=record;self.widgets={}
            self.heading.set(self.display(record))
            rank=self.doc.value(record,self.doc.by_offset[0x31])
            self.details.set(f'{record.pid} · Rank {rank} · '+('new class' if record.pid in self.doc.new_classes else 'original class'))
            for tab in self.notebook.tabs():self.nametowidget(tab).destroy()
            groups={name:[] for name in ('Overview','Stats','Skills & gear','Promotion','Advanced','Used by')}
            for f in self.doc.fields:
                off=f.offset
                title=('Stats' if 0x120<=off<=0x19a or 0x1a4<=off<=0x1b0 or 0x219<=off<=0x223 else
                       'Skills & gear' if 0x80<=off<=0x100 else
                       'Promotion' if off in (0x48,0x50,0x1b8,0x1c8,0x1d8,0x1e8,0x1f8,0x1f9,0x208) else
                       'Overview' if off in (0x20,0x28,0x30,0x31,0x32,0x38,0x58,0x68,0x200,0x218,0x228) else 'Advanced')
                groups[title].append(f)
            tips={
                'Overview':'Class identity, movement, links and appearance. Enum values remain raw numbers.',
                'Skills & gear':'Class, ally, enemy and mastery skill lists. + searches existing English names.',
                'Promotion':'Use … to edit condition groups with one ID per line. The raw form preserves JSON group rows.',
                'Advanced':'Raw engine settings and experience values. Labels translate the schema; enum meanings are unverified.',
            }
            for title,fields in groups.items():
                tab=ttk.Frame(self.notebook);self.notebook.add(tab,text=title)
                canvas=tk.Canvas(tab,highlightthickness=0,background='#f4f5f7')
                bar=ttk.Scrollbar(tab,orient='vertical',command=canvas.yview)
                canvas.configure(yscrollcommand=bar.set);bar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
                body=ttk.Frame(canvas,padding=8);window=canvas.create_window((0,0),window=body,anchor='nw')
                body.bind('<Configure>',lambda event,c=canvas:c.configure(scrollregion=c.bbox('all')))
                canvas.bind('<Configure>',lambda event,c=canvas,w=window:c.itemconfigure(w,width=max(event.width,c.winfo_reqwidth())))
                if title=='Stats':self.class_stat_grid(body,record)
                elif title=='Used by':self.class_uses(body,record)
                else:
                    first=0
                    if title=='Overview':
                        from class_ui import tools
                        tools(self,body,record);first=2
                    ttk.Label(body,text=tips[title],style='Hint.TLabel',wraplength=700).grid(row=first,column=0,columnspan=4,sticky='w',pady=(0,8))
                    for col,text in ((0,'Field'),(1,'Raw reference / Japanese'),(2,'English / explanation'),(3,'Source')):
                        ttk.Label(body,text=text,style='Hint.TLabel').grid(row=first+1,column=col,sticky='w',pady=(0,3))
                    refs=[f for f in fields if f.kind in TEXT_TYPES|LIST_TYPES]
                    numeric=[f for f in fields if f.kind in FORMATS]
                    for row,f in enumerate(refs+numeric,first+2):
                        if f.kind in TEXT_TYPES|LIST_TYPES:self.reference_row(body,row,f,record)
                        else:self.numeric_row(body,row,f,record)
                    body.columnconfigure(1,weight=1,uniform='classrefs',minsize=150)
                    body.columnconfigure(2,weight=1,uniform='classrefs',minsize=150)
                def wheel(event,c=canvas):
                    if c.bbox('all') and c.bbox('all')[3]>c.winfo_height():
                        c.yview_scroll(-1 if getattr(event,'num',0)==4 or getattr(event,'delta',0)>0 else 1,'units')
                    return 'break'
                def bind_wheel(widget,fn=wheel):
                    if not isinstance(widget,(tk.Text,ttk.Treeview)):
                        for event in ('<MouseWheel>','<Button-4>','<Button-5>'):widget.bind(event,fn,add='+')
                    for child in widget.winfo_children():bind_wheel(child,fn)
                bind_wheel(body)
                for event in ('<MouseWheel>','<Button-4>','<Button-5>'):canvas.bind(event,wheel)
            self.notebook.select(min(active,len(groups)-1))

        def stat_grid(self, body, record):
            ttk.Label(body,text='Personal stats · identified columns are named; remaining blocks retain their original numbers.',style='Hint.TLabel').pack(anchor='w',pady=(0,6))
            tables = ttk.Frame(body); tables.pack(fill='x')
            stats = ttk.Frame(tables); stats.pack(side='left',anchor='n',padx=(0,14))
            starts = (0x1c2,0x1d8,0x1ee,0x204,0x21c,0x232)
            for col,start in enumerate(starts,1):
                label={1:'Personal\nbases',5:'Personal\ngrowths'}.get(col,f'Block {col}')
                ttk.Label(stats,text=label,style='Hint.TLabel').grid(row=0,column=col,padx=3,pady=3)
            for i in range(11):
                field = self.doc.by_offset[starts[0]+i*2]
                ttk.Label(stats,text=field.label,width=11).grid(row=i+1,column=0,sticky='w')
                for col,start in enumerate(starts,1):
                    f = self.doc.by_offset[start+i*2]
                    widget = ttk.Entry(stats,width=5,justify='right')
                    widget.insert(0,str(self.doc.value(record,f)))
                    widget.grid(row=i+1,column=col,padx=2,pady=2)
                    self.widgets[f.offset]=(f,widget)
            aptitudes = ttk.Frame(tables); aptitudes.pack(side='left',anchor='n')
            ttk.Label(aptitudes,text='Aptitudes',style='Hint.TLabel').grid(row=0,column=0,sticky='w')
            for col,label in ((1,'Starting\nvalue'),(2,'Aptitude\ngrowth')):
                ttk.Label(aptitudes,text=label,style='Hint.TLabel').grid(row=0,column=col,padx=3)
            for i in range(13):
                field = self.doc.by_offset[0x248+i]
                ttk.Label(aptitudes,text=field.label,width=12).grid(row=i+1,column=0,sticky='w')
                for col,start in enumerate((0x248,0x255),1):
                    f=self.doc.by_offset[start+i]
                    widget=ttk.Entry(aptitudes,width=5,justify='right');widget.insert(0,str(self.doc.value(record,f)))
                    widget.grid(row=i+1,column=col,padx=2,pady=2); self.widgets[f.offset]=(f,widget)
            ttk.Separator(body).pack(fill='x',pady=8)
            levels = ttk.Frame(body); levels.pack(fill='x')
            offsets = list(range(0x1ba,0x1c2)) + [0x21a,0x21b,0x262]
            controls=[]
            for i,off in enumerate(offsets):
                f=self.doc.by_offset[off]
                label=ttk.Label(levels,text=f.label)
                widget=ttk.Entry(levels,width=6,justify='right');widget.insert(0,str(self.doc.value(record,f)))
                controls.append((label,widget));self.widgets[off]=(f,widget)
            def arrange(event):
                columns=3 if event.width>=790 else 2
                for i,(label,widget) in enumerate(controls):
                    col=(i%columns)*2;row=i//columns
                    label.grid(row=row,column=col,sticky='w',padx=(0,5),pady=3)
                    widget.grid(row=row,column=col+1,sticky='w',padx=(0,14),pady=3)
            levels.bind('<Configure>',arrange)

        def show(self, record):
            if isinstance(self.doc,EventView):
                from event_ui import show_table
                return show_table(self,record)
            if isinstance(self.doc,ExpandedView):
                from expanded_ui import show_table
                return show_table(self,record)
            if isinstance(self.doc,Legion):
                from legion_ui import show_legion
                return show_legion(self,record)
            if isinstance(self.doc,DeploymentView):
                from deployment_ui import show_table
                return show_table(self,record)
            if isinstance(self.doc,ShopView):
                from shop_ui import show_table
                return show_table(self,record)
            if isinstance(self.doc,FacilityView):
                from facility_ui import show_row
                return show_row(self,record)
            if isinstance(self.doc,ProfileView):
                from profile_ui import show_row
                return show_row(self,record)
            if isinstance(self.doc,AppearanceView):
                from appearance_ui import show_row
                return show_row(self,record)
            if isinstance(self.doc,RelianceView):
                from supports_ui import show_row
                return show_row(self,record)
            if isinstance(self.doc,Item):
                from item_ui import show_item
                return show_item(self,record)
            if isinstance(self.doc,Skill):
                from skill_ui import show_skill
                return show_skill(self,record)
            if isinstance(self.doc,Progression):
                from progression_ui import show_table
                return show_table(self,record)
            if isinstance(self.doc,Learning):
                from learning_ui import show_table
                return show_table(self,record)
            if isinstance(self.doc,Job):return self.show_class(record)
            active = self.notebook.index('current') if self.notebook.tabs() else 0
            self.clear_previews()
            self.current = record; self.widgets = {}
            self.heading.set(self.display(record))
            serial = self.doc.original(record, self.doc.by_offset[0x30])
            self.details.set(f'{record.pid}  ·  Serial {serial} · '+('new character (serial fixed at creation)' if record.pid in self.doc.new_characters else 'original slot (fixed)'))
            for tab in self.notebook.tabs(): self.nametowidget(tab).destroy()
            groups = {name:[] for name in ('Character','Classes','Stats','Skills','Items','Advanced','Used by')}
            for field in self.doc.fields:
                offset=field.offset
                tab=('Character' if offset in (0x20,0x28,0x30,0x1b8,0x1b9,0x268,0x278,0x280,0x290,0x148,0x118,0x108,0x2b0) else
                     'Classes' if offset in (0x38,0x48,0x58,0x68,0x88,0x128) else
                     'Stats' if 0x1ba<=offset<=0x262 else
                     'Skills' if 0x98<=offset<=0xf8 else
                     'Items' if offset in (0x78,0x168,0x178,0x188,0x198,0x1a8) else 'Advanced')
                groups[tab].append(field)
            tips={
                'Character':'Change display identity and appearance here. Slot IDs and serials stay fixed.',
                'Classes':'Raw IDs stay editable. English names update beside them as you type.',
                'Skills':'Keep route roles such as convoy access and Blaze eligibility when needed.',
                'Items':'Lists use one raw reference per line; + opens an English-searchable chooser.',
                'Advanced':'Undocumented flags and raw engine fields. Double-click an English preview to add a translation.',
            }
            for title,fields in groups.items():
                tab = ttk.Frame(self.notebook); self.notebook.add(tab,text=title)
                canvas=tk.Canvas(tab,highlightthickness=0,background='#f4f5f7')
                bar=ttk.Scrollbar(tab,orient='vertical',command=canvas.yview)
                canvas.configure(yscrollcommand=bar.set);bar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
                body=ttk.Frame(canvas,padding=8);window=canvas.create_window((0,0),window=body,anchor='nw')
                body.bind('<Configure>',lambda event,c=canvas:c.configure(scrollregion=c.bbox('all')))
                canvas.bind('<Configure>',lambda event,c=canvas,w=window:c.itemconfigure(w,width=max(event.width,c.winfo_reqwidth())))
                def wheel(event,c=canvas):
                    if c.bbox('all') and c.bbox('all')[3]>c.winfo_height():
                        c.yview_scroll(-1 if getattr(event,'num',0)==4 or getattr(event,'delta',0)>0 else 1,'units')
                    return 'break'
                # Bind each tab's descendants, without replacing other applications' global wheel bindings.
                if title=='Stats':
                    self.stat_grid(body,record)
                elif title=='Used by':
                    from person_ui import usage
                    usage(self,body,record)
                else:
                    first=0
                    if title=='Character':
                        from person_ui import tools
                        tools(self,body,record);first=2
                    ttk.Label(body,text=tips[title],style='Hint.TLabel',wraplength=700).grid(row=first,column=0,columnspan=4,sticky='w',pady=(0,8))
                    for column,text in ((0,'Field'),(1,'Raw reference / Japanese'),(2,'English / explanation'),(3,'Source')):
                        ttk.Label(body,text=text,style='Hint.TLabel').grid(row=first+1,column=column,sticky='w',pady=(0,3))
                    references=[f for f in fields if f.kind in TEXT_TYPES|ARRAY_TYPES]
                    numeric=[f for f in fields if f.kind in FORMATS]
                    for row,field in enumerate(references+numeric,first+2):
                        if field.kind in TEXT_TYPES|ARRAY_TYPES: self.reference_row(body,row,field,record)
                        else:self.numeric_row(body,row,field,record)
                    body.columnconfigure(1,weight=1,uniform='references',minsize=165)
                    body.columnconfigure(2,weight=1,uniform='references',minsize=165)
                def bind_wheel(widget,fn=wheel):
                    if not isinstance(widget,tk.Text):
                        for event in ('<MouseWheel>','<Button-4>','<Button-5>'):widget.bind(event,fn,add='+')
                    for child in widget.winfo_children():bind_wheel(child,fn)
                bind_wheel(body)
                for event in ('<MouseWheel>','<Button-4>','<Button-5>'):canvas.bind(event,wheel)
            self.notebook.select(min(active,len(groups)-1))

        def suggestions(self, field):
            if isinstance(self.doc,EventView):
                from event_ui import suggestions
                return suggestions(self,field)
            if isinstance(self.doc,ExpandedView):
                from expanded_ui import suggestions
                return suggestions(self,field)
            if isinstance(self.doc,Legion):
                from legion_ui import suggestions
                return suggestions(self,field)
            if isinstance(self.doc,Progression):
                category=self.doc.value(self.learning_row,self.doc.by_offset[0x20]) if self.learning_row else None
                if 0x20 in self.widgets:category=self.widget_value(*self.widgets[0x20])
                if type(category) is not int or not 0<=category<=255:raise DataError('Category code must be between 0 and 255.')
                prefix=self.doc.reference_prefix(category)
                values={self.doc.value(row,f) for row in self.doc.records if self.doc.value(row,self.doc.by_offset[0x20])==category for f in self.doc.fields[1:]}
                if prefix:values.update(key.removeprefix(prefix) for key in reference_ids(self,prefix))
                return sorted(values-{''})
            if isinstance(self.doc,DeploymentView):
                from deployment_ui import suggestions
                return suggestions(self,field)
            if isinstance(self.doc,ShopView):
                from shop_ui import suggestions
                return suggestions(self,field)
            if isinstance(self.doc,FacilityView):
                from facility_ui import suggestions
                return suggestions(self,field)
            if isinstance(self.doc,ProfileView):
                from profile_ui import suggestions
                return suggestions(self,field)
            if isinstance(self.doc,AppearanceView):
                from appearance_ui import suggestions
                return suggestions(self,field)
            if isinstance(self.doc,RelianceView):
                from supports_ui import suggestions
                return suggestions(self,field)
            if isinstance(self.doc,Item):
                from item_ui import suggestions
                return suggestions(self,field)
            if isinstance(self.doc,Skill):
                from skill_ui import suggestions
                return suggestions(self,field)
            if isinstance(self.doc,Person) and field.offset==0x88:
                values={value for row in self.doc.records for value in self.doc.value(row,field) if value}
                growth=self.documents.get('Learning tables')
                if growth:values.update(growth.tables_by_id)
                return sorted(values)
            prefix={0x20:'MPID_',0x38:'JID_',0x48:'JID_',0x58:'JID_',0x78:'IID_',0x88:'LID_',
                    0x98:'SID_',0xa8:'SID_',0xb8:'SID_',0xc8:'SID_',0xd8:'SID_',0xe8:'SID_',0xf8:'SID_',
                    0x118:'PRF_',0x128:'GLID_',0x148:'BID_',0x168:'IID_',0x178:'IID_',0x198:'IID_',
                    0x268:'PID_',0x278:'AID_',0x2b0:'PID_'}.get(field.offset)
            if isinstance(self.doc,Job):
                prefix={0x20:'MJID_',0x28:'MJID_',0x48:'JID_',0x50:'JID_',0x58:'JID_',0x68:'RID_',0x80:'IID_',
                        **{offset:'SID_' for offset in range(0x90,0x101,0x10)},
                        0x1d8:'IID_',0x1e8:'PID_',0x208:'IID_',0x228:'AID_'}.get(field.offset)
            if isinstance(self.doc,Learning):prefix={0x28:'SID_'}.get(field.offset)
            cache_key=(self.doc.filename,field.offset)
            if prefix in ('IID_','JID_','PID_') or cache_key not in self.suggestion_cache:
                values=set()
                for record in self.doc.records:
                    value=self.doc.original(record,field)
                    values.update(entry for row in value for entry in row) if field.kind in NESTED_TYPES else values.update(value if isinstance(value,list) else [value])
                values.discard('')
                if prefix:
                    values.update(reference_ids(self,prefix))
                    if prefix in ('MPID_','MJID_'):values.update(key for key in self.names if key.startswith(prefix))
                if prefix in ('IID_','JID_','PID_'):return sorted(values)
                self.suggestion_cache[cache_key]=sorted(values)
            return self.suggestion_cache[cache_key]

        def pick(self, field, widget):
            try:
                values=self.suggestions(field)
                rows=[(value,self.translate_value(value,field)) for value in values]
            except DataError as exc:self.error(exc);return
            dialog=tk.Toplevel(self);dialog.title('Choose '+field.label);dialog.geometry('850x500');dialog.minsize(650,350);dialog.transient(self)
            search=tk.StringVar();search_entry=ttk.Entry(dialog,textvariable=search)
            search_entry.pack(fill='x',padx=8,pady=8);search_entry.focus_set()
            listing=ttk.Treeview(dialog,columns=('name','id','source'),show='headings',selectmode='extended' if field.kind in LIST_TYPES else 'browse')
            for key,label,width in [('name','English / explanation',300),('id','Raw reference / Japanese',350),('source','Source',120)]:
                listing.heading(key,text=label);listing.column(key,width=width)
            listing.pack(side='top',fill='both',expand=True,padx=8)
            bar=ttk.Scrollbar(dialog,orient='vertical',command=listing.yview);listing.configure(yscrollcommand=bar.set)
            bar.place(relx=1,x=-8,y=45,relheight=1,height=-91,anchor='ne')
            query_job=None
            def refresh(*_):
                listing.delete(*listing.get_children());query=search.get().casefold().strip()
                for i,(value,result) in enumerate(rows):
                    if not query or query in (result.text+' '+value).casefold():
                        listing.insert('','end',iid=str(i),values=(result.text,value,result.source))
            def choose():
                chosen=[values[int(i)] for i in listing.selection()]
                if not chosen:return
                if field.kind in LIST_TYPES:
                    existing=widget.get('1.0','end-1c').strip()
                    widget.delete('1.0','end');widget.insert('1.0',(existing+'\n' if existing else '')+'\n'.join(chosen))
                elif self.multiline_text(field):widget.delete('1.0','end');widget.insert('1.0',chosen[0])
                else:widget.delete(0,'end');widget.insert(0,chosen[0])
                self.update_preview(field.offset)
                dialog.destroy()
            search.trace_add('write',refresh);refresh()
            listing.bind('<Double-1>',lambda _:choose());listing.bind('<Return>',lambda _:choose())
            ttk.Button(dialog,text='Use selection',command=choose,style='Accent.TButton').pack(anchor='e',padx=8,pady=8)

        def glossary(self, raw=''):
            dialog=tk.Toplevel(self);dialog.title('Translation glossary');dialog.geometry('720x480');dialog.transient(self)
            ttk.Label(dialog,text='Local display translations · raw game IDs stay unchanged',font=('DejaVu Sans',10,'bold')).pack(anchor='w',padx=10,pady=8)
            ttk.Label(dialog,text='Use an exact ID or a Japanese word. Word translations also apply inside longer IDs.\nChanges update the editor immediately. No text is sent to an online service.',wraplength=680).pack(anchor='w',padx=10)
            form=ttk.Frame(dialog,padding=10);form.pack(fill='x');form.columnconfigure(1,weight=1)
            source=tk.StringVar(value=raw);english=tk.StringVar(value=self.custom_translations.get(raw,''))
            ttk.Label(form,text='Japanese / raw ID').grid(row=0,column=0,sticky='w',padx=(0,8))
            ttk.Entry(form,textvariable=source).grid(row=0,column=1,sticky='ew',pady=3)
            ttk.Label(form,text='English').grid(row=1,column=0,sticky='w')
            target=ttk.Entry(form,textvariable=english);target.grid(row=1,column=1,sticky='ew',pady=3)
            listing=ttk.Treeview(dialog,columns=('raw','english'),show='headings',selectmode='browse',height=7)
            listing.heading('raw',text='Custom raw ID / word');listing.heading('english',text='English')
            listing.pack(fill='both',expand=True,padx=10)
            def refresh():
                listing.delete(*listing.get_children())
                for i,(key,value) in enumerate(sorted(self.custom_translations.items())):
                    listing.insert('','end',iid=str(i),values=(key,value))
            def selected(event=None):
                if listing.selection():
                    key,value=listing.item(listing.selection()[0],'values');source.set(key);english.set(value)
            def store(remove=False):
                key=source.get().strip();value=english.get().strip()
                if not key or (not remove and not value):return
                updated=dict(self.custom_translations)
                if remove:updated.pop(key,None)
                else:updated[key]=value
                try:atomic_write(self.glossary_path,json.dumps(updated,ensure_ascii=False,indent=2).encode('utf8'))
                except OSError as exc:self.error(exc);return
                self.custom_translations=updated;self.rebuild_translator();refresh()
                self.status.set('Display glossary saved. Raw references and project edits are unchanged.')
            buttons=ttk.Frame(dialog,padding=10);buttons.pack(fill='x')
            ttk.Button(buttons,text='Save translation',command=store,style='Accent.TButton').pack(side='left')
            ttk.Button(buttons,text='Remove',command=lambda:store(True)).pack(side='left',padx=5)
            ttk.Button(buttons,text='Close',command=dialog.destroy).pack(side='right')
            listing.bind('<<TreeviewSelect>>',selected);refresh()
            if raw:target.focus_set()

        def reset(self):
            if not self.current:return
            pid=self.current.pid
            if isinstance(self.doc,CollectionTable):self.doc.reset_table(pid)
            else:self.doc.changes={key:value for key,value in self.doc.changes.items() if key[0]!=pid}
            self.show(self.current);self.filter();self.status.set('Entry restored to source values.')

        def save_project(self):
            if not self.documents or not self.apply(True):return
            path=filedialog.asksaveasfilename(title='Save edit project',defaultextension='.json',initialdir=self.preferences.initial_dir('last_project'),initialfile=self.project_path.name if self.project_path else 'crednas-creation-kit-project.json',filetypes=[('Edit project','*.json')],parent=self)
            if not path:return
            try:
                if Path(path).suffix.lower() != '.json':
                    raise DataError('Save projects with a .json extension.')
                atomic_write(path,json.dumps(suite_project(self.documents),ensure_ascii=False,indent=2).encode('utf8'))
                self.saved_state = self.session_state()
                self.remember_project(path)
                self.status.set('Project saved: '+path)
            except Exception as exc:self.error(exc)

        def load_project(self):
            if not self.documents:self.error('Open the original editable game tables first.');return
            path=filedialog.askopenfilename(title='Open edit project',initialdir=self.preferences.initial_dir('last_project'),filetypes=[('Edit project','*.json')],parent=self)
            if not path:return
            try:
                if not self.apply(True):return
                if any(doc.modified for doc in self.documents.values()) and not messagebox.askyesno('Open project','Replace current edits with this project?',parent=self):return
                from script_data import load_with_scripts
                load_with_scripts(self.documents,self.sources,self.data_directory,json.loads(Path(path).read_text(encoding='utf8')),load_suite_project)
                self.suggestion_cache.clear()
                self.saved_state = self.session_state()
                self.remember_project(path)
                if self.current:
                    if isinstance(self.doc,Learning):self.current=self.doc.tables_by_id.get(self.current.pid,self.doc.collections[0])
                    if isinstance(self.doc,(Item,Job,Person)):self.current=self.doc.by_pid.get(self.current.pid,self.doc.records[0])
                    self.show(self.current)
                self.rebuild_translator()
                self.filter();self.status.set('Project loaded · '+str(sum(len(doc.changes) for doc in self.documents.values()))+' changed fields · '+str(sum(getattr(doc,'added_count',0) for doc in self.documents.values()))+' added entries.')
            except Exception as exc:self.error(exc)

        def export(self):
            if not self.documents or not self.apply(True):return
            directory=filedialog.askdirectory(title='Choose a separate mod folder for the loaded tables',initialdir=self.preferences.initial_dir('last_export'),parent=self)
            if not directory:return
            try:
                targets=export_suite(self.documents,self.sources,directory)
                self.remember_paths(last_export=str(Path(directory).resolve()))
                self.saved_state = self.session_state()
                self.filter();self.status.set('Exported '+', '.join(t.name for t in targets))
                messagebox.showinfo('Mod exported',f'Created:\n'+ '\n'.join(str(t) for t in targets)+'\n\nPlace this mod folder inside Eden’s mod directory. Restart the game to test.\nOriginal files were not changed.',parent=self)
            except Exception as exc:self.error(exc)

        def close(self):
            try:dirty=bool(self.documents and (self.session_state() != self.saved_state or self.dirty_widgets()))
            except Exception:dirty=True
            if dirty and not messagebox.askyesno('Close editor','Close this session? Save a project first if you want to keep your edits.',parent=self):return
            self.destroy()

    Editor().mainloop()


if __name__ == '__main__':
    try:
        main()
    except ImportError as exc:
        hint = 'Install official Python with Tcl/Tk support.' if sys.platform == 'win32' else 'Install Tk support: sudo apt install python3-tk'
        raise SystemExit(hint+'\n'+str(exc))
