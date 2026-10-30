#!/usr/bin/env bash
# Re-run the task's verifier on a recorded trial's collected artifact, locally.
#
#   scripts/regrade-local.sh <trial-dir> [<out-dir>]
#
# <trial-dir> is a Harbor trial directory (jobs/<job>/<task>__<id>) holding
# artifacts/app/repo.git. The verifier image is built from
# tasks/git-repo-recovery/tests, the artifact is copied in at /app/repo.git
# the way Harbor uploads it, /tests/test.sh runs, and the verifier output
# (reward.txt, ctrf.json, reward-details.json, git logs) is copied to
# <out-dir> (default: tmp/regrade/<trial-id>).
#
# Used when Harbor recorded the agent phase and collected the artifact but
# did not get to verification (RESULTS.md says which trials). The agent
# phase is never repeated.
set -euo pipefail
trial="${1:?trial dir}"
out="${2:-tmp/regrade/$(basename "$trial")}"
cd "$(dirname "$0")/.."
artifact="$trial/artifacts/app/repo.git"
[ -d "$artifact" ] || { echo "no artifact at $artifact" >&2; exit 2; }

image=grr-verifier-local
docker build -q -t "$image" tasks/git-repo-recovery/tests >/dev/null
cid=$(docker create "$image" bash -c 'bash /tests/test.sh; echo "test.sh exit=$?"; cat /logs/verifier/reward.txt 2>/dev/null || echo "no reward file"')
trap 'docker rm -f "$cid" >/dev/null 2>&1 || true' EXIT
docker cp "$artifact/." "$cid:/app/repo.git/"
docker start -a "$cid"
mkdir -p "$out"
docker cp "$cid:/logs/verifier/." "$out/"
echo "verifier output copied to $out"
python3 - "$out" <<'PY'
import json, sys, pathlib
out = pathlib.Path(sys.argv[1])
reward = (out / "reward.txt").read_text().strip() if (out / "reward.txt").exists() else "none"
print("reward:", reward)
ctrf = out / "ctrf.json"
if ctrf.exists():
    t = json.loads(ctrf.read_text())["results"]
    print("checks:", t["summary"]["passed"], "passed,", t["summary"]["failed"], "failed;",
          "failing:", [x["name"].rsplit("::", 1)[-1] for x in t["tests"] if x["status"] != "passed"])
PY
