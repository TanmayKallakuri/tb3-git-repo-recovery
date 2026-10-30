# Orbit repository recovery

The bare repository was repaired in place at `/app/repo.git`. Its original history and object IDs are preserved.

## Result

- `git fsck --full --strict`, run in `/app/repo.git`, exits 0 with no output.
- All 579 original objects are present, hash-verified and reachable: 150 commits, 263 trees, 162 blobs and 4 annotated tag objects.
- The recovered object set exactly equals the original pack-index and loose-object inventory. No extra objects were introduced.
- All 5 local branches, 7 tags and 3 mirror-tracking refs exist. Four branches and four tags were restored; surviving refs are unchanged.
- Original HEAD, configuration, packed refs and reflog records are preserved. Ref recovery added administrative reflog entries.

## Object recovery

1. Preserved the original repository files in `original.tar` before making repairs.
2. Rebuilt the missing index of the intact older pack.
3. Decoded both packs using their indexes, retaining only entries whose CRCs and reconstructed object hashes validate. Resolved delta bases across packs, recovering objects whose bases were damaged in the newer pack.
4. Repaired each of the six damaged loose objects by correcting one compressed byte and verifying the original object hash. Details are in `loose-repairs.json`.
5. Applied the archived three-patch retry-policy series to its original parent. Reconstructed the original trees, blobs and commits, including author and committer metadata and full messages. Every reconstructed commit matches the hash in its archived patch; every recovered packed object matches the original index. Details are in `patch-reconstruction.json`.
6. Regenerated the missing API documentation using the repository's generator and the v1.3.0 source tree, verified its original blob hash, then decoded the remaining dependent delta.
7. Retained the damaged pack and loose files under this recovery directory, outside Git's active object store.

## Ref evidence

Branch tips came from surviving branch reflogs and the mirror's update-by-push ref/reflog for `feature/retry-policy`. Annotated tag names and targets came from their original tag objects. Lightweight point-release tags came from the release commits, VERSION/CHANGELOG records, release script and complete object inventory. Restoring these tags also reproduces all three archived git-describe VERSION strings exactly. Per-ref evidence is in `restored-refs.json`.

## Final refs

| Ref | Object ID |
| --- | --- |
| `refs/heads/develop` | `6a1c42a2adb5cb6991cf51c848b58793e404ab29` |
| `refs/heads/feature/cache-warmup` | `fc1b7e8984ec70b6ee8ab78deceda6116e970f43` |
| `refs/heads/feature/retry-policy` | `d13c784d66243541536833780676efba0d86042a` |
| `refs/heads/hotfix/1.2.1` | `69305d3a6d68e96388e91dcdde3447ea7042944f` |
| `refs/heads/main` | `2b777f6ff2bfa4437a5576904761d0621d5fd43a` |
| `refs/remotes/mirror/develop` | `6a1c42a2adb5cb6991cf51c848b58793e404ab29` |
| `refs/remotes/mirror/feature/retry-policy` | `d13c784d66243541536833780676efba0d86042a` |
| `refs/remotes/mirror/main` | `2b777f6ff2bfa4437a5576904761d0621d5fd43a` |
| `refs/tags/v0.9.0-rc1` | `518aac585f9a5f3220b0b504cb5df30edee0e99f` |
| `refs/tags/v1.0.0` | `769013b9f4a84795d101ca52157a07dbea36ea7b` |
| `refs/tags/v1.1.0` | `808da7c33e7ae9c4a01418296aedbe08c62e274e` |
| `refs/tags/v1.2.0` | `45628f3693a2a93bbe3570e21b871bf91d0b6acf` |
| `refs/tags/v1.2.1` | `bb11f51d295d4ace7c8eab9b7404adc0bfeb5c67` |
| `refs/tags/v1.3.0` | `493c34b0aa4c65d0a21d81db383cf35bb56f6ee0` |
| `refs/tags/v1.3.1` | `35e60b11842b491b815e3e98c835e7b23596609a` |

`audit.json` records the final verification results. Recovery scripts and original damaged files are retained here for review. No history was rewritten.
