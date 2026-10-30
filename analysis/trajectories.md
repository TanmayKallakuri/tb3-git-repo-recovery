# Trajectory analysis: what the agents did, and where the task stopped them

The brief asks for three attempts per agent that genuinely fail. Version
1.0.0 stopped neither model: every completed attempt repaired the
repository exactly. Version 1.1.0 (two losses with no local oracle, the
witnesses out of the instruction) stopped claude-code in two of its three
attempts and codex in none. This file records both: the 1.1.0
trajectories at their decision points first, the two pilots in full and
the four later attempts by what they did differently, then the 1.0.0
analysis under its own heading, unchanged except for the note on what
1.1.0 built from its closing list.

Numbers come from the trajectories under `runs/` (`agent/trajectory.json`);
the "active" time is the span from the first to the last trajectory step,
which excludes CLI start-up and session copying and is therefore shorter
than the agent-phase time in RESULTS.md.

## Version 1.1.0: the six attempts

| Job / trial | Agent | Active time | Tool calls | Input tokens (cached) / output | Verdict |
|---|---|---|---|---|---|
| `pilot-codex-h` / `m9wqtVr` | codex gpt-6-astra xhigh | 7.1 min (agent phase 7.4) | 14 | 924k (855k) / 12k | 1.0 (Harbor, 5 of 5) |
| `pilot-claude-h` / `w2hS6QT` | claude-code fable-5-1 max | 22.8 min (agent phase 22.9) | 39 | 4.46M (4.28M) / 100k | 0.0 (Harbor, 3 of 5) |
| `run-codex-h` / `FDY3d3q` | codex | 6.9 min (agent phase 7.1) | 17 | 1.08M (1.01M) / 12k | 1.0 (Harbor, 5 of 5) |
| `run-codex-h` / `wjs6dMz` | codex | 5.4 min (agent phase 5.6) | 14 | 984k (904k) / 11k | 1.0 (Harbor, 5 of 5) |
| `run-claude-h` / `CMQWEQW` | claude-code | 24.9 min (agent phase 25.0) | 45 | 6.43M (6.23M) / 102k | 0.0 (Harbor, 3 of 5) |
| `run-claude-h` / `kLSoSqt` | claude-code | 24.7 min (agent phase 24.8) | 38 | 4.41M (4.21M) / 109k | 1.0 (Harbor, 5 of 5) |

All six attempts did the salvage the same way the 1.0.0 attempts did (the six
moves below under "The skeleton every passing trajectory followed"): own
pack parser, index CRCs against the pack bytes, intact entries written out,
delta dependents recombined, single-byte repair of the six corrupt loose
objects in under half a second each, the three archived 1.2 commits
rebuilt and checked against the ids in their From lines, `docs/API.md`
regenerated at the release trees and checked by hash, the missing pack
index recreated. Where they parted is the refs.

### Codex: `pilot-codex-h`, reward 1.0

Fourteen tool calls, each a script of several commands. The decision
points:

1. **Step 8, the inventory read everything that is not an object.** Its
   second call printed every file under the repository outside
   `objects/??/`: `HEAD`, `config` (the `mirror` remote with its fetch
   spec), `packed-refs`, every loose ref including the five under
   `refs/remotes/mirror/`, and every reflog. It also copied the damaged
   repository aside before touching it.
2. **Step 14, it read the project's tooling at HEAD, all of it.** After the
   salvage it printed `tools/archive-series.sh`, `tools/release.sh`,
   `tools/gen_api_docs.py`, `docs/patches/cache-warmup/series`, the
   cache-warmup patch, the three 1.2 patches and `CHANGELOG.md`, and
   dumped every commit's text sorted by date into one file. Its message at
   this point: the remaining gaps "appear to be recoverable from archived
   patches, generated documentation, and surviving Git deltas", and it was
   checking those "alongside the evidence for the missing refs".
