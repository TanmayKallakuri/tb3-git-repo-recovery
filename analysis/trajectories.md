# Trajectory analysis: what the agents did, and where the task stopped them

The brief asks for three attempts per agent that genuinely fail. Version
1.0.0 stopped neither model: every completed attempt repaired the
repository exactly. Version 1.1.0 (two losses with no local oracle, the
witnesses out of the instruction) stopped claude-code in two of its three
attempts and codex in none. Version 1.2.1 carries the 1.2.0 design, in
which the sibling patterns point the wrong way for both losses, with one
added instruction clause. It stopped claude-code in two of three attempts
again; both completed codex attempts passed, the third was cut by the
subscription's usage window, and its replacement, run twice because the
replacement script was launched twice, passed both times. The shipped
version, 1.2.2, changes only the verifier's config check, and it grades
the eight 1.2.1 attempts and the claude-code cheat trial exactly as
recorded (RESULTS.md, "Version 1.2.2 (shipped)").

This file records the 1.2.1 trajectories first: the six attempts, the
two interruptions and the two replacement attempts, then the 1.2.0 codex
pilot, then the 1.2.1 cheat trials. Then come the 1.1.0 trajectories at
their decision points, the two
pilots in full and the four later attempts by what they did differently,
and the 1.0.0 analysis. The 1.1.0 and 1.0.0 sections are under their own
headings, unchanged except for cross-references, version labels and the
note on what 1.1.0 built from the 1.0.0 closing list.

Numbers come from the trajectories under `runs/` (`agent/trajectory.json`)
and from Harbor's results. The 1.2.1 table gives Harbor's agent-phase
time, as RESULTS.md does; step numbers refer to each trial's
`agent/trajectory.json`. In the 1.1.0 and 1.0.0 tables the "active" time
is the span from the first to the last trajectory step, which excludes
CLI start-up and session copying and is therefore shorter than the
agent-phase time in RESULTS.md.

## Version 1.2.1: the six attempts, and the 1.2.0 codex pilot

| Job / trial | Agent | Agent phase | Tool calls | Input tokens (cached) / output | Verdict |
|---|---|---|---|---|---|
| `run-codex-121` / `EfjWeTS` | codex gpt-6-astra xhigh | 5.7 min | 18 | 1.10M (1.04M) / 13k | 1.0 (5 of 5) |
| `run-codex-121` / `ynnvZxs` | codex | 6.7 min | 20 | 1.42M (1.32M) / 17k | 1.0 (5 of 5) |
| `run-codex-121` / `sweKZhw` | codex | 4.8 min, cut by the usage window | 15 | 883k (814k) / 11k | 0.0 (4 of 5), not counted |
| `run-codex-121b` / `JqpXXzg` | codex | 5.9 min | 22 | 1.61M (1.52M) / 15k | 1.0 (5 of 5) |
| `run-codex-121b` / `oj4orbL` | codex | 6.3 min | 21 | 1.27M (1.21M) / 15k | 1.0 (5 of 5) |
| `run-claude-121` / `w83Yrhe` | claude-code fable-5-1 max | 49.6 min | 55 | 3.26M (2.96M) / 186k | 0.0 (3 of 5) |
| `run-claude-121` / `rfCGPva` | claude-code | 42.2 min | 64 | 4.52M (4.20M) / 178k | 1.0 (5 of 5) |
| `run-claude-121` / `qA8XRxY` | claude-code | 21.7 min | 48 | 2.60M (2.40M) / 97k | 0.0 (3 of 5) |
| `pilot-codex-120` / `myvwxLc` (1.2.0) | codex | 6.3 min | 17 | 1.18M (1.11M) / 15k | 1.0 (5 of 5) |

Facts checked across the trials. `tools/archive-series.sh` has exactly
one blob in the whole history (`71a45c24`), so reading it at HEAD or at
the archive commit gives the same text; it contains `git rebase -q
--committer-date-is-author-date "$onto" "$branch"` and `git format-patch
-q --no-thread --zero-commit --no-signature`. The only reflog evidence for
`feature/retry-policy` is `logs/refs/remotes/mirror/feature/retry-policy`,
whose entries are the mirror cron's `update by push` up to `d13c784d`;
there is no `logs/refs/heads/feature/*`. The mirror's
`feature/cache-warmup` reflog last moved at 2026-10-13 02:00 UTC; the
archive commit `c3c89302` is dated 2026-10-15 10:28 UTC.

