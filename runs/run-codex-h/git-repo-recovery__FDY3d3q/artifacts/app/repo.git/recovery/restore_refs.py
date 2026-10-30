from pathlib import Path
import subprocess,json,hashlib
ROOT=Path('/app/repo.git');R=ROOT/'recovery'
def git(*args,data=None):return subprocess.check_output(['git',*args],cwd=ROOT,input=data)
def tag_bytes(commit,name,notes=False):
 raw=git('cat-file','commit',commit)
 ident=next(l[len(b'committer '):] for l in raw.split(b'\n\n')[0].splitlines() if l.startswith(b'committer '))
 message=f'orbit {name}\n'.encode()
 if notes:
  changelog=git('show',f'{commit}:CHANGELOG.md')
  script=git('show',f'{commit}:tools/release.sh')
  assert b"printf 'orbit %s\\n\\n'" in script
  bullets=subprocess.check_output(['sed','-n',f'/^## {name} - /,/^## /{{/^- /p;}}'],input=changelog)
  assert bullets
  message+=b'\n'+bullets
 return f'object {commit}\ntype commit\ntag {name}\ntagger '.encode()+ident+b'\n\n'+message
# Confirm tag serialization against every surviving annotated tag.
known=[('v1.0.0','1fbcf50531d91c00e33bae40dd0b1f4ec3494e65','769013b9f4a84795d101ca52157a07dbea36ea7b'),('v1.1.0','9099f204096190b4e3cbd96891387f65db44e675','808da7c33e7ae9c4a01418296aedbe08c62e274e'),('v1.2.0','c256b5c79663b545147eb748961436ae09201284','45628f3693a2a93bbe3570e21b871bf91d0b6acf'),('v1.3.0','ebcc265012e322e29e4bb97e4afdae1ba2c87492','493c34b0aa4c65d0a21d81db383cf35bb56f6ee0')]
for name,commit,oid in known:
 assert tag_bytes(commit,name)==git('cat-file','tag',oid)
 print('VERIFIED TAG SERIALIZATION',name,oid)
tag14=git('mktag',data=tag_bytes('407a8740ca9fe7768f2f31fd8169dc6edb94aa9b','v1.4.0',True)).decode().strip()
print('RECONSTRUCTED TAG',tag14)
refs={}
evidence={}
for name in ['main','develop','hotfix/1.2.1']:
 ref='refs/heads/'+name
 refs[ref]=(ROOT/'logs'/ref).read_text().splitlines()[-1].split()[1]
 evidence[ref]='Last recorded local push in logs/'+ref
refs['refs/heads/feature/retry-policy']=git('rev-parse','refs/remotes/mirror/feature/retry-policy').decode().strip()
evidence['refs/heads/feature/retry-policy']='Surviving mirror ref, its reflog, and terminal commit of the retry-policy graph'
refs['refs/heads/feature/cache-warmup']=(R/'cache-tip.txt').read_text().strip()
evidence['refs/heads/feature/cache-warmup']='docs/patches/cache-warmup/series identifies the branch and tip archive; patches reproduce the surviving first commit and the surviving final tree'
refs['refs/tags/v0.9.0-rc1']='518aac585f9a5f3220b0b504cb5df30edee0e99f'
evidence['refs/tags/v0.9.0-rc1']='Surviving packed ref'
for name,commit,oid in known:
 refs['refs/tags/'+name]=oid
 evidence['refs/tags/'+name]='Surviving annotated tag object with matching name and release commit'
for name,commit in [('v1.2.1','bb11f51d295d4ace7c8eab9b7404adc0bfeb5c67'),('v1.3.1','35e60b11842b491b815e3e98c835e7b23596609a')]:
 refs['refs/tags/'+name]=commit
 evidence['refs/tags/'+name]='Release commit, VERSION, changelog, and lightweight point-release policy in tools/release.sh'
refs['refs/tags/v1.4.0']=tag14
evidence['refs/tags/v1.4.0']='Recreated from tools/release.sh and CHANGELOG.md at the release commit, using its committer identity and date'
existing=dict(line.split(' ',1)[::-1] for line in git('show-ref').decode().splitlines())
for ref,oid in sorted(refs.items()):
 git('check-ref-format',ref)
 typ=git('cat-file','-t',oid).decode().strip()
 assert typ in ('commit','tag')
 if ref.startswith('refs/heads/'):assert typ=='commit'
 if ref in existing:
  assert existing[ref]==oid
  continue
 path=ROOT/ref;path.parent.mkdir(parents=True,exist_ok=True)
 # Restore loose refs atomically while preserving surviving reflogs byte-for-byte.
 lock=path.with_name(path.name+'.lock')
 with lock.open('x') as f:f.write(oid+'\n')
 lock.rename(path)
 print('RESTORED REF',ref,oid)
(R/'restored-refs.json').write_text(json.dumps({ref:{'oid':oid,'evidence':evidence[ref]} for ref,oid in sorted(refs.items())},indent=2)+'\n')
