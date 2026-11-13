"""Synthetic format fixture. Contains no game data."""
import struct


def person_fixture():
    fields = [('名前','string',8,0x20), ('識別子','string',8,0x28),
              ('通し番号','u8',1,0x30), ('HP','s16',2,0x1c2),
              ('Items','data[]',16,0x78), ('Conditions','string[]',16,0x1a8),
              ('Assets','string',8,0x278), ('Reuse','data',16,0x268), ('Original','data',16,0x2b0)]
    occupied = {at+i for _,_,size,at in fields for i in range(size)}
    for at in range(0x31,704):
        if len(fields)==143: break
        if at not in occupied: fields.append((f'Field_{at}','u8',1,at))
    fields.sort(key=lambda f:f[3])
    start = len(fields)*32
    body=bytearray(start+2*704)
    pointers={}
    pool=bytearray()
    strings={}

    def string(at,value):
        if value not in strings:
            strings[value]=len(pool);pool.extend(value.encode('utf8')+b'\0')
        pointers[at]=('string',strings[value])

    for i,(name,kind,size,at) in enumerate(fields):
        string(i*32,name);string(i*32+8,kind)
        struct.pack_into('<II',body,i*32+24,size,at)
    shared=len(body);body.extend(b'\0'*16);string(shared,'IID_SYNTHETIC')
    labels=[]
    for i in range(2):
        at=start+i*704
        pid=f'PID_SYNTHETIC_{i}'
        string(at+8,pid);labels.append((at,strings[pid]))
        struct.pack_into('<HH',body,at+16,i,1)
        string(at+0x20,f'MPID_SYNTHETIC_{i}');string(at+0x28,f'Synthetic{i}')
        struct.pack_into('<B',body,at+0x30,i+1)
        struct.pack_into('<h',body,at+0x1c2,20+i)
        struct.pack_into('<HHIQ',body,at+0x78,1,16,0,shared)
        pointers[at+0x80]=('data',shared)
        struct.pack_into('<HHIQ',body,at+0x1a8,0,8,0,0)
    meta=len(body);body.extend(b'\0'*32)
    struct.pack_into('<Q',body,meta,0x120251201)
    string(meta+8,'個人');struct.pack_into('<IIQ',body,meta+16,704,143,0)
    pointers[meta+24]=('data',0)
    order=sorted(pointers)
    string_base=len(body)+len(order)*8+len(labels)*8
    for at,(kind,value) in pointers.items():
        struct.pack_into('<Q',body,at,string_base+value if kind=='string' else value)
    header=bytearray(32)
    struct.pack_into('<4I',header,0,32+string_base+len(pool),len(body),len(order),len(labels))
    return bytes(header+body+struct.pack(f'<{len(order)}Q',*order)+
                 b''.join(struct.pack('<II',*entry) for entry in labels)+pool)


def job_fixture():
    """Two invented class rows with shared arrays, conditions and direct pointers."""
    fields=[('名前','string',8,0x20),('ヘルプ','string',8,0x28),
            ('移動タイプ','u8',1,0x30),('ランク','u8',1,0x31),
            ('下級職','ref',8,0x48),('上級職','ref',8,0x50),('下馬先','ref',8,0x58),
            ('専用装備','data[]',16,0x80),('所持スキル','data[]',16,0x90),
            ('HP','s16',2,0x120),('CC必要条件','string[,]',16,0x1b8),
            ('CC秘匿条件','string[,]',16,0x1c8),('CC必要アイテム','data',16,0x1d8),
            ('CC禁止キャラ','data[]',16,0x1e8),('アイコン名','string',8,0x200),
            ('HP','s8',1,0x219),('アセットフラグ','string',8,0x228)]
    occupied={at+i for _,_,size,at in fields for i in range(size)}
    for at in range(0x32,560):
        if len(fields)==134:break
        if at not in occupied:fields.append((f'Field_{at}','u8',1,at))
    fields.sort(key=lambda f:f[3])
    start=len(fields)*32;body=bytearray(start+2*560);pool=bytearray();strings={};pointers={}
    def string(at,value):
        if value not in strings:strings[value]=len(pool);pool.extend(value.encode()+b'\0')
        pointers[at]=('string',strings[value])
    for i,(name,kind,size,at) in enumerate(fields):
        string(i*32,name);string(i*32+8,kind);struct.pack_into('<II',body,i*32+24,size,at)
    shared=len(body);body.extend(b'\0'*16);string(shared,'SID_SYNTHETIC')
    outer=len(body);body.extend(b'\0'*32)
    leaf=len(body);body.extend(b'\0'*16)
    string(leaf,'condition_A');string(leaf+8,'condition_B')
    for i in range(2):
        struct.pack_into('<HHIQ',body,outer+i*16,2,8,0,leaf)
        pointers[outer+i*16+8]=('data',leaf)
    labels=[]
    for i in range(2):
        at=start+i*560;key=f'JID_SYNTHETIC_{i}'
        string(at+8,key);labels.append((at,strings[key]));struct.pack_into('<HH',body,at+16,i,1)
        string(at+0x20,f'MJID_SYNTHETIC_{i}');struct.pack_into('<BB',body,at+0x30,i+1,i+1)
        link=at+(0x50 if i==0 else 0x48);pointers[link]=('data',start+(1-i)*560)
        struct.pack_into('<HHIQ',body,at+0x80,0,16,0,0)
        struct.pack_into('<HHIQ',body,at+0x90,1,16,0,shared);pointers[at+0x98]=('data',shared)
        struct.pack_into('<h',body,at+0x120,20+i)
        struct.pack_into('<b',body,at+0x219,-2)
        struct.pack_into('<HHIQ',body,at+0x1b8,2,16,0,outer);pointers[at+0x1c0]=('data',outer)
        struct.pack_into('<HHIQ',body,at+0x1c8,0,16,0,0)
        struct.pack_into('<HHIQ',body,at+0x1e8,0,16,0,0)
    extra=len(body);body.extend(b'\0'*48);string(extra+8,'SUPPORT_SYNTHETIC');string(extra+32,'opaque retained text')
    labels.append((extra,strings['SUPPORT_SYNTHETIC']))
    meta=len(body);body.extend(b'\0'*32);struct.pack_into('<Q',body,meta,0x120251201)
    string(meta+8,'兵種');struct.pack_into('<IIQ',body,meta+16,560,134,0);pointers[meta+24]=('data',0)
    order=sorted(pointers);base=len(body)+len(order)*8+len(labels)*8
    for at,(kind,value) in pointers.items():struct.pack_into('<Q',body,at,base+value if kind=='string' else value)
    header=bytearray(32);struct.pack_into('<4I',header,0,32+base+len(pool),len(body),len(order),len(labels))
    return bytes(header+body+struct.pack(f'<{len(order)}Q',*order)+b''.join(struct.pack('<II',*entry) for entry in labels)+pool)


