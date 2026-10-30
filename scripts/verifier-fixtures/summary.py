"""Prints one RESULT line for a fixture case from the verifier's output files, plus a DETAIL line per failed check.

    python3 -I summary.py <case> <test.sh exit code>
"""

import json
import sys

VERIFIER = "/logs/verifier"


def main() -> None:
    name, rc = sys.argv[1], sys.argv[2]
    reward = "none"
    try:
        with open(f"{VERIFIER}/reward.txt", encoding="utf-8") as source:
            reward = source.read().strip() or "none"
    except OSError:
        pass
    failed = []
    try:
        with open(f"{VERIFIER}/ctrf.json", encoding="utf-8") as source:
            tests = json.load(source)["results"]["tests"]
        failed = [str(test.get("name", "")).rsplit("::", 1)[-1] for test in tests if test.get("status") != "passed"]
    except (OSError, ValueError, KeyError, TypeError):
        failed = ["(no ctrf report)"]
    messages = {}
    try:
        with open(f"{VERIFIER}/reward-details.json", encoding="utf-8") as source:
            messages = {check: result.get("message", "") for check, result in json.load(source).get("checks", {}).items()}
    except (OSError, ValueError, AttributeError):
        pass
    for check in failed:
        lines = str(messages.get(check, "")).splitlines()[:2]
        print(f"DETAIL {check}: {' | '.join(line.strip() for line in lines) or '(no message)'}")
    print(f"RESULT case={name} exit={rc} reward={reward} failed={','.join(failed) or '-'}")


if __name__ == "__main__":
    main()
