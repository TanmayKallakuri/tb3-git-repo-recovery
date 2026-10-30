# Results: every gate and trial for `git-repo-recovery`

Machine: Windows 11, Docker Desktop 29.8.1 (Linux VM, 16 CPUs, 15.3 GB),
Harbor `0.23.1.dev202609170426`, dockerfile-pin 1.5.0, upstream
`terminal-bench` at commit `7b1f530` (2026-10-28, the commit that added the
`check-lockfiles` static check). Commands run from the repository root in
Git Bash with `PYTHONUTF8=1` exported. Job directories under `jobs/` are
gitignored; trimmed copies (no `config.json`, no agent session state, home
paths redacted, JSON redacted structurally) live under `runs/`, rendered
byte for byte from the job directories by `scripts/trim-run.py`.

Two versions of the task were measured. Sections 1 to 7 cover the shipped
version, 1.1.0 (task commits `45ca827` and `719f13e`, oracle polish
`e8c602c`, verifier preflight `f29cadf`, which is the final task commit).
Sections 8 to 12 keep the measurements of version 1.0.0 as they were made;
they are evidence of the iteration, not of the shipped task.

## What changed since the external review

An external review of version 1.0.0 (2026-10-30) found the points in the
left column. Each one is mapped to what was done and where a reader can
check it.

| Finding | Change | Where to verify | Status |
|---|---|---|---|
| The central criterion failed: all six 1.0.0 trials passed | Task version 1.1.0: two losses whose ids are written nowhere in the repository (L1, the last commit of `feature/cache-warmup`; L2, the annotated tag `v1.4.0`), a nightly cron model for the mirror, witnesses removed from the instruction; commits `45ca827`, `719f13e`, `e8c602c` | Section 4 (damage table), section 6 (codex passed 3 of 3, claude-code passed 1 of 3 and failed 2), `SPEC.md` section 3, `tasks/git-repo-recovery/README.md` change log | NOT MET: codex 0 of 3 failed, claude-code 2 of 3 failed |
| Object ids act as a local oracle | For L1 and L2 no pack index, `packed-refs` line, reflog, patch header or other object holds the id, as a 7-hex prefix or in 20-byte binary form; the generator asserts this no-leak property on every build and builds byte-identically twice | `scripts/gen-repo/damage.py`, `scripts/gen-repo/check_damage.py`; `SPEC.md` section 3; the two failing claude-code attempts in section 6 (their own id census found 608 of 608 ids present and they stopped) | reduced, not removed: 2 of 53 items have no local oracle; the object id still checks the other 51 |
| The instruction listed the witnesses | The instruction states the end state only; repacks, reflogs, the mirror, the release script and the archived series are not named | `tasks/git-repo-recovery/instruction.md`, `SPEC.md` section 4 | fixed (`45ca827`) |
| One published `result.json` was invalid | `scripts/trim-run.py` redacts `.json` files structurally (parse, redact, re-serialise only when something changed), aborts on a file that does not parse, validates every published `.json`, and every run directory was re-rendered from its job so the committed files match the sources byte for byte; commit `4083042` | `scripts/trim-run.py` (module docstring), `runs/` | fixed (`4083042`) |
| `scripts/run-trials.sh run-codex` pointed at a missing config | `run-codex` points at `scripts/run-job-codex-2.json`; every mode exits 2 when its config file is absent; commit `4083042` | `scripts/run-trials.sh` lines 20 to 26 | fixed (`4083042`) |
| No raw static-check transcript committed | The 1.1.0 transcript is committed (`5402624`), rerun and recommitted at the final task commit (`4a2cb6a`) | `runs/static-checks/check-all-1.1.0.log` (section 1) | fixed (`5402624`, `4a2cb6a`) |
| Verifier: the submitted `config` was replaced silently | The submitted config is parsed as the unprivileged checker and checked against an explicit allowlist before the pinned grading config replaces it; an unparseable config or a key outside the allowlist fails `test_artifact_staged`; commit `16e1f1c` | `tests/harness.py` (`validate_config`); fixtures `config-invalid`, `config-hookspath`, `config-extensions`, `config-bare-false` in section 3 | fixed (`16e1f1c`) |
| Verifier: `refs/replace` was erased before the no-rewrite check | Ref names are inventoried from `refs/` and `packed-refs` before the indirections are removed, so a replace ref fails `test_no_history_rewrite`; commit `16e1f1c` | `tests/harness.py` (`disk_refs`); fixture `replace-ref-added` | fixed (`16e1f1c`) |
| Verifier: the `refs/remotes` namespace was exempt from the extra-ref check | Every ref name on the artifact, in any namespace, must exist in the original; commit `16e1f1c`. Also: symlinks and special files anywhere in the artifact, alternates, grafts, shallow and promisor markers fail staging; root-side faults raise an infrastructure error and never a reward, while errors the artifact provokes (over-long names, loops, collisions) grade 0 and never become infrastructure errors; commits `b94763b`, `792672f` | `tests/harness.py` (`compare_refs`, `copy_tree`, `clean_repo`); fixtures `remote-ref-added`, `notes-ref-added`, `symlink`, `alternates`, `grafts`, `shallow`, `promisor`; `analysis/verifier-fixtures.md` | fixed (`16e1f1c`, `b94763b`, `792672f`) |
| Cheat wording overstated: zero reward presented as robustness | README, RESULTS and `analysis/trajectories.md` describe the cheat trials as the required zero rewards and point to the mutation fixtures for robustness evidence; commit `4083042` | Sections 7 and 12; `analysis/verifier-fixtures.md` | fixed (`4083042`) |

## 1. Static checks (CI: `static-checks.yml`, 29 checks), version 1.1.0

Command:

```bash
bash scripts/check-all.sh tasks/git-repo-recovery
```

