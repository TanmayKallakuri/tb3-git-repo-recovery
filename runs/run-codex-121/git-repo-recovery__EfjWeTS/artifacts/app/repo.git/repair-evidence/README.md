# Orbit repository repair

The repository at `/app/repo.git` was repaired in place using only its surviving files. No remote was accessed. All 612 original object IDs found in the damaged loose objects and pack index have been recovered and are reachable. All 619 objects in the completed repository have been independently rehashed and verified.

The resulting refs are recorded in `verification.json`: five branches, eight tags, and the five unchanged remote-tracking refs. Existing refs, reflogs, HEAD, config, and packed-refs were preserved byte for byte. The four lost branches and five lost tags are recorded in `restored-refs.json`.

## Recovery evidence

- The checksum-valid second pack supplied redundant copies of most erased objects; its missing index was rebuilt.
- Six corrupted loose objects were repaired by a unique single-byte correction matching the original SHA-1.
- Three erased retry-policy commits and their trees and blobs were reconstructed from archived patches. All resulting commit IDs matched the surviving pack index and patch headers exactly.
- Two missing versions of `docs/API.md` were regenerated with the original generator and source at their respective releases. Their blob IDs matched the original IDs exactly.
- The develop and hotfix tips came from their original reflogs. The retry-policy tip survived in the mirror ref.
- The cache-warmup branch had been rebased after the last mirror update. Its two commits were reconstructed using the archive script at the archive commit, the archived series, the archive commit's parent as the rebase base, the archive committer's identity, and the author dates and time zones mandated by the script. Re-exporting that branch reproduced both archived patches byte for byte.
- Surviving annotated tag objects restored v1.2.0 and v1.3.0. The release script and release commits identify lightweight tags v1.2.1 and v1.3.1.
- The missing v1.4.0 annotated tag was reconstructed from the release-time version of the release script and changelog. Its message includes the original release notes; its tagger is the release committer and its UTC timestamp comes from the changelog heading. Later edits to the script and notes were not used.

## Preserved evidence and validation

Original files are saved in `objects/`, `refs/`, `logs/`, and the top-level metadata files in this directory. Every object indexed in the damaged pack has been recovered into valid loose objects. The original damaged pack and index are outside Git's active object storage and are preserved in `quarantined/` as well as the initial snapshot. They are evidence, not active Git object files.

`verify_repair.py` independently hashes every active object, checks that all 612 original IDs remain reachable, compares surviving metadata byte for byte, verifies the restored refs, and runs `git fsck --full --strict` from `/app/repo.git`. Final status: exit 0, no output.
