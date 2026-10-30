from collections import Counter
from pathlib import Path
import hashlib
import json
import subprocess
import tarfile

root = Path('/app/repo.git')

def git(*args):
    return subprocess.check_output(['git', *args], cwd=root)

expected_refs = json.loads((root / 'recovery/refs-expected.json').read_text())
actual_refs = {ref: oid for oid, ref in (line.split() for line in git('show-ref').decode().splitlines())}
assert expected_refs == actual_refs
expected_objects = set((root / 'recovery/objects-expected.txt').read_text().splitlines())
listed = git('cat-file', '--batch-all-objects', '--batch-check=%(objectname) %(objecttype)').decode().splitlines()
actual_objects = {line.split()[0] for line in listed}
assert actual_objects == expected_objects
reachable = {line.split()[0] for line in git('rev-list', '--objects', '--all').decode().splitlines()}
assert reachable == expected_objects
preserved = []
with tarfile.open(root / 'recovery/original.tar') as archive:
    for member in archive.getmembers():
        name = member.name.removeprefix('./')
        if member.isfile() and (name.startswith(('refs/', 'logs/')) or name in ['HEAD', 'config', 'packed-refs', 'description', 'info/exclude']):
            assert (root / name).read_bytes() == archive.extractfile(member).read(), name
            preserved.append(name)

for dist in [
    '582b0b5e2cb698b3ed5bdffc0cd45a3902c26d21',
    'af4e4cd4deff009ddf4a7bb1e8ce4b954eecfa82',
    '148c15071f76a8de6d7b8eb496202345e41ac9bf',
]:
    assert git('describe', '--tags', '--always', dist + '^') == git('show', dist + ':VERSION')

result = subprocess.run(['git', 'fsck', '--full', '--strict'], cwd=root, capture_output=True)
(root / 'recovery/fsck-final.txt').write_bytes(result.stdout + result.stderr)
assert result.returncode == 0 and not result.stdout and not result.stderr

summary = {
    'repository': str(root),
    'fsck_command': 'git fsck --full --strict',
    'fsck_exit_status': result.returncode,
    'fsck_output_bytes': len(result.stdout) + len(result.stderr),
    'original_object_ids': len(expected_objects),
    'verified_object_ids': len(actual_objects),
    'reachable_object_ids': len(reachable),
    'object_types': dict(Counter(line.split()[1] for line in listed)),
    'branches': len([ref for ref in actual_refs if ref.startswith('refs/heads/')]),
    'tags': len([ref for ref in actual_refs if ref.startswith('refs/tags/')]),
    'remote_tracking_refs': len([ref for ref in actual_refs if ref.startswith('refs/remotes/')]),
    'restored_refs': len(json.loads((root / 'recovery/refs-restored.json').read_text())),
    'original_metadata_files_preserved': preserved,
    'historical_dist_versions_reproduced': 3,
    'original_archive_sha256': hashlib.sha256((root / 'recovery/original.tar').read_bytes()).hexdigest(),
}
(root / 'recovery/audit.json').write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
