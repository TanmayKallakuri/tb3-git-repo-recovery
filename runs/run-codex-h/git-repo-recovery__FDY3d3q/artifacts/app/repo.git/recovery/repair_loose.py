from pathlib import Path
import pickle,zlib,hashlib
root=Path('/app/repo.git')
objects,sources,records,lost,corrupt=pickle.load(open(root/'recovery/objects.pkl','rb'))
for oid in corrupt:
 p=root/'objects'/oid[:2]/oid[2:];d=p.read_bytes();matches=[]
 for pos in range(len(d)):
  for b in range(256):
   if b==d[pos]:continue
   candidate=d[:pos]+bytes([b])+d[pos+1:]
   try:
    raw=zlib.decompress(candidate)
    if hashlib.sha1(raw).hexdigest()==oid:matches.append((pos,b,candidate))
   except zlib.error:pass
 print(oid,'matches',[(pos,d[pos],b) for pos,b,c in matches],flush=True)
 if len(matches)==1:p.write_bytes(matches[0][2])