Where the attempts parted is the refs, and above all `feature/cache-warmup`.
Every agent-produced artifact graded in the `scripts/run-121.sh` pipeline
had a clean fsck, apart from the untouched repository of the codex cheat
run; the nop gate's repository fails fsck by design.

### Codex: `EfjWeTS`, reward 1.0

Twenty-five steps and eighteen tool calls in 5.7 minutes. It wrote its
helper scripts inside the repository, at `/app/repo.git/repair-evidence/`
(`recover.py`, `restore_valid.py`, `restore_patches.py`,
`restore_docs.py`, `restore_refs.py`, `verify_repair.py` and a
`README.md`), and left them there.

1. **Step 21, L1.** It applied the cache-warmup series onto the archive
   commit's parent with committer equal to the archive commit's committer
   and the author timestamp and zone, building the commits by hand, which
   gave `4a5aaf2c` and `1282507d`. It then re-exported them with `git
   format-patch --no-thread --zero-commit --no-signature` and compared the
   result with the archive byte for byte.
2. **L2.** Tagger equal to the release commit's committer, timestamp
   parsed from the CHANGELOG heading, the tag written with `git mktag`:
   `24fda256`.
3. **Refs.** One `update-ref --stdin` transaction with `-c
   core.logAllRefUpdates=false`; step 23 restored the original reflog
   bytes. The damaged pack was moved out of active storage.

The verifier staged 794 files, the helper scripts among them, and graded
5 of 5, since it compares refs and objects only and has no rule against
extra non-git files in the artifact; that is an observation, not a defect
of the grade.

### Codex: `ynnvZxs`, reward 1.0

Twenty-seven steps and twenty tool calls in 6.7 minutes, with its scripts
under `/app/recovery-work/`, outside the repository. Step 18 rebuilt the
archived 1.2 series with `git mailinfo`, `git apply --cached` and
hand-built commit bytes. Step 21 did the same for cache-warmup, with
committer equal to the archive commit's committer at the author date, and
built the tag from the release-time script and the CHANGELOG, giving
`1282507d` and `24fda256`. Step 25 wrote the refs in one `update-ref
--stdin` transaction, which appended reflog entries under a recovery
identity. The corrupt pack was replaced by a new verified pack.

### Codex: `sweKZhw`, cut by the usage window

Agent phase 18:37:57 to 18:42:46 UTC, last step at 18:42:26, trial ended
18:43:15; scripts under `/app/orbit-recovery/`. The output of the step-21
script reports both rebased commits reconstructed at `4a5aaf2c` and
`1282507d`, the archived patches matching the regenerated series byte for
byte, the tag reconstructed at `24fda256`, and the seven reconstructed
objects transferred into `/app/repo.git/objects`. Immediately after, the
console log records the provider's usage-limit error and the turn
failing. There is no `git update-ref`, ref file write or `packed-refs`
edit anywhere in the trajectory, so the verifier staged only the 9
surviving refs; fsck passed, every one of the original's 613 objects was
present, and only `test_refs_restored` failed. The answer was in hand when the quota ended
the run. It is not counted as an attempt; its replacement, run twice,
passed both times (next two sections).

### Codex: `JqpXXzg`, reward 1.0 (replacement, first launch)

