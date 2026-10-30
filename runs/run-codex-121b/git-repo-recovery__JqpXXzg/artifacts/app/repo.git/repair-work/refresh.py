from recover import *
db,es=pickle.load(open(W/'inventory.pkl','rb'))
for p in (R/'objects').glob('??/*'):
 raw=zlib.decompress(p.read_bytes()); head,data=raw.split(b'\0',1); typ,size=head.decode().split(); oid=p.parent.name+p.name
 assert oidof(typ,data)==oid
 db[oid]=(typ,data)
while True:
 changed=0
 for e in es:
  if e['oid'] in db or e['payload'] is None: continue
  b=e['base']; oid=b['oid'] if isinstance(b,dict) else b
  if oid not in db: continue
  typ,base=db[oid]; data=apply_delta(base,e['payload']); oid=oidof(typ,data)
  assert oid==e['oid']
  db[oid]=(typ,data); save(oid,typ,data); changed+=1
  print('DELTA RECOVERED',oid)
 if not changed: break
pickle.dump((db,es),open(W/'inventory.pkl','wb'))
for e in es:
 if e['oid'] not in db: print('MISSING',e['oid'],e['type'],e['size'])
print('Verified objects',len(db))
