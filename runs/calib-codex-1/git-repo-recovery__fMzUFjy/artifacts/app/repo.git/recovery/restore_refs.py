from pathlib import Path
import subprocess, json, re
root=Path('/app/repo.git');rec=root/'recovery'
def git(*args,data=None):
 return subprocess.check_output(['git','--git-dir='+str(root),*args],input=data)
current=dict(line.split(' ',1)[::-1] for line in git('show-ref').decode().splitlines())
restore={};evidence={}
for p in sorted((root/'logs/refs/heads').rglob('*')):
 if not p.is_file():continue
 ref=str(p.relative_to(root/'logs'));oid=p.read_text().splitlines()[-1].split()[1]
 if ref in current:assert current[ref]==oid
 else:restore[ref]=oid;evidence[ref]=str(p.relative_to(root))+' final entry'
ref='refs/heads/feature/retry-policy';oid=current['refs/remotes/mirror/feature/retry-policy']
assert git('cat-file','-t',oid).strip()==b'commit'
restore[ref]=oid;evidence[ref]='refs/remotes/mirror/feature/retry-policy and its update-by-push reflog'
objects=git('cat-file','--batch-all-objects','--batch-check=%(objectname) %(objecttype)').decode().splitlines()
for line in objects:
 oid,kind=line.split()
 if kind!='tag':continue
 body=git('cat-file','tag',oid).decode()
 name=next(l[4:] for l in body.splitlines() if l.startswith('tag '))
 ref='refs/tags/'+name
 if ref in current:assert current[ref]==oid
 else:restore[ref]=oid;evidence[ref]='surviving annotated tag object, including original tag name and target'
for name,oid in [('v1.2.1','bb11f51d295d4ace7c8eab9b7404adc0bfeb5c67'),('v1.3.1','35e60b11842b491b815e3e98c835e7b23596609a')]:
 assert git('show','-s','--format=%s',oid).decode().strip()=='Release '+name
 assert git('show',oid+':VERSION').decode().strip()==name
 ref='refs/tags/'+name;restore[ref]=oid
 evidence[ref]='point-release commit, VERSION and CHANGELOG, release.sh lightweight-tag option, later git-describe VERSION output, and complete original object inventory with no annotated tag for this release'
assert len(restore)==8,restore
for ref,oid in sorted(restore.items()):print(oid,ref,'SOURCE:',evidence[ref])
commands='start\n'+''.join(f'create {ref} {oid}\n' for ref,oid in sorted(restore.items()))+'prepare\ncommit\n'
print(git('update-ref','-m','Restore ref from surviving repository evidence','--stdin',data=commands.encode()).decode())
(rec/'restored-refs.json').write_text(json.dumps({ref:dict(oid=oid,evidence=evidence[ref]) for ref,oid in sorted(restore.items())},indent=2)+'\n')
