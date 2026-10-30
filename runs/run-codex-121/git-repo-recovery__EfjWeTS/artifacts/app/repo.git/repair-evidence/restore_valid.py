from recover import *
db,es=pickle.load(open(WORK/'state.pkl','rb'))
for p in (ROOT/'objects').glob('[0-9a-f][0-9a-f]/*'):
 h=p.parent.name+p.name
 if h in db:continue
 bad=p.read_bytes();found=[]
 for pos in range(len(bad)):
  for val in range(256):
   if val==bad[pos]:continue
   b=bad[:pos]+bytes([val])+bad[pos+1:]
   try:
    raw=zlib.decompress(b);hdr,d=raw.split(b'\0',1);t,n=hdr.split()
    if int(n)==len(d) and oid(t.decode(),d)==h:found.append((pos,val,t.decode(),d,b))
   except Exception:pass
 assert len(found)==1,(h,[(v[0],v[1]) for v in found])
 pos,val,t,d,b=found[0];put(db,t,d,h);print('Repaired single byte',h,'position',pos,'old',bad[pos],'new',val,flush=True)
while resolve(db,es):pass
for h,(t,d) in db.items():
 p=ROOT/'objects'/h[:2]/h[2:];p.parent.mkdir(exist_ok=True)
 raw=t.encode()+b' '+str(len(d)).encode()+b'\0'+d
 if p.exists():
  try:
   if zlib.decompress(p.read_bytes())==raw:continue
  except zlib.error:pass
 p.write_bytes(zlib.compress(raw))
pickle.dump((db,es),open(WORK/'state.pkl','wb'));print('Wrote verified objects',len(db))
