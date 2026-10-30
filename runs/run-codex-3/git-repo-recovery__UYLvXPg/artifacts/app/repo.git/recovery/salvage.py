from pathlib import Path
import hashlib
import json
import struct
import zlib

ROOT = Path('/app/repo.git')
DEST = ROOT / 'recovery/verified-objects'
objects = {}
sources = {}
errors = []

def save(kind, data, expected=None, source=''):
    raw = kind.encode() + b' ' + str(len(data)).encode() + b'\0' + data
    oid = hashlib.sha1(raw).hexdigest()
    if expected is not None and oid != expected:
        raise ValueError(f'hash mismatch: {expected} != {oid}')
    objects[oid] = (kind, data)
    sources.setdefault(oid, []).append(source)
    path = DEST / oid[:2] / oid[2:]
    if not path.exists():
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_bytes(zlib.compress(raw))
    return oid

for base in [DEST, ROOT / 'objects']:
    for path in sorted(base.glob('??/*')):
        if len(path.name) != 38:
            continue
        oid = path.parent.name + path.name
        try:
            raw = zlib.decompress(path.read_bytes())
            header, data = raw.split(b'\0', 1)
            kind, size = header.decode().split()
            assert int(size) == len(data)
            save(kind, data, oid, str(path.relative_to(ROOT)))
        except Exception as exc:
            errors.append([str(path.relative_to(ROOT)), str(exc)])

def apply_delta(base, delta):
    pos = 0
    def varint():
        nonlocal pos
        value = shift = 0
        while True:
            c = delta[pos]; pos += 1
            value |= (c & 127) << shift
            if not c & 128:
                return value
            shift += 7
    base_size, result_size = varint(), varint()
    assert base_size == len(base)
    output = bytearray()
    while pos < len(delta):
        cmd = delta[pos]; pos += 1
        if cmd & 128:
            off = size = 0
            for j in range(4):
                if cmd & (1 << j):
                    off |= delta[pos] << (8*j); pos += 1
            for j in range(3):
                if cmd & (16 << j):
                    size |= delta[pos] << (8*j); pos += 1
            size = size or 65536
            assert off + size <= len(base)
            output.extend(base[off:off+size])
        else:
            assert cmd and pos + cmd <= len(delta)
            output.extend(delta[pos:pos+cmd]); pos += cmd
    assert len(output) == result_size
    return bytes(output)

pending = []
inventory = []
for pack in sorted((ROOT / 'objects/pack').glob('*.pack')):
    idx = pack.with_suffix('.idx').read_bytes()
    assert idx[:8] == b'\xfftOc\x00\x00\x00\x02'
    count = struct.unpack_from('>I', idx, 1028)[0]
    offsets = {}
    crcs = {}
    for i in range(count):
        oid = idx[1032+20*i:1052+20*i].hex()
        off = struct.unpack_from('>I', idx, 1032+24*count+4*i)[0]
        assert off < 2**31
        offsets[off] = oid
        crcs[off] = struct.unpack_from('>I', idx, 1032+20*count+4*i)[0]
    data = pack.read_bytes()
    ordered = sorted(offsets)
    for i, off in enumerate(ordered):
        oid = offsets[off]
        end = ordered[i+1] if i+1 < count else len(data)-20
        pos = off
        c = data[pos]; pos += 1
        kind = (c >> 4) & 7
        size = c & 15
        shift = 4
        while c & 128:
            c = data[pos]; pos += 1
            size |= (c & 127) << shift; shift += 7
        base = None
        if kind == 6:
            c = data[pos]; pos += 1
            distance = c & 127
            while c & 128:
                c = data[pos]; pos += 1
                distance = ((distance + 1) << 7) | (c & 127)
            base = offsets[off-distance]
        elif kind == 7:
            base = data[pos:pos+20].hex(); pos += 20
        crc_ok = zlib.crc32(data[off:end]) == crcs[off]
        item = dict(pack=pack.name, oid=oid, offset=off, kind=kind, size=size, base=base, crc_ok=crc_ok)
        inventory.append(item)
        try:
            inflater = zlib.decompressobj()
            inflated = inflater.decompress(data[pos:end])
            assert inflater.eof and not inflater.unused_data and len(inflated) == size
            assert crc_ok
            if kind in (6, 7):
                pending.append((oid, base, inflated, f'{pack.name}:{off}'))
            else:
                save({1:'commit',2:'tree',3:'blob',4:'tag'}[kind], inflated, oid, f'{pack.name}:{off}')
        except Exception as exc:
            errors.append([f'{pack.name}:{off}:{oid}', str(exc)])

while True:
    next_pending = []
    for oid, base, delta, source in pending:
        if base not in objects:
            next_pending.append((oid, base, delta, source))
        else:
            kind, data = objects[base]
            save(kind, apply_delta(data, delta), oid, source)
    if len(next_pending) == len(pending):
        break
    pending = next_pending

(ROOT / 'recovery/pack-inventory.json').write_text(json.dumps(inventory, indent=2))
(ROOT / 'recovery/salvage-errors.json').write_text(json.dumps(errors, indent=2))
(ROOT / 'recovery/object-sources.json').write_text(json.dumps(sources, indent=2))
missing = sorted({x['oid'] for x in inventory} - objects.keys())
(ROOT / 'recovery/missing-packed.json').write_text(json.dumps(missing, indent=2))
print(f'Verified objects: {len(objects)}; damaged entries: {len(errors)}; unresolved deltas: {len(pending)}; missing packed objects: {len(missing)}')
print('Missing packed:', *missing, sep='\n')
