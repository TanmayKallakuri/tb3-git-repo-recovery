#!/usr/bin/env python3
"""Copy a Harbor job directory into runs/<job> keeping only what the write-up
needs and nothing that could hold a secret or a local path.

Kept: the job-level result.json and log, every trial's result.json, trial.log,
the verifier output, the collected artifacts (minus vendored protobuf code)
and the agent's trajectory.json and console log (not the CLI's own session
state directory).  Dropped: config.json (holds the agent
env, scrubbed or not) and anything named auth or credentials.  Every kept
text file is scanned for the OAuth token in ~/.harbor/claude.env, for
`sk-ant-` / `sk-` style keys and for the codex auth.json path (a hit aborts),
and the local home directory is redacted to <home> (the tool, Python and
temp directories under it to <harbor-install>, <python-install>, <temp>).  In a provider
safeguard refusal everything after the refusal sentence (it describes the
account, not the trial) is replaced by a placeholder, and Claude Code's
`rate_limit_event` records (subscription state) are dropped from the
console logs.

Files ending in .json are redacted structurally: the bytes are parsed, redact()
is applied to every string value and dict key, and the file is written back
unchanged if nothing changed, otherwise re-serialised (indent 2).  A .json
file that does not parse aborts the run, and after copying every .json under
the target directory is parsed again; a failure aborts.  Redacting the raw
text of a JSON file can break its escaping, so it is never done.

    python3 scripts/trim-run.py gate-oracle gate-nop
"""
import json
import os
import pathlib
import re
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
JOBS = REPO / "jobs"
RUNS = REPO / "runs"
DROP_NAMES = {"config.json"}
DROP_PATTERNS = re.compile(r"auth|credential|secret|\.env$", re.IGNORECASE)
TOKEN_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
    re.compile(r"eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
]
USERNAME = os.environ.get("USERNAME") or os.environ.get("USER") or ""
# Harbor's codex agent logs the path of the auth file it uploads; the path is
# redacted (the file itself never enters a job directory).
AUTH_PATH = re.compile(r"\S*auth\.json\S*")
# A safeguard refusal continues with the account's programme eligibility and
# security settings; that text describes the account, not the trial.
REFUSAL_TAIL = re.compile(r'(flagged for possible cybersecurity risk\.)[^"\n]*')
REFUSAL_PLACEHOLDER = r"\1 <rest of the provider refusal message removed>"
# Harbor's exception text also carries a truncated copy of the same message
# that starts mid-sentence after a "[N chars truncated] ..." marker (or at a
# line start) and ends with the provider's closing boilerplate sentence.
REFUSAL_TAIL_TRUNCATED = re.compile(
    r'(^|\[\d+ chars truncated\] \.\.\. )[^"\n]*?Other safeguards still apply\.', re.MULTILINE
)
# Claude Code's console stream carries subscription telemetry records.
BILLING_EVENT = '"type":"rate_limit_event"'
HOME_FORMS = [
    "C:\\Users\\" + USERNAME,
    "C:\\\\Users\\\\" + USERNAME,
    "C:/Users/" + USERNAME,
    "/c/Users/" + USERNAME,
    "Users\\" + USERNAME,
    "Users/" + USERNAME,
]


def load_token() -> str:
    env = pathlib.Path.home() / ".harbor" / "claude.env"
    if not env.exists():
        return ""
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("CLAUDE_CODE_OAUTH_TOKEN="):
            return line.split("=", 1)[1].strip()
    return ""


def scan(path: pathlib.Path, text: str, token: str) -> None:
    if token and token in text:
        raise SystemExit(f"ABORT: OAuth token found in {path}")
    for pat in TOKEN_PATTERNS:
        if pat.search(text):
            raise SystemExit(f"ABORT: token-shaped string in {path}: {pat.pattern}")
    if "auth.json" in text and not AUTH_PATH.search(text):
        raise SystemExit(f"ABORT: unexpected auth.json mention in {path}")


