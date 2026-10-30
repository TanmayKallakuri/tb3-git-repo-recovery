from recover import *
import os,subprocess,email,email.utils,datetime,re

def git(*args,indata=None,env=None):
 e=os.environ.copy();e['GIT_DIR']=str(ROOT)
 if env:e.update(env)
 return subprocess.run(['git',*args],input=indata,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=e,check=True).stdout

def write(t,d,expected=None):
 h=oid(t,d)
 if expected:assert h==expected,(h,expected,d)
 assert git('hash-object','-w','-t',t,'--stdin',indata=d).decode().strip()==h
 return h

def apply_series(base,paths,committer=None,zeros=False):
 env={'GIT_INDEX_FILE':str(WORK/'patch-index')};git('read-tree',base,env=env);parent=base;results=[]
 for path in paths:
  patch=git('show','main:'+path);m=email.message_from_bytes(patch.split(b'\n',1)[1]);msg=m.get_payload();msg=re.split(r'^---$', msg, maxsplit=1, flags=re.M)[0]
  subject=re.sub(r'^\[PATCH[^\]]*\] ','',m['Subject']);message=subject+'\n'+(('\n'+msg.rstrip()+'\n') if msg.strip() else '')
  dt=email.utils.parsedate_to_datetime(m['Date']);ident=m['From']+' '+str(int(dt.timestamp()))+' '+dt.strftime('%z');ci=ident if committer is None else committer+' '+str(int(dt.timestamp()))+' '+dt.strftime('%z')
  git('apply','--cached','--whitespace=nowarn','-',indata=patch,env=env);tree=git('write-tree',env=env).decode().strip()
  data=f'tree {tree}\nparent {parent}\nauthor {ident}\ncommitter {ci}\n\n{message}'.encode()
  h=oid('commit',data);old=patch.split(b' ',2)[1].decode()
  if not zeros:assert h==old,(h,old,data)
  write('commit',data,h);results.append(h);print('Reconstructed patch commit',h,'tree',tree,flush=True);parent=h
 return results

if __name__=='__main__':
 apply_series('881cb3036f76b7bf5055b2fe511ee9bc515252f8',[
 'docs/patches/0001-Add-a-retry-policy-with-exponential-backoff.patch',
 'docs/patches/0002-Use-the-retry-policy-from-the-runner.patch',
 'docs/patches/0003-Add-tests-for-the-retry-policy.patch'])
