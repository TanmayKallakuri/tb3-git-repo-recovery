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

Result: (pending)

## 2. Oracle and nop (CI: the `/validate` job)

Commands:

```bash
harbor run -p tasks/git-repo-recovery -a oracle --env docker --yes --job-name gate-oracle-1
harbor run -p tasks/git-repo-recovery -a nop --env docker --yes --job-name gate-nop-1
```

Result: (pending)

## 3. Ground truth and the damage

The original repository and the damage are generated deterministically by
`scripts/gen-repo/` inside a container with the task images' git. The
generator records every damaged or lost item and its intended recovery
path in `tasks/git-repo-recovery/tests/damage.json` (never in the agent
image). (Counts pending.)

## 4. Implementation rubric

(pending)

## 5. Trials (`/run`) and cheat trials (`/cheat`)

(pending; one codex calibration attempt runs first)
