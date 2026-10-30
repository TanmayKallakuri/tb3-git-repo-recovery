# How this task was arrived at: three designs, each measured before the next

The assessment asks for the iteration process. Three task designs were
built end to end during the week; each cleared the CI gates, and each was
measured against the frontier models before the decision to keep or
replace it. The git recovery task in this repository is the third. The
first two live in their own repositories with the same layout (SPEC,
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