def asset_fixture(aid='AID_ALPHA',include_info=False):
    """Invented appearance rules, condition sets and a linked FID record."""
    main=[('条件','string[,]',16,0x20),('体モデル','string',8,0x30),
          ('頭モデル','string',8,0x40),('髪モデル','string',8,0x48),
          ('アニメ','string[]',16,0x80),('全身','f32',4,0xfc),
          ('肌カラー','color',4,0x118),('容姿','data',16,0x158)]
    occupied={off+i for _,_,size,off in main for i in range(size)}
    for off in range(0x38,384):
        if len(main)==49:break
        if off not in occupied:main.append((f'Raw_{off}','u8',1,off))
    main.sort(key=lambda f:f[3])
    voice=[('ボイス','string',8,0x20),('フェイス','string',8,0x28),('特殊','u8',1,0x30)]
    voice += [(f'Eye{i}','f32',4,0x34+i*4) for i in range(6)]
    voice += [('Noise','bool',1,0x4c),('Hidden','bool',1,0x4d)]
    groups=[('アセットテーブル',384,main,[('',{0x20:[[aid]],0x30:'CD_TEST',0x40:'HD_TEST',0x158:'Alpha',0xfc:1.25,0x118:'#01020304'}),
              ('',{0x20:[['!'+aid,aid+'_CAPE']],0x30:'CD_NEGATED'}),('Alpha',{0x30:'CD_DEFAULT'})]),
            ('容姿情報',80,voice,[('FID_Alpha',{0x20:'VoiceTest',0x28:'FaceTest'})]),
            ('条件セット',64,[('条件','string[,]',16,0x20),('追加フラグ','string[]',16,0x30)],[(aid,{0x20:[],0x30:['coat']})])]
    if include_info:
        fields=[(f'Effect{off}','string',8,off) for off in range(0x20,0x78,8)]+[('Scale','f32',4,0x78)]
        groups.append(('アセット情報',128,fields,[('INFO_Test',{0x40:'EffectA (BoneA)\nEffectB (BoneB)',0x48:'SmallA\r\nSmallB',0x60:'DeathA\nDeathB',0x78:1.0})]))
    body=bytearray();pool=bytearray();strings={};pointers={};labels=[];pending=[]
    def string(at,value):
        if not value:return
        if value not in strings:strings[value]=len(pool);pool.extend(value.encode()+b'\0')
        pointers[at]=('string',strings[value])
    for group,stride,fields,rows in groups:
        schema=len(body);body.extend(b'\0'*(len(fields)*32));start=len(body);body.extend(b'\0'*(stride*len(rows)))
        for i,(name,kind,size,off) in enumerate(fields):
            string(schema+i*32,name);string(schema+i*32+8,kind);struct.pack_into('<II',body,schema+i*32+24,size,off)
        for i,(label,values) in enumerate(rows):
            at=start+i*stride;struct.pack_into('<HH',body,at+16,i,1)
            if label:string(at+8,label);labels.append((at,strings[label]))
            for name,kind,size,off in fields:
                pending.append((at+off,kind,values.get(off)))
        meta=len(body);body.extend(b'\0'*32);struct.pack_into('<Q',body,meta,0x120251201)
        string(meta+8,group);struct.pack_into('<II',body,meta+16,stride,len(fields));pointers[meta+24]=('data',schema)
    def assign(at,kind,value):
        if kind in ('string','data'):string(at,value or '')
        elif kind=='string[]':
            value=value or [];pointer=len(body) if value else 0;body.extend(b'\0'*(8*len(value)))
            for i,v in enumerate(value):string(pointer+i*8,v)
            struct.pack_into('<HHIQ',body,at,len(value),8,0,pointer)
            if value:pointers[at+8]=('data',pointer)
        elif kind=='string[,]':
            value=value or [];pointer=len(body) if value else 0;body.extend(b'\0'*(16*len(value)))
            for i,row in enumerate(value):assign(pointer+i*16,'string[]',row)
            struct.pack_into('<HHIQ',body,at,len(value),16,0,pointer)
            if value:pointers[at+8]=('data',pointer)
        elif kind=='color':body[at:at+4]=bytes.fromhex((value or '#00000000')[1:])
        else:struct.pack_into('<'+{'u8':'B','bool':'B','f32':'f'}[kind],body,at,value or 0)
    for args in pending:assign(*args)
    order=sorted(pointers);base=len(body)+len(order)*8+len(labels)*8
    for at,(kind,target) in pointers.items():struct.pack_into('<Q',body,at,base+target if kind=='string' else target)
    header=bytearray(32);struct.pack_into('<4I',header,0,32+base+len(pool),len(body),len(order),len(labels))
    return bytes(header+body+struct.pack(f'<{len(order)}Q',*order)+b''.join(struct.pack('<II',*label) for label in labels)+pool)


