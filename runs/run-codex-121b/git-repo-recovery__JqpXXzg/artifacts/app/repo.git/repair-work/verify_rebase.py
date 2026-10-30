from rebuild_series import *
scratch=W/'verify-rebase'; scratch.mkdir(exist_ok=True)
def run(*args,env=None):
 p=subprocess.run(['git',*args],cwd=scratch,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
 return p.stdout
run('init','-q')
(scratch/'.git/objects/info/alternates').write_text(str(R/'objects')+'\n')
run('config','user.name','Mira Okafor')
run('config','user.email','mira@orbit.example')
run('checkout','--detach','03d41e4d28a0b0ccbd8f2ab30b581c2a450879c8')
run('rebase','--committer-date-is-author-date','8caad076eb6b22df3d1854065aa4df86dcc869fb')
actual=run('rev-parse','HEAD').decode().strip()
expected=json.loads((W/'cache-reconstruction.json').read_text())[-1]['oid']
assert actual==expected,(actual,expected)
print('Independent Git rebase reproduced original branch tip:',actual)
# Re-exporting with the historical archive flags must reproduce both surviving patches.
patches=json.loads((W/'cache-reconstruction.json').read_text())
export=scratch/'export'; export.mkdir(exist_ok=True)
run('format-patch','--no-thread','--zero-commit','--no-signature','--output-directory',str(export),'8caad076eb6b22df3d1854065aa4df86dcc869fb..'+actual)
for item in patches:
 exported=(export/Path(item['patch']).name).read_bytes()
 expected=git('show','HEAD:'+item['patch'])
 assert exported==expected,item['patch']
 print('Archive round trip verified:',item['patch'])
(W/'rebase-verification.txt').write_text('Independent Git rebase and exact patch archive round trip passed.\nTip: '+actual+'\n')
