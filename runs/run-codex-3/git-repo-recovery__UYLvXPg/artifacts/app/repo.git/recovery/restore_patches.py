from pathlib import Path
import email
import email.policy
import email.utils
import hashlib
import json
import os
import re
import subprocess
import zlib

root = Path('/app/repo.git')
env = dict(os.environ, GIT_OBJECT_DIRECTORY=str(root / 'recovery/verified-objects'),
           GIT_INDEX_FILE=str(root / 'recovery/patch-index'))

def git(*args, data=None):
    return subprocess.check_output(['git', *args], input=data, cwd=root, env=env)

patches = [
    'docs/patches/0001-Add-a-retry-policy-with-exponential-backoff.patch',
    'docs/patches/0002-Use-the-retry-policy-from-the-runner.patch',
    'docs/patches/0003-Add-tests-for-the-retry-policy.patch',
]
parent = '881cb3036f76b7bf5055b2fe511ee9bc515252f8'
git('read-tree', parent)
report = []
for patch_path in patches:
    patch = git('show', 'HEAD:' + patch_path)
    expected = patch.splitlines()[0].split()[1].decode()
    message = email.message_from_bytes(patch, policy=email.policy.default)
    who = str(message['From'])
    dt = email.utils.parsedate_to_datetime(str(message['Date']))
    identity = f'{who} {int(dt.timestamp())} {dt.strftime("%z")}'
    subject = re.sub(r'^\[PATCH[^\]]*\] ', '', str(message['Subject']))
    body = message.get_payload().split('\n---\n', 1)[0].rstrip('\n')
    # A subject-only patch starts directly with the diffstat separator.
    if body.startswith('---\n'):
        body = ''
    log = subject + ('\n\n' + body if body else '') + '\n'
    git('apply', '--cached', '--whitespace=nowarn', '-', data=patch)
    tree = git('write-tree').decode().strip()
    data = f'tree {tree}\nparent {parent}\nauthor {identity}\ncommitter {identity}\n\n{log}'.encode()
    raw = b'commit ' + str(len(data)).encode() + b'\0' + data
    actual = hashlib.sha1(raw).hexdigest()
    assert actual == expected, (expected, actual, data)
    oid = git('hash-object', '-t', 'commit', '-w', '--stdin', data=data).decode().strip()
    assert oid == expected
    report.append(dict(commit=oid, tree=tree, parent=parent, archive=patch_path))
    print('Restored', oid, subject, 'tree', tree)
    parent = oid
(root / 'recovery/patch-repairs.json').write_text(json.dumps(report, indent=2))
