from pathlib import Path
import hashlib,zlib,json
r=Path('/app/repo.git')
log=[]
for p in sorted((r/'objects').glob('??/*')):
 oid=p.parent.name+p.name
 raw=p.read_bytes()
 try:
  content=zlib.decompress(raw)
  if hashlib.sha1(content).hexdigest()==oid: continue
 except zlib.error: pass
 found=None
 for i,b in enumerate(raw):
  for bit in range(1,256):
   test=raw[:i]+bytes([b^bit])+raw[i+1:]
   try: content=zlib.decompress(test)
   except zlib.error: continue
   if hashlib.sha1(content).hexdigest()==oid:
    found=(test,i,bit); break
  if found: break
 if found:
  test,i,bit=found
  p.write_bytes(test)
  print('REPAIRED',oid,'byte',i,'bit',bit,flush=True)
  log.append(dict(oid=oid,byte=i,bit=bit))
 else: print('UNRESOLVED',oid,flush=True)
(r/'repair-work/loose-repairs.json').write_text(json.dumps(log,indent=2)+'\n')
