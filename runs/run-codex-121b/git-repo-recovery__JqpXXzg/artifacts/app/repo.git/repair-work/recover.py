from pathlib import Path
import struct,zlib,hashlib,pickle,collections,json
R=Path('/app/repo.git'); W=R/'repair-work'; TYPES={1:'commit',2:'tree',3:'blob',4:'tag'}
def rawobj(typ,data): return typ.encode()+b' '+str(len(data)).encode()+b'\0'+data
def oidof(typ,data): return hashlib.sha1(rawobj(typ,data)).hexdigest()
def parse_delta(delta):
 p=0
 def size():
  nonlocal p
  n=0; shift=0
  while True:
   c=delta[p]; p+=1; n|=(c&127)<<shift
   if c<128: return n
   shift+=7
 src=size(); dst=size(); ops=[]
 while p<len(delta):
  op=delta[p]; p+=1
  if op&128:
   off=0; n=0
   for i in range(4):
    if op&(1<<i): off|=delta[p]<<(8*i); p+=1
   for i in range(3):
    if op&(16<<i): n|=delta[p]<<(8*i); p+=1
   n=n or 65536; ops.append((off,n))
  else:
   assert op
   ops.append(delta[p:p+op]); p+=op
 return src,dst,ops
def apply_delta(base,delta):
 src,dst,ops=parse_delta(delta); assert len(base)==src
 out=b''.join(base[op[0]:op[0]+op[1]] if isinstance(op,tuple) else op for op in ops)
 assert len(out)==dst
 return out

def inventory():
 db={}; entries=[]
 for p in sorted((R/'objects').glob('??/*')):
  try:
   raw=zlib.decompress(p.read_bytes()); typ_size,data=raw.split(b'\0',1); typ,size=typ_size.decode().split(' ')
   oid=p.parent.name+p.name; assert oidof(typ,data)==oid and len(data)==int(size)
   db[oid]=(typ,data)
  except Exception: print('BAD LOOSE',p)
 for pack in sorted((R/'objects/pack').glob('*.pack')):
  data=pack.read_bytes(); count=struct.unpack_from('>I',data,8)[0]; offsets={}
  if pack.with_suffix('.idx').exists():
   ix=pack.with_suffix('.idx').read_bytes(); n=struct.unpack_from('>I',ix,1028)[0]; assert n==count
   for i in range(n):
    oid=ix[1032+20*i:1052+20*i].hex(); crc=struct.unpack_from('>I',ix,1032+20*n+4*i)[0]; off=struct.unpack_from('>I',ix,1032+24*n+4*i)[0]
    offsets[off]=(oid,crc)
  boundaries=sorted(offsets)+[len(data)-20]; pos=12; loc={}
  for i in range(count):
   off=pos; c=data[pos]; pos+=1; typ=(c>>4)&7; size=c&15; shift=4
   while c&128:
    c=data[pos]; pos+=1; size|=(c&127)<<shift; shift+=7
   base=None
   if typ==6:
    c=data[pos]; pos+=1; back=c&127
    while c&128:
     c=data[pos]; pos+=1; back=((back+1)<<7)|(c&127)
    base=loc[off-back]
   elif typ==7: base=data[pos:pos+20].hex(); pos+=20
   oid,crc=offsets.get(off,(None,None))
   payload=None; start=pos
   if oid and zlib.crc32(data[off:boundaries[i+1]])!=crc:
    pos=boundaries[i+1]; assert set(data[start:pos])=={0}
   else:
    z=zlib.decompressobj(); payload=z.decompress(data[pos:]); assert z.eof and len(payload)==size
    pos=len(data)-len(z.unused_data)
   e=dict(pack=pack.name,offset=off,type=typ,size=size,base=base,oid=oid,payload=payload)
   loc[off]=e; entries.append(e)
  assert pos==len(data)-20
  print(pack.name,'entries',count,'erased',sum(e['payload'] is None for e in loc.values()))
 def resolve():
  changed=0
  for e in entries:
   if e.get('resolved') or e['payload'] is None: continue
   if e['type'] in TYPES: typ=TYPES[e['type']]; obj=e['payload']
   else:
    base=e['base']; oid=base.get('oid') if isinstance(base,dict) else base
    if oid not in db: continue
    typ,raw=db[oid]; obj=apply_delta(raw,e['payload'])
   oid=oidof(typ,obj)
   assert not e['oid'] or e['oid']==oid,(e['oid'],oid)
   db[oid]=(typ,obj); e['oid']=oid; e['resolved']=True; changed+=1
  return changed
 while resolve(): pass
 print('Resolved',len(db),collections.Counter(t for t,d in db.values()),'unresolved entries',sum(not e.get('resolved') for e in entries))
 pickle.dump((db,entries),open(W/'inventory.pkl','wb'))
 return db,entries

def save(oid,typ,data):
 assert oid==oidof(typ,data)
 p=R/'objects'/oid[:2]/oid[2:]; p.parent.mkdir(exist_ok=True); p.write_bytes(zlib.compress(rawobj(typ,data)))

if __name__=='__main__':
 db,entries=inventory()
 (W/'commits.txt').write_text('\n'.join(oid+' '+data.decode() for oid,(typ,data) in db.items() if typ=='commit'))
 (W/'tags.txt').write_text('\n'.join(oid+' '+data.decode() for oid,(typ,data) in db.items() if typ=='tag'))
 with open(W/'unresolved.txt','w') as f:
  for e in entries:
   if not e.get('resolved'):
    b=e['base']; base=b.get('oid') or ('@'+str(b['offset'])) if isinstance(b,dict) else b
    f.write(f"{e['pack'][5:13]} @{e['offset']} {e['oid']} type={e['type']} size={e['size']} base={base} erased={e['payload'] is None}\n")

def tree_entries(data):
 out=[]; p=0
 while p<len(data):
  q=data.index(b' ',p); mode=data[p:q].decode(); p=q+1; q=data.index(b'\0',p); name=data[p:q].decode(); p=q+1
  oid=data[p:p+20].hex(); p+=20; out.append((mode,name,oid))
 return out

def make_tree(entries):
 return b''.join(m.encode()+b' '+n.encode()+b'\0'+bytes.fromhex(o) for m,n,o in sorted(entries,key=lambda x:(x[1]+('/' if x[0]=='40000' else '')).encode()))

def flatten(db,oid,prefix=''):
 if oid not in db: return {prefix:('missing',oid)}
 typ,data=db[oid]
 if typ=='commit': return flatten(db,data.splitlines()[0][5:].decode(),prefix)
 assert typ=='tree'
 out={}
 for mode,name,h in tree_entries(data):
  if mode=='40000': out.update(flatten(db,h,prefix+name+'/'))
  else: out[prefix+name]=(mode,h)
 return out
