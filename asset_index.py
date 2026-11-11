"""Read-only AID discovery, appearance-rule inspection and source evidence.

Consumes the existing binary reader through dependency injection; no game data,
asset-rule evaluation, writes, or runtime appearance predictions are included.
"""
from dataclasses import dataclass
from collections import defaultdict
from pathlib import Path
import re
import struct

AID_PATTERN = re.compile(r'(?<![\w])(?P<negative>!?)(?P<aid>AID_[^,\s;"\'<>\[\]{}!&|]+)')
GROUP_NAMES = {'アセットテーブル':'Appearance rules','アセット情報':'Asset information',
               'バリエーション':'Variations','容姿情報':'Voice / portrait', '条件セット':'Condition sets'}
FIELD_NAMES = {
    '条件':'Conditions','追加フラグ':'Additional flags','体モデル':'Body model','体格':'Build value',
    '頭モデル':'Head model','髪モデル':'Hair model','馬モデル':'Mount model','馬衣装1':'Mount outfit 1',
    '馬衣装2':'Mount outfit 2','右手':'Right hand','左手':'Left hand','魔法':'Magic',
    'アニメ':'Animations','表情アニメ':'Face animation','アクセサリ':'Accessories',
    '足跡エフェクト':'Footstep effects','傷マスク':'Wound mask','傷カラー':'Wound color',
    'タトゥーマスク':'Tattoo mask','タトゥーカラー':'Tattoo color','足音':'Footstep sound',
    '武器材質':'Weapon material','鎧(服)材質':'Armor / clothing material','LODプリセット':'LOD preset',
    'マップ':'Map scale','全身':'Full-body scale','頭':'Head scale','部位':'Part scale',
    '肌パターン':'Skin pattern','肌カラー':'Skin color','髪カラー':'Hair color','髪グラデ0':'Hair gradient 0',
    '髪グラデ1':'Hair gradient 1','チーク色':'Cheek color','口紅色':'Lip color','爪色':'Nail color',
    '白目色':'Eye white','目基本色':'Eye base color','目グラデ':'Eye gradient',
    '馬の毛':'Mount coat color','馬の肌':'Mount skin color','毛グラデ0':'Coat gradient 0',
    '毛グラデ1':'Coat gradient 1','武器色':'Weapon color','容姿':'Appearance link',
    'AOVプリセット':'AOV preset','キーワード':'Keywords','ボイス':'Voice ID','フェイス':'Portrait ID',
    '特殊':'Special value','会話フェイス\nノイズ再生':'Dialogue portrait noise',
    '会話フェイス\n非表示':'Hide dialogue portrait',
}


def aid_tokens(text):
    """Return complete (AID, negated) tokens; commas split flags, parentheses do not."""
    return tuple((m['aid'],bool(m['negative'])) for m in AID_PATTERN.finditer(text))


def field_label(name):
    if name in FIELD_NAMES:return FIELD_NAMES[name]
    if name.startswith('マスク'):return 'Mask '+name[-1]
    if name.startswith('バリエーション'):return 'Variation '+name.removeprefix('バリエーション')
    # Asset information fields contain long Japanese comments; their stable offsets
    # are retained alongside concise translations of the bracketed heading.
    if name.startswith('【'):
        heading=name.partition('】')[0][1:]
        return {'武器サウンドID':'Weapon sound ID','サウンド汎用ID':'Generic sound ID',
                '武器落下音':'Weapon drop sound','追加足音':'Additional footsteps',
                'オーラ詳細':'Detailed aura','オーラ簡略':'Simplified aura','攻撃エフェクト':'Attack effect',
                'ダメージエフェクト':'Damage effect','死亡時エフェクト':'Death effect',
                'ユニークID':'Unique effect ID','モンスターカメラ':'Monster camera',
                'エフェクトサイズ':'Effect scale'}.get(heading,heading)
    return name


def flatten(value):
    if isinstance(value,str):yield value
    elif isinstance(value,list):
        for entry in value:yield from flatten(entry)


@dataclass(frozen=True)
class AssetField:
    name: str
    kind: str
    size: int
    offset: int

    @property
    def label(self):return field_label(self.name)


@dataclass
class AssetRow:
    source: str
    group: str
    index: int
    offset: int
    label: str
    fields: tuple
    values: dict

    @property
    def key(self):return (self.source,self.group,self.index)

    @property
    def title(self):return f'{self.source} · {GROUP_NAMES.get(self.group,self.group)} #{self.index}'


@dataclass(frozen=True)
class Evidence:
    aid: str
    source: str
    offset: int
    text: str
    negative: bool


@dataclass(frozen=True)
class User:
    module: str
    record: str
    field: str
    relationship: str
    text: str


