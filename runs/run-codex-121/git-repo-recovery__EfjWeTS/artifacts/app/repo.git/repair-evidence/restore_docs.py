from restore_patches import *

def generate(commit):
 dest=WORK/('docgen-'+commit[:8]);dest.mkdir(exist_ok=True)
 listing=git('ls-tree','-rz',commit).split(b'\0')
 for row in listing:
  if not row:continue
  meta,path=row.split(b'\t',1);name=path.decode();mode,t,h=meta.decode().split()
  if name.startswith('orbit/') or name=='tools/gen_api_docs.py':
   p=dest/name;p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(git('cat-file','blob',h))
 subprocess.run(['python',str(dest/'tools/gen_api_docs.py')],check=True)
 result=(dest/'docs/API.md').read_bytes();expected=git('rev-parse',commit+':docs/API.md').decode().strip()
 assert oid('blob',result)==expected,(commit,oid('blob',result),expected)
 write('blob',result,expected);print('Restored generated API docs',commit,expected,len(result))

if __name__=='__main__':
 generate('cba733c406273a7abe5131c1259a52beba999df5')
 generate('c256b5c79663b545147eb748961436ae09201284')
