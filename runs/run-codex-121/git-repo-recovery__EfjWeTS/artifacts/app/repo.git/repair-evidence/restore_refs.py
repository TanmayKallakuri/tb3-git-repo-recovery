from restore_patches import *
import json

base='8caad076eb6b22df3d1854065aa4df86dcc869fb'
archive='c3c89302673fc6a602389c513c8f81c000234d78'
archive_raw=git('cat-file','commit',archive).decode()
assert ('parent '+base+'\n') in archive_raw
archive_committer=next(x for x in archive_raw.splitlines() if x.startswith('committer '))[10:].rsplit(' ',2)[0]
series=git('show',archive+':docs/patches/cache-warmup/series').decode().splitlines()
assert series[0]=='# Series cache-warmup: exported from the tip of feature/cache-warmup; the patches in order.'
patches=['docs/patches/cache-warmup/'+x for x in series[1:]]
rebased=apply_series(base,patches,archive_committer,True)
export=WORK/'reexport';export.mkdir(exist_ok=True)
git('format-patch','--no-thread','--zero-commit','--no-signature','-o',str(export),base+'..'+rebased[-1])
for path in patches:
 assert (export/Path(path).name).read_bytes()==git('show',archive+':'+path),path
print('Re-exported rebased series matches archived patches byte for byte')

release='cba733c406273a7abe5131c1259a52beba999df5';name='v1.4.0'
changelog=git('show',release+':CHANGELOG.md').decode();lines=changelog.splitlines();heading=next(x for x in lines if x.startswith('## '+name+' - '));stamp=heading.split(' - ',1)[1];dt=datetime.datetime.strptime(stamp,'%Y-%m-%d %H:%M:%S %z');timestamp=int(dt.timestamp())
notes=[]
for line in lines[lines.index(heading)+1:]:
 if line.startswith('## '):break
 if line.startswith('- '):notes.append(line)
release_raw=git('cat-file','commit',release).decode();release_committer=next(x for x in release_raw.splitlines() if x.startswith('committer '))[10:].rsplit(' ',2)[0]
message='orbit '+name+'\n\n'+'\n'.join(notes)+'\n'
tag_data=f'object {release}\ntype commit\ntag {name}\ntagger {release_committer} {timestamp} +0000\n\n{message}'.encode()
tag_id=git('mktag',indata=tag_data).decode().strip();assert tag_id==oid('tag',tag_data)
print('Reconstructed annotated release tag',tag_id);print(tag_data.decode())
refs={
 'refs/heads/develop':(ROOT/'logs/refs/heads/develop').read_text().splitlines()[-1].split()[1],
 'refs/heads/hotfix/1.2.1':(ROOT/'logs/refs/heads/hotfix/1.2.1').read_text().splitlines()[-1].split()[1],
 'refs/heads/feature/retry-policy':(ROOT/'refs/remotes/mirror/feature/retry-policy').read_text().strip(),
 'refs/heads/feature/cache-warmup':rebased[-1],
 'refs/tags/v1.2.0':'45628f3693a2a93bbe3570e21b871bf91d0b6acf',
 'refs/tags/v1.2.1':'bb11f51d295d4ace7c8eab9b7404adc0bfeb5c67',
 'refs/tags/v1.3.0':'493c34b0aa4c65d0a21d81db383cf35bb56f6ee0',
 'refs/tags/v1.3.1':'35e60b11842b491b815e3e98c835e7b23596609a',
 'refs/tags/v1.4.0':tag_id,
}
for ref,h in refs.items():
 t=git('cat-file','-t',h).decode().strip();assert t==('tag' if ref in ['refs/tags/v1.2.0','refs/tags/v1.3.0','refs/tags/v1.4.0'] else 'commit')
 if ref.startswith('refs/tags/') and t=='commit':assert git('log','-1','--format=%s',h).decode().strip()=='Release '+ref.split('/')[-1]
(WORK/'restored-refs.json').write_text(json.dumps(refs,indent=2)+'\n')
commands='start\n'+''.join(f'create {ref} {h}\n' for ref,h in refs.items())+'prepare\ncommit\n'
print(git('-c','core.logAllRefUpdates=false','update-ref','--stdin',indata=commands.encode()).decode())