def learning_fixture():
    """Two invented LIDs, three leaf rows and opaque non-learning data."""
    fields=[('レベル','u8',1,0x20),('技能タイプ','u8',1,0x21),('技能レベル','u8',1,0x22),
            ('スキル','data',16,0x28),('必要条件','string[]',16,0x38)]
    schema=0;start=5*32;body=bytearray(start+2*48);pool=bytearray();strings={};pointers={};labels=[]
    def string(at,value):
        if value not in strings:strings[value]=len(pool);pool.extend(value.encode()+b'\0')
        pointers[at]=('string',strings[value])
    for i,(name,kind,size,offset) in enumerate(fields):
        string(i*32,name);string(i*32+8,kind);struct.pack_into('<II',body,i*32+24,size,offset)
    leaf=len(body);body.extend(b'\0'*3*72)
    for i,(key,amount,pointer) in enumerate((('LID_SYNTHETIC_A',2,leaf),('LID_SYNTHETIC_B',1,leaf+2*72))):
        at=start+i*48;string(at+8,key);labels.append((at,strings[key]));struct.pack_into('<HHHH',body,at+16,i,amount,0,4+i)
        pointers[at+32]=('data',pointer)
        for j in range(amount):
            r=pointer+j*72;string(r+8,key);struct.pack_into('<HHHH',body,r+16,j,1,1,10+i*3+j)
            struct.pack_into('<BBB',body,r+32,5+j,i,j+3);string(r+0x28,'SID_SYNTHETIC_'+str(j))
            struct.pack_into('<HHIQ',body,r+0x38,1,8,0,0)
    shared=len(body);body.extend(b'\0'*8);string(shared,'shared_condition')
    for i in range(3):pointers[leaf+i*72+0x40]=('data',shared)
    extra=len(body);body.extend(b'\0'*48);string(extra+8,'GLID_SYNTHETIC');string(extra+32,'opaque progression value')
    labels.append((extra,strings['GLID_SYNTHETIC']))
    meta=len(body);body.extend(b'\0'*32);struct.pack_into('<Q',body,meta,0x220251201)
    string(meta+8,'技能習得');struct.pack_into('<II',body,meta+16,72,5);pointers[meta+24]=('data',schema)
    order=sorted(pointers);base=len(body)+len(order)*8+len(labels)*8
    for at,(kind,target) in pointers.items():struct.pack_into('<Q',body,at,base+target if kind=='string' else target)
    header=bytearray(32);struct.pack_into('<4I',header,0,32+base+len(pool),len(body),len(order),len(labels))
    return bytes(header+body+struct.pack(f'<{len(order)}Q',*order)+b''.join(struct.pack('<II',*label) for label in labels)+pool)


def growth_fixture():
    """Invented combined LID/GLID data, including shared string targets and opaque bytes."""
    from fw_editor import Binary
    old=Binary(learning_fixture());body=bytearray(old.raw[32:32+old.size]);pool=bytearray(old.raw[32+old.pool:])
    pointers={};strings={}
    for at in old.pointers:
        ptr=struct.unpack_from('<Q',body,at)[0]
        pointers[at]=('string',ptr-old.pool) if ptr>=old.pool else ('data',ptr)
        if ptr>=old.pool:strings[old.string(ptr)]=ptr-old.pool
    labels=[(at-32,strings[key]) for key,at in old.labels.items() if key.startswith('LID_')]
    def string(at,value):
        if not value:return
        if value not in strings:strings[value]=len(pool);pool.extend(value.encode()+b'\0')
        pointers[at]=('string',strings[value])
    body.extend(b'\0'*(-len(body)%8));schema=len(body);body.extend(b'\0'*(81*32+2*48))
    fields=[('カテゴリ','u8',1,0x20)]+[(str(i) if i<80 else '80～','string',8,0x28+(i-1)*8) for i in range(1,81)]
    for i,(name,kind,size,offset) in enumerate(fields):
        string(schema+i*32,name);string(schema+i*32+8,kind);struct.pack_into('<II',body,schema+i*32+24,size,offset)
    start=schema+81*32;leaf=len(body);body.extend(b'\0'*(3*680))
    for i,(key,amount,pointer) in enumerate((('GLID_SYNTHETIC_A',2,leaf),('GLID_SYNTHETIC_B',1,leaf+2*680))):
        at=start+i*48;string(at+8,key);labels.append((at,strings[key]));struct.pack_into('<HHHH',body,at+16,i,amount,0,40+i)
        pointers[at+32]=('data',pointer)
        for j in range(amount):
            r=pointer+j*680;string(r+8,key);struct.pack_into('<HHHH',body,r+16,j,1,1,45+i*3+j)
            body[r+32]=0 if j==0 else 4
            string(r+0x28,'Shared bare name');string(r+0x28+19*8,'テスト');string(r+0x2a0,'80+ raw')
    meta=len(body);body.extend(b'\0'*32);struct.pack_into('<Q',body,meta,0x220251201)
    string(meta+8,'成長リスト');struct.pack_into('<II',body,meta+16,680,81);pointers[meta+24]=('data',schema)
    order=sorted(pointers);base=len(body)+len(order)*8+len(labels)*8
    for at,(kind,target) in pointers.items():struct.pack_into('<Q',body,at,base+target if kind=='string' else target)
    header=bytearray(old.raw[:32]);struct.pack_into('<4I',header,0,32+base+len(pool),len(body),len(order),len(labels))
    return bytes(header+body+struct.pack(f'<{len(order)}Q',*order)+b''.join(struct.pack('<II',*label) for label in labels)+pool)


