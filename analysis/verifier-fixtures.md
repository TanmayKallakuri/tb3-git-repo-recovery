# Verifier mutation fixtures

Scratch repositories, each a fresh copy of `tests/original` changed in
exactly one way, graded by the real verifier (`tests/test.sh` inside the
verifier image, the artifact at `/app/repo.git` the way Harbor uploads it):
19 cases up to 1.2.1, and 25 since 1.2.2 added four legitimate configs and
two more rejected settings (the last section). Each case has a reward it
must get: every legitimate layout 1, every mutation 0.
`scripts/verifier-fixtures.sh` builds the image, runs every case
in its own container, prints the table and exits non-zero on any mismatch.
A verifier that fails to run (no reward file, `test.sh` exit 2, container
error) prints INFRA, never 0.
Every 0-case also names the check that must be among the failed checks, and a
0 for any other reason is reported as MISMATCH; the table prints the observed
failed set. The branch, tag and HEAD refs a mutation touches are discovered in
the copy at run time (`symbolic-ref HEAD`, `for-each-ref`), not hardcoded; a
missing ref makes the case INFRA.

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
The raw output of this run is `runs/verifier-fixtures/verifier-fixtures-1.0.0.log`
(the three raw logs are all in `runs/verifier-fixtures/`).

## What changed in the verifier

The isolation design is untouched: grading still runs on a checker-owned copy
whose config is the pinned `BARE_CONFIG` and whose indirections (alternates,
grafts, shallow, hooks, replace refs, commit-graph, multi-pack-index,
worktrees, promisor markers) have been removed. What changed is that the
root-held staged copy is now examined before it is cleaned, so what the
cleaning used to erase silently is recorded and graded.

1. **Config is parsed and checked.** `validate_config` reads the
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
   Version 1.2.2 replaced this allowlist with a denylist, after the second
   review showed that it rejected a correct repair; the parse, the size cap
   and the format-version and bare checks are unchanged (last section).
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

## Run of 2026-10-30 on the 1.1.0 original

The same 19 cases, graded again after the repository was regenerated for
task version 1.1.0 (commit `45ca827`: two losses with no local oracle, the
nightly mirror model, 610 reachable objects and 13 refs). The fixture
runner discovers the HEAD branch, a second branch and an annotated tag in
the copy at run time, so no case needed editing for the new original. The
verifier image digest changed because `tests/original/` is part of it.

| item | value |
|---|---|
| date | 2026-10-30 09:15 UTC |
| host | Windows 11, Docker Desktop 29.8.1 (Linux containers), Git Bash |
| verifier image | `grr-verifier-fixtures` `sha256:42e4d2d307d21ecda22b40609aa9a3f5ceebec93a18939ac87a0d86bfde1ad6e` |
| base image | `python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e` |
| git in the image | 2.39.5 |
| raw output | `runs/verifier-fixtures/verifier-fixtures-1.1.0.log` (the table below is copied from it) |

| case | expected | observed | status | must fail | failed checks (observed) |
|---|---|---|---|---|---|
| unchanged | 1 | 1 | PASS | - | - |
| repack | 1 | 1 | PASS | - | - |
| branch-moved | 0 | 0 | PASS | test_refs_restored | test_refs_restored |
| tag-deleted | 0 | 0 | PASS | test_refs_restored | test_refs_restored |
| remote-ref-added | 0 | 0 | PASS | test_no_history_rewrite | test_no_history_rewrite |
| replace-ref-added | 0 | 0 | PASS | test_no_history_rewrite | test_no_history_rewrite |
| notes-ref-added | 0 | 0 | PASS | test_no_history_rewrite | test_no_history_rewrite |
| loose-object-deleted | 0 | 0 | PASS | test_fsck_clean | test_fsck_clean, test_refs_restored, test_history_intact |
| blob-rewritten | 0 | 0 | PASS | test_fsck_clean | test_fsck_clean |
| config-invalid | 0 | 0 | PASS | test_artifact_staged | test_artifact_staged |
| config-hookspath | 0 | 0 | PASS | test_artifact_staged | test_artifact_staged |
| config-extensions | 0 | 0 | PASS | test_artifact_staged | test_artifact_staged |
| alternates | 0 | 0 | PASS | test_artifact_staged | test_artifact_staged |
| symlink | 0 | 0 | PASS | test_artifact_staged | test_artifact_staged, test_fsck_clean, test_refs_restored, test_history_intact, test_no_history_rewrite |
| grafts | 0 | 0 | PASS | test_artifact_staged | test_artifact_staged |
| shallow | 0 | 0 | PASS | test_artifact_staged | test_artifact_staged |
| promisor | 0 | 0 | PASS | test_artifact_staged | test_artifact_staged |
| config-bare-false | 0 | 0 | PASS | test_artifact_staged | test_artifact_staged |
| head-moved | 0 | 0 | PASS | test_refs_restored | test_refs_restored |

