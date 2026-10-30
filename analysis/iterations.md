# How this task was arrived at: four designs, each measured before the next

The assessment asks for the iteration process. Four task designs were
built end to end during the week; each cleared the CI gates, and each was
measured against the frontier models before the decision to keep or
replace it. The git recovery task in this repository is the third, and
its 1.1.0 hardening is the fourth. The first two live in their own repositories with the same layout (SPEC,
RESULTS, trimmed runs) and are available on request; their numbers below
are copied from their RESULTS files.

## Design 1: `model-scanner-hardening` (Security)

Harden a static scanner for machine-learning model files against a hidden
corpus of 648 artifacts (pickle in every protocol and container, PyTorch,
NumPy, TensorFlow SavedModel, Keras) regenerated from a seed inside the
verifier; reward 1 only at 100 percent recall with zero false positives.

| Gate or trial | Result |
|---|---|
| Static checks, oracle, nop | 28 of 28 (before `check-lockfiles` existed), 1.0, 0.0 |
| Rubric | 36 pass, 0 fail, 1 n/a |
| claude-code, three completed attempts | reward 0 each: 187, 200 and 205 of 262 malicious items caught, 16 to 30 of 386 clean items flagged |
| codex, one completed attempt | reward 0: 258 of 262 caught, 54 clean items flagged (its "unsupported" verdict on clean twins) |
| codex, four further launches | each ended on the ChatGPT subscription's usage limit or a capacity error at 27 to 87 minutes, before the agent stopped |
| cheat trials | reward 0 for both (claude-code found no bypass; codex was refused by the provider's safeguard) |

What it taught: a large hidden space with symmetric error costs does make
the frontier models fail, but the corpus grew into a corner-case pile the
TB3 rubric warns against, every attempt ran 40 to 90 minutes, and one
codex attempt no longer fit inside a subscription window. The design was
set aside for cost and for the shape of its difficulty.

## Design 2: `reproducible-release-build` (Software / Systems)

A small project whose `make release` produced a different tarball on
every build and machine; six seeded causes (build banner, generator order,
a cache keyed on source bytes only, tar and gzip metadata, a hand-rolled
wheel packer, locale and timezone); a verifier that rebuilt the tree under
six hostile environments and demanded identical archives plus a mutated
rebuild to prove the output came from source.

| Gate or trial | Result |
|---|---|
| Static checks, oracle, nop | 29 of 29, 1.0, 0.0 |
| Rubric | 33 pass, 2 fail (one wording fix applied, one the author's paragraph), 2 n/a |
| codex calibration (one attempt before any other trial) | **reward 1.0** in 23.6 minutes, 19 tool calls, 817k input tokens |

What it taught: an instruction that must name the axes to vary hands the
agent its own test matrix. Codex sanitised the runner environment,
re-keyed the cache on the preprocessed unit and the compiler, mapped paths
out of the debug information, and wrote its own cross-environment
regression suite. No further trials were spent on it.

## Design 3: `git-repo-recovery` (this repository)

Chosen to remove the local oracle: the agent cannot test its way to the
answer, it has to reason from the repository's own evidence. Results are
in RESULTS.md. The calibration rule was kept: one codex attempt before any
other trial.

## The rule that made the iteration affordable

Every design got exactly one codex attempt before anything else was run.
Designs 2 and 3 together cost about four dollars of equivalent usage and
thirty minutes of agent time to measure, against the twelve full trials
that would otherwise have been run on them.

## Design 4: `git-repo-recovery` 1.1.0, the hardening (this repository, shipped)

Version 1.0.0 was measured in full (six passes, two cheat trials at zero,
RESULTS.md sections 8 to 12) and reviewed externally on 2026-10-30. The
review's central finding was the one the measurements already showed:
every completed attempt by either model passed. Its reading of why
matched `trajectories.md`: object ids act as a local oracle (all 43 of the
lost objects were named by a hash the agent could compute, so every
reconstruction was search with instant feedback), and the instruction
listed the witnesses (the mirror, the reflogs, the release script, the
archived series), so finding them was not part of the work.

Principle of the redesign: keep everything else, remove the oracle for a
few targets. Two losses were added whose exact bytes are derivable from
explicit evidence in the tree but whose ids appear nowhere in the
repository, not as a 7-hex prefix, not in binary form, not in a pack
index, `packed-refs`, a reflog or a patch header. The generator asserts
that property on every build. A wrong reconstruction of either passes
`git fsck --full --strict` and every check the agent can run; only the
hidden original rejects it. Everything else stays locally checkable, so
the task cannot be solved by scanning for ids alone.

- L1: the last commit on `feature/cache-warmup`, made after the nightly
  mirror push, deleted with its ref and reflog; its tree and blobs left
  dangling. The series is archived in the tree with zero commit ids
  (`format-patch --zero-commit --no-thread --no-signature`) and a series
  file naming the branch it was exported from. The commit has to be
  rebuilt byte for byte: the mirror's commit as parent, the patch's author
  and date, committer equal to author as on every commit in the
  repository. Restoring the branch at the mirror's value is the wrong
  answer that passes fsck.
- L2: the annotated tag `v1.4.0`, made by version 2 of `tools/release.sh`
  (message from the CHANGELOG section, tagger and date from the release
  commit), deleted with its ref. Version 1 made the surviving tags,
  version 3 at the tip is one-line and its commit body says 1.4.0 carried
  the full notes. The tag has to be rebuilt by replaying the script as of
  the release commit, not as of HEAD. A one-line tag, or a lightweight
  one, is the wrong answer that passes fsck.
- The mirror became a simulated nightly cron (15 pushes at 02:00 UTC,
  documented in `docs/operations.md`, `update by push` entries by
  `mirror cron` in the mirror reflogs), so every mirror ref equals its
  branch at the last nightly and lags every branch that moved on the last
  day.
- The instruction states the end state only. Nothing names the repacks,
  the reflogs, the mirror, the release script or the archived series.
- Every timestamp before the tail of the history is frozen, so both
  packfiles and the D1, D2, D4, D5 and D6 victims are unchanged from
  1.0.0; the oracle gained the series route and the release-replay route;
  the verifier gained the config allowlist, the pre-clean ref inventory
  and the full ref-name comparison (`verifier-fixtures.md`).

What the red-team review of the design predicted, before any trial. The
review read the design text before the generator was changed (its T1 and
T2 are L1 and L2 here). It expected the lost cache-warmup commit to be the
most common failure: a strong agent would restore the branch to the
mirror's stale commit and stop there, because at that point fsck already
reports nothing missing. For the tag it expected agents to make `v1.4.0`
lightweight, the way `v1.2.1` and `v1.3.1` are restored, or to copy the
one-line format of HEAD's v3 script or of the surviving v1 tags. Per
attempt it put codex at about 0.45 to rebuild the commit exactly and 0.50
for the tag, and claude-code at about 0.60 for each; that gives about 0.45
that all three codex attempts fail, 0.30 for claude-code, and 0.13 for
both agents. Two wording fixes it asked for were applied and are asserted
by the generator: the series file says the patches were exported from the
tip of `feature/cache-warmup`, and the archive script's header says commit
ids are omitted because the archive records content, not history
positions. The calibration rule was kept: one attempt per agent before
anything else.

| Gate or trial | Result |
|---|---|
| Static checks, oracle, nop | 29 of 29 twice (transcript committed), oracle 1.0 three times, nop 0.0 twice, the last pair on the final task commit `f29cadf` |
| Verifier fixtures | 19 of 19 on the 1.0.0 original, on the 1.1.0 original, and on the final verifier (`f29cadf`); raw logs in `runs/verifier-fixtures/` |
| Rubric | 33 pass, 1 fail, 3 not applicable; after the verifier preflight change (`f29cadf`) 34 pass, 0 fail, 3 not applicable |
| codex pilot (`pilot-codex-h`, `m9wqtVr`) | **reward 1.0** in 7.4 minutes, 14 tool calls, 924k input tokens: read `tools/release.sh` as of the release commit, replayed the archived series onto the mirror's commit with the tree checked against the dangling one, rebuilt both hidden targets exactly |
| claude-code pilot (`pilot-claude-h`, `w2hS6QT`) | **reward 0.0** in 22.9 minutes, 39 tool calls, 4.46M input tokens: fsck clean, every id its own census could name present, four refs restored from reflogs and tag objects, five refs missing (L1, L2, the mirror route, the two describe-string tags) |
| codex attempts 2 and 3 (`run-codex-h`, `FDY3d3q`, `wjs6dMz`) | **1.0 and 1.0**, 7.1 and 5.6 minutes |
| claude-code attempts 2 and 3 (`run-claude-h`, `CMQWEQW`, `kLSoSqt`) | **0.0 and 1.0**, 25.0 and 24.8 minutes; attempt 2 stopped the way the pilot did, with the same five refs missing; attempt 3 read the release script as of the release commit, replayed the series and passed |
| cheat trials (`cheat-claude-h` `AZor9ML`, `cheat-codex-h` `TBSMyN8`) | **0.0 and 0.0**; claude-code ran four inventory commands, was stopped by a safety classifier, and the agent then declined; codex made no tool call (provider safeguard rejection); neither exercised the verifier |

What it taught: removing the local oracle for two items changed the
outcome for one model and not the other, and the trials inverted the
review's per-agent expectation. Codex passed all three attempts in 5.6 to
7.4 minutes; claude-code failed two of three and passed one; both cheat
trials scored 0. The brief's requirement of three genuine failures per
agent is not met: not for codex at all, and for claude-code two of three.
What 1.1.0 did achieve is two genuine, verifier-confirmed failures of a
frontier agent on exactly the elements that were changed: both failing
final messages show the agent saw the evidence (the series file, the
zero-id patch, the dangling tree, the mirror's refs and reflogs, and in
attempt 2 the release script and the point-release versions as well) and
decided against acting on it, while codex, and claude-code on its third
attempt, treated the same evidence as instructions.

## The rule that made the iteration affordable, applied again

Design 4 followed the same rule: one codex attempt and one claude-code
attempt before the remaining trials were launched, in parallel processes
once the pilots had shown the task survives contact.
