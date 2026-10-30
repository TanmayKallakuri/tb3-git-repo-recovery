from pathlib import Path
import subprocess, json
from salvage import oid_for, store
root=Path('/app/repo.git');rec=root/'recovery';work=rec/'doc-generation'
work.mkdir(exist_ok=True)
commit='ebcc265012e322e29e4bb97e4afdae1ba2c87492'
def git(*args):return subprocess.check_output(['git','--git-dir='+str(root),*args])
for entry in git('ls-tree','-r','-z',commit,'orbit','tools/gen_api_docs.py').split(b'\0'):
 if not entry:continue
 header,name=entry.split(b'\t',1);mode,kind,oid=header.decode().split();assert kind=='blob'
 p=work/name.decode();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(git('cat-file','blob',oid))
subprocess.run(['python3',str(work/'tools/gen_api_docs.py')],check=True)
expected=git('ls-tree',commit,'docs/API.md').decode().split()[2]
body=(work/'docs/API.md').read_bytes();actual=oid_for('blob',body)
assert actual==expected,(actual,expected)
store(expected,'blob',body)
(rec/'docs-reconstruction.json').write_text(json.dumps(dict(oid=expected,commit=commit,generator='tools/gen_api_docs.py'),indent=2)+'\n')
print('Regenerated',expected,'from release',commit)