def skill_fixture():
    """Two invented skill records with shared nested and numeric arrays."""
    fields=[('名前','string',8,0x20),('ヘルプ','string',8,0x30),('引数0','string[]',16,0x38),
            ('種類','u8',1,0x68),('必要スキル','data[,]',16,0x88),('無効スキル','data[,]',16,0x98),
            ('値','s16[]',16,0x100),('周期','u8[]',16,0x120),('物攻','s16',2,0x14a),
            ('物攻','float',4,0x15c),('同時習得スキル','data[]',16,0x1f0),('強制装備','data',16,0x238),('表示','b16',2,0x2f2)]
    occupied={n for _,_,size,offset in fields for n in range(offset,offset+size)}
    for at in range(0x40,904):
        if len(fields)==157:break
        if at not in occupied:fields.append((f'Raw {at}','u8',1,at))
    fields.sort(key=lambda f:f[3]);start=157*32;body=bytearray(start+2*904);pool=bytearray();strings={};pointers={};labels=[]
    def string(at,value):
        if not value:return
        if value not in strings:strings[value]=len(pool);pool.extend(value.encode()+b'\0')
        pointers[at]=('string',strings[value])
    for i,(name,kind,size,off) in enumerate(fields):
        string(i*32,name);string(i*32+8,kind);struct.pack_into('<II',body,i*32+24,size,off)
    nested=len(body);body.extend(b'\0'*16);leaf=len(body);body.extend(b'\0'*32)
    struct.pack_into('<HHIQ',body,nested,2,16,77,leaf);pointers[nested+8]=('data',leaf)
    string(leaf,'SID_SYNTHETIC_B');string(leaf+16,'SID_SYNTHETIC_A')
    # Nonzero opaque cached fields must survive on unchanged/shared original lists.
    struct.pack_into('<Q',body,leaf+8,0x10203040)
    signed=len(body);body.extend(struct.pack('<3h',-300,0,300));period=len(body);body.extend(bytes([1,3,255]))
    body.extend(b'\0'*(-len(body)%8));flat=len(body);body.extend(b'\0'*16);string(flat,'SID_SYNTHETIC_B')
    for i,key in enumerate(('SID_SYNTHETIC_A','SID_SYNTHETIC_B')):
        at=start+i*904;string(at+8,key);labels.append((at,strings[key]));struct.pack_into('<HHHH',body,at+16,i,1,0,20+i)
        string(at+0x20,'MSID_SYNTHETIC_'+str(i));string(at+0x30,'MSID_HELP_'+str(i))
        struct.pack_into('<HHIQ',body,at+0x38,0,8,0,0)
        for off in (0x88,0x98):
            struct.pack_into('<HHIQ',body,at+off,1,16,7,nested);pointers[at+off+8]=('data',nested)
        for off,pointer,count,width in ((0x100,signed,3,2),(0x120,period,3,1),(0x1f0,flat,1,16)):
            struct.pack_into('<HHIQ',body,at+off,count,width,9,pointer);pointers[at+off+8]=('data',pointer)
        struct.pack_into('<f',body,at+0x15c,1.0);struct.pack_into('<h',body,at+0x14a,-5)
    opaque=len(body);body.extend(b'opaque auxiliary bytes!'+b'\0'*10)
    meta=len(body);body.extend(b'\0'*32);struct.pack_into('<Q',body,meta,0x220251201)
    string(meta+8,'スキル');struct.pack_into('<II',body,meta+16,904,157);pointers[meta+24]=('data',0)
    order=sorted(pointers);base=len(body)+len(order)*8+len(labels)*8
    for at,(kind,target) in pointers.items():struct.pack_into('<Q',body,at,base+target if kind=='string' else target)
    header=bytearray(32);struct.pack_into('<4I',header,0,32+base+len(pool),len(body),len(order),len(labels))
    return bytes(header+body+struct.pack(f'<{len(order)}Q',*order)+b''.join(struct.pack('<II',*label) for label in labels)+pool)


