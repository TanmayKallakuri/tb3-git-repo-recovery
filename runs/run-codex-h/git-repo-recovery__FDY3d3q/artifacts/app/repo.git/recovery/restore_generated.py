from pathlib import Path
import subprocess,hashlib,pickle,zlib
ROOT=Path('/app/repo.git');R=ROOT/'recovery';stage=R/'generate-api'
def git(*args,data=None):return subprocess.check_output(['git',*args],cwd=ROOT,input=data)
for entry in git('ls-tree','-r','-z','main','orbit','tools/gen_api_docs.py').split(b'\0'):
 if not entry:continue
 meta,path=entry.split(b'\t');mode,kind,oid=meta.split()
 target=stage/path.decode();target.parent.mkdir(parents=True,exist_ok=True)
 target.write_bytes(git('cat-file','blob',oid.decode()))
subprocess.run(['python',str(stage/'tools/gen_api_docs.py')],check=True)
data=(stage/'docs/API.md').read_bytes();expected='0f21f2abd320bc7a3e95791a7f6b334c59b2557a'
actual=git('hash-object','--stdin',data=data).decode().strip();assert actual==expected,(actual,expected)
git('hash-object','-w','--stdin',data=data);print('REGENERATED API',actual,len(data))
# Load the already validated delta instructions saved before quarantine.
_,_,records,_,_=pickle.load(open(R/'objects.pkl','rb'))
def apply(base,delta):
 p=0
 def varint():
  nonlocal p
  result=0;shift=0
  while True:
   b=delta[p];p+=1;result|=(b&127)<<shift;shift+=7
   if not b&128:return result
 assert varint()==len(base);size=varint();out=bytearray()
 while p<len(delta):
  cmd=delta[p];p+=1
  if cmd&128:
   offset=0;length=0
   for i in range(4):
    if cmd&(1<<i):offset|=delta[p]<<(i*8);p+=1
   for i in range(3):
    if cmd&(1<<(i+4)):length|=delta[p]<<(i*8);p+=1
   if length==0:length=65536
   assert offset+length<=len(base)
   out+=base[offset:offset+length]
  else:
   assert cmd and p+cmd<=len(delta)
   out+=delta[p:p+cmd];p+=cmd
 assert len(out)==size
 return bytes(out)
for oid,base,delta,source in records:
 typ=git('cat-file','-t',base).decode().strip();data=apply(git('cat-file',typ,base),delta)
 actual=git('hash-object','-t',typ,'--stdin',data=data).decode().strip();assert actual==oid
 git('hash-object','-t',typ,'-w','--stdin',data=data);print('RESTORED DELTA',typ,oid)
