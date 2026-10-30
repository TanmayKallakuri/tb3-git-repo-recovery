from pathlib import Path
import subprocess, tarfile, struct, hashlib, json, collections, re
root=Path('/app/repo.git');rec=root/'recovery'
def git(*args):return subprocess.check_output(['git','--git-dir='+str(root),*args])
original=set();original_refs={};original_logs={}
with tarfile.open(rec/'original.tar') as archive:
 for entry in archive:
  name=entry.name.removeprefix('./')
  if re.fullmatch(r'objects/[0-9a-f]{2}/[0-9a-f]{38}',name):
   original.add(name.split('/')[1]+name.split('/')[2])
  if name.endswith('.idx'):
   data=archive.extractfile(entry).read()
   assert hashlib.sha1(data[:-20]).digest()==data[-20:]
   n=struct.unpack_from('>I',data,1028)[0]
   original.update(data[1032+20*i:1052+20*i].hex() for i in range(n))
  if entry.isfile() and name.startswith('refs/'):
   original_refs[name]=archive.extractfile(entry).read().decode().strip()
  if entry.isfile() and name=='packed-refs':
   for line in archive.extractfile(entry).read().decode().splitlines():
    if not line.startswith(('#','^')):
     oid,ref=line.split();original_refs[ref]=oid
  if entry.isfile() and name.startswith('logs/'):
   original_logs[name]=archive.extractfile(entry).read()
  if name in ('HEAD','config','packed-refs'):
   assert archive.extractfile(entry).read()==(root/name).read_bytes(),name
current_refs=dict(line.split(' ',1)[::-1] for line in git('show-ref').decode().splitlines())
restored=json.loads((rec/'restored-refs.json').read_text())
expected_refs=original_refs|{ref:entry['oid'] for ref,entry in restored.items()}
assert current_refs==expected_refs
for name,data in original_logs.items():assert (root/name).read_bytes().startswith(data),name
all_objects={}
for line in git('cat-file','--batch-all-objects','--batch-check=%(objectname) %(objecttype) %(objectsize)').decode().splitlines():
 oid,kind,size=line.split();all_objects[oid]=(kind,int(size))
assert set(all_objects)==original,dict(missing=list(original-set(all_objects)),extra=list(set(all_objects)-original))
for oid,(kind,size) in all_objects.items():
 data=git('cat-file',kind,oid)
 assert len(data)==size
 assert hashlib.sha1(kind.encode()+b' '+str(size).encode()+b'\0'+data).hexdigest()==oid
reachable={line.split()[0] for line in git('rev-list','--objects','--all').decode().splitlines()}
assert reachable==original,dict(unreachable=list(original-reachable))
version_checks=[]
for commit in ('582b0b5e2cb698b3ed5bdffc0cd45a3902c26d21','af4e4cd4deff009ddf4a7bb1e8ce4b954eecfa82','148c15071f76a8de6d7b8eb496202345e41ac9bf'):
 stored=git('show',commit+':VERSION').decode().strip()
 described=git('describe','--tags','--always',commit+'^').decode().strip()
 assert stored==described,(commit,stored,described)
 version_checks.append(dict(commit=commit,version=stored))
fsck=subprocess.run(['git','fsck','--full','--strict'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(rec/'final-fsck.txt').write_bytes(fsck.stdout)
assert fsck.returncode==0 and fsck.stdout==b'',fsck.stdout.decode()
counts=dict(collections.Counter(kind for kind,size in all_objects.values()))
summary=dict(objects=len(original),object_types=counts,branches=sum(r.startswith('refs/heads/') for r in current_refs),tags=sum(r.startswith('refs/tags/') for r in current_refs),remote_refs=sum(r.startswith('refs/remotes/') for r in current_refs),restored_refs=len(restored),original_objects_present=True,all_objects_reachable=True,extra_objects=0,refs=current_refs,version_checks=version_checks,fsck_exit_code=fsck.returncode,fsck_output=fsck.stdout.decode())
(rec/'audit.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='refs'},indent=2))
report='''# Orbit repository recovery

The bare repository was repaired in place at `/app/repo.git`. Its original history and object IDs are preserved.

## Result

- `git fsck --full --strict`, run in `/app/repo.git`, exits 0 with no output.
- All 579 original objects are present, hash-verified and reachable: 150 commits, 263 trees, 162 blobs and 4 annotated tag objects.
- The recovered object set exactly equals the original pack-index and loose-object inventory. No extra objects were introduced.
- All 5 local branches, 7 tags and 3 mirror-tracking refs exist. Four branches and four tags were restored; surviving refs are unchanged.
- Original HEAD, configuration, packed refs and reflog records are preserved. Ref recovery added administrative reflog entries.

## Object recovery

1. Preserved the original repository files in `original.tar` before making repairs.
2. Rebuilt the missing index of the intact older pack.
3. Decoded both packs using their indexes, retaining only entries whose CRCs and reconstructed object hashes validate. Resolved delta bases across packs, recovering objects whose bases were damaged in the newer pack.
4. Repaired each of the six damaged loose objects by correcting one compressed byte and verifying the original object hash. Details are in `loose-repairs.json`.
5. Applied the archived three-patch retry-policy series to its original parent. Reconstructed the original trees, blobs and commits, including author and committer metadata and full messages. Every reconstructed commit matches the hash in its archived patch; every recovered packed object matches the original index. Details are in `patch-reconstruction.json`.
6. Regenerated the missing API documentation using the repository's generator and the v1.3.0 source tree, verified its original blob hash, then decoded the remaining dependent delta.
7. Retained the damaged pack and loose files under this recovery directory, outside Git's active object store.

## Ref evidence

Branch tips came from surviving branch reflogs and the mirror's update-by-push ref/reflog for `feature/retry-policy`. Annotated tag names and targets came from their original tag objects. Lightweight point-release tags came from the release commits, VERSION/CHANGELOG records, release script and complete object inventory. Restoring these tags also reproduces all three archived git-describe VERSION strings exactly. Per-ref evidence is in `restored-refs.json`.

## Final refs

| Ref | Object ID |
| --- | --- |
'''
for ref,oid in sorted(current_refs.items()):report+=f'| `{ref}` | `{oid}` |\n'
report+='\n`audit.json` records the final verification results. Recovery scripts and original damaged files are retained here for review. No history was rewritten.\n'
(rec/'REPORT.md').write_text(report)