def item_fixture():
    """Invented IID records: shared skill lists, signed int32 and an opaque group."""
    fields=[('名前','string',8,0x20),('ヘルプ','string',8,0x30),('引数0','string[]',16,0x38),
            ('種類','u8',1,0x48),('値段','u32',4,0x4c),('売値','u32',4,0x50),('物理攻撃','s16',2,0x6c),
            ('装備スキル','data[]',16,0x98),('使用スキル','data',16,0xb8),('修理素材','data',16,0x108),
            ('素材数','int',4,0x118),('費用','int',4,0x11c),('錬成先','data',16,0x120),('錬成素材','data',16,0x130),
            ('素材数','int',4,0x140),('費用','int',4,0x144),('条件','string',8,0x148),('フラグ','b32',4,0x150)]
    occupied={n for _,_,size,offset in fields for n in range(offset,offset+size)}
    for at in range(0x40,456):
        if len(fields)==80:break
        if at not in occupied:fields.append((f'Raw {at}','u8',1,at))
    fields.sort(key=lambda f:f[3]);start=80*32;body=bytearray(start+2*456);pool=bytearray();strings={};pointers={};labels=[]
    def string(at,value):
        if value not in strings:strings[value]=len(pool);pool.extend(value.encode()+b'\0')
        pointers[at]=('string',strings[value])
    for i,(name,kind,size,off) in enumerate(fields):
        string(i*32,name);string(i*32+8,kind);struct.pack_into('<II',body,i*32+24,size,off)
    shared=len(body);body.extend(b'\0'*32);string(shared,'SID_SYNTHETIC_A');string(shared+16,'SID_SYNTHETIC_B')
    struct.pack_into('<Q',body,shared+8,0x11223344)
    for i,key in enumerate(('IID_SYNTHETIC_A','IID_SYNTHETIC_A|')):
        at=start+i*456;string(at+8,key);labels.append((at,strings[key]));struct.pack_into('<HHHH',body,at+16,i,1,0,30+i)
        string(at+0x20,'MIID_SYNTHETIC_'+str(i));string(at+0x30,'MIID_HELP_'+str(i))
        struct.pack_into('<HHIQ',body,at+0x38,0,8,0,0)
        struct.pack_into('<HHIQ',body,at+0x98,2,16,7,shared);pointers[at+0xa0]=('data',shared)
        string(at+0xb8,'SID_SYNTHETIC_A');string(at+0x108,'IID_SYNTHETIC_A|');string(at+0x120,'IID_SYNTHETIC_A')
        struct.pack_into('<i',body,at+0x118,-1);struct.pack_into('<I',body,at+0x4c,100);struct.pack_into('<h',body,at+0x6c,-7)
    opaque=len(body);body.extend(b'opaque item aux group!!!\0'*2)
    meta=len(body);body.extend(b'\0'*32);struct.pack_into('<Q',body,meta,0x220251201)
    string(meta+8,'アイテム');struct.pack_into('<II',body,meta+16,456,80);pointers[meta+24]=('data',0)
    order=sorted(pointers);base=len(body)+len(order)*8+len(labels)*8
    for at,(kind,target) in pointers.items():struct.pack_into('<Q',body,at,base+target if kind=='string' else target)
    header=bytearray(32);struct.pack_into('<4I',header,0,32+base+len(pool),len(body),len(order),len(labels))
    return bytes(header+body+struct.pack(f'<{len(order)}Q',*order)+b''.join(struct.pack('<II',*label) for label in labels)+pool)


def reliance_fixture():
    """Invented seven-section file, directional matrix and unnamed/duplicate rows."""
    from reliance_data import SECTIONS
    configs={
      'matrix':[(0x20,'u8[]',16)],
      'special':[(0x20,'data',16),(0x30,'data',16)]+[(o,'s16',2) for o in range(0x40,0x52,2)]+[(0x52,'u8',1)],
      'talks':[(0x20,'data',16),(0x30,'data',16),(0x48,'data[]',16),(0x58,'string[]',16),(0x80,'string',8)],
      'scout':[(0x20,'u8',1),(0x21,'u8',1),(0x22,'u16',2),(0x28,'string[]',16),(0x38,'string[]',16),(0x50,'data',16),(0x60,'u16',2)],
      'assist':[(0x20,'u8[]',16)],
      'voices':[(0x20,'data',16),(0x30,'data',16),(0x40,'string',8),(0x48,'string[]',16),(0x58,'string',8)],
      'drinks':[(0x20,'data[]',16)]}
    body=bytearray();pool=bytearray();strings={};pointers={};labels=[];descriptors=[]
    def string(at,value):
        if not value:return
        if value not in strings:strings[value]=len(pool);pool.extend(value.encode()+b'\0')
        pointers[at]=('string',strings[value])
    shared={}
    def array(at,kind,values):
        width=1 if kind=='u8[]' else 16 if kind=='data[]' else 8
        signature=(kind,tuple(values))
        if signature not in shared:
            body.extend(b'\0'*(-len(body)%8));ptr=len(body);body.extend(b'\0'*(width*len(values)))
            for i,value in enumerate(values):
                if kind=='u8[]':body[ptr+i]=value
                else:string(ptr+i*width,value)
            shared[signature]=ptr
        ptr=shared[signature];struct.pack_into('<HHIQ',body,at,len(values),width,19,ptr)
        if values:pointers[at+8]=('data',ptr)
    for key,(_,name,stride,count) in SECTIONS.items():
        fields=list(configs[key]);occupied={i for off,_,size in fields for i in range(off,off+size)}
        for at in range(32,stride):
            if len(fields)==count:break
            if at not in occupied:fields.append((at,'u8',1))
        fields.sort();body.extend(b'\0'*(-len(body)%8));schema=len(body);body.extend(b'\0'*(count*32))
        for i,(off,kind,size) in enumerate(fields):
            string(schema+i*32,f'Field{off}');string(schema+i*32+8,kind);struct.pack_into('<II',body,schema+i*32+24,size,off)
        n=4 if key=='scout' else 3 if key=='drinks' else 1 if key=='assist' else 2
        start=len(body);body.extend(b'\0'*(n*stride))
        for i in range(n):
            at=start+i*stride;label=(f'RID_SYNTH_{i}' if key=='matrix' else 'Talk_duplicate' if key=='talks' else f'PID_SYNTH_{i//2}' if key=='scout' and i%2==0 else ('好物','通常','嫌い')[i] if key=='drinks' else '')
            if label:string(at+8,label);labels.append((at,strings[label]))
            struct.pack_into('<HHHH',body,at+16,i,1,0,60+i)
            for off,kind,_ in fields:
                if kind in ('string[]','data[]','u8[]'):
                    values=([0,1] if i==0 else [4,0]) if key=='matrix' else [0,1,2,3,4] if key=='assist' else ['IID_SYNTH_ITEM'] if key=='drinks' else ['PID_SYNTH_0'] if kind=='data[]' else ['shared_flag']
                    array(at+off,kind,values)
                elif kind=='data':string(at+off,'IID_SYNTH_ITEM' if key=='scout' else f'PID_SYNTH_{0 if off==0x20 else 1}')
                elif kind=='string':string(at+off,'native_voice' if key=='voices' else 'flag')
                elif kind=='s16':struct.pack_into('<h',body,at+off,-3)
            if key=='scout':body[at+0x20]=i%2+1;body[at+0x21]=3
        descriptors.append((name,stride,count,schema))
    body.extend(b'OPAQUE_RELIANCE_SENTINEL!');body.extend(b'\0'*(-len(body)%8))
    for name,stride,count,schema in descriptors:
        at=len(body);body.extend(b'\0'*32);struct.pack_into('<Q',body,at,0x120251201)
        string(at+8,name);struct.pack_into('<II',body,at+16,stride,count);pointers[at+24]=('data',schema)
    order=sorted(pointers);base=len(body)+len(order)*8+len(labels)*8
    for at,(kind,target) in pointers.items():struct.pack_into('<Q',body,at,base+target if kind=='string' else target)
    header=bytearray(32);struct.pack_into('<4I',header,0,32+base+len(pool),len(body),len(order),len(labels))
    return bytes(header+body+struct.pack(f'<{len(order)}Q',*order)+b''.join(struct.pack('<II',*entry) for entry in labels)+pool)


