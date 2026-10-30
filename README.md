# git-repo-recovery: a Terminal-Bench 3 task

One original task in the Harbor task format, built for the Klavis founding
engineer assessment, with local evidence that it clears every gate the
Terminal-Bench 3 CI applies and the results of the required agent trials.
The shipped version is 1.2.1. Versions 1.0.0, 1.1.0 and 1.2.0 were
measured and superseded on 2026-10-30; 1.0.0 was also reviewed externally.

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
all. One is a feature branch that was rebased and force-pushed after the
nightly mirror push and archived as patches with zero commit ids, while
the mirror still holds the pre-rebase pair. The other is an annotated
release tag that the release script, as of that release, dated from its
CHANGELOG heading. Their ids appear nowhere in the repository, and the
patterns an agent can check on the surviving commits and tags point at
wrong answers, so a wrong reconstruction passes `git fsck` and only the
verifier's hidden original catches it. The verifier holds the original
repository and compares every ref and every reachable object; reward is
all or nothing.

- Task directory: [`tasks/git-repo-recovery/`](tasks/git-repo-recovery/) (instruction, README with the four explanations and the change log, environment, solution, tests).
- Design: [`SPEC.md`](SPEC.md). Results of every gate and trial: [`RESULTS.md`](RESULTS.md). Trial outputs: [`runs/`](runs/). Failure analysis and the verifier fixtures: [`analysis/`](analysis/).

## Why this task

Two earlier designs were built and measured before this one. A hidden
corpus task grew into a corner-case pile and codex attempts no longer fit
in a ChatGPT window; a reproducible-build task was clean and cheap but
codex solved it in 24 minutes, because an instruction that names the axes
to vary hands the agent its own test matrix. This task reduces the local
oracle, but does not remove it: 2 of the 53 damage items have no local
oracle, and the object id still checks the other 51. Object ids are
checksums, so a candidate repair of those can be checked, but the original
refs and the content of the damaged objects have to be derived from the
repository's own data. The difficulty is inference, and
an agent that does the obvious salvage gets most of the way and still
scores zero. Version 1.0.0 left one oracle in place, the ids themselves:
all 43 of its lost objects were named by a hash the agent could compute,
and both models passed every attempt. Version 1.1.0 adds two losses whose
ids are written nowhere and takes the witnesses out of the instruction.
Version 1.2.0 inverts the sibling patterns for both of them: in 1.1.0 the
conventions an agent can verify on surviving data pointed at the right
answer, and in 1.2.0 they point at a wrong answer that passes fsck. The
lost branch tip is a rebase whose committer is not its author, unlike
every other commit, and the lost tag is dated from its CHANGELOG heading,
unlike the four surviving tags. Version 1.2.1 adds one clause to the
instruction and changes nothing in the repository.

## Gates and how to reproduce them

All commands run from this repository root with the upstream
`terminal-bench` clone checked out next to it (commit recorded in
RESULTS.md), Harbor `0.23.1.dev202609170426` and `dockerfile-pin` 1.5.0 on
`PATH`, and Docker running. `export PYTHONUTF8=1` first on Windows.