3. **Step 15, it read `tools/release.sh` as of the 1.4.0 release commit**,
   not as of HEAD (`git show <release commit>:tools/release.sh`), together
   with the trees of the series' base commit, the mirror's two feature
   tips and the one dangling tree fsck reported.
4. **Step 18, it named the two reconstructions before doing them.** Its
   message: the ref recovery "still needs two reconstructions: the
   cache-warmup branch advanced beyond the mirror's recorded tip, and the
   missing v1.4.0 tag used an older release-script format". The same call
   printed `tools/release.sh` as of the 1.3.0 release too (to see the
   format change), every release commit with its `VERSION` content and
   committer line, and `git log --all -- tools/archive-series.sh
   tools/release.sh docs/patches`.
5. **Step 19, the reconstruction script.** For L1 it replayed the
   cache-warmup series on the merge base with `git mailinfo`, `git apply
   --cached` and `write-tree`, built the commit objects itself with
   committer equal to author and the header's date, asserted that the
   first patch reproduces the mirror's commit and that the second patch's
   tree equals the dangling tree, and pointed the branch at the rebuilt
   commit. For L2 it took the release commit's committer line as the
   tagger, the `## v1.4.0` section of `CHANGELOG.md` at that commit for
   the message (`orbit v1.4.0`, a blank line, the bullet lines), and
   wrote the tag object with `git mktag`. The lightweight tags went on the
   `Release v1.2.1` and `Release v1.3.1` commits from the release listing
   of step 18; `develop` and `hotfix/1.2.1` came from the last reflog
   line, `feature/retry-policy` from the mirror. All nine refs were
   created in one `update-ref --stdin` transaction after an assertion that
   none of them existed.
6. **Step 20, the self-check.** `show-ref` against its own expected list,
   every object re-hashed, `HEAD`, `config`, `description`, `packed-refs`
   and every surviving ref byte-identical to its copy, the archived series
   reproduced byte for byte by `format-patch --no-thread --zero-commit
   --no-signature` from the restored tip, fsck clean, zero unreachable
   objects, 610 objects (158 commits, 276 trees, 171 blobs, 5 tags), 5
   branches, 8 tags.

It left its scripts, a copy of the damaged repository and a validation
report under `/app/orbit-recovery/` (outside the artifact) and quarantined
the damaged pack after writing its contents out loose; the artifact graded
5 of 5. Both hidden targets were right the first time; nothing in the
trajectory was retried.

### Claude-code: `pilot-claude-h`, reward 0.0

Thirty-nine tool calls over 22.8 minutes. It did more object work than
codex and less ref work. The decision points:

1. **Steps 2 to 8, the inventory was complete.** `ls`, `HEAD`, `config`,
   `packed-refs`, the refs tree with all five mirror refs, the logs tree,
   and the full text of every reflog including the mirror's (whose entries
   read `update by push` by `mirror cron`), then a backup copy. It had the same evidence in front of
   it that codex had at step 8.
2. **Steps 9 to 15, the salvage**, as above, into a scratch repository;
   506 intact entries of the damaged pack written out, 41 failed (the 37
   zeroed entries and four deltas on them).
3. **Step 16, the first ref decision.** It wrote a `packed-refs` for the
   scratch repository with the surviving refs only: `main`, the two
   branches whose reflogs survive, the five mirror refs, the three tags
   `packed-refs` still held. fsck in the scratch repository then listed
   what was missing.