Run twice: at 09:19 UTC on task commit `719f13e` (transcript committed as
`5402624`) and at 11:49 UTC on the final task commit `f29cadf`, after the
verifier preflight change of section 5 (committed as `4a2cb6a`). Both:
**29 passed, 0 warned, 0 failed of 29**, upstream `7b1f530`. The committed
transcript is the second run, `runs/static-checks/check-all-1.1.0.log`
(home directory redacted, every other line as printed, exit 0 recorded on
the last line).

## 2. Oracle and nop (CI: the `/validate` job), version 1.1.0

Launched by `scripts/run-hardened.sh gates`, which runs:

```bash
harbor run -p tasks/git-repo-recovery -a oracle --env docker --yes --job-name gate-oracle-h
harbor run -p tasks/git-repo-recovery -a nop --env docker --yes --job-name gate-nop-h
```

| Job | Trial | Reward | Exceptions | Total (UTC, 2026-10-30) | Notes |
|---|---|---|---|---|---|
| `gate-oracle-h` | `git-repo-recovery__T5RFqnC` | **1.0** | 0 | 09:15:43 to 09:16:24 | 5 of 5 checks passed; verifier 0.4 min, Harbor end to end |
| `gate-nop-h` | `git-repo-recovery__ASmMsCy` | **0.0** | 0 | 09:16:44 to 09:17:20 | `test_fsck_clean`, `test_refs_restored`, `test_history_intact` fail (9 refs absent, rev-list dies on the damaged pack entries and corrupt loose objects); `test_artifact_staged` and `test_no_history_rewrite` pass |
| `gate-oracle-h2` | `git-repo-recovery__u8q8U2r` | **1.0** | 0 | 09:31:09 to 09:31:45 | rerun after the oracle polish in `e8c602c` (pinned replay environment, fatal check when a release stays untagged); 5 of 5 |
| `gate-oracle-h3` | `git-repo-recovery__ZBVUAoo` | **1.0** | 0 | 11:49:22 to 11:50:09 | rerun on the final task commit `f29cadf`, after the verifier preflight of section 5; 5 of 5 |
| `gate-nop-h3` | `git-repo-recovery__rQutkJh` | **0.0** | 0 | 11:49:22 to 11:50:06 | same rerun; the same three checks fail, the same two pass |

`scripts/run-hardened.sh` hard-codes the `-h` job names, so the reruns used
explicit names. The hand-launched jobs were run from the repository root
with `export PYTHONUTF8=1`:

```bash
harbor run -p tasks/git-repo-recovery -a oracle --env docker --yes --job-name gate-oracle-h2
harbor run -p tasks/git-repo-recovery -a oracle --env docker --yes --job-name gate-oracle-h3
harbor run -p tasks/git-repo-recovery -a nop --env docker --yes --job-name gate-nop-h3
```

`rubric-review-h2` (section 5) was launched by hand the same way:

```bash
python3 scripts/rubric-review/stage.py tasks/git-repo-recovery tmp/rubric-review
harbor run -p tmp/rubric-review -a claude-code -m claude-sonnet-5 --agent-setup-timeout-multiplier 3 --env-file "$HOME/.harbor/claude.env" --ae 'CLAUDE_CODE_OAUTH_TOKEN=${CLAUDE_CODE_OAUTH_TOKEN}' --env docker --yes --job-name rubric-review-h2
```

Trimmed copies: `runs/gate-oracle-h/`, `runs/gate-nop-h/`, `runs/gate-oracle-h2/`,
`runs/gate-oracle-h3/`, `runs/gate-nop-h3/`.

## 3. Verifier mutation fixtures, version 1.1.0

`scripts/verifier-fixtures.sh` grades 19 scratch repositories, each a copy
of `tests/original` changed in exactly one way, with the real verifier in
its own container, and requires the reward each case must get and the
check that must fail. The two legitimate layouts (unchanged, repacked)
must score 1; the seventeen mutations (moved branch, deleted tag, refs
added under `refs/remotes`, `refs/replace` and `refs/notes`, a deleted and
a rewritten object, four config mutations, alternates, a symlink, grafts,
shallow, a promisor marker, HEAD moved) must score 0 on the named check.

| Run | Original | Result |
|---|---|---|
| 2026-10-30 08:44 UTC | 1.0.0 | 19 of 19 as expected; the committed 1.0.0 verifier (`a972b72`) graded on the same cases accepted 11 of the 17 mutations |
| 2026-10-30 09:15 UTC | 1.1.0 (regenerated original) | 19 of 19 as expected, exit 0 |
| 2026-10-30 12:08 UTC | 1.1.0, final verifier (`f29cadf`, with the manifest preflight) | 19 of 19 as expected, exit 0 |

Raw logs: `runs/verifier-fixtures/verifier-fixtures-1.0.0.log`,
`runs/verifier-fixtures/verifier-fixtures-1.1.0.log` and
`runs/verifier-fixtures/verifier-fixtures-final.log`. All three tables,
with the verifier image digests, are in `analysis/verifier-fixtures.md`. The third run is on the verifier as
shipped, after `f29cadf` (section 5) added the preflight of the damage
manifest against the original.

## 4. Ground truth and the damage, version 1.1.0

The original repository and the damage are generated deterministically by
`scripts/gen-repo/` inside a container with the task images' git; the
build was repeated and produced byte-identical files. Every timestamp
before the tail of the history is frozen, so both packfiles and the
victims of D1, D2, D4, D5 and D6 are the 1.0.0 ones
(`scripts/gen-repo/frozen-victims.txt`, checked by `verify.sh`); the D3
picks changed because they are chosen among loose objects and the tail
added some. The generator records every item and its intended recovery
path in `tests/damage.json` (never in the agent image).

Sizing: 610 reachable objects, 158 commits, 13 refs (5 branches, 8 tags)
in the original; 53 damage items in 11 classes (46 objects counting the
deleted pack index, 9 lost refs; L1 and L2 each count once).

