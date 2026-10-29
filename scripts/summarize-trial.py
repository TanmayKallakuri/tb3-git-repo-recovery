#!/usr/bin/env python3
"""Summarise every trial of one or more Harbor jobs for the write-up.

    python3 scripts/summarize-trial.py run-1 cheat-1 > analysis/trials.md

For each trial: agent, model, reward, exception, timings, token counts, the
number of tool calls, the verifier's per-check verdicts with the failing
checks' messages, the per-environment build results, and the agent's final
message (trimmed).  Reads jobs/<job>/ (or
runs/<job>/ when the job directory is gone).
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def trial_dirs(job):
    root = REPO / "jobs" / job
    if not root.is_dir():
        root = REPO / "runs" / job
    return sorted(p for p in root.iterdir() if p.is_dir() and (p / "result.json").exists())


def tool_calls(trial):
    traj = trial / "agent" / "trajectory.json"
    if not traj.exists():
        return 0, None
    try:
        data = load(traj)
    except Exception:
        return 0, None
    steps = data.get("steps", []) if isinstance(data, dict) else data
    n = 0
    final = None
    for s in steps:
        if not isinstance(s, dict):
            continue
        n += len(s.get("tool_calls") or [])
        if s.get("source") in ("agent", "assistant") and s.get("message"):
            final = s["message"]
    return n, final


def details(trial):
    rd = trial / "verifier" / "reward-details.json"
    if not rd.exists():
        return None
    d = load(rd)
    checks = {k: (v.get("ok"), v.get("message", "")) for k, v in (d.get("checks") or {}).items()}
    envs = {}
    for name, e in (d.get("environments") or {}).items():
        envs[name] = (e.get("returncode"), (e.get("sha256") or "")[:12], round(e.get("seconds") or 0, 1), e.get("reason") or "")
    return checks, envs, d.get("failed_checks"), d.get("total_seconds")


def span(d, key):
    s = d.get(key) or {}
    a, b = s.get("started_at"), s.get("finished_at")
    if not (a and b):
        return ""
    from datetime import datetime

    try:
        t0 = datetime.fromisoformat(a.replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(b.replace("Z", "+00:00"))
        return f"{(t1 - t0).total_seconds() / 60:.1f} min"
    except ValueError:
        return ""


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    for job in sys.argv[1:]:
        print(f"# Job `{job}`\n")
        for trial in trial_dirs(job):
            d = load(trial / "result.json")
            ai = d.get("agent_info") or {}
            ar = d.get("agent_result") or {}
            ex = d.get("exception_info") or {}
            reward = ((d.get("verifier_result") or {}).get("rewards") or {}).get("reward")
            n_calls, final = tool_calls(trial)
            print(f"## `{trial.name}`\n")
            print(f"- Agent: {ai.get('name')} / {(ai.get('model_info') or {}).get('name')}")
            print(f"- Reward: **{reward}**; exception: {ex.get('exception_type') or 'none'}")
            print(f"- Agent phase: {span(d, 'agent_execution')}; verifier: {span(d, 'verifier')}; total: {d.get('started_at', '')[11:19]} to {(d.get('finished_at') or '')[11:19]} UTC")
            print(f"- Tokens: {ar.get('n_input_tokens')} in / {ar.get('n_output_tokens')} out; tool calls: {n_calls}")
            det = details(trial)
            if det:
                checks, envs, failed, total = det
                print(f"- Checks ({sum(1 for ok, _ in checks.values() if ok)} of {len(checks)} passed, {total} s of builds): " + ", ".join(f"{k}={'ok' if ok else 'FAIL'}" for k, (ok, _) in checks.items()))
                for k, (ok, msg) in checks.items():
                    if not ok and msg:
                        print(f"  - {k}: {str(msg).replace(chr(10), ' | ')[:700]}")
                if envs:
                    print("- Environments: " + "; ".join(f"{k}: rc {rc} sha {sha} {sec}s{(' ' + why) if why else ''}" for k, (rc, sha, sec, why) in envs.items()))
            if final:
                text = str(final).strip().replace("\n", " ")
                print(f"- Final message: {text[:900]}{'...' if len(text) > 900 else ''}")
            print()


if __name__ == "__main__":
    main()