Twenty-nine steps and twenty-two tool calls in 5.9 minutes, agent phase
23:14:39 to 23:20:33 UTC. Like `EfjWeTS` it worked inside the repository,
at `/app/repo.git/repair-work/`, where it first archived the damaged
repository as a tar file and saved the fsck output. Steps 10 to 17 took
the object store apart in Python: an inventory of both packs, `git
index-pack` tried on the damaged pack (exit 128) and both packs parsed by
hand instead, the damaged loose objects repaired by trying single-byte
changes until the object's own id matched. Step 18 printed
`tools/release.sh`, `tools/gen_api_docs.py` and `tools/archive-series.sh`
at the archive commit, with the `--committer-date-is-author-date` line,
and the release commits. Steps 20 to 24 rebuilt the archived series and
the cache-warmup pair from the patches, regenerated the API documentation
with the project's own generator, and built the tag with the recipe of
the earlier passes, the CHANGELOG heading's time `@1790655342 +0000`
included. Steps 25 and 26 checked the rebase by re-running it natively in
a scratch clone and comparing the `format-patch` export with the archive.
Step 27 ran `git fsck --full --strict` and listed every ref; step 28
removed the scratch directories and wrote a report. The refs were written
with `git update-ref`. It saw the mirror's `03d41e4d` and did not use it;
the verifier found `feature/cache-warmup` at `1282507d` and `v1.4.0` at
`24fda256`.

### Codex: `oj4orbL`, reward 1.0 (replacement, second launch)

Twenty-eight steps and twenty-one tool calls in 6.3 minutes, agent phase
23:14:36 to 23:20:51 UTC, with every script and a full copy of the
damaged repository under `/tmp/orbit-recovery/`, outside the repository.
The route is the same: `git index-pack` on the damaged pack fails (step
11), Python takes both packs apart (step 12), the damaged loose objects
are repaired by trying single-byte changes until the id matches (step
14), and an inspection module (step 15) walks trees by hand. Step 17
searched the `develop` reflog and its own graph dump for the release,
archive, retry and cache commits; steps 20 to 24 rebuilt the archived
series and the cache-warmup pair from the patches and the tag from the
CHANGELOG heading's time (`reconstruct.py`, `reconstruct_refs.py`); step
25 copied the repository to a verification clone and step 26 replayed the
rebase there natively (`validate_reconstruction.py`) before step 27
installed the objects and refs into `/app/repo.git` and wrote
`repair-report.json`. Its final message states that the surviving refs
and reflogs were left unchanged. It saw the mirror's `03d41e4d` and did
not use it; the verifier confirmed `1282507d` and `24fda256`.

### Claude-code: `w83Yrhe`, reward 0.0

Twenty-one steps and fifty-five tool calls in 49.6 minutes.

1. **Steps 10 and 11, the tooling at HEAD.** It listed `tools/` from
   `main` and printed `tools/archive-series.sh` and `tools/release.sh` at
   HEAD. The step-11 observation contains the
   `--committer-date-is-author-date` line. No agent message ever mentions
   rebasing the branch, and whether it noticed the flag is not visible in
   the trajectory. It never ran `git rebase` or `git am` for cache-warmup.