19 cases, 0 not as expected, exit 0. The observed failed sets are the same
as in the first run, case for case.

## Run of 2026-10-30 12:08 UTC on the final verifier

The same 19 cases, graded once more after `f29cadf` added the preflight
check of the damage manifest against the original, so the table below
is for the verifier code as finally committed (`f29cadf`), which 1.2.0 and
1.2.1 use unchanged.

| item | value |
|---|---|
| verifier image | `grr-verifier-fixtures` `sha256:22ba9fb2e88694bd3160fc696a7bf527be2c5c3dea1f2ef8cff971d170bb6d49` |
| base image | `python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e` |
| git in the image | 2.39.5 |
| verifier commit | `f29cadf` |
| raw output | `runs/verifier-fixtures/verifier-fixtures-final.log` |

| case                   | expected | observed | status   | must fail                | failed checks (observed) |
|------------------------|----------|----------|----------|--------------------------|--------------------------|
| unchanged              | 1        | 1        | PASS     | -                        | - |
| repack                 | 1        | 1        | PASS     | -                        | - |
| branch-moved           | 0        | 0        | PASS     | test_refs_restored       | test_refs_restored |
| tag-deleted            | 0        | 0        | PASS     | test_refs_restored       | test_refs_restored |
| remote-ref-added       | 0        | 0        | PASS     | test_no_history_rewrite  | test_no_history_rewrite |
| replace-ref-added      | 0        | 0        | PASS     | test_no_history_rewrite  | test_no_history_rewrite |
| notes-ref-added        | 0        | 0        | PASS     | test_no_history_rewrite  | test_no_history_rewrite |
| loose-object-deleted   | 0        | 0        | PASS     | test_fsck_clean          | test_fsck_clean,test_refs_restored,test_history_intact |
| blob-rewritten         | 0        | 0        | PASS     | test_fsck_clean          | test_fsck_clean |
| config-invalid         | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| config-hookspath       | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| config-extensions      | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| alternates             | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| symlink                | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged,test_fsck_clean,test_refs_restored,test_history_intact,test_no_history_rewrite |
| grafts                 | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| shallow                | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| promisor               | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| config-bare-false      | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| head-moved             | 0        | 0        | PASS     | test_refs_restored       | test_refs_restored |

19 cases, 0 not as expected, exit 0. The observed failed sets are the same
as in the two earlier runs, case for case.

## Run of 2026-10-30 18:03 UTC on the 1.2.0 original

The same 19 cases on the 1.2.0 original (task commit `0502a89`: the rebased
series, the heading-dated tag, the new D3 picks). The verifier code is the
one of `f29cadf`; only `tests/original`, `tests/damage.json` and
`tests/expected-refs.txt` changed. 1.2.1 changed none of the three, so this
run also stands for 1.2.1, the measured version.

| item | value |
|---|---|
| verifier image | `grr-verifier-fixtures` `sha256:e492946baae70a94ab6c616037e7ab6b2b093d39b36c763e326ff6c7b951fda7` |
| base image | `python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e` |
| git in the image | 2.39.5 |
| verifier commit | `f29cadf` (code); original of `0502a89` |
| raw output | `runs/verifier-fixtures/verifier-fixtures-1.2.0.log` |