| Class | Damage | Items | Intended recovery |
|---|---|---|---|
| D1 | pack-B entries zeroed, intact copies in pack-A | 20 | read pack-A |
| D2 | pack-B delta bases zeroed, 6 dependents intact only in pack-B | 3 (+6) | base from pack-A, apply pack-B's delta |
| D3 | loose objects with one altered zlib byte | 6 | checksum-guided single-byte search |
| D4 | the three archived 1.2 patch commits with their trees and blobs, zeroed, no copy | 13 | rebuild from `docs/patches/*.patch`, committer = author; the From lines carry the ids |
| D5 | `docs/API.md` blob of v1.3.0, zeroed, no copy | 1 | regenerate with the tree's `tools/gen_api_docs.py` |
| D6 | pack-A index deleted | 1 | `git index-pack` |
| R1 | loose ref of `develop` deleted, reflog intact | 1 | reflog |
| R2 | `feature/retry-policy` ref and reflog deleted | 1 | `refs/remotes/mirror/feature/retry-policy` (equal to the tip: no change after the last nightly) |
| R3 | `packed-refs` truncated (annotated `v1.2.0`, `v1.3.0`; lightweight `v1.2.1`, `v1.3.1`), loose `hotfix/1.2.1` deleted | 5 | tag objects; reflog; release commit pinned by `VERSION`, `CHANGELOG.md` and later `git describe` strings |
| L1 | the last commit of `feature/cache-warmup` (made after the last nightly push), its ref and its reflog; tree and blobs left dangling; the id appears nowhere | 1 | `docs/patches/cache-warmup/series` and its second patch (zero commit ids): apply on the commit the mirror holds, committer = author, date from the header; the tree must be the one dangling tree |
| L2 | the annotated tag object `v1.4.0` and its ref; the id appears nowhere; tags have no reflog and are not mirrored | 1 | `tools/release.sh` as of the release commit (v2: full CHANGELOG section as the message, tagger and date from the release commit); v1 made the surviving tags, v3 at the tip is one-line and says so |

What makes L1 and L2 different from everything else: a wrong
reconstruction of either passes `git fsck --full --strict` and every
check an agent can run locally, and only the hidden original rejects it.
Restoring `feature/cache-warmup` at the mirror's value, or tagging 1.4.0
with a one-line message, is exactly such a wrong reconstruction. The
mirror is a simulated nightly cron (15 pushes at 02:00 UTC, documented in
`docs/operations.md` in the tree and visible in the mirror reflogs), so
every mirror ref equals its branch at the last nightly.

## 5. Implementation rubric (CI: the hosted `/review` job), version 1.1.0

Staged by `scripts/rubric-review/stage.py` the way upstream's
`stage_task.py` does and launched by `scripts/run-hardened.sh rubric`
(reviewer `claude-code` with the CI reviewer model named `claude-sonnet-5`,
see section 11 for why the provider prefix is dropped).

| Job | Trial | Time (UTC, 2026-10-30) | Verdicts |
|---|---|---|---|
| `rubric-review-h` | `rubric-review__JJjxRBk` | 10:11:59 to 10:18:22 | **33 pass, 1 fail, 3 not applicable** |
| `rubric-review-h2` | `rubric-review__2qLU29t` | 11:49:23 to 11:54:22 | **34 pass, 0 fail, 3 not applicable** |

First run, on the task directory before `f29cadf`: the one failing
criterion was `no_extraneous_files`, because `tests/damage.json`, the
generator's manifest of every damaged item and its intended recovery path,
was read by nothing in the task. Response, commit `f29cadf`: the verifier's
preflight now checks that manifest against the original before grading,
every listed object id present in the original and every lost ref present
in `tests/expected-refs.txt` (81 ids and 9 refs), so the file has a role in
the task. Second run, on `f29cadf`: 34 pass, 0 fail. The three criteria
not applicable in both runs are `structured_data_schema` (the deliverable
is a repository state), `artifact_efficiency` and `score_provenance`
(every check is boolean). Verdicts:
`runs/rubric-review-h/rubric-review__JJjxRBk/artifacts/app/verdicts.json`
and `runs/rubric-review-h2/rubric-review__2qLU29t/artifacts/app/verdicts.json`.
In both runs the reviewer ran the reference solution against the damaged
repository itself and confirmed a clean fsck, the exact ref and HEAD match
and the exact reachable set.

The 1.0.0 review (35 pass, 0 fail, 2 not applicable on the second
complete run) is in section 11.

## 6. Trials (`/run`, 3 attempts per agent) and cheat trials (`/cheat`), version 1.1.0

All attempts use the CI defaults (`.github/harbor-run-defaults.yml` at
upstream `7b1f530`): codex `openai/gpt-6-astra` at `reasoning_effort=xhigh`,
claude-code `anthropic/claude-fable-5-1` at `reasoning_effort=max` with
`CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000`. Subscriptions, no API keys; the
agent-setup allowance tripled (section 12 records why). Launched by
`scripts/run-hardened.sh`, one stage at a time so that the calibration
rule holds (one attempt per agent before any further trial is spent):
`gates`, `pilot-codex`, `pilot-claude`, then `rest-codex` and
`rest-claude` in two processes, `cheats`, `rubric`. Every trial here was
graded by Harbor end to end.

Provenance: the pilots ran on task commit `719f13e` and the remaining
attempts and the cheats on `e8c602c`. The only later changes before the
shipped `f29cadf` were to `solution/recover.py` (replay environment
pinning) and `tests/preflight.py` (manifest check), neither visible to the
agent, so the trials are valid for the shipped task; the gates and the
rubric were rerun on `f29cadf`.

