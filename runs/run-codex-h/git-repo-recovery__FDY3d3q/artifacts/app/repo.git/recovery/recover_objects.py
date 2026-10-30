from pathlib import Path
import hashlib, zlib, struct, json, collections, pickle
ROOT=Path('/app/repo.git')
REC=ROOT/'recovery'
OBJECTS=ROOT/'objects'

def object_id(kind, data):
    return hashlib.sha1(kind.encode()+b' '+str(len(data)).encode()+b'\0'+data).hexdigest()

def read_index(path):
    d=path.read_bytes()
    assert d[:8]==b'\xfftOc\0\0\0\2'
    assert hashlib.sha1(d[:-20]).digest()==d[-20:]
    n=struct.unpack_from('>I',d,1028)[0]
    rows=[]
    for j in range(n):
        oid=d[1032+20*j:1052+20*j].hex()
        crc=struct.unpack_from('>I',d,1032+20*n+4*j)[0]
        off=struct.unpack_from('>I',d,1032+24*n+4*j)[0]
        assert off<2**31
        rows.append((off,oid,crc))
    return sorted(rows)

def delta_apply(base,delta):
    p=0
    def varint():
        nonlocal p
        result=0;shift=0
        while True:
            b=delta[p];p+=1;result|=(b&127)<<shift;shift+=7
            if not b&128:return result
    base_size=varint();size=varint()
    assert len(base)==base_size,(len(base),base_size)
    out=bytearray()
    while p<len(delta):
        cmd=delta[p];p+=1
        if cmd&128:
            offset=0;length=0
            for i in range(4):
                if cmd&(1<<i):offset|=delta[p]<<(i*8);p+=1
            for i in range(3):
                if cmd&(1<<(i+4)):length|=delta[p]<<(i*8);p+=1
            if length==0:length=65536
            assert offset+length<=len(base)
            out+=base[offset:offset+length]
        else:
            assert cmd and p+cmd<=len(delta)
            out+=delta[p:p+cmd];p+=cmd
    assert len(out)==size
    return bytes(out)

objects={};sources={};records=[];lost=[];corrupt=[]
def add(oid,kind,data,source):
    assert object_id(kind,data)==oid,(oid,kind,source)
    if oid in objects:assert objects[oid]==(kind,data)
    objects[oid]=(kind,data);sources.setdefault(oid,[]).append(source)

for p in sorted(OBJECTS.glob('??/*')):
    if not p.is_file():continue
    oid=p.parent.name+p.name
    compressed=p.read_bytes()
    try:
        raw=zlib.decompress(compressed)
        assert hashlib.sha1(raw).hexdigest()==oid
    except Exception:
        matches=[]
        for pos in range(len(compressed)):
            for bit in range(8):
                candidate=compressed[:pos]+bytes([compressed[pos]^(1<<bit)])+compressed[pos+1:]
                try:
                    raw=zlib.decompress(candidate)
                    if hashlib.sha1(raw).hexdigest()==oid:matches.append((pos,bit,candidate,raw))
                except zlib.error:pass
        if len(matches)!=1:
            corrupt.append(oid);print('UNRESOLVED LOOSE',oid,'matches',len(matches));continue
        pos,bit,repaired,raw=matches[0]
        p.write_bytes(repaired)
        print('REPAIRED LOOSE',oid,'byte',pos,'bit',bit)
    hdr,data=raw.split(b'\0',1);kind,size=hdr.decode().split(' ')
    assert int(size)==len(data)
    add(oid,kind,data,'loose')

for pack in sorted(OBJECTS.glob('pack/*.pack')):
    rows=read_index(pack.with_suffix('.idx'));d=pack.read_bytes()
    offsets={off:oid for off,oid,crc in rows}
    for j,(off,oid,crc) in enumerate(rows):
        end=rows[j+1][0] if j+1<len(rows) else len(d)-20
        p=off;b=d[p];p+=1;typ=(b>>4)&7;size=b&15;shift=4
        while b&128:b=d[p];p+=1;size|=(b&127)<<shift;shift+=7
        base=None
        if typ==6:
            b=d[p];p+=1;dist=b&127
            while b&128:b=d[p];p+=1;dist=((dist+1)<<7)+(b&127)
            base=offsets[off-dist]
        elif typ==7:base=d[p:p+20].hex();p+=20
        source=f'{pack.name}:{off}'
        if zlib.crc32(d[off:end])!=crc:
            lost.append({'oid':oid,'type':typ,'size':size,'base':base,'source':source});continue
        dec=zlib.decompressobj();data=dec.decompress(d[p:end])+dec.flush()
        assert dec.eof and not dec.unused_data and len(data)==size
        if typ in (6,7):records.append((oid,base,data,source))
        else:add(oid,{1:'commit',2:'tree',3:'blob',4:'tag'}[typ],data,source)

while True:
    remaining=[];done=0
    for oid,base,delta,source in records:
        if base in objects:
            kind,basedata=objects[base];data=delta_apply(basedata,delta)
            add(oid,kind,data,source);done+=1
        else:remaining.append((oid,base,delta,source))
    records=remaining
    if not done:break

for oid,(kind,data) in objects.items():
    p=OBJECTS/oid[:2]/oid[2:]
    if not p.exists():
        p.parent.mkdir(exist_ok=True);p.write_bytes(zlib.compress(kind.encode()+b' '+str(len(data)).encode()+b'\0'+data))
pickle.dump((objects,sources,records,lost,corrupt),open(REC/'objects.pkl','wb'))
print('VERIFIED',len(objects),collections.Counter(t for t,d in objects.values()))
print('UNRESOLVED DELTAS',len(records),'ZEROED',len(lost),'ZEROED WITHOUT DUPLICATES',len([r for r in lost if r['oid'] not in objects]))
for r in lost:
    if r['oid'] not in objects:print('MISSING',r)
for oid,base,delta,source in records:print('BLOCKED',oid,'base',base)