def grouped_fixture(groups):
    """Invented flat sections with numeric/reference arrays and opaque headers."""
    body=bytearray();pool=bytearray();strings={};pointers={};labels=[];pending=[]
    def string(at,value):
        if value not in strings:strings[value]=len(pool);pool.extend(value.encode('utf8')+b'\0')
        pointers[at]=('string',strings[value])
    for spec in groups:
        group,stride,fields,rows=spec[:4];container=spec[4] if len(spec)>4 else 1
        while len(body)%8:body.append(0)
        schema=len(body);start=schema+len(fields)*32;body.extend(b'\0'*(len(fields)*32+len(rows)*(48 if container==2 else stride)))
        for i,(name,kind,size,off) in enumerate(fields):
            string(schema+i*32,name);string(schema+i*32+8,kind);struct.pack_into('<II',body,schema+i*32+24,size,off)
        def leaf(at,index,label,values):
            struct.pack_into('<HHII',body,at+16,index,1,0xDEAD,0xBEEF)
            if label:string(at+8,label);labels.append((at,strings[label]))
            for name,kind,size,off in fields:pending.append((at+off,kind,values.get(off)))
        for i,(label,values) in enumerate(rows):
            at=start+i*(48 if container==2 else stride)
            if container==1:leaf(at,i,label,values)
            else:
                struct.pack_into('<HHII',body,at+16,i,len(values),0xBABA,0xCAFE)
                if label:string(at+8,label);labels.append((at,strings[label]))
                pointer=len(body) if values else 0;body.extend(b'\0'*(stride*len(values)))
                if values:pointers[at+32]=('data',pointer)
                for j,(key,value) in enumerate(values):leaf(pointer+j*stride,j,key,value)
        meta=len(body);body.extend(b'\0'*32);struct.pack_into('<Q',body,meta,(container<<32)|0x20251201)
        string(meta+8,group);struct.pack_into('<II',body,meta+16,stride,len(fields));pointers[meta+24]=('data',schema)
        if len(spec)>5 and spec[5]:labels.append((meta,strings[group]))
    formats={'u8':'B','s8':'b','b8':'B','u16':'H','b16':'H','s16':'h','s32':'i','u32':'I','b32':'I','int':'i','bool':'B','f32':'f'}
    def assign(at,kind,value):
        if kind in ('string','data'):string(at,value or '')
        elif kind in ('string[]','data[]','string[,]','data[,]','s16[]','u8[]'):
            values=value or [];width={'string[]':8,'data[]':16,'string[,]':16,'data[,]':16,'s16[]':2,'u8[]':1}[kind]
            while len(body)%8:body.append(0)
            pointer=len(body) if values else 0;body.extend(b'\0'*(width*len(values)))
            for i,v in enumerate(values):
                if kind in ('s16[]','u8[]'):struct.pack_into('<'+('h' if kind=='s16[]' else 'B'),body,pointer+i*width,v)
                elif kind in ('string[,]','data[,]'):assign(pointer+i*width,'data[]' if kind=='data[,]' else 'string[]',v)
                else:string(pointer+i*width,v)
            struct.pack_into('<HHIQ',body,at,len(values),width,0xCAFE,pointer)
            if values:pointers[at+8]=('data',pointer)
        else:struct.pack_into('<'+formats[kind],body,at,value or 0)
    for args in pending:assign(*args)
    while len(body)%8:body.append(0)
    order=sorted(pointers);base=len(body)+len(order)*8+len(labels)*8
    for at,(kind,target) in pointers.items():struct.pack_into('<Q',body,at,base+target if kind=='string' else target)
    header=bytearray(32);struct.pack_into('<4I',header,0,32+base+len(pool),len(body),len(order),len(labels))
    return bytes(header+body+struct.pack(f'<{len(order)}Q',*order)+b''.join(struct.pack('<II',*label) for label in labels)+pool)