| Agent | Job / trial | Reward | Agent phase | Tool calls | Tokens in (cached) / out | Grade route |
|---|---|---|---|---|---|---|
| codex, attempt 1 | `pilot-codex-h` / `git-repo-recovery__m9wqtVr` | **1.0** | 7.4 min | 14 | 924k (855k) / 12k | Harbor, 5 of 5 checks |
| codex, attempt 2 | `run-codex-h` / `git-repo-recovery__FDY3d3q` | **1.0** | 7.1 min | 17 | 1.08M (1.01M) / 12k | Harbor, 5 of 5 checks |
| codex, attempt 3 | `run-codex-h` / `git-repo-recovery__wjs6dMz` | **1.0** | 5.6 min | 14 | 984k (904k) / 11k | Harbor, 5 of 5 checks |
| claude-code, attempt 1 | `pilot-claude-h` / `git-repo-recovery__w2hS6QT` | **0.0** | 22.9 min | 39 | 4.46M (4.28M) / 100k | Harbor, 3 of 5: `test_refs_restored`, `test_history_intact` fail |
| claude-code, attempt 2 | `run-claude-h` / `git-repo-recovery__CMQWEQW` | **0.0** | 25.0 min | 45 | 6.43M (6.23M) / 102k | Harbor, 3 of 5: `test_refs_restored`, `test_history_intact` fail |
| claude-code, attempt 3 | `run-claude-h` / `git-repo-recovery__kLSoSqt` | **1.0** | 24.8 min | 38 | 4.41M (4.21M) / 109k | Harbor, 5 of 5 checks |
| claude-code + hack prompt | `cheat-claude-h` / `git-repo-recovery__AZor9ML` | **0.0** | 1.2 min | 4 | 179k (133k) / 4k | Harbor, 2 of 5: the untouched repository's three checks fail |
| codex + hack prompt | `cheat-codex-h` / `git-repo-recovery__TBSMyN8` | **0.0** | 0.2 min | 0 | none recorded | Harbor, 2 of 5; `AgentSafetyRefusalError` recorded |

Timings (UTC, 2026-10-30, whole trial including builds and verifier):
`pilot-codex-h` 09:18:26 to 09:29:12; `pilot-claude-h` 09:18:27 to
09:45:09; `run-codex-h` 10:11:59 to 10:23:00 and 10:23:00 to 10:31:19;
`run-claude-h` 10:11:59 to 10:40:48 and 10:40:48 to 11:08:04;
`cheat-claude-h` 11:46:25 to 11:50:42; `cheat-codex-h` 11:50:48 to
11:53:18. The two agents' remaining attempts ran in two processes at the
same time (`rest-codex`, `rest-claude`), each agent's attempts one after
the other. Trimmed copies with trajectory, console log, artifact and
verifier output are under `runs/<job>/`; the numbers come from
`python3 scripts/summarize-trial.py <job>`.

What the codex pilot did: inventoried both packs with its own parser
(index CRCs against the pack bytes), wrote every intact entry out and
recombined the delta dependents with their pack-A bases, repaired the six
corrupt loose objects by single-byte search, rebuilt the three archived
1.2 commits with `git mailinfo`, `git apply --cached` and `write-tree` and
commit objects with committer equal to author, regenerated `docs/API.md`
at every release commit with the tree's generator, then read
`tools/archive-series.sh`, `tools/release.sh`, the cache-warmup series
and `CHANGELOG.md` at HEAD and `tools/release.sh` as of the 1.4.0 release
commit (`git show <release commit>:tools/release.sh`). It replayed the
cache-warmup series on the merge base, checked that the first patch
reproduces the mirror's commit and that the second patch's tree is the one
dangling tree, and made the branch point at the rebuilt commit; it built
the `v1.4.0` tag object the way the v2 script specifies (tagger from the
release commit, `orbit v1.4.0`, the bullet lines of the CHANGELOG
section) with `git mktag`; it placed the lightweight tags on the
`Release v1.2.1` and `Release v1.3.1` commits after listing every release
commit with its `VERSION` content, and wrote all nine refs in one
`update-ref --stdin` transaction after asserting none existed. Before
finishing it checked that `format-patch --no-thread --zero-commit
--no-signature` from the restored tip reproduces the archived series byte
for byte and that fsck is clean with no unreachable objects. Both hidden
targets were right.

What the claude-code pilot did: the same salvage (own pack parser,
single-byte repair, the 1.2 series by hash, `docs/API.md` by hash), and
then more than was needed: it re-implemented git's delta encoder,
validated it against all 300 intact deltas, and rewrote the zeroed
payloads so the damaged pack's trailer checksum recomputed to the original
value. It restored four refs: `develop` and `hotfix/1.2.1` from their
reflogs, `v1.2.0` and `v1.3.0` from the dangling tag objects. Its own
census found every one of the 608 ids the damaged repository names
readable, fsck was clean, and it stopped. Five refs were missing:
`feature/cache-warmup` (L1), `v1.4.0` (L2), `feature/retry-policy` (R2,
the mirror route), `v1.2.1` and `v1.3.1` (R3, the describe-string route);
9 of the original's 610 reachable objects are not reachable from the
expected refs (the L1 commit with its root tree, subtree and blob, the L2
tag object, and the four objects only the lost branch's earlier commit
reaches). It had read the mirror's refs and reflogs, the cache-warmup
series file and both patches, and had listed the dangling tree, and its
final message says it left the feature branches and the series alone on
purpose, because the reflogs record no local `feature/*` branch and the
second patch "never existed" in the repository. It never read `VERSION`,
`CHANGELOG.md`, `tools/release.sh` or `docs/operations.md`, and never ran
`git describe`; in every 1.0.0 attempt, when the instruction named the
mirror and the release script, it did. That is a task failure, not an
infrastructure one: the agent phase completed, the artifact was collected
and graded, and the verifier's reasons are in
`runs/pilot-claude-h/git-repo-recovery__w2hS6QT/verifier/`. The
step-by-step account is in `analysis/trajectories.md`.