| case                   | expected | observed | status   | must fail                | failed checks (observed) |
|------------------------|----------|----------|----------|--------------------------|--------------------------|
| unchanged              | 1        | 1        | PASS     | -                        | - |
| repack                 | 1        | 1        | PASS     | -                        | - |
| branch-moved           | 0        | 0        | PASS     | test_refs_restored       | test_refs_restored |
| tag-deleted            | 0        | 0        | PASS     | test_refs_restored       | test_refs_restored |
| remote-ref-added       | 0        | 0        | PASS     | test_no_history_rewrite  | test_no_history_rewrite |
| replace-ref-added      | 0        | 0        | PASS     | test_no_history_rewrite  | test_no_history_rewrite |
| notes-ref-added        | 0        | 0        | PASS     | test_no_history_rewrite  | test_no_history_rewrite |
| loose-object-deleted   | 0        | 0        | PASS     | test_fsck_clean          | test_fsck_clean,test_refs_restored,test_history_intact |
| blob-rewritten         | 0        | 0        | PASS     | test_fsck_clean          | test_fsck_clean |
| config-invalid         | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| config-hookspath       | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| config-extensions      | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| alternates             | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| symlink                | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged,test_fsck_clean,test_refs_restored,test_history_intact,test_no_history_rewrite |
| grafts                 | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| shallow                | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| promisor               | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| config-bare-false      | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| head-moved             | 0        | 0        | PASS     | test_refs_restored       | test_refs_restored |

19 cases, 0 not as expected, exit 0. The observed failed sets are the same
as in the three earlier runs, case for case.

## Run of 2026-10-31 01:18 UTC on the 1.2.2 verifier

The second review found the config check too strict. It appended `[core]`
`pager = cat` to a correctly repaired repository, and
`test_artifact_staged` failed, because `core.pager` was not on the
allowlist. The instruction sets no constraint on the config, and grading
never reads the submitted one: the graded copy gets the pinned
`BARE_CONFIG`. A check on that file exists only to catch settings that
would make the submitted repository behave unlike the graded copy, which
the replacement would otherwise hide, so it should name those settings and
accept the rest. An allowlist does the opposite. It has to anticipate
every benign key a repair might leave, from a pager or an identity to a
remote, and each one it misses turns a correct repair into a zero, while
the danger it guards against is a short, known list: keys that include
another file, define an alias, name a program, helper, command, path or
worktree, redirect ref or object lookup, or change the repository format.
No fixture had measured that cost, because the two legitimate cases left
the config as generated.

Version 1.2.2 (task commit `34e636b`) therefore holds the parsed keys to
a denylist in `tests/harness.py` (`REJECTED_SECTIONS`, `REJECTED_KEYS`,
`key_problem`): the sections `extensions`, `include`, `includeif`,
`alias`, `credential`, `filter`, `uploadpack` and `gpg`, and any key whose
final name is `program`, `command`, `driver`, `path`, `helper`,
`hookspath`, `fsmonitor`, `sshcommand`, `gitproxy`, `askpass`,
`alternaterefscommand`, `alternaterefsprefixes` or `worktree`. Everything
else stands: the 64 KiB cap, the parse by git as checker with
`--no-includes --list -z` away from every repository, the rejection of a
config git cannot parse, and `core.repositoryformatversion` 0 and
`core.bare` true in every occurrence. Six cases were added: four
legitimate configs that must score 1, and two rejected settings that must
fail `test_artifact_staged`, one a format change and one a lookup
redirection.

| case | change to the config | expected |
|---|---|---|
| config-pager | `[core]` `pager = cat` appended, as in the review | 1 |
| config-user-color | `user.name`, `user.email`, `color.ui` | 1 |
| config-pack-gc | `pack.window = 20`, `gc.auto = 0` | 1 |
| config-remote | `remote.backup.url` and `remote.backup.fetch` | 1 |
| config-objectformat-sha256 | `extensions.objectFormat = sha256` | 0, test_artifact_staged |
| config-alternaterefs | `core.alternateRefsCommand = /tmp/refs.sh` | 0, test_artifact_staged |

| item | value |
|---|---|
| date | 2026-10-31 01:18 UTC |
| verifier image | `grr-verifier-fixtures` `sha256:df45c17fd8b69c95f4e8fee7dbe735cf160b5311d7b23ac8c0cb16407727ecd6` |
| base image | `python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e` |
| git in the image | 2.39.5 |
| verifier commit | the harness committed as `34e636b`; the run preceded the commit by four minutes, and its log records no commit |
| raw output | `runs/verifier-fixtures/verifier-fixtures-1.2.2.log` |

