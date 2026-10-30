from pathlib import Path
import subprocess,os,email.parser,email.policy,email.utils,re,hashlib,json
ROOT=Path('/app/repo.git');R=ROOT/'recovery'
env=os.environ.copy();env['GIT_INDEX_FILE']=str(R/'patches.index')
def git(*args,data=None):return subprocess.check_output(['git',*args],cwd=ROOT,env=env,input=data)
def oid(kind,data):return hashlib.sha1(kind.encode()+b' '+str(len(data)).encode()+b'\0'+data).hexdigest()
def restore(parent,blob,expected=None):
 patch=git('cat-file','blob',blob)
 msg=email.parser.BytesParser(policy=email.policy.default).parsebytes(patch.split(b'\n',1)[1])
 name,addr=email.utils.parseaddr(msg['From']);dt=email.utils.parsedate_to_datetime(msg['Date']);tz=dt.strftime('%z');stamp=str(int(dt.timestamp()))
 subject=re.sub(r'^\[PATCH[^]]*\]\s*','',str(msg['Subject']))
 body=re.split(r'^---$',msg.get_payload(),maxsplit=1,flags=re.MULTILINE)[0].rstrip('\n')
 message=(subject+'\n'+ ('\n'+body+'\n' if body else '')).encode()
 git('read-tree',parent)
 git('apply','--cached','--whitespace=nowarn','-',data=patch)
 tree=git('write-tree').decode().strip()
 ident=f'{name} <{addr}> {stamp} {tz}'
 commit=(f'tree {tree}\nparent {parent}\nauthor {ident}\ncommitter {ident}\n\n').encode()+message
 commit_id=oid('commit',commit)
 if expected:assert commit_id==expected,(commit_id,expected,commit)
 actual=git('hash-object','-t','commit','-w','--stdin',data=commit).decode().strip();assert actual==commit_id
 print(json.dumps({'commit':commit_id,'parent':parent,'tree':tree,'patch_blob':blob,'known_commit_verified':bool(expected)}),flush=True)
 return commit_id
parent='881cb3036f76b7bf5055b2fe511ee9bc515252f8'
for blob,expected in [('4691dda4f3222f39290b634d98cfd477e75d74ad','cac0888c02248f2457ccc0f47aad766d41e8a37c'),('304deb779d54ef4fc6bc2b49b72d1c7367393f4e','11546642caef9b8f524df49a139bb6862b747dc8'),('cd7084c9e5db82aa880f476b018d11d852aa8f35','c30cfac86f61d9e3f5782f272924333776ecd662')]:
 parent=restore(parent,blob,expected)
# Replay the zero-ID archive against its surviving base; its first commit must
# exactly reproduce the known mirrored commit before recovering the second.
parent=restore('43b85f3057459e6407714c6488448e713c1ef340','b3eb9026c1a57e5ca195dc4bf1d631c8b4790a44','aef3e022037917637248671a8d936d6710f61da6')
parent=restore(parent,'ea816c6120424a05ae1579204e480d60c962170f')
(R/'cache-tip.txt').write_text(parent+'\n')