2. **Steps 12 to 15, the tag, right.** Step 12 saw the later diff that
   shortened the tag message. Step 14 read version 2 of
   `tools/release.sh` as the one in effect at v1.4.0. Step 15 built the
   tag with the release commit's committer name, the epoch from `date -u
   -d '2026-09-29 04:15:42 +0000' +%s` (1790655342), the message from the
   script's own sed expression over `CHANGELOG.md` at `cba733c4`, and
   `GIT_COMMITTER_DATE="@$epoch +0000" git tag -a -F ... v1.4.0
   cba733c4`, which gave `24fda256`.
3. **Steps 16 and 17, the branch evidence.** Step 16 compared the
   `orbit/cache.py` blobs across the candidate commits; step 17 read
   `ROADMAP` and the commit bodies.
4. **Step 18, the install.** It wrote the refs as files: `03d41e4d...`
   into `refs/heads/feature/cache-warmup` and `d13c784d...` into
   `refs/heads/feature/retry-policy`, copies of the two mirror tracking
   refs, and installed the tag with `git hash-object -t tag -w`. It also
   rebuilt the damaged pack byte-exact, with the trailer matching the
   pack's name.
5. **Step 21, the final message.** It took both feature branches from the
   mirror because the operations note describes nightly mirroring and the
   series file says the series was exported from that branch hours before
   the failure.

The verifier found `feature/cache-warmup` at `03d41e4d`, the mirror's
value, and 8 of the 613 objects unreachable from the expected refs.

Reading. This is the failure 1.2.0 was built to produce. Every check
available on surviving data confirms the mirror's pair: both patches match
it by author, date and subject, `format-patch` of it reproduces the
archive, and nothing dangles. The agent printed the script that says
otherwise and did not act on it, while it read the release script as of
the release commit and got the tag right.

### Claude-code: `rfCGPva`, reward 1.0

Twenty-three steps and sixty-four tool calls in 42.2 minutes.

1. **Step 6.** It read both scripts.
2. **Steps 7 to 9, the tag.** Step 7 read `tools/release.sh` at the
   release commit; step 8 gathered the source commit header, the
   CHANGELOG tail at `cba733c4` and `date -u -d "2026-09-29 04:15:42" +%s`
   = 1790655342; step 9 ran `git tag -a -F` with committer Dev Patel and
   `GIT_COMMITTER_DATE="@1790655342 +0000"` on `cba733c4`, which gave
   `24fda256`.
3. **Step 13, candidates.** It built candidate rebased trees with `git
   mktree`, swapping the `cache.py` blob in the archive parent's tree, and
   commits with `git commit-tree`, with `GIT_AUTHOR_*` from the patch
   `Date` lines, committer Mira Okafor and committer date equal to author
   date. That gave `4a5aaf2c` and `1282507d`, which it confirmed absent
   from the store. It also read `ROADMAP`, the series file and the commit
   bodies.
4. **Step 14, the round trip.** It noted that the patches' `index` line
   pre-image matches `cache.py` at both the mirror's base and the archive
   parent, regenerated the patches with `git format-patch -q --no-thread
   --zero-commit --no-signature`, and `cmp` showed both patches and the
   series file identical.
5. **Step 15, the native check.** With full object access, `git config
   user.name "Mira Okafor"` and `git rebase -q
   --committer-date-is-author-date "$onto" feature/cache-warmup` gave the
   tip `1282507d`; a cross-check with `git am -q
   --committer-date-is-author-date` as Mira gave the same ids.
6. **Step 21, the install.** The seven reconstructed loose objects and
   all refs as plain files; the damaged pack restored byte-exact.

The evidence its final message (step 23) cites: the mirror ref two days
stale, `tools/archive-series.sh` rebasing and force-pushing on October 15,
and the committer rule documented in the script.

### Claude-code: `qA8XRxY`, reward 0.0

Twenty-two steps and forty-eight tool calls in 21.7 minutes.

1. **Steps 2 to 14, the inventory and the tooling.** It inspected the
   refs and logs tree (steps 2 and 3), dumped every reflog (step 6),
   examined both packs and the dangling tags (step 7), read
   `tools/archive-series.sh` including the rebase flag (step 13) and
   version 2 of `tools/release.sh` (step 14).
2. **Steps 15 and 17, one series replayed.** It used `git am -q
   --committer-date-is-author-date` with the right committer name for the
   archived 1.2 series only, and the ids matched. It never attempted
   cache-warmup, `feature/retry-policy` or the three missing tags.
3. **Step 19.** It searched for `v1.2.1`, `v1.3.1` and `v1.4.0` outside
   `objects/` and found only `packed-refs`, and printed the CHANGELOG
   headings, which show all three.
4. **Step 20, the install.** It replaced the damaged pack with a new pack
   and wrote `develop`, `hotfix/1.2.1`, `v1.2.0` and `v1.3.0`; fsck exited
   0.
5. **Step 22, done at 20:19:09.** The final message says all 13 refs are
   back, explicitly declines to create `v1.2.1`, `v1.3.1` and `v1.4.0`
   because no tag object or ref record exists, and does not mention the
   feature branches.

The verifier found 13 of 18 refs, with `feature/cache-warmup`,
`feature/retry-policy`, `v1.2.1`, `v1.3.1` and `v1.4.0` missing, and 9 of
613 objects unreachable. These are the same five refs both failing 1.1.0
attempts left out: the agent read the scripts and the release headings
and stopped at a clean fsck, as the 1.1.0 pilot did.

### The 1.2.0 codex pilot: `myvwxLc`, reward 1.0

Twenty-four steps and seventeen tool calls in 6.3 minutes, on task commit
`0502a89`. "S7" below means step 7 of
`runs/pilot-codex-120/git-repo-recovery__myvwxLc/agent/trajectory.json`.

1. **S7 to S10, inventory.** `git fsck --full --strict` (995 error
   lines); an inventory, with the repository copied to
   `/app/recovery-work/original.git`; `git index-pack` on the unindexed
   pack, which failed on a corrupt object in the other pack; a Python
   zlib and SHA check of the loose objects and pack trailers; then
   `inspect_pack.py`, which parsed the damaged pack's index and found 37
   zeroed payloads with bad CRCs.
2. **S11 to S16, the objects.** `recover.py` repaired the six corrupt
   loose objects by single-byte search, parsed both packs and resolved
   deltas: 597 objects, 15 unresolved. `analyze.py` built the
   missing-object graph and the commit list and dumped every blob
   containing `From `, `git ` or `refs/`, which is where it read every
   version of `tools/release.sh`, `tools/archive-series.sh` and the patch
   files. `reconstruct.py` replayed the three archived 1.2 patches with
   `read-tree`, `apply --cached` and `write-tree`, asserting the hashes
   against the patch From lines, and regenerated `docs/API.md` by running
   the historical generator on exports of two release trees: 612 objects,
   0 unresolved.
3. **S17 to S19, the refs.** Tips, reflog endpoints, release commits, the
   `VERSION` and describe history, the archive commit's parent tree. Its
   S19 message says the branch was rebased after its last mirror update,
   so the mirror's tip is stale. The evidence visible before that
   message: the `tools/archive-series.sh` text (S14) describing the rebase
   onto HEAD, the force-with-lease push and the zero-commit patches; the
   series file saying it was exported from the tip of
   `feature/cache-warmup` (S15); the archive commit by Mira, whose parent
   equals `mirror/develop` and holds the script but no series directory;
   the mirror tip `03d41e4` and the last mirror update time
   (S17). Which fact was decisive is not visible. It read the script
   through its own Python tree walker over recovered objects, not with a
   git command.
4. **L1.** Committer from the archive commit's committer line (Mira
   Okafor); dates from the patch `Date` headers via `git mailinfo`, the
   same value for author and committer. It rebuilt the pair by replaying
   the two patches onto the archive commit's parent with hand-built commit
   objects, which gave `1282507d`. The verification was not a
   `format-patch` round trip: in S20 it ran a native `git checkout -b
   feature/cache-warmup 03d41e4...` and `git rebase -q
   --committer-date-is-author-date 8caad076...` as Mira in a disposable
   checkout and asserted HEAD == `1282507d`.
5. **L2.** `tools/release.sh` as of `cba733c` through the tree walker,
   version 2 with `git tag -a -F -`, asserted in S19. Date: the heading
   `## v1.4.0 - 2026-09-29 04:15:42 +0000` parsed to 1790655342 +0000;
   `SOURCE_DATE_EPOCH` read only as the script's mechanism. Tagger: the
   release commit's committer, Dev Patel. Message: the CHANGELOG bullets
   as of `cba733c`, not HEAD's. Verified with `git mktag` (S19) and with a
   native `git tag -a -F -` under `GIT_COMMITTER_DATE='@1790655342
   +0000'`, fed by the script's own sed expression (S20): `24fda256`. It
   did not re-create the release commit or re-run `tools/release.sh`, and
   it also checked the describe strings in three `VERSION` blobs against
   the reconstructed tags.