class AssetTable:
    """Decode the five supplied AssetTable group layouts, including unnamed rows."""
    def __init__(self, source, binary):
        self.source=source;self.binary=binary;self.rows=[];self.by_label={};self.groups={}
        expected={'アセットテーブル':(384,49),'アセット情報':(128,12),
                  'バリエーション':(192,10),'容姿情報':(80,11),'条件セット':(64,2)}
        for group,stride,count,schema in binary.groups():
            if group not in expected or (stride,count)!=expected[group]:
                raise ValueError(f'Unsupported asset group layout: {group}')
            fields=[]
            for i in range(count):
                n,k,_,size,offset=struct.unpack_from('<QQQII',binary.raw,schema+i*32)
                if offset<32 or offset+size>stride:raise ValueError('Asset field is outside its record.')
                fields.append(AssetField(binary.string(n),binary.string(k),size,offset))
            rows=[];start=schema+count*32
            for i in range(65536):
                at=start+i*stride
                if at+stride>32+binary.size or struct.unpack_from('<HH',binary.raw,at+16)!=(i,1):break
                label=binary.string(struct.unpack_from('<Q',binary.raw,at+8)[0])
                values={f.offset:self.read(at+f.offset,f.kind) for f in fields}
                row=AssetRow(source,group,i,at,label,tuple(fields),values)
                rows.append(row);self.rows.append(row)
                if label:self.by_label[label]=row
            self.groups[group]=rows
        if 'アセットテーブル' not in self.groups:raise ValueError('The appearance-rule group is missing.')

    @classmethod
    def from_document(cls,document):
        table=cls.__new__(cls);table.source=document.filename;table.binary=document
        table.rows=[];table.by_label={};table.groups={}
        for view in document.views.values():
            fields=tuple(AssetField(f.name,f.kind,f.size,f.offset) for f in view.fields);rows=[]
            for record in view.records:
                values={f.offset:view.value(record,f) for f in view.fields}
                row=AssetRow(document.filename,view.group_name,record.index,record.offset,view.names[record.pid],fields,values)
                rows.append(row);table.rows.append(row)
                if row.label:table.by_label[row.label]=row
            table.groups[view.group_name]=rows
        return table

    def read(self,at,kind):
        b=self.binary
        formats={'u8':'B','bool':'B','u32':'I','f32':'f'}
        if kind in formats:return struct.unpack_from('<'+formats[kind],b.raw,at)[0]
        if kind=='color':return '#'+b.raw[at:at+4].hex().upper()
        if kind in ('string','data'):return b.string(struct.unpack_from('<Q',b.raw,at)[0])
        if kind in ('string[]','string[,]'):
            count,width,_,pointer=struct.unpack_from('<HHIQ',b.raw,at)
            expected=16 if kind=='string[,]' else 8
            if width!=expected or (count and (not pointer or pointer+count*width>b.size)):
                raise ValueError('Invalid asset array layout.')
            return [self.read(pointer+32+i*width,'string[]' if kind=='string[,]' else 'string') for i in range(count)]
        raise ValueError('Unsupported asset field type: '+kind)


