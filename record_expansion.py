"""Append primary records without moving existing record indexes.

Preserves all registered relocation locations/targets and indexed labels.
"""
import struct


def expanded_raw(doc,DataError,additions):
    source=doc.raw[32:32+doc.size];pool=bytearray(doc.raw[32+doc.pool:])
    at=doc._source_records[-1].offset-32+doc.stride
    template=doc._source_records[0].offset-32;delta=doc.stride*len(additions)
    body=bytearray(source[:at]);names={};starts={}
    tag=max(struct.unpack_from('<H',doc.raw,r.offset+22)[0] for r in doc._source_records)+1
    if tag+len(additions)>65536:raise DataError('New record-header tags exceed the 16-bit format limit.')
    for i,key in enumerate(additions):
        start=len(body);starts[key]=start;body.extend(source[template:template+doc.stride])
        struct.pack_into('<HH',body,start+16,len(doc._source_records)+i,1)
        struct.pack_into('<H',body,start+22,tag+i)
        names[key]=len(pool);pool.extend(key.encode('utf8')+b'\0')
    body.extend(source[at:])
    def moved(value):return value+delta if value>=at else value
    def target(slot):
        value=struct.unpack_from('<Q',source,slot)[0]
        return ('string',value-doc.pool) if value>=doc.pool else ('data',moved(value))
    pointers={moved(slot):target(slot) for slot in doc.pointers}
    slots=[slot for slot in doc.pointers if template<=slot<template+doc.stride]
    for key,start in starts.items():
        for slot in slots:pointers[start+slot-template]=target(slot)
        pointers[start+8]=('string',names[key])
    order=[moved(slot) for slot in doc.pointers];order.extend(sorted(set(pointers)-set(order)))
    additions=[(starts[key],names[key]) for key in additions];labels=[];inserted=False
    for offset,name in struct.iter_unpack('<II',doc.label_bytes):
        if not inserted and offset>=at:labels.extend(additions);inserted=True
        labels.append((moved(offset),name))
    if not inserted:labels.extend(additions)
    new_pool=len(body)+8*len(order)+8*len(labels);total=32+new_pool+len(pool)
    if total>=1<<32:raise DataError('Expanded record file exceeds the format size limit.')
    for slot,(kind,value) in pointers.items():struct.pack_into('<Q',body,slot,value+new_pool if kind=='string' else value)
    header=bytearray(doc.raw[:32]);struct.pack_into('<4I',header,0,total,len(body),len(order),len(labels))
    return bytes(header+body+struct.pack('<'+str(len(order))+'Q',*order)+b''.join(struct.pack('<II',*v) for v in labels)+pool)
