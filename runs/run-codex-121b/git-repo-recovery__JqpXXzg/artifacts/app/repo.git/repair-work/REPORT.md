# Orbit repository recovery

The repository was repaired in place at `/app/repo.git`, using only its surviving contents.

## Result

- `git fsck --full --strict` exits 0 with no output.
- 619 valid objects, including 161 reachable commits.
- Five branches, eight tags, and all five original mirror refs.
- All surviving refs retain their original targets. All original reflog entries remain intact; restoration entries were appended where Git maintained a reflog.
- Every object listed in the original pack index and every original loose object is present under its original hash. No surviving history was rewritten.

## Reconstruction evidence

1. Six corrupt loose objects each had one damaged byte. The corrected decompressed content was accepted only when its SHA-1 matched the original object filename.
2. The indexed pack contained 37 erased compressed streams. Its readable objects and deltas were salvaged; the original damaged pack and index are quarantined in `repair-work/damaged-pack/` outside Git's object storage.
3. The second pack had a valid original checksum but no index. Its objects supplied overlapping content and history. After recovering its dependencies, its index was rebuilt successfully.
4. The three missing retry-policy commits were reproduced from the surviving `docs/patches/0001...0003` archive, based on commit `881cb3036f76b7bf5055b2fe511ee9bc515252f8`. Each reconstructed commit matched the full original hash recorded in its patch and the damaged pack index. Their blobs and trees also recovered the remaining erased objects in that series.
5. Two missing API documentation blobs were regenerated using the historical `tools/gen_api_docs.py` and package source at releases v1.2.0 and v1.3.0. Both matched their expected original blob hashes exactly.
6. `develop` and `hotfix/1.2.1` were restored from their surviving branch reflogs. `feature/retry-policy` was restored from its surviving mirror tip and complete history.
7. `feature/cache-warmup` had been rebased after the mirror's last update. The archived series and historical `tools/archive-series.sh` specify its base (the archive commit's parent), patches, committer identity, and preservation of author dates as committer dates. Reconstructing this operation gives tip `1282507db11c676ede8b3873227070b19cd7c7ef`. An independent Git rebase of the surviving old branch reproduced this exact tip, and exporting the reconstructed series reproduced both archived patch files byte for byte.
8. The v1.2.0 and v1.3.0 annotated tag objects survived. The v1.2.1 and v1.3.1 lightweight tags were restored to their release commits. Every surviving VERSION value produced by `git describe` was checked against the restored tag set and matched exactly.
9. The missing v1.4.0 annotated tag was reconstructed using the release script and CHANGELOG at release commit `cba733c406273a7abe5131c1259a52beba999df5`, before later edits to those files. It uses Dev Patel's identity, timestamp `1790655342 +0000` from the historical changelog heading, and that release's original note text. Its object ID is `24fda256be3109a82ee0d188786d72528b7630fe`.

## Final references

| Reference | Object ID |
| --- | --- |
| `refs/heads/develop` | `fe3c1bd736a49008c896bfe91cd633a1922003ef` |
| `refs/heads/feature/cache-warmup` | `1282507db11c676ede8b3873227070b19cd7c7ef` |
| `refs/heads/feature/retry-policy` | `d13c784d66243541536833780676efba0d86042a` |
| `refs/heads/hotfix/1.2.1` | `69305d3a6d68e96388e91dcdde3447ea7042944f` |
| `refs/heads/main` | `96c39b55657285256dc37c2f43385dc564a654f1` |
| `refs/remotes/mirror/develop` | `8caad076eb6b22df3d1854065aa4df86dcc869fb` |
| `refs/remotes/mirror/feature/cache-warmup` | `03d41e4d28a0b0ccbd8f2ab30b581c2a450879c8` |
| `refs/remotes/mirror/feature/retry-policy` | `d13c784d66243541536833780676efba0d86042a` |
| `refs/remotes/mirror/hotfix/1.2.1` | `69305d3a6d68e96388e91dcdde3447ea7042944f` |
| `refs/remotes/mirror/main` | `cba733c406273a7abe5131c1259a52beba999df5` |
| `refs/tags/v0.9.0-rc1` | `518aac585f9a5f3220b0b504cb5df30edee0e99f` |
| `refs/tags/v1.0.0` | `769013b9f4a84795d101ca52157a07dbea36ea7b` |
| `refs/tags/v1.1.0` | `808da7c33e7ae9c4a01418296aedbe08c62e274e` |
| `refs/tags/v1.2.0` | `45628f3693a2a93bbe3570e21b871bf91d0b6acf` |
| `refs/tags/v1.2.1` | `bb11f51d295d4ace7c8eab9b7404adc0bfeb5c67` |
| `refs/tags/v1.3.0` | `493c34b0aa4c65d0a21d81db383cf35bb56f6ee0` |
| `refs/tags/v1.3.1` | `35e60b11842b491b815e3e98c835e7b23596609a` |
| `refs/tags/v1.4.0` | `24fda256be3109a82ee0d188786d72528b7630fe` |

## Retained recovery records

`original.tar` is the complete damaged repository as it existed before repair. Recovery scripts, reconstruction metadata, initial diagnostics, final reference and object inventories, and quarantined damaged pack files are retained here. They are not active Git objects or refs. The temporary verification checkout and generated source copies were removed after validation.
