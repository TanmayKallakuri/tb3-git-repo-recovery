# Orbit repository recovery

The bare repository remains at `/app/repo.git`. Its original object IDs and
history have been preserved. Recovery used only data already in the repository.

## Result

- `git fsck --full --strict` exits 0 with no output.
- All 579 original objects are present, verified, and reachable from refs:
  150 commits, 263 trees, 162 blobs, and 4 annotated tag objects.
- The repository has 5 local branches, 7 tags, and the 3 existing mirror refs.
- Four missing branch refs and four missing tag refs were restored.
- Existing refs, reflogs, HEAD, configuration, and packed refs were preserved
  byte-for-byte. No replacement refs, grafts, or history rewriting were used.

## Evidence and method

The older pack's SHA-1 trailer matched its complete contents. Rebuilding its
missing index exposed 397 intact objects. Independent parsing of the newer
pack recovered every intact entry and resolved deltas against verified bases
from both packs. Every accepted object was checked against its original ID.

Six corrupt loose objects each had one damaged compressed byte. The correction
for each was identified by successful zlib decoding and an exact original
object hash match. Details are in `loose-repairs.json`.

The three archived 1.2 patches reproduced their original commits, including
trees, parents, author and committer metadata, and complete messages. All three
commit hashes matched the IDs recorded in the patches and pack index. Their
recovered trees and blobs also completed dependent packed deltas.

The two missing API documentation blobs were regenerated using the project's
own generator and the source trees of releases v1.2.0 and v1.3.0. Both hashes
matched their original tree entries exactly.

Branch tips came from the final local reflog records and the surviving mirror
push record for `feature/retry-policy`. The v1.2.0 and v1.3.0 refs point to their
surviving annotated tag objects. The v1.2.1 and v1.3.1 lightweight refs came from
the point-release workflow, release commits, and subsequent committed
`git describe` output. All three historical dist VERSION files reproduce
exactly with the recovered tags.

## Retained recovery records

- `original.tar`: exact pre-repair repository files.
- `quarantine/`: the damaged newer pack and its original index, removed from
  the active object database after recovery.
- `refs-restored.json`: each restored ref, original object ID, and evidence.
- `refs-expected.json`: complete final ref manifest.
- `objects-expected.txt`: all original object IDs, with no additional IDs.
- `audit.json`: final verification results.
- `fsck-before.txt` and `fsck-final.txt`: before and after checks.
- Recovery scripts, object provenance, staged verified objects, and regenerated
  documentation are retained for inspection. They are not Git refs or commits.

The final audit can be rerun with `python3 recovery/audit_recovery.py` while the
repository remains in this recovered state. The installation script records a
one-time operation and should not be rerun.