What attempts 2 and 3 did. Codex (`FDY3d3q`, `wjs6dMz`): the same route
as the pilot, in 7.1 and 5.6 minutes: the tooling read including
`tools/release.sh` as of the 1.4.0 release commit, the cache-warmup series
replayed on the mirror's commit, the tag built from the v2 script with
`git mktag`; each said before its ref step that the archive records a
commit newer than the mirror's tip and that the preserved release script
gives the tag format. Both hidden targets right; the first left its
scripts and a recovery report under `recovery/` inside the repository,
the second outside it. Claude-code attempt 2 (`CMQWEQW`)
stopped the way the pilot did: fsck clean, 608 of 608 ids present by its
own census, four refs restored, and a final message that says it created
no ref without evidence, the mirror's feature branches having no local
reflog and the point releases `v1.2.1`, `v1.3.1` and `v1.4.0` having left
no tag object or ref trace; it had read the series file, both cache-warmup
patches, the release script, `VERSION` and `CHANGELOG.md` at v1.3.0, and
had identified the dangling tree as the archived "cache size limit" state,
which it called never pushed. The same five refs were missing and the same
9 objects unreachable as in the pilot. Claude-code attempt 3 (`kLSoSqt`)
read the three versions of `tools/release.sh` including the one as of the
1.4.0 release commit, listed the `VERSION` blob at every release commit,
checked the second cache-warmup patch's tree against the dangling tree
with `diff-tree`, established the committer-equals-author convention by
searching committer timestamps for the three 1.2 commits (every hit at
offset zero), rebuilt the L1 commit and the L2 tag, placed the lightweight
tags on the release commits using the release script's rule and the
describe strings in `VERSION`, and repacked everything into one pack;
its final message names the two refs that rest on reconstruction rather
than hash verification. Step by step in `analysis/trajectories.md`.

Cheat trials (hack prompt appended, 1 per agent). `cheat-claude-h`
(`AZor9ML`): 1.2 minutes, four tool calls, all inventory; the run was
stopped by a safety classifier at step 6 (stop_reason refusal), after its
inventory steps, and the agent then declined the brief. `cheat-codex-h` (`TBSMyN8`): 0.2
minutes, no tool call; the provider's safeguard rejected the turn and
Harbor recorded `AgentSafetyRefusalError`, then ran the verifier. Both
repositories are byte-identical to the shipped damaged one (`diff -rq`),
which grades 0 on `test_fsck_clean`, `test_refs_restored` and
`test_history_intact`. The zero rewards are the required numerical
outcome; neither run exercised the verifier; evidence that the verifier
rejects bypass attempts is the fixture set in section 3.

### Final results, version 1.1.0

| Agent (CI defaults) | Attempts | Passed | Failed | Agent phase per attempt | Cheat trial |
|---|---|---|---|---|---|
| codex `openai/gpt-6-astra`, `xhigh` | 3 | **3** (`m9wqtVr`, `FDY3d3q`, `wjs6dMz`) | 0 | 7.4, 7.1, 5.6 min | 0.0 (`TBSMyN8`; verifier not exercised) |
| claude-code `anthropic/claude-fable-5-1`, `max` | 3 | **1** (`kLSoSqt`) | **2** (`w2hS6QT`, `CMQWEQW`; the same five refs missing in both) | 22.9, 25.0, 24.8 min | 0.0 (`AZor9ML`; verifier not exercised) |

No infrastructure error occurred in the 1.1.0 trials; every attempt's
agent phase completed and every one was graded by Harbor.

## 7. Reading against the brief, version 1.1.0

The brief asks for three attempts per agent that genuinely fail, with the
task still correct, deterministic and cheap, and cheat trials at zero.

- Correct, deterministic, cheap: the oracle passes (three times, section
  2), the nop fails on the right checks, the static checks are 29 of 29
  twice with the transcript committed, the rubric review passes every
  applicable criterion on the final task commit (section 5), the verifier
  rejects all seventeen mutations and accepts both legitimate layouts
  (section 3), the repository builds byte-identically, and the six
  attempts cost 5.6 to 25.0 minutes of agent time on subscriptions.
- Codex: 3 of 3 passed, in 7.4, 7.1 and 5.6 minutes. No failure.
- Claude-code: attempts 1 and 2 failed (reward 0.0, Harbor-verified), both
  on exactly the elements that have no local oracle (L1, L2) and the
  witnesses the instruction no longer names (the mirror route, the
  describe-string route), with the same five refs missing; attempt 3
  passed in 24.8 minutes after reading the release script as of the
  release commit and replaying the archived series.
- Cheat trials: 0.0 and 0.0, the required numerical outcome. Neither run
  exercised the verifier (section 6); evidence that the verifier rejects
  bypass attempts is section 3.

Final verdict against the brief: **not met**. The requirement of three
genuine failures per agent is not met for codex at all (three passes) and
for claude-code two of three (two failures, one pass). What 1.1.0 did
achieve, and 1.0.0 did not: two genuine, verifier-confirmed failures of a
frontier agent at its CI settings, each on exactly the oracle-free elements
and the de-listed witnesses, with the task still correct, deterministic
and cheap, and with codex's three passes showing that the repository's own
evidence is sufficient to solve it in under eight minutes.

## Previous version 1.0.0 (superseded)

Sections 8 to 12 are the measurements of version 1.0.0 (task commit
`a972b72` with the rubric fixes of `7d7e6ac`), kept with their numbers
unchanged. Trimmed copies of every 1.0.0 job remain under `runs/`. The
six passing trials and the two zero-reward cheat trials are the evidence
that drove the 1.1.0 redesign; they say nothing about the shipped task.

## 8. Static checks (CI: `static-checks.yml`, 29 checks), version 1.0.0

Command:

```bash
bash scripts/check-all.sh tasks/git-repo-recovery
```

Result (2026-10-29, on the 1.0.0 task directory): **29 passed, 0 warned,
0 failed of 29.** Both images install only apt packages or a committed
`uv.lock`, so the new `check-lockfiles` check passes; the ground-truth
files under `tests/` carry the canary line the canary check requires. No
raw transcript of this run was committed; the 1.1.0 transcript in section
1 is the committed one.

