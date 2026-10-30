from pathlib import Path
import zlib,hashlib,struct,json,pickle,collections
ROOT=Path('/app/repo.git'); WORK=ROOT/'repair-evidence'; TYPES={1:'commit',2:'tree',3:'blob',4:'tag'}
def oid(t,d):return hashlib.sha1(t.encode()+b' '+str(len(d)).encode()+b'\0'+d).hexdigest()
def put(db,t,d,h=None):
 actual=oid(t,d)
 if h is not None:assert actual==h,(h,actual,t,len(d))
 db[actual]=(t,d);return actual
def varint(d,p):
 v=0;s=0
 while True:
  c=d[p];p+=1;v|=(c&127)<<s;s+=7
  if not c&128:return v,p
def delta_info(d):
 bs,p=varint(d,0);ts,p=varint(d,p);ops=[];q=0
 while p<len(d):
  c=d[p];p+=1
  if c&128:
   off=0;size=0
   for j in range(4):
    if c&(1<<j):off|=d[p]<<(j*8);p+=1
   for j in range(3):
    if c&(1<<(4+j)):size|=d[p]<<(j*8);p+=1
   size=size or 0x10000; assert off+size<=bs
   ops.append((q,off,size));q+=size
  else:
   assert c
   ops.append((q,None,d[p:p+c]));q+=c;p+=c
 assert q==ts
 return bs,ts,ops
def apply_delta(base,d):
 bs,ts,ops=delta_info(d);assert len(base)==bs
 out=b''.join(base[off:off+v] if off is not None else v for _,off,v in ops);assert len(out)==ts;return out

def load_loose():
 db={};bad=[]
 for p in (ROOT/'objects').glob('[0-9a-f][0-9a-f]/*'):
  h=p.parent.name+p.name
  try:
   raw=zlib.decompress(p.read_bytes());hdr,d=raw.split(b'\0',1);t,n=hdr.split();assert int(n)==len(d);put(db,t.decode(),d,h)
  except Exception as e:bad.append((h,str(e)))
 print('loose',len(db),'bad',bad);return db

def load_pack(p):
 b=p.read_bytes();assert b[:4]==b'PACK';n=struct.unpack('>I',b[8:12])[0];idx=p.with_suffix('.idx');imap={}
 if idx.exists():
  i=idx.read_bytes();assert hashlib.sha1(i[:-20]).digest()==i[-20:]
  ni=struct.unpack('>I',i[1028:1032])[0];assert n==ni
  for j in range(n):
   h=i[1032+20*j:1052+20*j].hex();crc,off=struct.unpack('>I',i[1032+20*n+4*j:1036+20*n+4*j])[0],struct.unpack('>I',i[1032+24*n+4*j:1036+24*n+4*j])[0];imap[off]=(h,crc)
  ends=dict(zip(sorted(imap),sorted(imap)[1:]+[len(b)-20]))
 pos=12;entries=[]
 for j in range(n):
  start=pos;c=b[pos];pos+=1;t=(c>>4)&7;s=c&15;shift=4
  while c&128:c=b[pos];pos+=1;s|=(c&127)<<shift;shift+=7
  base=None
  if t==6:
   c=b[pos];pos+=1;offset=c&127
   while c&128:c=b[pos];pos+=1;offset=((offset+1)<<7)|(c&127)
   base=start-offset
  elif t==7:base=b[pos:pos+20].hex();pos+=20
  zpos=pos;err=None
  try:
   z=zlib.decompressobj();d=z.decompress(b[pos:]);assert z.eof;pos=len(b)-len(z.unused_data);assert len(d)==s
   if imap:assert pos==ends[start]
  except Exception as e:
   assert imap,(p,start,str(e));d=None;err=str(e);pos=ends[start]
  h,crc=imap.get(start,(None,None));entry=dict(pack=p.name,offset=start,end=pos,zpos=zpos,type=t,size=s,base=base,oid=h,data=d,error=err);entries.append(entry)
 assert pos==len(b)-20
 byoff={e['offset']:e for e in entries}
 for e in entries:
  if isinstance(e['base'],int):e['base_entry']=byoff[e['base']];e['base']=e['base_entry']['oid']
 print(p.name,'entries',len(entries),'unreadable',sum(e['data'] is None for e in entries),'types',collections.Counter(e['type'] for e in entries));return entries

def resolve(db,entries):
 count=0
 for e in entries:
  if e['data'] is None:continue
  t=e['type'];d=e['data'];h=e['oid']
  if t in TYPES:
   e['oid']=put(db,TYPES[t],d,h)
  else:
   base=e.get('base_entry',{}).get('oid') or e['base'];e['base']=base
   if base not in db:continue
   bt,bd=db[base];e['oid']=put(db,bt,apply_delta(bd,d),h)
  if not e.get('resolved'):count+=1;e['resolved']=True
 return count

def main():
 db=load_loose();entries=[]
 for p in sorted((ROOT/'objects/pack').glob('*.pack')):entries+=load_pack(p)
 while resolve(db,entries):pass
 pickle.dump((db,entries),open(WORK/'state.pkl','wb'))
 missing=collections.Counter(e['base'] for e in entries if e['type'] in [6,7] and e['data'] is not None and not e.get('resolved'))
 print('resolved objects',len(db),collections.Counter(t for t,d in db.values()));print('unresolved entries',sum(not e.get('resolved') for e in entries),'bases',missing)
 for e in entries:
  if e['pack'].startswith('pack-dc') and not e.get('resolved'):print('thin unresolved',e['offset'],e['oid'],'base',e['base'],'delta lengths',delta_info(e['data'])[:2])
if __name__=='__main__':main()
