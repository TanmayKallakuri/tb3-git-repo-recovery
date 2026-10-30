#!/usr/bin/env python3
"""Regenerate the missing API documents using their original source trees."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path('/app/repo.git')
REC = ROOT/'recovery'

def git(*args, data=None):
    return subprocess.run(['git', *args],cwd=ROOT,input=data,capture_output=True,check=True).stdout

proof=[]
for commit in ['c256b5c79663b545147eb748961436ae09201284',
               'ebcc265012e322e29e4bb97e4afdae1ba2c87492']:
    expected=git('rev-parse',commit+':docs/API.md').decode().strip()
    build=REC/('api-build-'+commit[:12])
    for line in git('ls-tree','-r','-z',commit,'orbit','tools/gen_api_docs.py').split(b'\0'):
        if not line:continue
        meta,path=line.split(b'\t',1); mode,typ,oid=meta.split()
        assert typ==b'blob' and mode==b'100644'
        dest=build/path.decode();dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(git('cat-file','blob',oid.decode()))
    subprocess.run(['python3','tools/gen_api_docs.py'],cwd=build,check=True)
    data=(build/'docs/API.md').read_bytes()
    raw=b'blob '+str(len(data)).encode()+b'\0'+data
    actual=hashlib.sha1(raw).hexdigest()
    assert actual==expected,(commit,expected,actual)
    assert git('hash-object','-w','--stdin',data=data).decode().strip()==expected
    (REC/'verified'/actual).write_bytes(raw)
    proof.append(dict(commit=commit,blob=actual,bytes=len(data)))
    print(commit,'API.md',actual,len(data),'bytes')
(REC/'api-reconstruction.json').write_text(json.dumps(proof,indent=2)+'\n')
