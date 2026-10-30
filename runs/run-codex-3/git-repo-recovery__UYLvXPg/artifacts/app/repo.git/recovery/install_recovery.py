from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import zlib

root = Path('/app/repo.git')
stage = root / 'recovery/verified-objects'
env = dict(os.environ, GIT_OBJECT_DIRECTORY=str(stage))

def git(*args, data=None):
    return subprocess.check_output(['git', *args], input=data, cwd=root, env=env)

existing = {ref: oid for oid, ref in (line.split() for line in git('show-ref').decode().splitlines())}
expected = dict(existing)
evidence = {}
for path in sorted((root / 'logs/refs/heads').rglob('*')):
    if not path.is_file():
        continue
    ref = str(path.relative_to(root / 'logs'))
    tip = path.read_text().splitlines()[-1].split()[1]
    assert tip != '0' * 40
    assert ref not in expected or expected[ref] == tip
    expected[ref] = tip
    evidence[ref] = str(path.relative_to(root)) + ': final update'

# The surviving push record names the exact branch and its final pushed tip.
ref = 'refs/heads/feature/retry-policy'
mirror = 'refs/remotes/mirror/feature/retry-policy'
expected[ref] = existing[mirror]
assert (root / ('logs/' + mirror)).read_text().splitlines()[-1].split()[1] == expected[ref]
evidence[ref] = mirror + ' and its update-by-push reflog'

for path in stage.glob('??/*'):
    raw = zlib.decompress(path.read_bytes())
    header, data = raw.split(b'\0', 1)
    if header.startswith(b'tag '):
        tag = next(line[4:].decode() for line in data.splitlines() if line.startswith(b'tag '))
        oid = path.parent.name + path.name
        name = 'refs/tags/' + tag
        assert name not in expected or expected[name] == oid
        expected[name] = oid
        evidence[name] = 'surviving annotated tag object ' + oid

for tag, commit, dist in [
    ('v1.2.1', 'bb11f51d295d4ace7c8eab9b7404adc0bfeb5c67', 'af4e4cd4deff009ddf4a7bb1e8ce4b954eecfa82'),
    ('v1.3.1', '35e60b11842b491b815e3e98c835e7b23596609a', '148c15071f76a8de6d7b8eb496202345e41ac9bf'),
]:
    assert git('show', '-s', '--format=%s', commit).decode().strip() == 'Release ' + tag
    assert git('show', commit + ':VERSION') == (tag + '\n').encode()
    assert git('show', dist + ':VERSION').startswith((tag + '-').encode())
    name = 'refs/tags/' + tag
    assert name not in expected
    expected[name] = commit
    evidence[name] = 'point-release script, release commit and VERSION, subsequent git-describe VERSION at ' + dist

assert len(expected) == 15
for name, oid in expected.items():
    git('check-ref-format', name)
    kind = git('cat-file', '-t', oid).decode().strip()
    assert kind in ('commit', 'tag')
    if name.startswith(('refs/heads/', 'refs/remotes/')):
        assert kind == 'commit'

inventory = json.loads((root / 'recovery/pack-inventory.json').read_text())
original = {entry['oid'] for entry in inventory}
original.update(p.parent.name + p.name for p in (root / 'objects').glob('??/*') if len(p.name) == 38)
verified = {p.parent.name + p.name for p in stage.glob('??/*') if len(p.name) == 38}
assert original == verified
for oid in sorted(verified):
    source = stage / oid[:2] / oid[2:]
    raw = zlib.decompress(source.read_bytes())
    assert hashlib.sha1(raw).hexdigest() == oid
    header, data = raw.split(b'\0', 1)
    assert int(header.split()[1]) == len(data)
    target = root / 'objects' / oid[:2] / oid[2:]
    target.parent.mkdir(exist_ok=True)
    temporary = target.with_name(target.name + '.recovered')
    shutil.copyfile(source, temporary)
    os.replace(temporary, target)

quarantine = root / 'recovery/quarantine'
quarantine.mkdir(exist_ok=True)
for suffix in ['pack', 'idx']:
    name = 'pack-0edbe236157d7f40502eaa2e054bc68160f770ab.' + suffix
    shutil.move(str(root / 'objects/pack' / name), str(quarantine / name))

# Atomic file restoration keeps the original reflogs byte-for-byte intact.
restored = {}
for name, oid in sorted(expected.items()):
    if name in existing:
        assert existing[name] == oid
        continue
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    assert not path.exists()
    temporary = path.with_name(path.name + '.lock')
    with temporary.open('x') as handle:
        handle.write(oid + '\n')
    os.replace(temporary, path)
    restored[name] = dict(oid=oid, evidence=evidence[name])

(root / 'recovery/refs-before.json').write_text(json.dumps(existing, indent=2, sort_keys=True))
(root / 'recovery/refs-restored.json').write_text(json.dumps(restored, indent=2, sort_keys=True))
(root / 'recovery/refs-expected.json').write_text(json.dumps(expected, indent=2, sort_keys=True))
(root / 'recovery/objects-expected.txt').write_text(''.join(oid + '\n' for oid in sorted(verified)))
print('Installed', len(verified), 'verified original objects and restored', len(restored), 'refs.')
for name, item in restored.items():
    print(name, item['oid'])
