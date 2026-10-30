from pathlib import Path
import hashlib
import json
import zlib

root = Path('/app/repo.git')
dest = root / 'recovery/verified-objects'
report = []
for name, error in json.loads((root / 'recovery/salvage-errors.json').read_text()):
    if not name.startswith('objects/'):
        continue
    path = root / name
    expected = path.parent.name + path.name
    damaged = path.read_bytes()
    repaired = None
    for pos in range(len(damaged)):
        for value in range(256):
            if value == damaged[pos]:
                continue
            candidate = damaged[:pos] + bytes([value]) + damaged[pos+1:]
            try:
                raw = zlib.decompress(candidate)
            except zlib.error:
                continue
            if hashlib.sha1(raw).hexdigest() == expected:
                repaired = candidate
                report.append(dict(oid=expected, byte_offset=pos, before=damaged[pos], after=value))
                break
        if repaired is not None:
            break
    if repaired is None:
        raise RuntimeError(f'No single-byte repair for {expected}')
    output = dest / expected[:2] / expected[2:]
    output.parent.mkdir(exist_ok=True)
    output.write_bytes(repaired)
    print('Repaired', report[-1])
(root / 'recovery/loose-repairs.json').write_text(json.dumps(report, indent=2))
