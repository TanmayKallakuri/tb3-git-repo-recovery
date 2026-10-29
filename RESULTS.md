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
(`runs/rubric-review-1/verdicts.json`). The reviewer rated the difficulty
"deep git internals expertise ... well beyond what an average
undergraduate could do in a few days", the task "not a standard textbook
git exercise", and the anti-cheat design sound (content-addressed ids,
the original only in the verifier image, the artifact cleaned of
alternates, hooks, replace refs and promisor markers before grading).

| Criterion | Reviewer's finding | Change |
|---|---|---|
| `difficulty_explanation_quality` | The explanation did not say who does this work in the real world or whether the repository is synthetic. | Two sentences added: git-hosting engineers and data-recovery contractors; synthetic history made by git itself, one route back per loss. |
| `task_readme` | `Relevant experience` is the `TODO(Tanmay)` placeholder. | To be written by the author in his own words; rerun as `rubric-review-2` afterwards. |

Not applicable: `structured_data_schema` (the deliverable is a repository
state) and `score_provenance` (every check is boolean).


## 5. Trials (`/run`) and cheat trials (`/cheat`)

(pending; one codex calibration attempt runs first)