def profile_fixture():
    """All five supported profile layouts, using invented records and text."""
    from profile_data import SECTIONS
    fields=[('Conditions','string[]',16,0x20),('Group','data',16,0x30),('Year','u16',2,0x40),('Month','u8',1,0x42),('Day','u8',1,0x43),('Height','u16',2,0x44)]
    fields += [(name,'string',8,off) for name,off in [('Alias',0x48),('Title',0x50),('Scout',0x58),('Travel',0x60),('Hobby',0x88),('Like',0x90),('Dislike',0x98),('Code',0xa0)]]
    fields += [('Years','s16[]',16,0x68),('History','string[]',16,0x78)]
    fields += [(f'Rating_{off}','u8',1,off) for off in range(0xa8,0xbd)]
    fields += [('Theater','u8[]',16,0xc0)]
    fields += [(f'List_{off}','data[]',16,off) for off in (0xd0,0xe0,0xf0,0x100,0x110,0x120,0x138)]
    fields += [('Speech','u8',1,0x130)]
    groups=[(SECTIONS['profiles'][1],328,sorted(fields,key=lambda f:f[3]),[
        ('PRF_ALPHA',{0x20:['active'],0x40:1426,0x44:192,0x68:[1426,1449],0x78:['MID_One','MID_Two'],0xf0:['IID_SYNTHETIC'],0x138:['PRF_BETA']}),
        ('PRF_BETA',{0x30:'PRF_ALPHA',0x68:[1400],0x78:['MID_Other']})])]
    groups.append((SECTIONS['affiliations'][1],88,[('Clan','string',8,0x20),('Route','u8',1,0x28),('Icon','string',8,0x30),('Conditions','string[,]',16,0x38),('Next','data',16,0x48)],[('BID_ALPHA',{0x20:'MID_Clan_ALPHA',0x38:[['route','event'],[]],0x48:'BID_BETA'}),('BID_BETA',{0x48:'BID_ALPHA'})]))
    groups.append((SECTIONS['expressions'][1],64,[('Face3D','string',8,0x20),('Face2D','string',8,0x28),('Motion','string',8,0x30),('Mouth','u8',1,0x38),('Shape','u8',1,0x39),('Sweat','b32',4,0x3c)],[('normal',{0x20:'FaceNormal'})]))
    groups.append((SECTIONS['limits'][1],48,[('Conditions','string[]',16,0x20)],[('MID_Conversation',{0x20:['restrict']})]))
    groups.append((SECTIONS['order'][1],56,[(name,'s16',2,0x20+i*2) for i,name in enumerate(['JPja','USen','EUfr','EUes','EUde','EUit','CNzh','TWzh','KRko'])],[('MPID_ALPHA',{0x22:10})]))
    return grouped_fixture(groups)


def facility_fixture(source='Facility.bin'):
    """Invented data in all facility/reward layouts, including grouped empty lists."""
    from facility_data import SECTIONS,FACILITY_KEYS,REWARD_KEYS
    from facility_layouts import LAYOUTS
    keys=FACILITY_KEYS if source=='Facility.bin' else REWARD_KEYS if source=='Reward.bin' else ('notices',)
    groups=[]
    for key in keys:
        _,name,stride,_,container=SECTIONS[key]
        fields=[('Field_'+hex(off),kind,size,off) for kind,size,off in LAYOUTS[key]]
        if key=='cooking':values={0x20:'MID_FOOD_ALPHA',0x34:300}
        elif key=='baths':values={0x48:['SID_ALPHA','SID_BETA'],0x58:[1,3]}
        elif key=='training':values={0x68:'IID_SYNTHETIC',0x78:['JID_SYNTHETIC_0']}
        elif key=='questions':values={0x20:'PID_SYNTHETIC_0',0x40:'ALPHA'}
        elif key=='notices':values={0x28:['notice_flag'],0xa8:['IID_SYNTHETIC']}
        elif key=='exspots':values={0x30:'ALPHA'}
        else:values={}
        rows=[('COOK_ALPHA' if key=='cooking' else 'PCHA_ALPHA' if key=='answers' else key+'_ALPHA',values),('',{})]
        if container==2:rows=[(key+'_GROUP_A',[('',{0x20:'STATE_A'}),('',{0x20:'STATE_B'})]),(key+'_EMPTY',[]),(key+'_GROUP_B',[('',{0x20:'STATE_C'})])]
        groups.append((name,stride,fields,rows,container))
    return grouped_fixture(groups)


