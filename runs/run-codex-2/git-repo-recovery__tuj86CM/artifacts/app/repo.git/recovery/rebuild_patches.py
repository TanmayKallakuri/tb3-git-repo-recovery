#!/usr/bin/env python3
"""Replay the archived patch contents into a private index, verifying commit IDs."""
from pathlib import Path
import email.parser
import email.utils
import hashlib
import json
import os
import re
import subprocess
import zlib

ROOT = Path('/app/repo.git')
REC = ROOT/'recovery'
env = dict(os.environ, GIT_INDEX_FILE=str(REC/'patch-index'))

def git(*args, data=None):
    return subprocess.run(['git', *args], cwd=ROOT, env=env, input=data,
                          capture_output=True, check=True).stdout

parent = '881cb3036f76b7bf5055b2fe511ee9bc515252f8'
git('read-tree', parent)
patch_names = git('ls-tree', '--name-only', 'main:docs/patches').decode().splitlines()
proof = []
for name in patch_names:
    patch = git('show', f'main:docs/patches/{name}')
    (REC/name).write_bytes(patch)
    expected = patch.splitlines()[0].split()[1].decode()
    git('apply', '--cached', '--whitespace=nowarn', str(REC/name))
    tree = git('write-tree', '--missing-ok').decode().strip()
    mail = email.parser.BytesParser().parsebytes(patch)
    date = email.utils.parsedate_to_datetime(mail['Date'])
    identity = f"{mail['From']} {int(date.timestamp())} {date.strftime('%z')}"
    subject = re.sub(r'^\[PATCH[^\]]*\] ', '', mail['Subject'])
    body = mail.get_payload().split('---\n', 1)[0].rstrip('\n')
    message = subject + ('\n\n'+body if body else '') + '\n'
    data = (f'tree {tree}\nparent {parent}\nauthor {identity}\ncommitter {identity}\n\n'+message).encode()
    raw = b'commit '+str(len(data)).encode()+b'\0'+data
    actual = hashlib.sha1(raw).hexdigest()
    assert actual == expected, (name, expected, actual, data)
    assert git('hash-object', '-w', '-t', 'commit', '--stdin', data=data).decode().strip() == expected
    (REC/'verified'/actual).write_bytes(raw)
    proof.append(dict(patch=name,commit=actual,tree=tree,parent=parent,identity=identity))
    print(name, actual, 'tree',tree)
    parent = actual
(REC/'patch-reconstruction.json').write_text(json.dumps(proof,indent=2)+'\n')