| Check | Result |
|---|---|
| Canary strings, No cheat directory, Dockerfile refs, Image digest pins, Dependency lockfiles, Dockerfile sanity, Dockerfile platform | PASS |
| Absolute paths, Test refs, test.sh sanity, Task fields, Task fix changelog, Task timeout cap | PASS |
| Instruction suffix, Instruction headings, GPU types, Resource sizes, Allow internet, No internet opt-in | PASS |
| Task slug length, Task package name, Separate verifier, Verifier tooling baked, Trial network fetch | PASS |
| Pip pinning, Pytest version pin, Nproc usage, CPU parallelism advisory, Compose volumes | PASS |

## 9. Oracle and nop (CI: the `/validate` job), version 1.0.0

Commands:

```bash
harbor run -p tasks/git-repo-recovery -a oracle --env docker --yes --job-name gate-oracle-2
harbor run -p tasks/git-repo-recovery -a nop --env docker --yes --job-name gate-nop-2
```

| Job | Trial | Reward | Exceptions | Verifier (UTC) | Notes |
|---|---|---|---|---|---|
| `gate-oracle-2` | `git-repo-recovery__RJLMpZQ` | **1.0** | 0 | 2026-10-29 19:27:48 to 19:28:10 | 5 of 5 checks passed: fsck clean, 12 refs and HEAD identical, 579 reachable objects identical, no extra refs; under a second of git work |
| `gate-nop-2` | `git-repo-recovery__Xqe8i2w` | **0.0** | 0 | 2026-10-29 19:28:46 to 19:29:10 | `test_fsck_clean`, `test_refs_restored` and `test_history_intact` fail as expected (8 refs absent, every rev-list dies on a damaged pack entry); the other two pass |
| `gate-nop-3` | `git-repo-recovery__Xd8qmr2` | **0.0** | 0 | 2026-10-30 02:52:41 to 02:53:16 | rerun after the Docker Desktop restart described in section 12, to confirm Harbor again runs the verifier end to end; the same three checks fail, the same two pass; 35 s for the whole job |

An earlier pair (`gate-oracle-1` / `gate-nop-1`, 19:17) passed the same
way on the repository before the leak fix of section 10. They were the
pre-regeneration gates, and their directories were not kept under `runs/`;
`gate-oracle-2` and `gate-nop-2` are the kept 1.0.0 gates.

## 10. Ground truth and the damage, version 1.0.0

The 1.0.0 repository had 579 reachable objects and 12 refs (5 branches, 7
tags); 43 damaged or lost objects plus the pack-A index, and 8 lost refs.
The classes below are the 1.0.0 ones; the 1.1.0 table is section 4.

| Class | Damage | Items | Intended recovery |
|---|---|---|---|
| D1 | pack-B entries zeroed, intact copies in pack-A | 20 | read pack-A |
| D2 | pack-B delta bases zeroed, 6 dependents intact only in pack-B | 3 (+6) | base from pack-A, apply pack-B's delta |
| D3 | loose objects with one altered zlib byte | 6 | checksum-guided single-byte search |
| D4 | the three archived patch commits with their trees and blobs, zeroed, no copy | 13 | rebuild from `docs/patches/*.patch`, committer = author |
| D5 | `docs/API.md` blob of v1.3.0, zeroed, no copy | 1 | regenerate with the tree's `tools/gen_api_docs.py` |
| D6 | pack-A index deleted | 1 | `git index-pack` |
| R1 | loose refs of `develop`, `feature/cache-warmup` deleted, reflogs intact | 2 | reflog |
| R2 | `feature/retry-policy` ref and reflog deleted | 1 | `refs/remotes/mirror/feature/retry-policy` |
| R3 | `packed-refs` truncated (annotated `v1.2.0`, `v1.3.0`; lightweight `v1.2.1`, `v1.3.1`), loose `hotfix/1.2.1` deleted | 5 | tag objects; reflog; release commit pinned by `VERSION`, `CHANGELOG.md` and later `git describe` strings |

A review before any trial found that `info/refs`, the stale server-info
listing git writes on repack, still named every lost ref with its id; the
damage step now removes it (and `objects/info/packs`) and the generator
asserts that no file outside `objects/`, `logs/` and `refs/remotes/`
contains a lost ref's name or id, and that each lightweight tag's release
commit is the only candidate consistent with the later describe strings
(`git rev-list --count` against the described commit). The oracle never
read those files. Everything is regenerated deterministically: three
generations produced byte-identical files.

## 11. Implementation rubric (CI: the hosted `/review` job, `claude-code` with `anthropic/claude-sonnet-5`, 37 criteria), version 1.0.0

Staged the way upstream's `terminal-bench/scripts/review/stage_task.py` does, by `scripts/rubric-review/stage.py` (the task
under review at `/app/task-under-review/`, the rubric at `/app/rubric.toml`,
the reviewer template as the instruction, a verifier that only checks
`verdicts.json` exists). Command:

```bash
python3 scripts/rubric-review/stage.py tasks/git-repo-recovery tmp/rubric-review
harbor run -p tmp/rubric-review -a claude-code -m anthropic/claude-sonnet-5 --env-file ~/.harbor/claude.env --ae 'CLAUDE_CODE_OAUTH_TOKEN=${CLAUDE_CODE_OAUTH_TOKEN}' --env docker --yes --job-name rubric-review-1
```

First run (`rubric-review-1`, 2026-10-29 19:29 to 19:34 UTC, trial
`rubric-review__dqZFNnb`): **33 pass, 2 fail, 2 not applicable**
(`runs/rubric-review-1/rubric-review__dqZFNnb/artifacts/app/verdicts.json`). The reviewer rated the difficulty
"deep git internals expertise ... well beyond what an average
undergraduate could do in a few days", the task "not a standard textbook
git exercise", and the anti-cheat design sound (content-addressed ids,
the original only in the verifier image, the artifact cleaned of
alternates, hooks, replace refs and promisor markers before grading).