def merge_fixture_tables(parts):
    """Combine invented tables, rebasing their data/string/label pointers."""
    from fw_editor import Binary
    bodies=bytearray();pool=bytearray();pointers={};labels=[]
    for raw in parts:
        b=Binary(raw)
        while len(bodies)%8:bodies.append(0)
        data_base=len(bodies);pool_base=len(pool)
        bodies.extend(raw[32:32+b.size]);pool.extend(raw[32+b.pool:])
        for location in b.pointers:
            target=struct.unpack_from('<Q',raw,32+location)[0]
            pointers[data_base+location]=('string',pool_base+target-b.pool) if target>=b.pool else ('data',data_base+target)
        label_start=32+b.size+len(b.pointers)*8
        for index in range(len(b.label_bytes)//8):
            at,text=struct.unpack_from('<II',raw,label_start+index*8);labels.append((data_base+at,pool_base+text))
    while len(bodies)%8:bodies.append(0)
    ordered=sorted(pointers);base=len(bodies)+len(ordered)*8+len(labels)*8
    for at,(kind,value) in pointers.items():struct.pack_into('<Q',bodies,at,base+value if kind=='string' else value)
    header=bytearray(32);struct.pack_into('<4I',header,0,32+base+len(pool),len(bodies),len(ordered),len(labels))
    return bytes(header+bodies+struct.pack(f'<{len(ordered)}Q',*ordered)+b''.join(struct.pack('<II',*label) for label in labels)+pool)


def shop_fixture(empty_shops=False):
    """Main item slots and invented shops/loot/value tiers in one file."""
    from shop_data import SECTIONS,EXPECTED
    groups=[]
    for key,(title,native,stride,count,container) in SECTIONS.items():
        fields=[('Field_'+hex(offset),kind,size,offset) for offset,(kind,size) in EXPECTED[key].items()]
        if key=='shops':
            rows=[('SHOP_ALPHA',[('',{0x20:'MID_Shop_ALPHA',0x28:'IID_SYNTHETIC_A',0x38:['available'],0x48:['IID_SYNTHETIC_A|'],0x58:[3],0x68:150,0x6a:-5,0x6b:1}),('',{0x28:'IID_SYNTHETIC_A|'})]),('SHOP_EMPTY',[]),('SHOP_BETA',[('',{0x28:'IID_SYNTHETIC_A'})])]
            if empty_shops:rows=[(name,[]) for name,_ in rows]
        elif key=='loot':rows=[('LOT_ALPHA',[('',{0x20:'IID_SYNTHETIC_A',0x30:10}),('',{0x20:'IID_SYNTHETIC_A|',0x30:20,0x38:['conditional']})]),('LOT_BETA',[('',{0x20:'IID_SYNTHETIC_A'})])]
        else:rows=[('TIER_ALPHA',{0x20:100,0x22:50}),('TIER_BETA',{0x20:200,0x22:100})]
        groups.append((native,stride,fields,rows,container))
    return merge_fixture_tables([item_fixture(),grouped_fixture(groups)])


def deployment_fixture():
    from deployment_data import EXPECTED
    fields=[('Synthetic_'+str(off),kind,size,off) for off,(kind,size) in sorted(EXPECTED.items())]
    return grouped_fixture([('配置',328,fields,[('Player',[(None,{0x20:'PID_SYNTHETIC_0',0x34:-1,0x68:'IID_SYNTHETIC_A|'})]),
        ('Empty',[]),('Enemy',[(None,{0x20:'PID_SYNTHETIC_1',0x3b:7,0x68:'IID_SYNTHETIC_A|'}),(None,{0x20:'PID_SYNTHETIC_0'})])],2,True)])


def legion_fixture():
    from legion_data import EXPECTED
    fields=[('Legion_'+str(off),kind,size,off) for off,(kind,size) in sorted(EXPECTED.items())]
    return grouped_fixture([('軍団兵',192,fields,[('LID_無し',{0x20:'MLID_SYNTHETIC_NONE'}),
        ('LID_SYNTHETIC',{0x20:'MLID_SYNTHETIC',0x28:'MLID_H_SYNTHETIC',0x30:1,0x31:6,0x38:'SID_SYNTHETIC',0x48:['IID_SYNTHETIC_A|'],0x58:['SID_EXTRA'],0xa0:['AID_ALPHA','!AID_BETA'],0xb0:'VID_SYNTHETIC'})])])


def expanded_fixture(filename):
    from expanded_data import SECTIONS,EXPECTED,GROWTH_KEYS,PERSON_KEYS
    keys=PERSON_KEYS if filename=='Person.bin' else GROWTH_KEYS if filename=='Growth.bin' else ('part2_items',)
    parts=[person_fixture()] if filename=='Person.bin' else [growth_fixture()] if filename=='Growth.bin' else []
    groups=[]
    for key in keys:
        title,native,stride,count,container=SECTIONS[key]
        fields=[('Expanded_'+str(off),kind,size,off) for off,(kind,size) in sorted(EXPECTED[key].items())]
        values={}
        if key=='exp_calculation':values={0x20:'EID_SYNTHETIC_CURVE'}
        elif key=='auto_class':values={0x20:'JID_SYNTHETIC_0',0x40:'PID_SYNTHETIC_1'}
        elif key in ('auto_items','auto_legions'):values={off:('LID_SYNTHETIC' if key=='auto_legions' else 'IID_SYNTHETIC_A|') for off in range(0x20,0x80,16)}
        elif key in ('hero_items','auto_gear'):values={0x20:'PID_SYNTHETIC_1',0x30:['IID_SYNTHETIC_A|']}
        elif key=='part2_items':values={0x28:[1,255],0x38:['IID_SYNTHETIC_A|','IID_SECOND'],0x48:[1]}
        elif key=='part2_legions':values={0x28:['LID_SYNTHETIC']}
        elif key=='difficulty':values={0x20:['SID_SYNTHETIC'],0x30:['IID_SYNTHETIC_A|'],0x40:[['SID_SYNTHETIC'],[],['SID_OTHER']]}
        if container==2:
            label={'exp_curve':'EID_SYNTHETIC_CURVE','exp_modifiers':'EID_SYNTHETIC_MODIFIERS','auto_exp':'AGME_SYNTHETIC'}[key]
            rows=[(label,[(None,values),(None,values)]),(label+'_EMPTY',[])]
        else:rows=[(('DID_' if key=='difficulty' else 'SYNTHETIC_')+key,values)]
        groups.append((native,stride,fields,rows,container))
    return merge_fixture_tables(parts+[grouped_fixture(groups)])