4. **Steps 22 to 26, it found and read the oracle-free evidence.** It
   listed `docs/patches/` in the `main` tree, printed the three 1.2
   patches (From lines with ids), then printed both cache-warmup patches
   (From lines all zeros) and the series file ("exported from the tip of
   feature/cache-warmup"), read `tools/gen_api_docs.py`,
   `tools/archive-series.sh` and the `Makefile` at HEAD, listed the
   dangling tree and its `orbit` subtree, and resolved the abbreviated
   blob ids in every patch's `index` lines, including the second
   cache-warmup patch's post-image, which exists in the repository as a
   dangling blob. It did not read `tools/release.sh`, `VERSION`,
   `CHANGELOG.md` or `docs/operations.md`, and it never ran `git
   describe`. In every 1.0.0 attempt, when the instruction named the
   mirror and the release script, it read them.
5. **Steps 27 to 30, the hash-checked rebuilds.** The 1.2 series by hash
   (every blob, tree and commit reported `MATCH`), `docs/API.md` by hash
   at every commit that has the generator. Then its census: the set of
   ids the damaged repository names (547 in the pack index plus 61 loose)
   against the scratch store: 608 of 608 present, none extra. That number
   is the oracle-free design doing its work: the two hidden targets are
   the two objects no id in the repository names, so an id census cannot
   miss them.
6. **Steps 31 to 33, work the task did not ask for.** It re-implemented
   git's delta encoder (`diff-delta.c`) in Python, validated it against
   all 300 intact deltas in the pack, and rewrote the zeroed payloads at
   zlib level 6 so that the damaged pack's trailer checksum recomputed to
   the original and the regenerated index was byte-identical to the
   original. About two and a half minutes of the run; correct, and not
   graded.
7. **Step 34, the install.** The restored pack, the recreated index, the
   six repaired loose objects, and four refs written as files: `develop`
   and `hotfix/1.2.1` at their reflogs' last value, `v1.2.0` and `v1.3.0`
   at the two dangling tag objects. fsck exit 0 with one dangling tree.
8. **Steps 35 to 40, the self-check**, thorough for what it had decided
   to restore: ref tips against reflog tails, history lengths, the 608-id
   census again, `verify-pack` on both packs, a file-level diff against
   its backup, an archive listing per ref, a final fsck.
9. **Step 41, the final message**, which reports success and names only
   the four refs it restored. Under "Deliberately not done" it says that no
   local `feature/*` branches were created because only remote-tracking
   refs for them exist and "there is no reflog or other evidence they were
   ever local branches"; that the cache-warmup series "contains a commit
   that never existed in this repository, with all-zero commit IDs" and
   was left alone; and that the dangling tree "predates the failure" and
   is informational.

The verifier's reasons (`runs/pilot-claude-h/git-repo-recovery__w2hS6QT/verifier/`):
five expected refs absent, `feature/cache-warmup` (L1), `v1.4.0` (L2),
`feature/retry-policy` (R2), `v1.2.1` and `v1.3.1` (R3); `rev-list` from
the two hidden targets fails with `bad object`; 9 of the original's 610
reachable objects are not reachable from the expected refs (the L1 commit
with its root tree, `orbit` subtree and `cache.py` blob, the L2 tag, and
the four objects that only the lost branch's earlier commit reaches). All
nine objects except the two hidden ones are physically present in the
artifact; they are unreachable because the branch that reaches them is
missing.

Reading. The failure is on exactly the elements 1.1.0 changed. The agent
did not miss the evidence; it found the mirror refs, the series file, the
zero-id patch and the dangling tree, and reasoned its way to leaving them
alone. The instruction is complete: it states the end state, and the
evidence that settles the open questions is in the repository, which the
agent did not inspect. That evidence is `docs/operations.md` (the mirror
is a nightly push of the local branches, which makes a mirror ref without
a local counterpart a lost local branch, not a remote-only one), the
`refs/remotes` refs and the mirror reflogs' `update by push` entries by
`mirror cron` (which the agent printed in step 6), the `VERSION` describe
strings, the series file, and the history of `tools/release.sh` (which
leads to the lightweight tags and the 1.4.0 tag format). Codex read the
tooling as a matter of course; in this attempt claude-code read only the
tools the fsck errors pointed at. Its two later
attempts, below, split: one read more and still stopped, one read the
same things codex read and passed.

### The four later attempts, by what they did differently

Codex `FDY3d3q` (7.1 min, 17 calls) and `wjs6dMz` (5.6 min, 14 calls)
followed the pilot's route without a detour: own pack parser, the loose
objects repaired by hash, the 1.2 series and `docs/API.md` rebuilt by
hash, then the project's tooling read, including `tools/release.sh` as of
the 1.4.0 release commit (`git show <commit>:tools/release.sh` in both),
the cache-warmup series replayed on the mirror's commit with `write-tree`,
and the tag built in the v2 format with `git mktag`. Each said the same
thing in its own words before the ref step: the cache-warmup archive
records a commit newer than the mirror's tip, and the release script
preserved at the 1.4.0 release shows how to rebuild the annotated tag
with its release notes. Both hidden targets right in both; `FDY3d3q` left
its scripts and report under `recovery/` inside the repository,
`wjs6dMz` outside it.

Claude-code `CMQWEQW` (25.0 min, 45 calls, reward 0.0) went further than
the pilot and stopped in the same place. It read the cache-warmup series
file and both patches and compared the first against the mirror's commit
(step 24), extracted the v1.3.0 tree to read `tools/release.sh`, `VERSION`
and `CHANGELOG.md` as of that release (steps 28 and 29), regenerated both
lost `docs/API.md` versions by hash, replayed the 1.2 series with `git
am` and matched the three ids, inspected the dangling tree and worked out
which archived patch it corresponds to (step 33), and ran the 608-id
census (step 34). It then wrote the same four refs the pilot wrote. Its
final message lists, under what it deliberately did not do, the mirror's
feature branches (no local reflog) and the point releases `v1.2.1`,
`v1.3.1` and `v1.4.0` (no tag object or ref trace), and calls the archived
"cache size limit" state never pushed. Same five refs missing, same 9
objects unreachable, same two checks failed as the pilot.

Claude-code `kLSoSqt` (24.8 min, 38 calls, reward 1.0) is the one passing
claude-code attempt. The difference is where it looked between its salvage
and its ref decisions: step 26 read the 1.2 patches, `tools/archive-series.sh`
and the series file; step 27 read `tools/release.sh`, the generator and
`CHANGELOG.md` at HEAD; step 28 listed every loose object's type and the
`VERSION` blob at every release commit; step 29 read `tools/release.sh`
as of the 1.4.0 release commit (`git show <release commit>:tools/release.sh`)
and the diffs between the script's three versions with the commits that
changed it; step 30 read both cache-warmup patches and the release commit
header; step 31 ran `diff-tree` between the mirror commit's tree and the
dangling tree to confirm the second patch is exactly the difference. Its
first hand-built 1.2 commits hashed wrong (step 33); it then searched the
committer timestamp for each (step 34), found every hit at offset zero,
and took that as the convention for the one commit it could not check.
Step 35 wrote the three verified 1.2 commits, the unverified L1 commit,
the API blobs and the tag; steps 36 to 39 installed them, put every
object into one new pack, wrote the nine refs (`feature/retry-policy` from
the mirror, the lightweight tags on the release commits from the release
script's rule and the describe strings in `VERSION`), reproduced the 1.2
series byte for byte with `format-patch`, removed the stale `info/refs`
and finished with a clean fsck. Its final message names the two refs that
rest on reconstruction rather than hash verification.

### Cheat trials (1.1.0)

`cheat-claude-h` (`AZor9ML`): 1.2 minutes, four tool calls, all
inventory; the run was stopped by a safety classifier at step 6
(stop_reason refusal), after its inventory steps, and the agent then
declined.
`cheat-codex-h` (`TBSMyN8`): 0.2 minutes, no tool call, the provider's
safeguard rejected the turn (`AgentSafetyRefusalError` recorded; the
verifier still ran). Both repositories byte-identical to the shipped
damaged one, both rewards 0.0 as required; neither exercised the verifier,
so robustness evidence remains the fixture set in `verifier-fixtures.md`.

### What a harder version would change, revisited

The 1.0.0 list below proposed three changes. 1.1.0 built the first in a
stronger form (a series with zero ids whose commit also has no ref, no
reflog and no mirror value, plus a tag whose format only the historical
script gives), and did not build the second (two candidates for a
lightweight tag) or the third (damaged reflogs). The six attempts say the first
change was enough to stop claude-code twice and not enough to stop codex
once.

## Version 1.0.0 (superseded)

On version 1.0.0 every completed attempt by either agent repaired the
repository exactly. This section records what each trajectory did, where
the intended difficulty went, and what the cheat trials showed.

### Completed attempts

| Job / trial | Agent | Active time | Tool calls | Input tokens (cached) / output | Verdict |
|---|---|---|---|---|---|
| `calib-codex-1` / `fMzUFjy` | codex gpt-6-astra xhigh | 5.8 min | 12 | 747k (689k) / 11k | 1.0 (Harbor) |
| `run-codex-2` / `tuj86CM` | codex | 6.4 min | 19 | 1.13M (1.06M) / 14k | 1.0 (local, same verifier image) |
| `run-codex-3` / `UYLvXPg` | codex | 5.3 min | 16 | 1.00M (930k) / 13k | 1.0 (local) |
| `run-claude-2` / `QUrYTyh` | claude-code fable-5-1 max | 18.4 min | 36 | 3.93M (3.75M) / 79k | 1.0 (local) |
| `run-claude-3` / `TpwXpFT` | claude-code | 22.4 min | 49 | 3.34M (3.11M) / 100k | 1.0 (Harbor) |
| `run-claude-3` / `ThewbT7` | claude-code | 21.4 min | 40 | 4.64M (4.46M) / 90k | 1.0 (Harbor) |

### The skeleton every passing trajectory followed

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

### Where the difficulty went

- **Object recovery has a perfect local oracle.** The design relied on
  there being no oracle for the *refs*, and that holds; but all 43 of the
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
- **Scale.** About 579 objects and 8 refs fit in one context window with
  room to spare; codex's three runs stayed near one million input tokens
  with over 90 percent cache hits.

Expert time for the task is six hours; the agents needed 5.3 to 22.4
minutes of active work.

### Cheat trials (1.0.0)

Both cheat trials (`cheat-claude-1`, `cheat-codex-1`, repeated after the
Docker restart as `cheat-claude-2`, `cheat-codex-2`) produced a repository
byte-identical to the shipped damaged one, which grades 0 on three of the
five checks, so both trials scored 0.0 as the brief requires. In its first run (`P2sYSqB`) claude-code ran no command: a safety
classifier stopped the run at step 2 (stop_reason refusal) and the agent
then declined the brief; in the rerun (`N2vu4vc`) it inventoried the
repository with five commands (listings, ref values, object counts, `git
fsck` twice), was stopped by the classifier at step 7, and the agent then
declined. Codex's turn was rejected by the provider's
safeguard before any command ran (Harbor recorded `AgentSafetyRefusalError`),
both times. Neither trial exercised the verifier, so the zero rewards show
the required numerical outcome, not adversarial robustness. The verifier's
anti-cheat properties (ground truth only in the verifier image, unprivileged
copy, symlink and gitfile refusal, alternates, grafts and replace refs
neutralised, errors graded 0 rather than infrastructure) were reviewed by
hand and by the rubric reviewer (SPEC.md, RESULTS.md section 11). Evidence
from running the verifier against bypass attempts comes from the mutation
fixtures in `scripts/verifier-fixtures.sh`, with results recorded in
`analysis/verifier-fixtures.md`. The 1.1.0 cheat trials are above.

### What a harder version would change (written against 1.0.0)

Recorded before 1.1.0 was built; see "revisited" above for what was
built.

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
