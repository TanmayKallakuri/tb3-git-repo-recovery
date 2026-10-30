# Verifier mutation fixtures

Nineteen scratch repositories, each a fresh copy of `tests/original` changed in
exactly one way, graded by the real verifier (`tests/test.sh` inside the
verifier image, the artifact at `/app/repo.git` the way Harbor uploads it).
Each case has a reward it must get: the two legitimate layouts 1, every
mutation 0. `scripts/verifier-fixtures.sh` builds the image, runs every case
in its own container, prints the table and exits non-zero on any mismatch.
A verifier that fails to run (no reward file, `test.sh` exit 2, container
error) prints INFRA, never 0.

## Run of 2026-10-30

| item | value |
|---|---|
| date | 2026-10-30 08:44 UTC |
| host | Windows 11, Docker Desktop 29.8.1 (Linux containers), Git Bash |
| verifier image (after the fixes) | `grr-verifier-fixtures` `sha256:66923d5a709256a818e963eee51559a2fea8c207042028f898f5462cdbabaea1` |
| verifier image (committed harness, for contrast) | `grr-verifier-before` `sha256:b33c5120653be236c5963edc0884817a5cfd515645d327ff28787a9f12e67926` |
| base image | `python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e` |
| git in the image | 2.39.5 (the agent image has the same) |
| wall time | 1 min 31 s for the 19 cases |

The "before" column is the committed verifier (`a972b72`) graded on the same
cases with `VERIFIER_FIXTURES_TESTS` pointing at a copy of `tests/` holding
the old `harness.py` and `test_outputs.py`; the mutations and the image are
otherwise identical.

| case | mutation | expected | before | after | check that fails now |
|---|---|---|---|---|---|
| unchanged | none | 1 | 1 | 1 | - |
| repack | `git repack -a -d` | 1 | 1 | 1 | - |
| branch-moved | `feature/cache-warmup` moved to its parent | 0 | 0 | 0 | test_refs_restored |
| tag-deleted | `refs/tags/v1.2.0` deleted | 0 | 0 | 0 | test_refs_restored |
| remote-ref-added | `refs/remotes/injected/extra` at main's commit | 0 | **1** | 0 | test_no_history_rewrite |
| replace-ref-added | `refs/replace/<main>` at develop's commit | 0 | **1** | 0 | test_no_history_rewrite ("replacement refs present") |
| notes-ref-added | `refs/notes/commits` at main's commit | 0 | 0 | 0 | test_no_history_rewrite |
| loose-object-deleted | main's commit object (loose only) removed | 0 | 0 | 0 | test_fsck_clean, test_refs_restored, test_history_intact |
| blob-rewritten | a loose blob rewritten in place, same name | 0 | 0 | 0 | test_fsck_clean (hash-path mismatch) |
| config-invalid | `[core` appended to config | 0 | **1** | 0 | test_artifact_staged ("bad config line 9") |
| config-hookspath | `core.hooksPath = /tmp/hooks` | 0 | **1** | 0 | test_artifact_staged ("core.hookspath is not an allowed key") |
| config-extensions | `extensions.objectFormat = sha1` | 0 | **1** | 0 | test_artifact_staged ("not in an allowed section") |
| alternates | `objects/info/alternates` present | 0 | **1** | 0 | test_artifact_staged |
| symlink | `description` replaced by a symlink to `HEAD` | 0 | **1** | 0 | test_artifact_staged (not staged; the other four report "not run") |
| grafts | `info/grafts` present | 0 | **1** | 0 | test_artifact_staged |
| shallow | `shallow` present | 0 | **1** | 0 | test_artifact_staged |
| promisor | `.promisor` marker next to a pack | 0 | **1** | 0 | test_artifact_staged |
| config-bare-false | `core.bare = false` | 0 | **1** | 0 | test_artifact_staged ("core.bare must be true") |
| head-moved | `HEAD` at `refs/heads/develop` | 0 | 0 | 0 | test_refs_restored |

After: 19 cases, 0 not as expected, exit 0. Before: 11 mismatches, exit 1.
Per-case verifier output (reward, ctrf, reward-details, git logs) is in
`tmp/verifier-fixtures/<case>/`.

## What changed in the verifier

The isolation design is untouched: grading still runs on a checker-owned copy
whose config is the pinned `BARE_CONFIG` and whose indirections (alternates,
grafts, shallow, hooks, replace refs, commit-graph, multi-pack-index,
worktrees, promisor markers) have been removed. What changed is that the
root-held staged copy is now examined before it is cleaned, so what the
cleaning used to erase silently is recorded and graded.

1. **Config is parsed and allowlisted.** `validate_config` reads the
   submitted `config` (over 64 KiB fails), copies it next to an empty
   directory under `/run/verifier`, and runs `git config --file <copy>
   --no-includes --list -z` there as checker with the usual limits, so the
   parse touches no repository and follows no include. Every key is held to
   an explicit allowlist (`CORE_KEYS`, `PLAIN_SECTIONS`, `NAMED_SECTIONS`,
   `OPEN_SECTIONS` in `harness.py`); `*.program`, `*.command`, `*.driver`
   and `*.path` are refused in every section. `core.repositoryformatversion`
   must be present and `0`, `core.bare` present and true (`true`, `yes`,
   `on`, `1`, or set without a value), in every occurrence. The parsed keys
   and the verdict go into the stage report; `test_artifact_staged` fails
   with the parse error or the first offending keys. The config of
   `tests/original` and of `environment/repo.git` (byte-identical) lists six
   keys and passes, which the `unchanged` case confirms end to end.
2. **Refs are inventoried on disk before cleaning.** `disk_refs` walks
   `refs/` for regular files (`.lock` files skipped, as git does) and parses
   `packed-refs` (`^` peel lines and `#` lines skipped) on the root-held
   staged copy, without git. Any name under `refs/replace/` now fails
   `test_no_history_rewrite` with "replacement refs present" instead of being
   deleted unseen.
3. **Every ref name is compared with the original's.** `original_objects`
   runs `for-each-ref` with no prefix on the staged original; `compare_refs`
   takes the union of git's listing on the graded copy and the on-disk
   inventory and fails `test_no_history_rewrite` for any name the original
   never had, whatever its namespace. The `refs/remotes/` exemption
   (`ALLOWED_NAMESPACES`) is gone. A remote-tracking ref the original had
   and the artifact lacks is not a failure, because the instruction asks for
   the branches and tags, which are still compared exactly with their peeled
   ids.

Two smaller changes were needed for the required table: `copy_tree` with
`reject=True` now refuses a symlink or special file anywhere in the artifact
(it used to skip it and grade the rest), and `clean_repo` reports which of
the removed paths are `FORBIDDEN` (alternates, http-alternates, grafts,
shallow, `.promisor` markers), which fails `test_artifact_staged`. Hooks,
commit-graph, multi-pack-index and worktrees are still removed without
penalty: `git gc` and `git repack` write the first three in normal use.

## Running it

    scripts/verifier-fixtures.sh                 # all cases
    scripts/verifier-fixtures.sh symlink repack  # a subset

Needs Docker reachable from Git Bash (Windows) or bash (Linux); no bind
mounts, files travel with `docker cp`. The mutations are in
`scripts/verifier-fixtures/run-case.sh` (one `case` arm each) and
`scripts/verifier-fixtures/mutate.py` (object-level ones); they run inside
the verifier container with its own git, so the host's git and line endings
never touch a fixture.