class AssetIndex:
    def __init__(self):
        self.tables=[];self.rows=[];self.rows_by_aid=defaultdict(list)
        self.mentions_by_row={};self.definitions=defaultdict(list)
        self.evidence=defaultdict(list);self.errors=[];self.scanned_files=[]
        self.base_aids=set();self.aids=[];self.users=defaultdict(list);self.documents={}
        self.base_sources=defaultdict(set);self.sources_by_aid={}
        self.by_label=defaultdict(list)

    @classmethod
    def load(cls,base,binary_type):
        index=cls();base=Path(base)
        # AssetTable side files are additive source evidence; no overlay order is assumed.
        for path in sorted(base.glob('AssetTable*.bin')):
            try:index.add_table(AssetTable(path.name,binary_type(path.read_bytes())))
            except (ValueError,struct.error,OSError,UnicodeError) as exc:index.errors.append((path.name,str(exc)))
        # Index exact strings in the available GameData tree, without treating a
        # string occurrence as a confirmed field assignment or resolved appearance.
        for path in sorted(base.rglob('*.bin')):
            source=path.relative_to(base).as_posix()
            if path.name.startswith('AssetTable') and path.parent==base:continue
            try:
                b=binary_type(path.read_bytes());index.scanned_files.append(source)
                seen=set()
                for at in b.pointers:
                    pointer=struct.unpack_from('<Q',b.raw,at+32)[0]
                    if pointer<b.pool or pointer in seen:continue
                    seen.add(pointer);text=b.string(pointer)
                    for aid,negative in set(aid_tokens(text)):
                        index.base_aids.add(aid)
                        index.base_sources[aid].add(source)
                        index.evidence[aid].append(Evidence(aid,source,pointer+32,text,negative))
            except (ValueError,struct.error,OSError,UnicodeError) as exc:index.errors.append((source,str(exc)))
        index.refresh_users({})
        return index

    def add_table(self,table):
        self.tables.append(table)
        if table.source not in self.scanned_files:self.scanned_files.append(table.source)
        for row in table.rows:
            self.rows.append(row)
            if row.label:self.by_label[row.label].append(row)
            mentions=set(aid_tokens(row.label))
            for value in row.values.values():
                for text in flatten(value):mentions.update(aid_tokens(text))
            self.mentions_by_row[row.key]=mentions
            for aid,negative in mentions:
                self.base_aids.add(aid);self.rows_by_aid[aid].append(row)
                self.base_sources[aid].add(table.source)
            # An AID-labelled condition set is a definition; an AID appearing in
            # its conditions is only a reference to a different flag.
            if row.group=='条件セット' and row.label.startswith('AID_'):
                self.definitions[row.label].append(row)

    def refresh_tables(self,documents):
        # Rebuild current rules from the loaded documents. Raw non-asset string
        # evidence remains original; removed rule flags must not survive as stale rules.
        if not hasattr(self,'original_tables'):self.original_tables=list(self.tables)
        active={doc.filename:doc for doc in documents.values() if doc.prefix=='APPEARANCE_'}
        signature=tuple((source,id(doc),repr(sorted(doc.changes.items()))) for source,doc in sorted(active.items()))
        if getattr(self,'table_signature',None)==signature:return
        self.table_signature=signature
        originals={table.source:table for table in self.original_tables}
        self.tables=[];self.rows=[];self.rows_by_aid=defaultdict(list);self.mentions_by_row={}
        self.definitions=defaultdict(list);self.by_label=defaultdict(list)
        self.base_aids=set(self.evidence);self.base_sources=defaultdict(set)
        for aid,refs in self.evidence.items():self.base_sources[aid].update(ref.source for ref in refs)
        for source in sorted(set(originals)|set(active)):
            self.add_table(AssetTable.from_document(active[source]) if source in active else originals[source])

    def refresh_users(self,documents):
        self.refresh_tables(documents)
        self.documents=documents;self.users=defaultdict(list);aids=set(self.base_aids)
        sources={aid:set(files) for aid,files in self.base_sources.items()}
        direct_by_person=defaultdict(list)
        targets=[('Characters',0x278),('Classes',0x228),('Legion',0xa0)]+[(name,0x1b8) for name,doc in documents.items() if doc.prefix=='IID_' and 0x1b8 in doc.by_offset]
        for module,offset in targets:
            doc=documents.get(module)
            if doc is None:continue
            for record in doc.records:
                seen=set()
                for text in flatten(doc.value(record,doc.by_offset[offset])):
                    for aid,negative in set(aid_tokens(text)):
                        if (aid,negative) in seen:continue
                        seen.add((aid,negative))
                        aids.add(aid)
                        sources.setdefault(aid,set()).add(doc.filename)
                        self.users[aid].append(User(module,record.pid,'Asset flag',
                            'Negated flag' if negative else 'Direct flag',text))
                        if module=='Characters' and not negative:direct_by_person[record.pid].append(aid)
        person=documents.get('Characters')
        if person:
            for record in person.records:
                # Show links as relationships, not as a prediction of inherited
                # models: original-character links do not prove asset inheritance.
                for offset,field in ((0x268,'Reuse assets from character'),(0x2b0,'Original character')):
                    target=person.value(record,person.by_offset[offset]);seen={record.pid};chain=[record.pid]
                    while target in person.by_pid and target not in seen:
                        chain.append(target);seen.add(target)
                        for aid in direct_by_person[target]:
                            self.users[aid].append(User('Characters',record.pid,field,'Linked character', ' → '.join(chain)))
                        target=person.value(person.by_pid[target],person.by_offset[offset])
        self.aids=sorted(aids)
        self.sources_by_aid={aid:tuple(sorted(files,key=str.casefold)) for aid,files in sources.items()}

    def sources_for(self,aid):
        """All discovery files, not an inferred single origin or runtime priority."""
        return self.sources_by_aid.get(aid,())

    def source_files(self):
        return sorted({source for files in self.sources_by_aid.values() for source in files},key=str.casefold)

    def direct_count(self,aid):
        return len({(u.module,u.record) for u in self.users[aid] if u.relationship=='Direct flag'})

    def linked_rows(self,aid):
        """Follow named string/data links; list possibilities without evaluating rules."""
        seeds=self.rows_by_aid.get(aid,[]);queue=[];seen={row.key for row in seeds};results=[]
        for row in seeds:
            if (aid,False) in self.mentions_by_row[row.key]:queue.append((row,0))
        for row,depth in queue:
            for field in row.fields:
                if field.kind not in ('data','string'):continue
                value=row.values[field.offset]
                if field.name=='容姿' and value:
                    value=value if value.startswith('FID_') else 'FID_'+value
                candidates=self.by_label.get(value,[])
                # Keep same-file matches and side-file alternatives distinct.
                for target in candidates:
                    if target.key in seen:continue
                    seen.add(target.key);results.append(target);queue.append((target,depth+1))
        return results

    def coverage(self):
        return {'files':list(self.scanned_files),'errors':list(self.errors),
                'asset_tables':{table.source:{name:len(rows) for name,rows in table.groups.items()} for table in self.tables},
                'aids':len(self.aids)}
