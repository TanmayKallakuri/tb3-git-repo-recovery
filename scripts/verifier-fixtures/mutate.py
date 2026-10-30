"""Object-level mutations for the verifier fixtures, run inside the verifier image.

    python3 -I mutate.py delete-loose <repo>   remove one reachable object that exists only as a loose file
    python3 -I mutate.py rewrite-blob <repo>   overwrite one such loose blob with different content, same name
"""

import os
import subprocess
import sys
import zlib


def git(repo: str, *args: str, stdin: bytes = b"") -> subprocess.CompletedProcess:
    return subprocess.run(["git", f"--git-dir={repo}", *args], input=stdin, capture_output=True, check=False)


def head_branch(repo: str) -> str:
    """The branch HEAD points at, from symbolic-ref; exits (a fixture build failure) when HEAD is not on a branch."""
    head = git(repo, "symbolic-ref", "HEAD")
    ref = head.stdout.decode(errors="replace").strip()
    if head.returncode != 0 or not ref.startswith("refs/heads/"):
        sys.exit(f"HEAD is not a symbolic ref to a branch: {head.stderr.decode(errors='replace').strip()}")
    return ref


def loose_reachable(repo: str, want_type: str | None = None) -> list[tuple[str, str]]:
    """Objects reachable from HEAD's branch, in traversal order, whose loose file exists; optionally of one type."""
    listing = git(repo, "rev-list", "--objects", head_branch(repo), "--")
    if listing.returncode != 0:
        sys.exit(f"rev-list failed: {listing.stderr.decode(errors='replace')}")
    ids = [line.split()[0] for line in listing.stdout.decode(errors="replace").splitlines() if line.strip()]
    typed = git(repo, "cat-file", "--batch-check=%(objectname) %(objecttype)", stdin="".join(i + "\n" for i in ids).encode())
    types = dict(line.split() for line in typed.stdout.decode(errors="replace").splitlines() if len(line.split()) == 2)
    found = []
    for oid in ids:
        path = os.path.join(repo, "objects", oid[:2], oid[2:])
        if os.path.isfile(path) and (want_type is None or types.get(oid) == want_type):
            found.append((oid, path))
    return found


def only_loose(repo: str, oid: str, path: str) -> bool:
    """True when git can no longer find the object once its loose file is gone, i.e. no pack holds a copy."""
    aside = "/tmp/aside-" + oid
    os.rename(path, aside)
    try:
        return git(repo, "cat-file", "-e", oid).returncode != 0
    finally:
        os.rename(aside, path)


def delete_loose(repo: str) -> None:
    for oid, path in loose_reachable(repo):
        if only_loose(repo, oid, path):
            os.unlink(path)
            print(f"deleted loose object {oid}")
            return
    sys.exit("no object reachable from HEAD's branch exists only as a loose file")


def rewrite_blob(repo: str) -> None:
    for oid, path in loose_reachable(repo, "blob"):
        if only_loose(repo, oid, path):
            shown = git(repo, "cat-file", "blob", oid)
            if shown.returncode != 0:
                sys.exit(f"cat-file blob {oid} failed")
            content = shown.stdout + b"\ntampered\n"
            os.chmod(path, 0o644)
            with open(path, "wb") as target:
                target.write(zlib.compress(b"blob %d\0" % len(content) + content))
            print(f"rewrote loose blob {oid} in place with {len(content)} bytes of different content")
            return
    sys.exit("no blob reachable from HEAD's branch exists only as a loose file")


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in ("delete-loose", "rewrite-blob"):
        sys.exit(__doc__)
    action, repo = sys.argv[1], sys.argv[2]
    if action == "delete-loose":
        delete_loose(repo)
    else:
        rewrite_blob(repo)


if __name__ == "__main__":
    main()
