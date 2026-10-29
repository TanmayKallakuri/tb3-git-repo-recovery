# git-repo-recovery: a Terminal-Bench 3 task

One original task in the Harbor task format, built for the Klavis founding
engineer assessment, with local evidence that it clears every gate the
Terminal-Bench 3 CI applies and the results of the required agent trials.

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
mirror's tracking refs, dangling tag objects, and the release script's
`git describe` strings. The verifier holds the original repository and
compares every ref and every reachable object; reward is all or nothing.

- Task directory: [`tasks/git-repo-recovery/`](tasks/git-repo-recovery/) (instruction, README with the four explanations, environment, solution, tests).
- Design: [`SPEC.md`](SPEC.md). Results of every gate and trial: [`RESULTS.md`](RESULTS.md). Trial outputs: [`runs/`](runs/). Failure analysis: [`analysis/`](analysis/).

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
scores zero.

## Gates and how to reproduce them

All commands run from this repository root with the upstream
`terminal-bench` clone checked out next to it (commit recorded in
RESULTS.md), Harbor `0.23.1.dev202609170426` and `dockerfile-pin` 1.5.0 on
`PATH`, and Docker running. `export PYTHONUTF8=1` first on Windows.

| Gate | Command |
|---|---|
| 29 static checks (`static-checks.yml`) | `bash scripts/check-all.sh tasks/git-repo-recovery` |
| Implementation rubric (37 criteria) | staged review run with the CI reviewer model, see RESULTS.md |
| Docker build, oracle | `harbor run -p tasks/git-repo-recovery -a oracle --env docker --yes` |
| nop | `harbor run -p tasks/git-repo-recovery -a nop --env docker --yes` |
| `/run` (3 attempts per agent, CI defaults) | `harbor run -c scripts/run-job.json ...` (auth flags in RESULTS.md) |
| `/cheat` (1 attempt per agent, hack prompt appended) | `harbor run -c scripts/cheat-job.json ...` |
| Regenerate the repository and the damage | `bash scripts/gen-repo/run.sh` (runs in a container; deterministic) |

## Note on the agent models

The assessment names `codex gpt-6.1-sol` at `xhigh` and `claude-code
opus-5.5` at `max`, and also says the current Terminal-Bench 3 CI
configuration is the source of truth. At the upstream commit used here the
CI defaults (`.github/harbor-run-defaults.yml`) are:

| Agent | Model | Settings |
|---|---|---|
| claude-code | `anthropic/claude-fable-5-1` | `reasoning_effort=max`, `CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000` |
| codex | `openai/gpt-6-astra` | `reasoning_effort=xhigh` |

The trials in this repository use the CI pair; `scripts/run-job.json` and
`scripts/cheat-job.json` mirror that file field for field.

## Results summary

See RESULTS.md. (Filled in after the trials.)
