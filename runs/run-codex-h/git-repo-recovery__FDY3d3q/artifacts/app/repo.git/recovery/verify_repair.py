from pathlib import Path
import subprocess,tarfile,struct,hashlib,zlib,collections,json,re
ROOT=Path('/app/repo.git');R=ROOT/'recovery'
def git(*args,data=None):return subprocess.check_output(['git',*args],cwd=ROOT,input=data)
expected=set();preserved=0;reflog_oids=set()
with tarfile.open(R/'original.tar') as archive:
 for member in archive.getmembers():
  if not member.isfile():continue
  name=member.name.removeprefix('./');data=archive.extractfile(member).read()
  if re.fullmatch(r'objects/[0-9a-f]{2}/[0-9a-f]{38}',name):expected.add(name.replace('objects/','').replace('/',''))
  if name.endswith('.idx') and name.startswith('objects/pack/'):
   assert hashlib.sha1(data[:-20]).digest()==data[-20:]
   n=struct.unpack_from('>I',data,1028)[0]
   expected.update(data[1032+20*i:1052+20*i].hex() for i in range(n))
  if name.startswith('logs/') or name.startswith('refs/') or name in ('HEAD','config','packed-refs'):
   assert (ROOT/name).read_bytes()==data,name
   preserved+=1
  if name.startswith('logs/'):
   for line in data.decode().splitlines():reflog_oids.update(line.split()[:2])
reflog_oids.discard('0'*40)
all_rows=git('cat-file','--batch-all-objects','--batch-check=%(objectname) %(objecttype)').decode().splitlines()
all_oids={r.split()[0] for r in all_rows}
assert expected<=all_oids,expected-all_oids
assert reflog_oids<=all_oids,reflog_oids-all_oids
for row in all_rows:
 oid,kind=row.split();data=git('cat-file',kind,oid)
 raw=kind.encode()+b' '+str(len(data)).encode()+b'\0'+data
 assert hashlib.sha1(raw).hexdigest()==oid
reachable={line.split()[0] for line in git('rev-list','--objects','--all').decode().splitlines()}
assert reachable==all_oids,(all_oids-reachable,reachable-all_oids)
refs=dict(line.split(' ',1)[::-1] for line in git('show-ref').decode().splitlines())
restored=json.loads((R/'restored-refs.json').read_text())
assert set(refs)==set(restored)|{'refs/remotes/mirror/'+s for s in ['main','develop','feature/cache-warmup','feature/retry-policy','hotfix/1.2.1']}
for ref,item in restored.items():assert refs[ref]==item['oid']
# Reproduce the zero-ID archive exactly, including both commit messages/dates.
stage=R/'verified-cache-series';stage.mkdir(exist_ok=True)
paths=git('format-patch','--no-thread','--zero-commit','--no-signature','-o',str(stage),'43b85f3057459e6407714c6488448e713c1ef340..refs/heads/feature/cache-warmup').decode().splitlines()
assert len(paths)==2
for path in paths:
 p=Path(path);original=git('show','main:docs/patches/cache-warmup/'+p.name)
 assert p.read_bytes()==original,p.name
result=subprocess.run(['git','fsck','--full','--strict'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(R/'fsck-final.txt').write_bytes(result.stdout)
assert result.returncode==0,(result.returncode,result.stdout)
assert result.stdout==b'',result.stdout
summary={'fsck_exit_code':result.returncode,'fsck_output_bytes':len(result.stdout),'total_objects':len(all_oids),'object_counts':dict(collections.Counter(r.split()[1] for r in all_rows)),'original_indexed_and_loose_object_ids_verified':len(expected),'original_metadata_files_preserved_exactly':preserved,'reflog_object_ids_verified':len(reflog_oids),'all_objects_reachable':True,'cache_archive_roundtrip':'byte-for-byte match','branches':sum(r.startswith('refs/heads/') for r in refs),'tags':sum(r.startswith('refs/tags/') for r in refs),'remote_tracking_refs':sum(r.startswith('refs/remotes/') for r in refs)}
(R/'verification.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
