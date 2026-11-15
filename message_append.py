"""Append own UTF-8 item messages without changing existing message indexes."""
import struct
from fw_editor import DataError, decompress
from script_data import compress


def sections(raw):
    if len(raw)<32 or raw[:10]!=b'MsgStdBn\xff\xfe' or raw[12:14]!=b'\0\3':
        raise DataError('Buyable mounts needs a supported little-endian UTF-8 Item message bank.')
    if struct.unpack_from('<I',raw,18)[0]!=len(raw):raise DataError('Message file size does not match its header.')
    result=[];at=32;seen=set()
    for _ in range(struct.unpack_from('<H',raw,14)[0]):
        if at+16>len(raw):raise DataError('Truncated message section header.')
        size=struct.unpack_from('<I',raw,at+4)[0];end=at+16+size
        if end>len(raw):raise DataError('Truncated message section.')
        name=bytes(raw[at:at+4])
        if name in seen:raise DataError('Duplicate message section.')
        seen.add(name);result.append((name,raw[at:at+16],raw[at+16:end],raw[end:(end+15)&~15]))
        at=(end+15)&~15
    if at!=len(raw):raise DataError('Unexpected message trailing data.')
    return result


def labels(payload,count):
    if len(payload)<4:raise DataError('Missing message label buckets.')
    buckets=struct.unpack_from('<I',payload)[0]
    if not 1<=buckets<=4096 or 4+buckets*8>len(payload):raise DataError('Invalid message label buckets.')
    result=[[] for _ in range(buckets)];seen=set()
    for i in range(buckets):
        amount,at=struct.unpack_from('<II',payload,4+i*8)
        for _ in range(amount):
            if at>=len(payload):raise DataError('Invalid message label.')
            width=payload[at];end=at+1+width
            if end+4>len(payload):raise DataError('Truncated message label.')
            name=payload[at+1:end];index=struct.unpack_from('<I',payload,end)[0]
            if index>=count or name in seen:raise DataError('Invalid or duplicate message label.')
            name.decode('utf8');seen.add(name);result[i].append((name,index));at=end+4
    return result


def append_messages(source, additions):
    """additions: (new label, own text, existing metadata-template label)."""
    raw=decompress(source);parts=sections(raw);data={n:v for n,h,v,p in parts}
    if set(data)!={b'LBL1',b'ATO1',b'ATR1',b'TSY1',b'TXT2',b'AOCM'}:raise DataError('Unsupported Item message sections.')
    txt=data[b'TXT2']
    if len(txt)<4:raise DataError('Missing message text count.')
    count=struct.unpack_from('<I',txt)[0];amount=len(additions)
    if not amount:return source
    if not count or count+amount>65535 or 4+count*4>len(txt):raise DataError('Unsupported message count.')
    offsets=list(struct.unpack_from(f'<{count}I',txt,4));start=4+count*4
    if offsets[0]!=start or offsets!=sorted(offsets) or offsets[-1]>=len(txt):raise DataError('Unsupported message text offsets.')
    buckets=labels(data[b'LBL1'],count);by_name={n.decode('utf8'):i for bucket in buckets for n,i in bucket}
    templates=[];new_text=[]
    for name,text,template in additions:
        encoded=name.encode('ascii')
        if not encoded or len(encoded)>255 or name in by_name:raise DataError('Generated message label already exists or is invalid.')
        if not isinstance(text,str) or any(ord(c)<32 for c in text):raise DataError('Generated text must be plain single-line text.')
        if template not in by_name:raise DataError('Missing message metadata template: '+template)
        index=count+len(new_text);templates.append(by_name[template]);by_name[name]=index;new_text.append(text.encode('utf8')+b'\0')
        hash_value=0
        for char in encoded:hash_value=(hash_value*0x492+char)&0xffffffff
        buckets[hash_value%len(buckets)].append((encoded,index))
    new_labels=bytearray(struct.pack('<I',len(buckets))+b'\0'*(8*len(buckets)))
    for i,bucket in enumerate(buckets):
        struct.pack_into('<II',new_labels,4+i*8,len(bucket),len(new_labels))
        for name,index in bucket:new_labels.extend(bytes([len(name)])+name+struct.pack('<I',index))
    body=txt[start:];new_offsets=[v+4*amount for v in offsets];at=4+(count+amount)*4+len(body)
    for text in new_text:new_offsets.append(at);at+=len(text)
    data[b'LBL1']=bytes(new_labels)
    data[b'TXT2']=struct.pack('<I',count+amount)+struct.pack(f'<{len(new_offsets)}I',*new_offsets)+body+b''.join(new_text)
    if len(data[b'TSY1'])!=count*4:raise DataError('Unsupported message styles.')
    data[b'TSY1']+=b''.join(data[b'TSY1'][i*4:i*4+4] for i in templates)
    if len(data[b'AOCM'])!=count+2 or struct.unpack_from('<H',data[b'AOCM'])[0]!=count:raise DataError('Unsupported message metadata.')
    aocm=data[b'AOCM'];data[b'AOCM']=struct.pack('<H',count+amount)+aocm[2:]+bytes(aocm[2+i] for i in templates)
    atr=data[b'ATR1'];ato=data[b'ATO1']
    if len(atr)<8 or len(ato)%4:raise DataError('Invalid message attributes.')
    n,stride=struct.unpack_from('<II',atr);end=8+count*stride
    # This schema has byte flags and string offsets. Infer each field width from
    # the next defined ATO offset, and require every four-byte value to be a valid
    # string pointer. Refuse other schemas instead of guessing their relocations.
    fields=sorted(v for v in struct.unpack(f'<{len(ato)//4}I',ato) if v!=0xffffffff)
    if n!=count or stride!=74 or fields!=[0,4,8,12,16,20,24,28,32,36,40,44,45,49,53,54,55,59,60,61,65,69,70] or end>len(atr):
        raise DataError('Unsupported Item message attribute schema.')
    pointers=[off for off,next_off in zip(fields,fields[1:]+[stride]) if next_off-off==4]
    records=bytearray(atr[8:end])+b''.join(atr[8+i*stride:8+(i+1)*stride] for i in templates)
    for i in range(count+amount):
        for off in pointers:
            at=i*stride+off;pointer=struct.unpack_from('<I',records,at)[0]
            if not end<=pointer<len(atr) or atr.find(b'\0',pointer)<0:raise DataError('Unsupported message attribute pointer.')
            struct.pack_into('<I',records,at,pointer+amount*stride)
    data[b'ATR1']=struct.pack('<II',count+amount,stride)+records+atr[end:]
    result=bytearray(raw[:32])
    for name,header,old,padding in parts:
        value=data[name];head=bytearray(header);struct.pack_into('<I',head,4,len(value));result.extend(head+value)
        width=-len(result)%16;result.extend(padding if len(padding)==width else b'\xab'*width)
    struct.pack_into('<I',result,18,len(result));sections(result)
    return bytes(result) if source.startswith(b'MsgStdBn') else compress(bytes(result))