6. **S21 to S24, the install.** `install_repair.py` wrote the loose
   objects into `/app/repo.git`, quarantined the damaged pack, ran `git
   index-pack` on the other pack (which now succeeded), added the 9
   missing refs and asserted the non-object files byte-identical. S22:
   fsck clean, `for-each-ref`, `rev-list --objects --all --reflog
   --missing=error`, `verify-pack`. S23 wrote a `RECOVERY.md`; S24 is the
   final message: fsck exits 0 silently, 5 branches and 8 tags at their
   original objects, 619 objects verified, reflogs preserved, no history
   rewritten.

The verifier agrees: 613 reachable objects from the 13 refs, none missing
or extra. Scripts and `RECOVERY.md` are under `/app/recovery-work/`.

### Cheat trials (1.2.1)

`cheat-claude-121` (`pHijg4V`, claude-code with the hack prompt appended,
reward 0.0, 32.0 minutes). Step 2 is an empty response with no tool call;
step 3 is the harness notice that the response was stopped by a safety
classifier. At step 4 the agent declined the overlay in its own words and
began an ordinary survey. It made no attempt
against the verifier: no tool call touches `/tests`, `/run`, `curl`,
`wget` or any URL, and every write goes to `/app/repo.git` or `/tmp`,
where it kept a backup copy of the damaged repository. It restored
`develop` and `hotfix/1.2.1` from their reflog tails, `v1.2.0` and
`v1.3.0` from the dangling tag objects, `v1.2.1` and `v1.3.1` from the
describe strings in `VERSION` blobs, and `v1.4.0` correctly at step 15
with the same recipe as the passing attempts: the release commit's
committer, `@1790655342 +0000` and the CHANGELOG bullets at `cba733c4`.
Step 16 removed the corrupt pack and repacked into one pack. It missed
both feature branches. Step 12 read `tools/archive-series.sh` and used
the cache-warmup patches only as a control, reproducing the pre-rebase
pair; its stated reason at step 18 is that the feature branches exist only
as mirror tracking refs with no local reflogs, so it did not create local
heads, although at step 5 it had dumped every reflog, the mirror's
`feature/retry-policy` log included. The verifier found both feature
branches missing and 8 objects unreachable. The zero is the required
numerical outcome; the verifier was exercised by an honest partial
repair, not by a bypass attempt, and robustness evidence remains the
fixture set in `verifier-fixtures.md`.

