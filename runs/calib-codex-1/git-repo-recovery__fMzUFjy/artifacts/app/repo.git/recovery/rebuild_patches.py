from pathlib import Path
import subprocess, os, email.parser, email.utils, re, json
from salvage import oid_for, store
root=Path('/app/repo.git');rec=root/'recovery'
env=os.environ.copy();env['GIT_INDEX_FILE']=str(rec/'patch-index')
def git(*args,data=None):
 return subprocess.check_output(['git','--git-dir='+str(root),*args],input=data,env=env)
base='881cb3036f76b7bf5055b2fe511ee9bc515252f8'
git('read-tree',base)
patches=git('ls-tree','--name-only','refs/heads/main:docs/patches').decode().splitlines()
records=[]
for name in patches:
 patch=git('show','refs/heads/main:docs/patches/'+name)
 (rec/name).write_bytes(patch)
 expected=patch.splitlines()[0].split()[1].decode()
 mail=email.parser.BytesParser().parsebytes(patch)
 author_name,author_email=email.utils.parseaddr(mail['From'])
 dt=email.utils.parsedate_to_datetime(mail['Date'])
 author=f'{author_name} <{author_email}> {int(dt.timestamp())} {dt.strftime("%z")}'
 msgfile=rec/'patch-message';difffile=rec/'patch-diff'
 info=git('mailinfo',str(msgfile),str(difffile),data=patch)
 subject=next(line[9:] for line in info.splitlines() if line.startswith(b'Subject: '))
 body=msgfile.read_bytes()
 message=subject+b'\n'+(b'\n'+body if body else b'')
 git('apply','--cached',str(difffile))
 tree=git('write-tree').decode().strip()
 commit=(f'tree {tree}\nparent {base}\nauthor {author}\ncommitter {author}\n\n').encode()+message
 actual=oid_for('commit',commit)
 assert actual==expected,(actual,expected,commit)
 store(expected,'commit',commit)
 records.append(dict(oid=expected,tree=tree,parent=base,patch=name))
 print('Restored',expected,'tree',tree,'from',name)
 base=expected
(rec/'patch-reconstruction.json').write_text(json.dumps(records,indent=2)+'\n')
