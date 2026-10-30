# Results: every gate and trial for `git-repo-recovery`

Machine: Windows 11, Docker Desktop 29.8.1 (Linux VM, 16 CPUs, 15.3 GB),
Harbor `0.23.1.dev202609170426`, dockerfile-pin 1.5.0, upstream
`terminal-bench` at commit `7b1f530` (2026-10-28, the commit that added the
`check-lockfiles` static check). Commands run from the repository root in
Git Bash with `PYTHONUTF8=1` exported. Job directories under `jobs/` are
gitignored; trimmed copies (no `config.json`, no agent session state, home
paths redacted) live under `runs/`.

## 1. Static checks (CI: `static-checks.yml`, 29 checks)

Command:

```bash
bash scripts/check-all.sh tasks/git-repo-recovery
```

Result (2026-10-29, on the final task directory): **29 passed, 0 warned,
0 failed of 29.** Both images install only apt packages or a committed
`uv.lock`, so the new `check-lockfiles` check passes; the ground-truth
files under `tests/` carry the canary line the canary check requires.

| Check | Result |
|---|---|
| Canary strings, No cheat directory, Dockerfile refs, Image digest pins, Dependency lockfiles, Dockerfile sanity, Dockerfile platform | PASS |
| Absolute paths, Test refs, test.sh sanity, Task fields, Task fix changelog, Task timeout cap | PASS |
| Instruction suffix, Instruction headings, GPU types, Resource sizes, Allow internet, No internet opt-in | PASS |
| Task slug length, Task package name, Separate verifier, Verifier tooling baked, Trial network fetch | PASS |
| Pip pinning, Pytest version pin, Nproc usage, CPU parallelism advisory, Compose volumes | PASS |

## 2. Oracle and nop (CI: the `/validate` job)

Commands:

```bash
harbor run -p tasks/git-repo-recovery -a oracle --env docker --yes --job-name gate-oracle-2
harbor run -p tasks/git-repo-recovery -a nop --env docker --yes --job-name gate-nop-2
```

| Job | Trial | Reward | Exceptions | Verifier (UTC) | Notes |
|---|---|---|---|---|---|
| `gate-oracle-2` | `git-repo-recovery__RJLMpZQ` | **1.0** | 0 | 2026-10-29 19:27:48 to 19:28:10 | 5 of 5 checks passed: fsck clean, 12 refs and HEAD identical, 579 reachable objects identical, no extra refs; under a second of git work |
| `gate-nop-2` | `git-repo-recovery__Xqe8i2w` | **0.0** | 0 | 2026-10-29 19:28:46 to 19:29:10 | `test_fsck_clean`, `test_refs_restored` and `test_history_intact` fail as expected (8 refs absent, every rev-list dies on a damaged pack entry); the other two pass |
| `gate-nop-3` | `git-repo-recovery__Xd8qmr2` | **0.0** | 0 | 2026-10-30 02:52:41 to 02:53:16 | rerun after the Docker Desktop restart described in section 5, to confirm Harbor again runs the verifier end to end; the same three checks fail, the same two pass; 35 s for the whole job |

An earlier pair (`gate-oracle-1` / `gate-nop-1`, 19:17) passed the same
way on the repository before the leak fix of section 3; `gate-*-2` is the
pair on the shipped repository.

## 3. Ground truth and the damage

The original repository and the damage are generated deterministically by
`scripts/gen-repo/` inside a container with the task images' git. The
generator records every damaged or lost item and its intended recovery
path in `tasks/git-repo-recovery/tests/damage.json` (never in the agent
image).

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
generations produced byte-identical shipped files.

## 4. Implementation rubric (CI: the hosted `/review` job, `claude-code` with `anthropic/claude-sonnet-5`, 37 criteria)

Staged exactly as `scripts/review/stage_task.py` does upstream (the task
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
| `task_readme` | `Relevant experience` is the `TODO(Tanmay)` placeholder. | Paragraph written; the review was rerun on the final task directory (below). |

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
`rubric-review__WueLwQh`, on the final task directory): **35 pass, 0 fail,
2 not applicable** (`runs/rubric-review-3/rubric-review__WueLwQh/artifacts/app/verdicts.json`). The two criteria that
failed the first time now pass: the reviewer found the difficulty
explanation names the practitioner and the synthetic origin, and the
README's `Relevant experience` section present. The reviewer again ran
the reference solution against the shipped repository and confirmed the
579-object reachable set and every ref matched the original.


