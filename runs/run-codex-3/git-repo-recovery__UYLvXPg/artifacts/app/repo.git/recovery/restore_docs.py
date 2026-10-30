from pathlib import Path
import hashlib
import json
import os
import subprocess

root = Path('/app/repo.git')
env = dict(os.environ, GIT_OBJECT_DIRECTORY=str(root / 'recovery/verified-objects'))

def git(*args, data=None):
    return subprocess.check_output(['git', *args], input=data, cwd=root, env=env)

report = []
for commit in ['c256b5c79663b545147eb748961436ae09201284', 'ebcc265012e322e29e4bb97e4afdae1ba2c87492']:
    work = root / 'recovery/render' / commit
    expected = git('rev-parse', commit + ':docs/API.md').decode().strip()
    entries = git('ls-tree', '-r', '-z', commit).split(b'\0')
    for entry in filter(None, entries):
        meta, name = entry.split(b'\t')
        name = name.decode()
        if name == 'tools/gen_api_docs.py' or (name.startswith('orbit/') and name.endswith('.py')):
            oid = meta.split()[2].decode()
            path = work / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(git('cat-file', 'blob', oid))
    subprocess.run(['python3', str(work / 'tools/gen_api_docs.py')], check=True)
    data = (work / 'docs/API.md').read_bytes()
    oid = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    assert oid == expected, (oid, expected)
    assert git('hash-object', '-t', 'blob', '-w', '--stdin', data=data).decode().strip() == expected
    report.append(dict(commit=commit, blob=expected, path='docs/API.md', bytes=len(data)))
    print('Regenerated', expected, 'from release', commit, 'bytes', len(data))
(root / 'recovery/docs-repairs.json').write_text(json.dumps(report, indent=2))
