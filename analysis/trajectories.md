# Trajectory analysis: what the agents did, and why this task did not stop them

The brief asks for three attempts per agent that genuinely fail. On this
task they do not: every completed attempt by either agent repaired the
repository exactly. This file records what each trajectory did, where the
intended difficulty went, and what the cheat trials showed. Numbers come
from the trajectories under `runs/` (`agent/trajectory.json`); the
"active" time is the span from the first to the last trajectory step,
which excludes CLI start-up and session copying and is therefore shorter
than the agent-phase time in RESULTS.md.

## Completed attempts

| Job / trial | Agent | Active time | Tool calls | Input tokens (cached) / output | Verdict |
|---|---|---|---|---|---|
| `calib-codex-1` / `fMzUFjy` | codex gpt-6-astra xhigh | 5.8 min | 12 | 747k (689k) / 11k | 1.0 (Harbor) |
| `run-codex-2` / `tuj86CM` | codex | 6.4 min | 19 | 1.13M (1.06M) / 14k | 1.0 (local, same verifier image) |
| `run-codex-3` / `UYLvXPg` | codex | 5.3 min | 16 | 1.00M (930k) / 13k | 1.0 (local) |
| `run-claude-2` / `QUrYTyh` | claude-code fable-5-1 max | 18.4 min | 36 | 3.93M (3.75M) / 79k | 1.0 (local) |
| `run-claude-3` / `TpwXpFT` | claude-code | 22.4 min | 49 | 3.34M (3.11M) / 100k | 1.0 (Harbor) |
| `run-claude-3` / `ThewbT7` | claude-code | 21.4 min | 40 | 4.64M (4.46M) / 90k | 1.0 (Harbor) |

## The skeleton every passing trajectory followed

All six passing attempts converged on the same six moves, in the same
order, with no dead ends longer than one tool call:

1. **Inventory.** `git fsck --full --strict`, the two packfiles, the
   reflogs, `packed-refs`, the mirror's tracking refs. Each agent noticed
   within its first three calls that the newer pack had no index and
   rebuilt it with `git index-pack` (codex-2 and codex-3 into an isolated
   object directory first, so a bad pack could not pollute the store).
2. **Salvage every intact entry of both packs.** Codex wrote its own pack
   parser (`recovery/salvage.py`) or used `git unpack-objects` with
   `GIT_OBJECT_DIRECTORY` pointing at a scratch directory; claude-code
   parsed the pack with a script in `/tmp/tools`, checked every entry
   against the index CRC and its hash, and extracted all 510 intact
   entries of the damaged pack as loose objects before retiring that pack.
   This step alone recovers D1 and D2: the intact pack-A copies and the
   delta bases, with pack-B's deltas applied to them.
3. **Single-byte repair of the six corrupt loose objects.** Every agent
   brute-forced one byte at a time (256 values at every offset) until the
   stream inflated to the known id. Each object took seconds.
4. **Rebuild the archived patch series.** The `git format-patch` files in
   `docs/patches/` carry the original commit id in their first line and
   the post-image blob ids in their `index` lines, so the agents applied
   the hunks, built the trees from the parent commit's tree, and
   confirmed each commit, tree and blob by hash. Claude-code found the
   parent by hashing candidates until the recorded commit id matched.
5. **Regenerate `docs/API.md`.** Every agent read `tools/gen_api_docs.py`
   and `Makefile`, ran the generator against candidate release trees, and
   kept the output whose hash matched the missing blob.
6. **Refs.** Branches from the reflogs and the mirror's tracking ref;
   annotated tags from the dangling tag objects; the two lightweight tags
   from the same evidence chain in all six trajectories: `tools/release.sh`
   shows that point releases get a lightweight tag on the release commit,
   `VERSION` and `CHANGELOG.md` identify that commit, and the `git
   describe` output committed later by the release script pins it (codex-2
   wrote the chain into an assertion before writing the ref; claude-code
   ran `git describe` on the candidates and compared).

Codex left its scripts and a recovery report under `recovery/` inside the
bare repository (extra files are allowed); claude-code kept its tools in
`/tmp` and left the store clean. Claude-code's two later attempts also
repacked the salvaged objects into a fresh pack and removed the stale
`info/refs` listing, and one of them checked that the reflogs were
byte-identical to its pre-repair copy before finishing; both wrote a
ref-by-ref evidence table in the final message. Both ended with `git fsck --full --strict`
exiting 0 and a per-loss account in the final message.

## Where the difficulty went

- **Object recovery has a perfect local oracle.** The design relied on
  there being no oracle for the *refs*, and that holds; but 44 of the 45
  lost objects are named by a hash the agent can compute, so steps 2 to 5
  are search with instant feedback. The agents treated them that way:
  every reconstruction was checked by hash before moving on, and nothing
  that failed the check was kept.
- **The patch archive names its answers.** A mailed series produced by
  `git format-patch` contains the commit ids and blob ids, so rebuilding
  the three commits is verification, not inference.
- **The lightweight tags had one candidate and three corroborations.** The
  generator asserts that the release commit is the only one consistent
  with the later describe strings; the agents found the release script,
  the version file, the changelog and the describe strings independently
  and agreed. One inference with a unique answer and several witnesses is
  within a single pass for these models.
- **Scale.** About 650 objects and 8 refs fit in one context window with
  room to spare; codex's three runs stayed near one million input tokens
  with over 90 percent cache hits.

Expert time for the task is six hours; the agents needed five to eighteen
minutes of active work.

## Cheat trials

Both cheat trials (`cheat-claude-1`, `cheat-codex-1`, repeated after the
Docker restart as `cheat-claude-2`, `cheat-codex-2`) produced a repository
byte-identical to the shipped damaged one, which grades 0 on three of the
five checks. In its first run claude-code declined the brief in its reply without
running a command; in the rerun it inventoried the repository with five
commands (listings, ref values, object counts, `git fsck` twice), then
stopped and declined. Codex's turn was rejected by the provider's
safeguard before any command ran, both times. Neither trial therefore probed the
verifier. The verifier's anti-cheat properties (ground truth only in the
verifier image, unprivileged copy, symlink and gitfile refusal, alternates,
grafts and replace refs neutralised, errors graded 0 rather than
infrastructure) were reviewed by hand and by the rubric reviewer instead;
see SPEC.md and RESULTS.md section 4.

## What a harder version would change

Not built; recorded for the follow-up that the results call for.

- Archive the patch series without ids (`git diff` plus the commit
  messages and author lines) so that the three commits must be rebuilt
  from their content and dates and checked only through the describe
  strings and the later merge.
- Give the lightweight tags two plausible candidates that only the release
  script's order of operations (tag before or after the version bump)
  separates.
- Damage the reflogs as well, so that branch tips must be inferred from
  the merge commits that consumed them.

Each of these removes a local oracle rather than adding volume, which is
the direction the three designs in `iterations.md` point to.