`cheat-codex-121` (`LzQEsGz`): the turn started, the provider's
usage-limit error came back before the first tool call, and the agent
exited. The repository was left untouched, which grades 0 on three
checks; it is not a valid cheat trial. Its replacement, `cheat-codex-121b`,
ran twice because the replacement script was launched twice (`8vNBzqi`,
`bRiK3UE`), and both runs went the same way: the turn started, the
provider's safeguard rejected it before the first tool call, Harbor
recorded `AgentSafetyRefusalError`, and the verifier graded the untouched
repository 0.0, 2 of 5. That is the codex cheat outcome of 1.0.0 and
1.1.0 again: no bypass attempt, and the verifier not exercised by one.

### What a harder version would change, revisited again

1.1.0 built the first item of the 1.0.0 list below in a strong form, and
1.2.0 went further in the same direction: it did not thin the evidence,
it made the evidence an agent can verify on surviving data point at a
wrong answer that passes fsck. On 1.2.1 that stopped claude-code twice in
three attempts, once by the exact route 1.2.0 was built to make attractive
and once in the 1.1.0 pattern, and did not stop codex in any of its
four completed attempts.

Across the two full measurements, 1.1.0 and 1.2.1, the hardenings stopped
claude-code in two of three attempts each time and codex in none of its
completed attempts. The codex trajectories above show why. It reads every
tool as of every commit, treats what a script says the project did as what
happened, validates each reconstruction against a hash or a native
re-run, and on 1.2.0 and 1.2.1 it finished in under seven minutes of agent
time. A small, fully inspectable git repository in which everything lost
is recoverable from what remains, which is what makes the task correct
and oracle-free, does not produce three genuine codex failures; making the
evidence thinner would make the task guessable, which the brief forbids.
The design was frozen at 1.2.1, and the remaining effort went into
evidence and the write-up rather than another redesign.

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
verifier still ran). Both repositories byte-identical to the 1.1.0
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
byte-identical to the 1.0.0 damaged one, which grades 0 on three of the
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
hand and by the rubric reviewer (SPEC.md, RESULTS.md section 19). Evidence
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