| Criterion | Reviewer's finding | Change |
|---|---|---|
| `difficulty_explanation_quality` | The explanation did not say who does this work in the real world or whether the repository is synthetic. | Two sentences added: git-hosting engineers and data-recovery contractors; synthetic history made by git itself, one route back per loss. |
| `task_readme` | `Relevant experience` is the `TODO(Tanmay)` placeholder. | Paragraph written; the review was rerun on the 1.0.0 task directory (below). |

Not applicable: `structured_data_schema` (the deliverable is a repository
state) and `score_provenance` (every check is boolean).

Second run. `rubric-review-2` (2026-10-30 03:54 UTC) did no review: the
agent image installed Claude Code 2.1.314 (the first run had 2.1.312),
and that version passed the model name `anthropic/claude-sonnet-5`
through unchanged, which the API answered with `model_not_found`; the
verifier found no `verdicts.json` and scored 0. The review was repeated as
`rubric-review-3` with the model named `claude-sonnet-5`, the same model
the first run resolved to.

Third run (`rubric-review-3`, 2026-10-30 04:00 to 04:05 UTC, trial
`rubric-review__WueLwQh`, on the 1.0.0 task directory): **35 pass, 0 fail,
2 not applicable** (`runs/rubric-review-3/rubric-review__WueLwQh/artifacts/app/verdicts.json`). The two criteria that
failed the first time now pass: the reviewer found the difficulty
explanation names the practitioner and the synthetic origin, and the
README's `Relevant experience` section present. The reviewer again ran
the reference solution against the 1.0.0 repository and confirmed the
579-object reachable set and every ref matched the original.

## 12. Trials (`/run`) and cheat trials (`/cheat`), version 1.0.0

### Calibration: one codex attempt before anything else

Command (`scripts/calib-job-codex.json`: codex `openai/gpt-6-astra`,
`reasoning_effort=xhigh`, one attempt, the CI defaults; auth via
`CODEX_FORCE_AUTH_JSON=1` in the process environment):

```bash
harbor run -c scripts/calib-job-codex.json --env docker --yes --job-name calib-codex-1
```

| Job | Trial | Agent | Outcome |
|---|---|---|---|
| `calib-codex-1` | `git-repo-recovery__fMzUFjy` | codex / gpt-6-astra xhigh | **Completed, reward 1.0**: 5.8 min of agent time, 12 tool calls, 747k input tokens (689k cached) / 11k output, no exception. |

What it did (`runs/calib-codex-1/`): inventoried both packs with its own
parser, wrote every readable entry out, recombined the delta dependents
with their pack-A bases, repaired the six corrupt loose objects by
checksum-guided search, rebuilt the three patch commits from
`docs/patches/`, regenerated `docs/API.md` with the tree's generator,
recreated the pack index, restored the branches from reflogs and the
mirror, the annotated tags from their tag objects, and placed the two
lightweight tags on the release commits after reading `tools/release.sh`,
`VERSION`, `CHANGELOG.md` and the later `git describe` strings, with
assertions on each. It left a recovery report inside the repository
(extra files are allowed) and removed the corrupt pack.

Reading: every intended recovery path was found and executed in under six
minutes. Version 1.0.0 was correct, cheap and well specified, and it was
not hard for this model.

### Full trial set (`/run`, 3 attempts per agent; `/cheat`, 1 per agent)

After the calibration the remaining trials were run on the subscriptions
(no API keys), one attempt at a time per agent, with the same CI defaults
(`scripts/run-job-codex-1.json`, `scripts/run-job-codex-2.json`,
`scripts/run-job-claude.json`, `scripts/run-job-claude-2.json`,
`scripts/cheat-job-*.json`, launched by `scripts/run-remaining.sh` with
`--agent-setup-timeout-multiplier 3`).

#### Attempt log

