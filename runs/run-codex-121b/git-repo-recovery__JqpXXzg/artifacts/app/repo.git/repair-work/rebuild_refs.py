from rebuild_series import *
from datetime import datetime
report=reconstruct_patch_series('8caad076eb6b22df3d1854065aa4df86dcc869fb',[
 'docs/patches/cache-warmup/0001-Warm-the-cache-in-a-background-thread.patch',
 'docs/patches/cache-warmup/0002-Add-a-cache-size-limit.patch'],committer='Mira Okafor <mira@orbit.example>',known=False)
(W/'cache-reconstruction.json').write_text(json.dumps(report,indent=2)+'\n')
release='cba733c406273a7abe5131c1259a52beba999df5'
commit=git('cat-file','commit',release)
committer=next(x for x in commit.splitlines() if x.startswith(b'committer '))[10:].rsplit(b' ',2)[0]
changelog=git('show',release+':CHANGELOG.md')
header=next(x for x in changelog.splitlines() if x.startswith(b'## v1.4.0 - '))
timestamp=int(datetime.strptime(header[12:].decode(),'%Y-%m-%d %H:%M:%S %z').timestamp())
# Reproduce the sed expression from this release's script, against this
# release's changelog, before its later correction.
notes=subprocess.run(['sed','-n','/^## v1.4.0 - /,/^## /{/^- /p;}'],input=changelog,stdout=subprocess.PIPE,check=True).stdout
message=b'orbit v1.4.0\n\n'+notes
obj=f'object {release}\ntype commit\ntag v1.4.0\ntagger '.encode()+committer+f' {timestamp} +0000\n\n'.encode()+message
tag=oidof('tag',obj); save(tag,'tag',obj)
print('RECONSTRUCTED TAG',tag)
print(obj.decode())
refs={
 'refs/heads/develop':(R/'logs/refs/heads/develop').read_text().splitlines()[-1].split()[1],
 'refs/heads/hotfix/1.2.1':(R/'logs/refs/heads/hotfix/1.2.1').read_text().splitlines()[-1].split()[1],
 'refs/heads/feature/retry-policy':(R/'refs/remotes/mirror/feature/retry-policy').read_text().strip(),
 'refs/heads/feature/cache-warmup':report[-1]['oid'],
 'refs/tags/v1.2.0':'45628f3693a2a93bbe3570e21b871bf91d0b6acf',
 'refs/tags/v1.2.1':'bb11f51d295d4ace7c8eab9b7404adc0bfeb5c67',
 'refs/tags/v1.3.0':'493c34b0aa4c65d0a21d81db383cf35bb56f6ee0',
 'refs/tags/v1.3.1':'35e60b11842b491b815e3e98c835e7b23596609a',
 'refs/tags/v1.4.0':tag,
}
(W/'refs-to-restore.json').write_text(json.dumps(refs,indent=2)+'\n')
