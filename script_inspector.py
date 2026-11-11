"""Read-only ASF wrapper/import inspector. Does not decode or rewrite instructions."""
from dataclasses import dataclass
import re
import struct


@dataclass(frozen=True)
class ScriptInfo:
    payload_offset:int
    payload_size:int
    imports:tuple
    identifiers:tuple


def inspect(raw):
    if len(raw)<16 or raw[:4]!=b'ASF\0':raise ValueError('Not an ASF compiled script.')
    offset,size,count=struct.unpack_from('<III',raw,4)
    if offset<16 or offset+size!=len(raw) or 16+count*128>offset:raise ValueError('Unsupported ASF wrapper bounds.')
    imports=[]
    for i in range(count):
        slot=raw[16+i*128:16+(i+1)*128];end=slot.find(b'\0')
        if end<0:raise ValueError('Unterminated ASF import path.')
        imports.append(slot[:end].decode('utf8'))
    # Evidence only: ASCII identifiers can be adjacent to serialized marker bytes.
    # Do not present these runs as function declarations or executed calls.
    identifiers=tuple(dict.fromkeys(m.group().decode('ascii') for m in re.finditer(rb'[A-Za-z_][A-Za-z_0-9:.]{4,}',raw[offset:])))
    return ScriptInfo(offset,size,tuple(imports),identifiers)
