#!/usr/bin/env python3
"""Restore only references evidenced by reflogs, mirror refs, and releases."""
from pathlib import Path
import json
import os
import re
import subprocess

ROOT=Path('/app/repo.git')
REC=ROOT/'recovery'

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT).decode().strip()

def refs_now():
    return {ref:oid for oid,ref in (line.split() for line in git('show-ref').splitlines())}

original=refs_now()
expected=dict(original)
evidence={ref:'Surviving reference' for ref in original}
for log in sorted((ROOT/'logs/refs/heads').rglob('*')):
    if not log.is_file():continue
    ref=str(log.relative_to(ROOT/'logs'))
    oid=log.read_text().splitlines()[-1].split()[1]
    assert oid != '0'*40
    assert git('cat-file','-t',oid)=='commit'
    if ref in expected:assert expected[ref]==oid
    expected[ref]=oid
    evidence[ref]=str(log.relative_to(ROOT))+': final recorded tip'

mirror='refs/remotes/mirror/feature/retry-policy'
expected['refs/heads/feature/retry-policy']=original[mirror]
evidence['refs/heads/feature/retry-policy']=mirror+' and its update-by-push reflog'

tag_objects={}
releases={}
for row in git('cat-file','--batch-all-objects','--batch-check=%(objectname) %(objecttype)').splitlines():
    oid,typ=row.split()
    if typ=='tag':
        data=git('cat-file','tag',oid)
        name=re.search(r'^tag (.+)$',data,re.M)[1]
        target=re.search(r'^object (.+)$',data,re.M)[1]
        assert name not in tag_objects
        tag_objects[name]=(oid,target)
    elif typ=='commit':
        message=git('cat-file','commit',oid).split('\n\n',1)[1]
        if re.fullmatch(r'Release v\d+\.\d+\.\d+',message):
            name=message[len('Release '):]
            assert git('show',oid+':VERSION')==name
            assert name not in releases
            releases[name]=oid

assert set(tag_objects)=={'v1.0.0','v1.1.0','v1.2.0','v1.3.0'}
assert set(releases)=={'v1.0.0','v1.1.0','v1.2.0','v1.2.1','v1.3.0','v1.3.1'}
for name,commit in releases.items():
    ref='refs/tags/'+name
    if name in tag_objects:
        oid,target=tag_objects[name];assert target==commit
        why='Original annotated tag object naming this release commit'
    else:
        assert name in {'v1.2.1','v1.3.1'}
        oid=commit
        why=('Lightweight point-release tag: release commit, VERSION, release.sh, '
             'later git-describe VERSION, and complete original object catalog')
    if ref in expected:assert expected[ref]==oid
    expected[ref]=oid;evidence[ref]=why

assert len([r for r in expected if r.startswith('refs/heads/')])==5
assert len([r for r in expected if r.startswith('refs/tags/')])==7
assert len(expected)==15
for ref,oid in sorted(expected.items()):
    git('check-ref-format',ref)
    if ref in original:continue
    path=ROOT/ref;path.parent.mkdir(parents=True,exist_ok=True)
    lock=Path(str(path)+'.lock')
    with lock.open('x') as f:
        f.write(oid+'\n');f.flush();os.fsync(f.fileno())
    os.replace(lock,path)
    print('Restored',ref,oid)

assert refs_now()==expected
manifest={ref:dict(oid=oid,evidence=evidence[ref],restored=ref not in original)
          for ref,oid in sorted(expected.items())}
(REC/'refs-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
