import os,subprocess,re,email,email.utils,json
from pathlib import Path
from recover import *
def git(*args,input=None,env=None):
 return subprocess.run(['git',*args],input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,env=env,cwd=R).stdout

def reconstruct_patch_series(base,patchpaths,committer=None,known=True):
 env=dict(os.environ,GIT_INDEX_FILE=str(W/'series.index'))
 (W/'series.index').unlink(missing_ok=True)
 git('read-tree',base,env=env)
 parent=base; report=[]
 for patchpath in patchpaths:
  patch=git('show','HEAD:'+patchpath)
  meta=email.message_from_bytes(patch)
  author_name,author_email=email.utils.parseaddr(meta['From'])
  date=email.utils.parsedate_to_datetime(meta['Date']); timestamp=int(date.timestamp()); tz=date.strftime('%z')
  subject=re.sub(r'^\[PATCH[^]]*\] ','',meta['Subject'])
  msg=patch.split(b'\n\n',1)[1].split(b'---\n',1)[0].strip(b'\n')
  message=subject.encode()+b'\n'+(b'\n'+msg+b'\n' if msg else b'')
  git('apply','--cached','--whitespace=nowarn','-',input=patch,env=env)
  tree=git('write-tree',env=env).decode().strip()
  author=f'{author_name} <{author_email}> {timestamp} {tz}'
  commit_ident=(committer or f'{author_name} <{author_email}>')+f' {timestamp} {tz}'
  content=f'tree {tree}\nparent {parent}\nauthor {author}\ncommitter {commit_ident}\n\n'.encode()+message
  oid=oidof('commit',content)
  if known:
   expected=patch.splitlines()[0].split()[1].decode()
   assert oid==expected,(oid,expected,content)
  save(oid,'commit',content)
  print('RECONSTRUCTED',oid,subject,flush=True)
  report.append(dict(oid=oid,parent=parent,tree=tree,patch=patchpath,author=author,committer=commit_ident))
  parent=oid
 (W/'series.index').unlink()
 return report
if __name__=='__main__':
 report=reconstruct_patch_series('881cb3036f76b7bf5055b2fe511ee9bc515252f8',[
  'docs/patches/0001-Add-a-retry-policy-with-exponential-backoff.patch',
  'docs/patches/0002-Use-the-retry-policy-from-the-runner.patch',
  'docs/patches/0003-Add-tests-for-the-retry-policy.patch'])
 (W/'retry-reconstruction.json').write_text(json.dumps(report,indent=2)+'\n')
