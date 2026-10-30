# git-repo-recovery: a Terminal-Bench 3 task

One original task in the Harbor task format, built for the Klavis founding
engineer assessment, with local evidence that it clears every gate the
Terminal-Bench 3 CI applies and the results of the required agent trials.
The shipped version is 1.1.0; version 1.0.0 was measured in full, reviewed
externally, and superseded on 2026-10-30.

The task: a team's bare git repository was recovered from a failing disk.
`git fsck` reports missing and corrupt objects, several branches and tags
are gone, and the last backup is useless. The agent repairs the repository
in place so that every branch and tag exists again with its original
target and every object is intact. Everything that was lost can be
reconstructed from what remains, but each loss has a different source:
intact copies in an older packfile, delta bases that have to be combined
with intact deltas, checksum-guided repair of single-byte corruption,
commits rebuilt from a mailed patch series archived in the tree, a
generated document regenerated with the project's own tool, reflogs, the
nightly mirror's tracking refs, dangling tag objects, and the release
script's `git describe` strings. Two of the losses have no local oracle at
all: the last commit of a feature branch, made after the nightly mirror
push and archived as a patch with zero commit ids, and an annotated
release tag whose format only the release script as of that release
specifies. Their ids appear nowhere in the repository, so a wrong
reconstruction passes `git fsck` and only the verifier's hidden original
catches it. The verifier holds the original repository and compares every
ref and every reachable object; reward is all or nothing.

- Task directory: [`tasks/git-repo-recovery/`](tasks/git-repo-recovery/) (instruction, README with the four explanations and the change log, environment, solution, tests).
- Design: [`SPEC.md`](SPEC.md). Results of every gate and trial: [`RESULTS.md`](RESULTS.md). Trial outputs: [`runs/`](runs/). Failure analysis and the verifier fixtures: [`analysis/`](analysis/).

## Why this task

Two earlier designs were built and measured before this one. A hidden
corpus task grew into a corner-case pile and codex attempts no longer fit
in a ChatGPT window; a reproducible-build task was clean and cheap but
codex solved it in 24 minutes, because an instruction that names the axes
to vary hands the agent its own test matrix. This task removes the local
oracle: object ids are checksums, so a candidate repair can be checked,
but the original refs and the content of the damaged objects have to be
derived from the repository's own data. The difficulty is inference, and
an agent that does the obvious salvage gets most of the way and still
scores zero. Version 1.0.0 left one oracle in place, the ids themselves:
44 of its 45 lost objects were named by a hash the agent could compute,
and both models passed every attempt. Version 1.1.0 adds two losses whose
ids are written nowhere and takes the witnesses out of the instruction.

## Gates and how to reproduce them

All commands run from this repository root with the upstream
`terminal-bench` clone checked out next to it (commit recorded in
RESULTS.md), Harbor `0.23.1.dev202609170426` and `dockerfile-pin` 1.5.0 on
`PATH`, and Docker running. `export PYTHONUTF8=1` first on Windows.

