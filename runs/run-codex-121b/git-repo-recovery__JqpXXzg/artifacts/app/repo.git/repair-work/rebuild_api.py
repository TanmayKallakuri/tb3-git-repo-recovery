from recover import *
import subprocess,json

db,es=pickle.load(open(W/'inventory.pkl','rb')); report=[]
for commit in ['c256b5c79663b545147eb748961436ae09201284','ebcc265012e322e29e4bb97e4afdae1ba2c87492']:
 files=flatten(db,commit); target=files['docs/API.md'][1]
 dest=W/'generated'/commit; dest.mkdir(parents=True,exist_ok=True)
 for name,(mode,oid) in files.items():
  if name.startswith('orbit/') and name.endswith('.py') or name=='tools/gen_api_docs.py':
   p=dest/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(db[oid][1])
 subprocess.run(['python3',str(dest/'tools/gen_api_docs.py')],check=True)
 data=(dest/'docs/API.md').read_bytes(); assert oidof('blob',data)==target
 save(target,'blob',data)
 print('REGENERATED',target,'at',commit,'bytes',len(data))
 report.append(dict(oid=target,commit=commit,generator=files['tools/gen_api_docs.py'][1]))
(W/'api-reconstruction.json').write_text(json.dumps(report,indent=2)+'\n')