def redact(text: str) -> str:
    if "auth.json" in text:  # the unanchored \S* pattern is quadratic on one-line files
        text = AUTH_PATH.sub("<codex-auth-file>", text)
    if "cybersecurity risk." in text:
        text = REFUSAL_TAIL.sub(REFUSAL_PLACEHOLDER, text)
    if "Other safeguards still apply." in text:
        text = REFUSAL_TAIL_TRUNCATED.sub(r"\1<rest of the provider refusal message removed>", text)
    if not USERNAME:
        return text
    for form in HOME_FORMS:
        text = text.replace(form, "<home>")
    # any remaining path form of the home directory (JSON-escaped, mixed separators)
    text = re.sub(r"(?i)[A-Za-z]:(?:\\|/)+Users(?:\\|/)+" + re.escape(USERNAME), "<home>", text)
    text = re.sub(r"(?i)/(?:mnt/)?c/Users/" + re.escape(USERNAME), "<home>", text)
    text = re.sub(r"(?i)Users(?:\\|/)+" + re.escape(USERNAME), "<home>", text)
    text = text.replace("C--Users-" + USERNAME + "-", "C--Users-<user>-")  # the desktop app's session-directory form
    # install and temp directories under the home directory (Harbor's uv tool
    # environment, the Python runtime, Harbor's compose temp files) carry no
    # secret but name the host's layout; any separator form, JSON-escaped too
    sep = r"(?:\\|/)+"
    text = re.sub(r"<home>" + sep + "AppData" + sep + "Local" + sep + "Packages" + sep + r"[^\\/\"]+" + sep + "LocalCache" + sep + "Roaming" + sep + "uv" + sep + "tools" + sep + "harbor", "<harbor-install>", text)
    text = re.sub(r"<home>" + sep + "AppData" + sep + "Local" + sep + "Programs" + sep + "Python" + sep + r"Python\d+", "<python-install>", text)
    text = re.sub(r"<home>" + sep + "AppData" + sep + "Local" + sep + "Temp", "<temp>", text)
    text = re.sub(r"<home>" + sep + "AppData" + sep + r"(?:Local|Roaming)", "<appdata>", text)
    return text


def redact_json_value(obj):
    if isinstance(obj, str):
        return redact(obj)
    if isinstance(obj, list):
        return [redact_json_value(v) for v in obj]
    if isinstance(obj, dict):
        return {redact(k): redact_json_value(v) for k, v in obj.items()}
    return obj


def redact_json_text(path: pathlib.Path, text: str) -> str:
    """Return the file's bytes as text, structurally redacted (original text if unchanged)."""
    try:
        obj = json.loads(text)
    except ValueError as exc:
        raise SystemExit(f"ABORT: {path} is not valid JSON before redaction: {exc}")
    new = redact_json_value(obj)
    if new == obj:
        return text
    return json.dumps(new, indent=2, ensure_ascii=False) + "\n"


def validate_json(dst: pathlib.Path) -> None:
    for q in sorted(dst.rglob("*.json")):
        try:
            json.loads(q.read_bytes().decode("utf-8"))
        except ValueError as exc:
            raise SystemExit(f"ABORT: published {q} does not parse: {exc}")


def render(path: pathlib.Path, data: bytes, token: str) -> bytes:
    """Return the bytes to publish for one kept source file (data containing a NUL byte or not decoding as UTF-8 is binary and copied exactly, unscanned and unparsed)."""
    if b"\x00" in data:
        return data
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    scan(path, text, token)
    if path.name == "claude-code.txt" and BILLING_EVENT in text:
        text = "".join(line for line in text.splitlines(keepends=True) if BILLING_EVENT not in line)
    if path.suffix == ".json":
        text = redact_json_text(path, text)
    else:
        text = redact(text)
    if USERNAME and re.search(r"(?i)Users(?:\\|/)+" + re.escape(USERNAME), text):
        raise SystemExit(f"ABORT: home path survives redaction in {path}")
    if "auth.json" in text:
        raise SystemExit(f"ABORT: auth.json survives redaction in {path}")
    return text.encode("utf-8")


def keep(path: pathlib.Path, rel: pathlib.Path) -> bool:
    """Whether the trim copies this source file."""
    if path.name in DROP_NAMES or DROP_PATTERNS.search(path.name):
        return False
    if any(DROP_PATTERNS.search(part) for part in rel.parts[:-1]):
        return False
    if "tfproto" in rel.parts or "sessions" in rel.parts or "setup" in rel.parts:
        return False
    if path.suffix in (".tar", ".gz", ".zip", ".pt", ".pkl", ".bin", ".npy", ".npz", ".h5", ".keras"):
        return False
    return True


def trim(job: str, token: str) -> None:
    src = JOBS / job
    dst = RUNS / job
    if not src.is_dir():
        raise SystemExit(f"no such job: {src}")
    if dst.exists():
        extra = [q for q in dst.rglob('*') if q.is_file() and not (src / q.relative_to(dst)).exists()]
        if extra:  # e.g. the rubric reviews' verdicts.json, written into runs/ by hand
            names = ', '.join(str(q.relative_to(dst)) for q in extra[:5])
            raise SystemExit(f'ABORT: {dst} holds files that did not come from {src}: {names}')
        shutil.rmtree(dst)
    kept = 0
    for path in sorted(src.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(src)
        if not keep(path, rel):
            continue
        data = path.read_bytes()
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(render(path, data, token))  # byte-exact: write_text would turn LF into CRLF on Windows
        kept += 1
    validate_json(dst)
    print(f"{job}: kept {kept} files under {dst.relative_to(REPO)}")


def main():
    token = load_token()
    for job in sys.argv[1:]:
        trim(job, token)


if __name__ == "__main__":
    main()