| Gate | Command |
|---|---|
| 29 static checks (`static-checks.yml`) | `bash scripts/check-all.sh tasks/git-repo-recovery` (the 1.2.1 transcript is `runs/static-checks/check-all-1.2.1.log`; the 1.2.0 and 1.1.0 transcripts are next to it) |
| `/run` and `/cheat`, 1.2.1 full set | `scripts/run-121.sh` (one process: static checks, oracle and nop, three attempts per agent in two parallel processes, the two cheat trials, the rubric review; auth flags in the script) |
| codex replacement trials | `scripts/run-121b.sh` (waits for the codex usage window to reopen, probes with the cheat trial, then runs one attempt; it was launched twice by mistake, so each of its two jobs holds two trials) |
| Implementation rubric (37 criteria), 1.1.0 stage | `scripts/run-hardened.sh rubric` (stages the task as upstream's `stage_task.py` does, reviews with the CI reviewer model; `scripts/run-121.sh` runs the same review for 1.2.1) |
| Docker build, oracle and nop, 1.1.0 stage | `scripts/run-hardened.sh gates` (or `harbor run -p tasks/git-repo-recovery -a oracle --env docker --yes`, and the same with `-a nop`) |
| Verifier mutation fixtures (19 cases, exact rewards and failing checks) | `scripts/verifier-fixtures.sh` (raw logs of four runs in `runs/verifier-fixtures/`, the last on the 1.2.0 original) |
| `/run` (3 attempts per agent, CI defaults), 1.1.0 stages | `scripts/run-hardened.sh pilot-codex`, then `pilot-claude`, then `rest-codex` and `rest-claude` (one attempt per agent first, the rest only after the pilots; auth flags in the script header) |
| `/cheat` (1 attempt per agent, hack prompt appended), 1.1.0 stage | `scripts/run-hardened.sh cheats` |
| Regenerate the repository and the damage | `bash scripts/gen-repo/run.sh` (runs in a container; deterministic, built twice byte-identically) |
| Trim a job into `runs/` | `python3 scripts/trim-run.py <job>`; summarise with `python3 scripts/summarize-trial.py <job>` |

The 1.0.0 trials were launched with `scripts/run-trials.sh` and
`scripts/run-remaining.sh` and the per-attempt configs under `scripts/`;
those commands stay as documented in RESULTS.md section 20.

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

Version 1.2.1 (shipped, task commit `fbccdfa`; every measurement below ran
on that commit): 619 objects and 161 commits reachable from all 18 refs,
613 objects and 159 commits from the 13 branches and tags the verifier
compares; 53 damage items in 11 classes; 7 hidden ids.

| Gate or trial | Result |
|---|---|
| 29 static checks | 29 pass, transcript committed (`runs/static-checks/check-all-1.2.1.log`) |
| Implementation rubric, 37 criteria | 34 pass, 0 fail, 3 not applicable |
| Oracle / nop | 1.0 / 0.0, Harbor end to end |
| Verifier mutation fixtures | 19 of 19 as expected on the 1.2.0 original; not rerun for 1.2.1, whose verifier and repository bytes are identical to 1.2.0 |
| codex `gpt-6-astra` xhigh, 3 attempts plus 2 replacements | **4 pass, 1 cut short**: 1.0 in 5.7 min and 1.0 in 6.7 min; the third attempt was stopped by the subscription's usage window with the answer in hand, the seven hidden objects rebuilt at their original ids and no ref yet written, and is not counted; the replacement script was launched twice, so two replacement attempts ran, 1.0 in 5.9 min and 1.0 in 6.3 min |
| claude-code `fable-5-1` max, 3 attempts | **2 fail, 1 pass**: 0.0 in 49.6 min with `feature/cache-warmup` at the mirror's stale value; 1.0 in 42.2 min; 0.0 in 21.7 min with 13 of 18 refs restored |
| Cheat trial, 1 per agent | claude-code 0.0: a safety classifier stopped one response, the agent declined the cheat instruction and did an ordinary partial repair; codex 0.0 in both replacement trials, the provider's safeguard rejected the turn before any tool call, as on 1.0.0 and 1.1.0 (its first run hit the closed usage window before any tool call and is not a valid trial; the replacement script was launched twice, hence two) |

Version 1.2.0 (superseded; task commit `0502a89`, the same repository,
damage and verifier as 1.2.1): static checks 29 of 29, oracle 1.0, nop
0.0, verifier fixtures 19 of 19 as expected, and one codex pilot, 1.0 in
6.3 minutes of agent time. Codex solved it as fast as it had solved 1.1.0,
so by the calibration rule no further 1.2.0 trial was spent; the full set
ran on 1.2.1.

Version 1.1.0 (superseded; 610 reachable objects, 158 commits, 13 refs; 53
damage items in 11 classes; RESULTS.md sections 9 to 15):

| Gate or trial | Result |
|---|---|
| Static checks, rubric, oracle / nop, fixtures | 29 of 29; 34 pass, 0 fail, 3 not applicable after the verifier preflight change; 1.0 / 0.0; 19 of 19 |
| codex, 3 attempts | 3 pass, 5.6 to 7.4 minutes of agent time |
| claude-code, 3 attempts | 2 fail, 1 pass: 0.0 in 22.9 and 25.0 min with the same five refs unrestored, 1.0 in 24.8 min |
| Cheat trial, 1 per agent | 0.0 and 0.0; neither run exercised the verifier |

Version 1.0.0 (superseded; 579 reachable objects, 12 refs, 43 lost
objects plus a pack index, 8 lost refs; RESULTS.md sections 16 to 20):

| Gate or trial | Result |
|---|---|
| Static checks, rubric, oracle / nop | 29 of 29; 35 pass, 0 fail, 2 not applicable after the fixes; 1.0 / 0.0 |
| codex, 3 attempts | 3 pass, 6 to 9 minutes of agent time each |
| claude-code, 3 attempts | 3 pass, 18 to 23 minutes each |
| Cheat trial, 1 per agent | 0.0 and 0.0; neither run exercised the verifier |

A cheat trial's zero reward is the required numerical outcome, not
evidence of robustness. Evidence that the verifier rejects bypass attempts
comes from the mutation fixtures in `scripts/verifier-fixtures.sh`
(`analysis/verifier-fixtures.md`): the 1.0.0 verifier accepted 11 of the
17 mutations, the shipped one accepts none.

The honest reading. The task is correct, deterministic and cheap: oracle
1.0 and nop 0.0 on 1.2.0 and on 1.2.1, static checks 29 of 29 on both,
fixtures 19 of 19 on the 1.2.0 original, the rubric at 34 pass, 0 fail and
3 not applicable on 1.2.1, byte-identical rebuilds, and agent phases of
5.7 to 49.6 minutes for the completed attempts, on subscriptions. The
brief's requirement of three genuine failures per agent is not met, for
the third version in a row. Codex: both completed 1.2.1 attempts passed,
in 5.7 and 6.7 minutes; the third was cut by the subscription window with
the seven hidden objects already reconstructed at the original ids; the
1.2.0 pilot passed in 6.3 minutes. The replacement attempt, run twice
because the replacement script was launched twice, passed both times, in
5.9 and 6.3 minutes. No codex attempt in any version has failed genuinely.
Claude-code failed two of three on 1.2.1, as on 1.1.0, and passed one, and
both failures are on the oracle-free elements and the witnesses the
instruction no longer names. Attempt 1
restored the rebased branch at the mirror's stale value, exactly the route
1.2.0 was built to make attractive, since every check on surviving data
confirms it, while it got the tag right by reading the release script as
of the release commit. Attempt 3 stopped at a clean fsck with 13 of 18
refs, the 1.1.0 pattern, and declined to create refs for which no record
exists.

What the hardenings taught. They were measured in full twice, on 1.1.0
and on 1.2.1, and each time they stopped claude-code in two of three
attempts and codex in none of its completed attempts, the two 1.2.1
replacement attempts included. Codex's trajectories show why: it
reads every tool as of every commit, treats what a script says the project
did as what happened, validates each reconstruction against a hash or a
native re-run, and on 1.2.0 and 1.2.1 it finished in under seven minutes
of agent time. A small, fully inspectable git repository in which
everything lost is recoverable from what remains, which is what makes the
task correct and oracle-free, does not produce three genuine codex
failures, and making the evidence thinner would make the task guessable,
which the brief forbids. The design was frozen at 1.2.1, and the remaining
effort went into evidence and the write-up rather than another redesign.

[`analysis/trajectories.md`](analysis/trajectories.md) has the six 1.2.1
attempts, the two 1.2.1 cheat trials and the 1.2.0 codex pilot at their
decision points, then the six 1.1.0 attempts with their cheat trials, and
the six 1.0.0 passes;
[`analysis/iterations.md`](analysis/iterations.md) records the five
designs, the last three being versions of this task, and what each
measured.
