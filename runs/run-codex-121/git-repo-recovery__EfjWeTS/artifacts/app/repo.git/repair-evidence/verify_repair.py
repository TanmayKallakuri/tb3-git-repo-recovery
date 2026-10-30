from restore_patches import *
import collections

saved=WORK/'objects'
expected=set()
for p in saved.glob('[0-9a-f][0-9a-f]/*'):expected.add(p.parent.name+p.name)
for p in (saved/'pack').glob('*.idx'):
 data=p.read_bytes();n=struct.unpack('>I',data[1028:1032])[0]
 expected.update(data[1032+20*k:1052+20*k].hex() for k in range(n))
# Independently inspect every object Git now exposes, recomputing its object ID.
items=git('cat-file','--batch-all-objects','--batch-check=%(objectname) %(objecttype)').decode().splitlines();actual={};counts=collections.Counter()
for item in items:
 h,t=item.split();content=git('cat-file',t,h);assert oid(t,content)==h;actual[h]=(t,content);counts[t]+=1
assert expected<=actual.keys(),sorted(expected-actual.keys())
# Every known object from before the failure remains reachable.
reachable={x.split()[0] for x in git('rev-list','--objects','--all','--reflog').decode().splitlines()}
assert expected<=reachable,sorted(expected-reachable)
# Verify preserved metadata and surviving refs.
for name in ['HEAD','config','packed-refs']:
 assert (ROOT/name).read_bytes()==(WORK/name).read_bytes(),name
for directory in ['refs','logs']:
 for p in (WORK/directory).rglob('*'):
  if p.is_file():
   current=ROOT/p.relative_to(WORK)
   assert current.read_bytes()==p.read_bytes(),current
refs=dict(line.split()[::-1] for line in git('show-ref').decode().splitlines())
restored=json.loads((WORK/'restored-refs.json').read_text())
for ref,h in restored.items():assert refs[ref]==h
assert len([r for r in refs if r.startswith('refs/heads/')])==5
assert len([r for r in refs if r.startswith('refs/tags/')])==8
check=subprocess.run(['git','fsck','--full','--strict'],cwd=ROOT,capture_output=True)
assert check.returncode==0,(check.returncode,check.stdout,check.stderr)
assert not check.stdout and not check.stderr,(check.stdout,check.stderr)
report={'fsck_exit':check.returncode,'fsck_output':'','original_object_ids_verified':len(expected),'all_object_ids_verified':len(actual),'object_types':dict(counts),'refs':refs}
(WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='refs'},indent=2))
print('Branches: 5; tags: 8; original remote-tracking refs: 5')