| Gate | Command |
|---|---|
| 29 static checks (`static-checks.yml`) | `bash scripts/check-all.sh tasks/git-repo-recovery` (the 1.1.0 transcript is `runs/static-checks/check-all-1.1.0.log`) |
| Implementation rubric (37 criteria) | `scripts/run-hardened.sh rubric` (stages the task as upstream's `stage_task.py` does, reviews with the CI reviewer model) |
| Docker build, oracle and nop | `scripts/run-hardened.sh gates` (or `harbor run -p tasks/git-repo-recovery -a oracle --env docker --yes`, and the same with `-a nop`) |
| Verifier mutation fixtures (19 cases, exact rewards and failing checks) | `scripts/verifier-fixtures.sh` |
| `/run` (3 attempts per agent, CI defaults) | `scripts/run-hardened.sh pilot-codex`, then `pilot-claude`, then `rest-codex` and `rest-claude` (one attempt per agent first, the rest only after the pilots; auth flags in the script header) |
| `/cheat` (1 attempt per agent, hack prompt appended) | `scripts/run-hardened.sh cheats` |
| Regenerate the repository and the damage | `bash scripts/gen-repo/run.sh` (runs in a container; deterministic, built twice byte-identically) |
| Trim a job into `runs/` | `python3 scripts/trim-run.py <job>`; summarise with `python3 scripts/summarize-trial.py <job>` |

The 1.0.0 trials were launched with `scripts/run-trials.sh` and
`scripts/run-remaining.sh` and the per-attempt configs under `scripts/`;
those commands stay as documented in RESULTS.md section 12.

## Note on the agent models

The assessment names `codex gpt-6.1-sol` at `xhigh` and `claude-code
opus-5.5` at `max`, and also says the current Terminal-Bench 3 CI
configuration is the source of truth. At the upstream commit used here the
CI defaults (`.github/harbor-run-defaults.yml`) are:

| Agent | Model | Settings |
|---|---|---|
| claude-code | `anthropic/claude-fable-5-1` | `reasoning_effort=max`, `CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000` |
| codex | `openai/gpt-6-astra` | `reasoning_effort=xhigh` |

The trials in this repository use the CI pair; `scripts/run-job.json`,
`scripts/cheat-job.json` and the per-attempt configs mirror that file
field for field.

## Results summary

Version 1.1.0 (shipped): 610 reachable objects, 158 commits, 13 refs; 53
damage items in 11 classes.

| Gate or trial | Result |
|---|---|
| 29 static checks | 29 pass, twice (task commit `719f13e`, final task commit `f29cadf`), transcript committed |
| Implementation rubric, 37 criteria | 33 pass, 1 fail, 3 not applicable (`no_extraneous_files`: the damage manifest was read by nothing); after the verifier preflight change 34 pass, 0 fail, 3 not applicable |
| Oracle / nop | 1.0 / 0.0, Harbor end to end; oracle 1.0 three times (first build, after the solution polish, after the verifier preflight), nop 0.0 twice |
| Verifier mutation fixtures | 19 of 19 as expected on the 1.0.0 original and again on the 1.1.0 original |
| codex `gpt-6-astra` xhigh, 3 attempts | **3 pass**, 7.4, 7.1 and 5.6 minutes of agent time |
| claude-code `fable-5-1` max, 3 attempts | **2 fail, 1 pass**: 0.0 in 22.9 min, 0.0 in 25.0 min, 1.0 in 24.8 min; both failures leave the same five refs unrestored and 9 of 610 objects unreachable |
| Cheat trial, 1 per agent | 0.0 and 0.0, as the brief requires; neither run exercised the verifier (the provider's safeguard rejected the codex turn; claude-code ran four inventory commands and declined); both left the repository byte-identical to the damaged one |

Version 1.0.0 (superseded; 579 reachable objects, 12 refs, 45 lost
objects plus a pack index, 8 lost refs):

| Gate or trial | Result |
|---|---|
| 29 static checks | 29 pass |
| Implementation rubric, 37 criteria | first review 33 pass, 2 fail, 2 not applicable; after the fixes 35 pass, 0 fail, 2 not applicable |
| Oracle / nop | 1.0 / 0.0, verified again after the Docker restart recorded in RESULTS.md |
| codex, 3 attempts | 3 pass, 6 to 9 minutes of agent time each |
| claude-code, 3 attempts | 3 pass, 18 to 23 minutes each |
| Cheat trial, 1 per agent | 0.0 and 0.0, as the brief requires; neither run exercised the verifier (the provider's safeguard rejected the codex turn; claude-code ran five inventory commands and declined); both left the repository byte-identical to the damaged one |

A cheat trial's zero reward is the required numerical outcome, not
evidence of robustness. Evidence that the verifier rejects bypass attempts
comes from the mutation fixtures in `scripts/verifier-fixtures.sh`
(`analysis/verifier-fixtures.md`): the 1.0.0 verifier accepted 11 of the
17 mutations, the shipped one accepts none.

The honest reading. The task is correct, deterministic and cheap, and the
brief's requirement of three genuine failures per agent is not met: not
for codex at all, which passed all three attempts in 5.6 to 7.4 minutes,
and for claude-code two of three. What 1.1.0 did achieve, and 1.0.0 did
not, is two genuine, verifier-confirmed failures of a frontier agent at
its CI settings, each on exactly the oracle-free elements and the
de-listed witnesses: with fsck clean and every id its own census could
name accounted for, claude-code restored the four refs the reflogs and tag
objects record and stopped, leaving the feature branches, the lightweight
tags and `v1.4.0` unrestored, and both final messages say the mirror's
branches and the archived series were left alone on purpose. Its third
attempt read `tools/release.sh` as of the release commit, replayed the
series onto the mirror's commit and passed. Codex did that in every
attempt. In every 1.0.0 attempt, when the instruction named the mirror and
the release script, both models found them.
[`analysis/trajectories.md`](analysis/trajectories.md) has the six 1.1.0
attempts at their decision points, the two cheat trials, and the six 1.0.0
passes;
[`analysis/iterations.md`](analysis/iterations.md) records the three
designs built before this version and what each measured, and the 1.1.0
hardening as design 4.