| case                   | expected | observed | status   | must fail                | failed checks (observed) |
|------------------------|----------|----------|----------|--------------------------|--------------------------|
| unchanged              | 1        | 1        | PASS     | -                        | - |
| repack                 | 1        | 1        | PASS     | -                        | - |
| config-pager           | 1        | 1        | PASS     | -                        | - |
| config-user-color      | 1        | 1        | PASS     | -                        | - |
| config-pack-gc         | 1        | 1        | PASS     | -                        | - |
| config-remote          | 1        | 1        | PASS     | -                        | - |
| branch-moved           | 0        | 0        | PASS     | test_refs_restored       | test_refs_restored |
| tag-deleted            | 0        | 0        | PASS     | test_refs_restored       | test_refs_restored |
| remote-ref-added       | 0        | 0        | PASS     | test_no_history_rewrite  | test_no_history_rewrite |
| replace-ref-added      | 0        | 0        | PASS     | test_no_history_rewrite  | test_no_history_rewrite |
| notes-ref-added        | 0        | 0        | PASS     | test_no_history_rewrite  | test_no_history_rewrite |
| loose-object-deleted   | 0        | 0        | PASS     | test_fsck_clean          | test_fsck_clean,test_refs_restored,test_history_intact |
| blob-rewritten         | 0        | 0        | PASS     | test_fsck_clean          | test_fsck_clean |
| config-invalid         | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| config-hookspath       | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| config-extensions      | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| config-objectformat-sha256 | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| config-alternaterefs   | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| alternates             | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| symlink                | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged,test_fsck_clean,test_refs_restored,test_history_intact,test_no_history_rewrite |
| grafts                 | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| shallow                | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| promisor               | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| config-bare-false      | 0        | 0        | PASS     | test_artifact_staged     | test_artifact_staged |
| head-moved             | 0        | 0        | PASS     | test_refs_restored       | test_refs_restored |

25 cases, 0 not as expected, exit 0. The observed failed sets of the 19
earlier cases are the same as in the 1.2.0 run, case for case.

### Regrade of the saved 1.2.1 artifacts

The 1.2.2 verifier graded the artifact Harbor collected from each of the
eight 1.2.1 attempts and from the claude-code cheat trial
(`scripts/regrade-local.sh`, one container per trial, verifier commit
`34e636b`, image `grr-verifier-local`
`sha256:97f30f883698b2b66cd05820ae0363e90d4907808d5915f472ea7c44ebf8335c`,
2026-10-31 01:23 UTC). Raw output:
`runs/verifier-fixtures/regrade-1.2.2.log`.

| job | trial | recorded | 1.2.2 | failed checks (1.2.2, identical to the recorded ones) |
|---|---|---|---|---|
| run-codex-121 | EfjWeTS | 1 | 1 | - |
| run-codex-121 | ynnvZxs | 1 | 1 | - |
| run-codex-121 | sweKZhw | 0 | 0 | test_refs_restored |
| run-codex-121b | JqpXXzg | 1 | 1 | - |
| run-codex-121b | oj4orbL | 1 | 1 | - |
| run-claude-121 | w83Yrhe | 0 | 0 | test_refs_restored, test_history_intact |
| run-claude-121 | rfCGPva | 1 | 1 | - |
| run-claude-121 | qA8XRxY | 0 | 0 | test_refs_restored, test_history_intact |
| cheat-claude-121 | pHijg4V | 0 | 0 | test_refs_restored, test_history_intact |

9 trials, 0 not as expected, exit 0. All nine configs parsed to the same
six keys as the original's (`core.repositoryformatversion`,
`core.filemode`, `core.bare`, `core.logallrefupdates`,
`remote.mirror.url`, `remote.mirror.fetch`) with no problem, so
`test_artifact_staged` passed in all nine under both verifiers, and the
wider check moves no recorded grade. The three codex cheat runs left the
damaged repository untouched and are not in the regrade.
