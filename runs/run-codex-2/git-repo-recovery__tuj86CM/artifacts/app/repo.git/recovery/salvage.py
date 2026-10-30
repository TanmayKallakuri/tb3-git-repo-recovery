#!/usr/bin/env python3
"""Validate and recover original Git objects from surviving indexed packs."""
from pathlib import Path
import collections
import hashlib
import json
import struct
import zlib

ROOT = Path('/app/repo.git')
OUT = ROOT / 'recovery/verified'
OUT.mkdir(exist_ok=True)
TYPES = {1: 'commit', 2: 'tree', 3: 'blob', 4: 'tag'}
objects = {}
provenance = collections.defaultdict(list)

def register(oid, typ, data, source):
    raw = typ.encode() + b' ' + str(len(data)).encode() + b'\0' + data
    assert hashlib.sha1(raw).hexdigest() == oid, (oid, source, 'hash mismatch')
    if oid in objects:
        assert objects[oid] == (typ, data)
    else:
        objects[oid] = (typ, data)
        (OUT / oid).write_bytes(raw)
    provenance[oid].append(source)

def read_index(path):
    b = path.read_bytes()
    assert b[:8] == b'\xfftOc\0\0\0\2'
    assert hashlib.sha1(b[:-20]).digest() == b[-20:]
    n = struct.unpack_from('>I', b, 8+255*4)[0]
    oids = [b[1032+i*20:1032+(i+1)*20].hex() for i in range(n)]
    crcs = struct.unpack_from('>'+str(n)+'I', b, 1032+n*20)
    offsets = struct.unpack_from('>'+str(n)+'I', b, 1032+n*24)
    assert all(o < 0x80000000 for o in offsets)
    return sorted(zip(offsets, oids, crcs))

def varint(b, pos):
    value, shift = 0, 0
    while True:
        c = b[pos]; pos += 1
        value |= (c & 127) << shift
        if not c & 128: return value, pos
        shift += 7

def apply_delta(base, delta):
    base_size, pos = varint(delta, 0)
    result_size, pos = varint(delta, pos)
    assert base_size == len(base)
    out = bytearray()
    while pos < len(delta):
        c = delta[pos]; pos += 1
        if c & 128:
            offset = size = 0
            for bit in range(4):
                if c & (1 << bit):
                    offset |= delta[pos] << (8*bit); pos += 1
            for bit in range(3):
                if c & (1 << (4+bit)):
                    size |= delta[pos] << (8*bit); pos += 1
            if not size: size = 65536
            assert offset + size <= len(base)
            out.extend(base[offset:offset+size])
        else:
            assert c and pos+c <= len(delta)
            out.extend(delta[pos:pos+c]); pos += c
    assert len(out) == result_size
    return bytes(out)

bad_loose = []
for path in sorted((ROOT/'objects').glob('??/'+'?'*38)):
    oid = path.parent.name + path.name
    try:
        raw = zlib.decompress(path.read_bytes())
        header, data = raw.split(b'\0', 1)
        typ, size = header.decode().split(' ')
        assert len(data) == int(size)
        register(oid, typ, data, str(path.relative_to(ROOT)))
    except Exception as e:
        bad_loose.append((oid, str(e)))

pending = []
bad_packed = []
all_oids = set()
for name, idx in [
    ('pack-dc1a3d5e56cdb2c83174659a7deaaca10d01e520', ROOT/'recovery/older-pack.idx'),
    ('pack-0edbe236157d7f40502eaa2e054bc68160f770ab', ROOT/'objects/pack/pack-0edbe236157d7f40502eaa2e054bc68160f770ab.idx')
]:
    b = (ROOT/'objects/pack'/f'{name}.pack').read_bytes()
    entries = read_index(idx)
    by_offset = {offset: oid for offset, oid, crc in entries}
    assert struct.unpack_from('>I', b, 8)[0] == len(entries)
    for i, (offset, oid, crc) in enumerate(entries):
        all_oids.add(oid)
        end = entries[i+1][0] if i+1 < len(entries) else len(b)-20
        pos = offset
        c = b[pos]; pos += 1
        typ, size, shift = (c >> 4) & 7, c & 15, 4
        while c & 128:
            c = b[pos]; pos += 1
            size |= (c & 127) << shift; shift += 7
        base = None
        if typ == 6:
            c = b[pos]; pos += 1
            distance = c & 127
            while c & 128:
                c = b[pos]; pos += 1
                distance = ((distance+1) << 7) | (c & 127)
            base = by_offset[offset-distance]
        elif typ == 7:
            base = b[pos:pos+20].hex(); pos += 20
        source = f'{name}:{offset}'
        try:
            assert zlib.crc32(b[offset:end]) == crc, 'CRC mismatch'
            dec = zlib.decompressobj()
            data = dec.decompress(b[pos:end]) + dec.flush()
            assert dec.eof and not dec.unused_data and len(data) == size
            if base:
                pending.append((oid, base, data, source))
            else:
                register(oid, TYPES[typ], data, source)
        except Exception as e:
            bad_packed.append(dict(oid=oid, base=base, offset=offset, end=end,
                                   compressed_start=pos, type=typ, size=size,
                                   source=source, error=str(e)))

while pending:
    remainder = []
    for oid, base, delta, source in pending:
        if base in objects:
            typ, data = objects[base]
            register(oid, typ, apply_delta(data, delta), source)
        else:
            remainder.append((oid, base, delta, source))
    if len(remainder) == len(pending): break
    pending = remainder

report = dict(objects=len(objects), types=dict(collections.Counter(t for t,d in objects.values())),
              bad_loose=bad_loose, bad_packed=bad_packed,
              unresolved_deltas=[dict(oid=o, base=b, source=s) for o,b,d,s in pending],
              indexed_missing=sorted(all_oids-objects.keys()), provenance=provenance)
(ROOT/'recovery/salvage-report.json').write_text(json.dumps(report, indent=2)+'\n')
print('Verified:', len(objects), report['types'])
print('Corrupt loose:', len(bad_loose), 'Damaged packed entries:', len(bad_packed))
print('Unresolved delta entries:', len(pending), 'Indexed unrecovered:', len(report['indexed_missing']))
for oid in report['indexed_missing']: print('  missing',oid)
