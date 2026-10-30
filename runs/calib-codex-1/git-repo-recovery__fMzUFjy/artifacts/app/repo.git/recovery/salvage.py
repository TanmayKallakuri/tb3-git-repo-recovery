from pathlib import Path
import struct, hashlib, zlib, json, collections
ROOT=Path('/app/repo.git')
REC=ROOT/'recovery'
TYPES={1:'commit',2:'tree',3:'blob',4:'tag'}
def oid_for(kind,data):
 return hashlib.sha1(kind.encode()+b' '+str(len(data)).encode()+b'\0'+data).hexdigest()
def store(oid,kind,data):
 assert oid_for(kind,data)==oid
 p=ROOT/'objects'/oid[:2]/oid[2:]
 raw=kind.encode()+b' '+str(len(data)).encode()+b'\0'+data
 if p.exists():
  try:
   if zlib.decompress(p.read_bytes())==raw:return
  except zlib.error:pass
 p.parent.mkdir(exist_ok=True)
 p.write_bytes(zlib.compress(raw))
def delta(base,d):
 pos=0
 def integer():
  nonlocal pos
  n=0;s=0
  while True:
   c=d[pos];pos+=1;n|=(c&127)<<s;s+=7
   if c<128:return n
 assert integer()==len(base)
 n=integer();out=bytearray()
 while pos<len(d):
  c=d[pos];pos+=1
  if c&128:
   off=0;size=0
   for j in range(4):
    if c&(1<<j):off|=d[pos]<<(8*j);pos+=1
   for j in range(3):
    if c&(1<<(j+4)):size|=d[pos]<<(8*j);pos+=1
   if not size:size=65536
   assert off+size<=len(base)
   out+=base[off:off+size]
  else:
   assert c and pos+c<=len(d)
   out+=d[pos:pos+c];pos+=c
 assert len(out)==n
 return bytes(out)
def parse_pack(p):
 idx=p.with_suffix('.idx').read_bytes(); pack=p.read_bytes()
 assert idx[:8]==b'\xfftOc\x00\x00\x00\x02'
 assert hashlib.sha1(idx[:-20]).digest()==idx[-20:]
 n=struct.unpack_from('>I',idx,1028)[0]
 assert struct.unpack_from('>I',pack,8)[0]==n
 entries=[]
 for i in range(n):
  oid=idx[1032+20*i:1052+20*i].hex()
  crc=struct.unpack_from('>I',idx,1032+20*n+4*i)[0]
  off=struct.unpack_from('>I',idx,1032+24*n+4*i)[0]
  if off&0x80000000:off=struct.unpack_from('>Q',idx,1032+28*n+8*(off&0x7fffffff))[0]
  entries.append(dict(oid=oid,crc=crc,offset=off,pack=p.name))
 entries.sort(key=lambda e:e['offset'])
 offsets={e['offset']:e['oid'] for e in entries}
 for i,e in enumerate(entries):
  off=e['offset'];end=entries[i+1]['offset'] if i+1<n else len(pack)-20
  pos=off;c=pack[pos];pos+=1;typ=(c>>4)&7;size=c&15;s=4
  while c&128:
   c=pack[pos];pos+=1;size|=(c&127)<<s;s+=7
  e['type']=TYPES.get(typ,'delta');e['size']=size
  if typ==6:
   c=pack[pos];pos+=1;distance=c&127
   while c&128:
    c=pack[pos];pos+=1;distance=((distance+1)<<7)+(c&127)
   e['base']=offsets[off-distance]
  elif typ==7:
   e['base']=pack[pos:pos+20].hex();pos+=20
  e['crc_ok']=zlib.crc32(pack[off:end])==e['crc']
  if e['crc_ok']:
   dec=zlib.decompressobj();data=dec.decompress(pack[pos:end]);data+=dec.flush()
   assert dec.eof and not dec.unused_data and len(data)==size
   e['data']=data
  yield e

def main():
 objects={};broken=[]
 for p in (ROOT/'objects').glob('[0-9a-f][0-9a-f]/*'):
  oid=p.parent.name+p.name
  try:
   raw=zlib.decompress(p.read_bytes());hdr,data=raw.split(b'\0',1);kind,size=hdr.decode().split(' ')
   assert int(size)==len(data) and oid_for(kind,data)==oid
   objects[oid]=(kind,data)
  except Exception:broken.append(oid)
 entries=[]
 for p in list((ROOT/'objects/pack').glob('*.pack'))+list((REC/'damaged-packs').glob('*.pack')):
  entries.extend(parse_pack(p))
 unresolved=[e for e in entries if e['crc_ok']]
 while True:
  remaining=[];added=0
  for e in unresolved:
   if e['oid'] in objects:continue
   if e['type']=='delta':
    if e['base'] not in objects:remaining.append(e);continue
    kind,base=objects[e['base']];data=delta(base,e['data'])
   else:kind=e['type'];data=e['data']
   assert oid_for(kind,data)==e['oid'],e
   objects[e['oid']]=(kind,data);added+=1
  unresolved=remaining
  if not added:break
 for oid,(kind,data) in objects.items():store(oid,kind,data)
 manifest=[{k:v for k,v in e.items() if k!='data'} for e in entries]
 (REC/'pack-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 missing=sorted(set(e['oid'] for e in entries)-objects.keys())
 (REC/'missing-pack-objects.json').write_text(json.dumps(missing,indent=2)+'\n')
 print('Verified objects:',len(objects),dict(collections.Counter(k for k,d in objects.values())))
 print('Corrupt loose objects:',broken)
 print('Unavailable pack objects:',len(missing))
 for oid in missing:
  e=next(e for e in entries if e['oid']==oid)
  print(oid,e['type'],'size',e['size'],'base',e.get('base','-'),'CRC intact',e['crc_ok'])
if __name__=='__main__':main()