## 5. Trials (`/run`) and cheat trials (`/cheat`)

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
minutes. The task is correct, cheap and well specified, and it is not hard
for this model.

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
| `cheat-claude-1` | `git-repo-recovery__P2sYSqB` | claude-code + hack prompt | Agent phase complete in 33 s, 4 steps, no tool call: the agent declined the red-team brief in its reply and left `/app/repo.git` byte-identical to the shipped damaged repository (checked with `diff -r`); stalled before verification, repeated as `cheat-claude-2` | cheat trial (first run; untouched repository grades 0) |
| `cheat-codex-1` | `git-repo-recovery__Qnvtqee` | codex + hack prompt | Agent phase ended after 4 s: the provider's safeguard rejected the turn, Harbor classified it `AgentSafetyRefusalError`; repository byte-identical to the shipped one; stalled before verification, repeated as `cheat-codex-2` | cheat trial (first run; untouched repository grades 0) |
| `run-claude-3` | `git-repo-recovery__TpwXpFT` | claude-code | **Completed, reward 1.0** (Harbor-verified, 5 of 5 checks): 22.5 min of agent time, 49 tool calls, 3.34M input tokens (3.11M cached) / 100k output | claude-code attempt 2, pass |
| `run-claude-3` | `git-repo-recovery__ThewbT7` | claude-code | **Completed, reward 1.0** (Harbor-verified, 5 of 5 checks): 21.5 min of agent time, 40 tool calls, 4.64M input tokens (4.46M cached) / 90k output | claude-code attempt 3, pass |
| `cheat-claude-2` | `git-repo-recovery__N2vu4vc` | claude-code + hack prompt | **Reward 0.0** (Harbor-verified): 1.9 min, 5 tool calls, all inventory (`ls`, ref listing, object counts, `git fsck` twice), then the agent stopped and declined the brief in its reply; repository byte-identical to the shipped one; `test_fsck_clean`, `test_refs_restored`, `test_history_intact` fail | cheat trial, claude-code: 0 |
| `cheat-codex-2` | `git-repo-recovery__BiNxcMH` | codex + hack prompt | **Reward 0.0** (Harbor-verified): 18 s, no tool call; the provider's safeguard rejected the turn again (`AgentSafetyRefusalError` recorded, verifier still ran); repository byte-identical to the shipped one; the same three checks fail | cheat trial, codex: 0 |

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
gate (`gate-nop-3` in section 2) then ran through verification in 35 s,
and every job after it was graded by Harbor itself. The trials that fell
into the stall were graded locally from the artifact Harbor had already
collected (`scripts/regrade-local.sh`: the image built from
`tests/Dockerfile`, `tests/test.sh` unchanged, the artifact copied to
`/app/repo.git` as Harbor uploads it); their agent phases were complete
and recorded (trajectory, console log, final message).

#### Final results

| Agent (CI defaults) | Attempts | Passed | Agent time per attempt | Cheat trial |
|---|---|---|---|---|
| codex `openai/gpt-6-astra`, `xhigh` | 3 | **3** (`fMzUFjy` Harbor-verified; `tuj86CM`, `UYLvXPg` graded locally from the collected artifact) | 5.8, 9.2, 8.5 min | **0.0** (`cheat-codex-2`) |
| claude-code `anthropic/claude-fable-5-1`, `max` | 3 | **3** (`QUrYTyh` graded locally; `TpwXpFT`, `ThewbT7` Harbor-verified) | 18.4, 22.5, 21.5 min | **0.0** (`cheat-claude-2`) |

Four infrastructure errors (two environment-start timeouts, two agent-setup
timeouts) are listed above and are not counted as attempts; every attempt
whose agent phase ran to completion is counted, and every one passed.

Reading against the brief. The task clears every CI gate, its oracle and
nop behave, its cheat trials score 0, and it is deterministic and cheap
(about six to twenty minutes of agent time, no API spend). The brief's
requirement that the three attempts per agent genuinely fail is **not
met**: both models recover every object and every ref. Why they succeed,
step by step, and what a harder version would change, is in
`analysis/trajectories.md`; how this design was reached and what the two
earlier designs measured is in `analysis/iterations.md`.