| Job | Trial | Agent | Outcome | Counts as |
|---|---|---|---|---|
| `calib-codex-1` | `git-repo-recovery__fMzUFjy` | codex | **Completed, reward 1.0** (Harbor-verified): 5.8 min, 12 tool calls | codex attempt 1, pass |
| `run-codex-1` | `git-repo-recovery__Wp8KWG7` | codex | `EnvironmentStartTimeoutError`: the environment container did not start within 900 s while a second job was building its image at the same time | infrastructure error |
| `run-codex-1` | `git-repo-recovery__SN62KED` | codex | `Agent setup timed out after 360 s`: installing the codex CLI in the container exceeded Harbor's default allowance (the allowance was tripled for every later job) | infrastructure error |
| `run-claude-1` | `git-repo-recovery__BUGpUS9` | claude-code | `EnvironmentStartTimeoutError`, same cause as above | infrastructure error |
| `run-claude-1` | `git-repo-recovery__gjBnYHF` | claude-code | `Agent setup timed out after 360 s`, same cause as above | infrastructure error |
| `run-codex-2` | `git-repo-recovery__tuj86CM` | codex | **Completed**: 9.2 min of agent time, declared done ("all 5 branches and 7 tags point to their original objects"); Harbor collected the artifact and then stalled on the Docker hang described in the note below, before it built the verifier; the collected artifact graded with the same verifier image by `scripts/regrade-local.sh`: **5 of 5 checks, reward 1** (`runs/run-codex-2/.../verifier-local/`) | codex attempt 2, pass (locally verified) |
| `run-codex-3` | `git-repo-recovery__UYLvXPg` | codex | **Completed**: 8.5 min of agent time, declared done; same stall after artifact collection; graded locally: **5 of 5 checks, reward 1** (`runs/run-codex-3/.../verifier-local/`) | codex attempt 3, pass (locally verified) |
| `run-claude-2` | `git-repo-recovery__QUrYTyh` | claude-code | **Completed**: 18.4 min of agent time, 37 turns, 36 tool calls, 3.93M input tokens (3.75M cached) / 79k output; declared done with a per-loss account of the repair; same stall after artifact collection; graded locally: **5 of 5 checks, reward 1** (`runs/run-claude-2/.../verifier-local/`) | claude-code attempt 1, pass (locally verified) |
| `cheat-claude-1` | `git-repo-recovery__P2sYSqB` | claude-code + hack prompt | Agent phase complete in 33 s, 4 steps, no tool call: the run was stopped by a safety classifier at step 2 (stop_reason refusal) and the agent then declined the red-team brief, and left `/app/repo.git` byte-identical to the shipped damaged repository (checked with `diff -r`); stalled before verification, repeated as `cheat-claude-2` | cheat trial (first run; untouched repository grades 0; the agent did not attempt a bypass) |
| `cheat-codex-1` | `git-repo-recovery__Qnvtqee` | codex + hack prompt | Agent phase ended after 4 s: the provider's safeguard rejected the turn, Harbor classified it `AgentSafetyRefusalError`; repository byte-identical to the shipped one; stalled before verification, repeated as `cheat-codex-2` | cheat trial (first run; untouched repository grades 0; no tool call was made) |
| `run-claude-3` | `git-repo-recovery__TpwXpFT` | claude-code | **Completed, reward 1.0** (Harbor-verified, 5 of 5 checks): 22.5 min of agent time, 49 tool calls, 3.34M input tokens (3.11M cached) / 100k output | claude-code attempt 2, pass |
| `run-claude-3` | `git-repo-recovery__ThewbT7` | claude-code | **Completed, reward 1.0** (Harbor-verified, 5 of 5 checks): 21.5 min of agent time, 40 tool calls, 4.64M input tokens (4.46M cached) / 90k output | claude-code attempt 3, pass |
| `cheat-claude-2` | `git-repo-recovery__N2vu4vc` | claude-code + hack prompt | **Reward 0.0** (Harbor-verified): 1.9 min, 5 tool calls, all inventory (`ls`, ref listing, object counts, `git fsck` twice); the run was then stopped by a safety classifier at step 7 (stop_reason refusal) and the agent declined the brief; repository byte-identical to the shipped one; `test_fsck_clean`, `test_refs_restored`, `test_history_intact` fail | cheat trial, claude-code: 0.0 as required; the verifier was not exercised (the agent inventoried and declined) |
| `cheat-codex-2` | `git-repo-recovery__BiNxcMH` | codex + hack prompt | **Reward 0.0** (Harbor-verified): 18 s, no tool call; the provider's safeguard rejected the turn again (`AgentSafetyRefusalError` recorded, verifier still ran); repository byte-identical to the shipped one; the same three checks fail | cheat trial, codex: 0.0 as required; the verifier was not exercised (the safeguard rejected the turn before any tool call) |

Note on the stalled jobs: from about 21:45 UTC on 2026-10-29 every Harbor
job on this machine stalled right after `Collecting main service
artifacts`. The agent phase had completed and the artifact had been copied
out, but Harbor's next step, a plain `docker inspect` of the environment
image before it builds the verifier, never returned. The cause was two
BuildKit builder containers (`moby/buildkit:buildx-stable-1`) stuck in the
`Created` state, which made `docker inspect` and `docker rm` of any
container block indefinitely while image and compose commands kept
working. (An earlier reading, that the jobs were being reaped, was wrong:
a process query showed every job alive and waiting.) Restarting Docker
Desktop at 02:47 UTC on 2026-10-30 cleared both containers; a fresh nop
gate (`gate-nop-3` in section 9) then ran through verification in 35 s,
and every job after it was graded by Harbor itself. The trials that fell
into the stall were graded locally from the artifact Harbor had already
collected (`scripts/regrade-local.sh`: the image built from
`tests/Dockerfile`, `tests/test.sh` unchanged, the artifact copied to
`/app/repo.git` as Harbor uploads it); their agent phases were complete
and recorded (trajectory, console log, final message).

#### Final results, version 1.0.0

| Agent (CI defaults) | Attempts | Passed | Agent time per attempt | Cheat trial |
|---|---|---|---|---|
| codex `openai/gpt-6-astra`, `xhigh` | 3 | **3** (`fMzUFjy` Harbor-verified; `tuj86CM`, `UYLvXPg` graded locally from the collected artifact) | 5.8, 9.2, 8.5 min | 0.0 (`cheat-codex-2`; verifier not exercised, see below) |
| claude-code `anthropic/claude-fable-5-1`, `max` | 3 | **3** (`QUrYTyh` graded locally; `TpwXpFT`, `ThewbT7` Harbor-verified) | 18.4, 22.5, 21.5 min | 0.0 (`cheat-claude-2`; verifier not exercised, see below) |

Four infrastructure errors (two environment-start timeouts, two agent-setup
timeouts) are listed above and are not counted as attempts; every attempt
whose agent phase ran to completion is counted, and every one passed.

Both cheat trials scored 0.0, as the brief requires. Neither run exercised
the verifier: codex made no tool call because the provider's safeguard
rejected the turn (Harbor recorded `AgentSafetyRefusalError`), and
claude-code ran five inventory commands, was stopped by a safety classifier, and then declined to attempt a bypass.
The zero rewards therefore show the required numerical outcome, not
adversarial robustness. Robustness evidence comes from the verifier
mutation fixtures in `scripts/verifier-fixtures.sh`, with results recorded
in `analysis/verifier-fixtures.md` (section 3).

Reading of 1.0.0 against the brief. Version 1.0.0 cleared every CI gate,
its oracle and nop behaved, its cheat trials scored 0.0 as the brief
requires (without exercising the verifier, so that is not evidence of its
robustness), and it was deterministic and cheap (about 5.8 to 22.5
minutes of agent time, no API spend). The brief's requirement that the
three attempts per agent genuinely fail was **not met**: both models
recovered every object and every ref. Why they succeeded, step by step,
is in `analysis/trajectories.md` under its 1.0.0 heading; the redesign
that followed is version 1.1.0 (sections 1 to 7) and design 4 in
`analysis/iterations.md`.
