from pathlib import Path
import zlib, hashlib, json
from salvage import store
records=[]
for p in Path('/app/repo.git/recovery/corrupt-loose').iterdir():
 data=bytearray(p.read_bytes());target=p.name;found=False
 for pos in range(len(data)):
  orig=data[pos]
  for replacement in range(256):
   data[pos]=replacement
   try:raw=zlib.decompress(data)
   except zlib.error:continue
   if hashlib.sha1(raw).hexdigest()!=target:continue
   hdr,body=raw.split(b'\0',1);kind,size=hdr.decode().split(' ')
   assert len(body)==int(size)
   store(target,kind,body)
   records.append(dict(oid=target,offset=pos,old_byte=orig,new_byte=data[pos]))
   print('Restored',target,kind,'one byte at offset',pos,'from',orig,'to',replacement)
   found=True;break
  data[pos]=orig
  if found:break
 if not found:print('Not a single byte:',target)
Path('/app/repo.git/recovery/loose-repairs.json').write_text(json.dumps(records,indent=2)+'\n')
