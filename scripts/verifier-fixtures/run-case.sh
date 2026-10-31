#!/bin/bash
# Runs inside the verifier image as root: builds one mutation of /tests/original at /app/repo.git with the
# image's own git, grades it with /tests/test.sh exactly as Harbor would, and prints one RESULT line.
#
#   bash /fixtures/run-case.sh <case>
#
# Exits non-zero only when the fixture itself cannot be built; the verifier's outcome is in the RESULT line.
set -euo pipefail
name="${1:?case name}"
repo=/app/repo.git
export HOME=/tmp/fixture-home LC_ALL=C GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
mkdir -p "$HOME"
rm -rf "$repo"
cp -r /tests/original "$repo"
chmod -R u+rwX "$repo"
g() { git --git-dir="$repo" "$@"; }

# Refs are discovered in the copy at run time, never named here. A missing ref is a fixture failure: exit 3, no
# RESULT line, so the runner reports INFRA.
die() { echo "fixture $name cannot be built: $*" >&2; exit 3; }
head_ref() {   # the branch HEAD points at
    local ref
    ref=$(g symbolic-ref HEAD) || die "HEAD is not a symbolic ref"
    case "$ref" in refs/heads/?*) printf '%s\n' "$ref" ;; *) die "HEAD points at $ref, not a branch" ;; esac
}
other_branch() {   # first branch (sorted) that is not HEAD's; with "parent", one whose tip also has a parent commit
    local head ref
    head=$(head_ref) || exit 3
    while IFS= read -r ref; do
        [ "$ref" = "$head" ] && continue
        if [ "${1:-}" = parent ]; then g rev-parse --verify -q "$ref^" >/dev/null 2>&1 || continue; fi
        printf '%s\n' "$ref"
        return 0
    done < <(g for-each-ref --format='%(refname)' refs/heads)
    die "no branch other than $head${1:+ with a parent commit}"
}
annotated_tag() {   # first annotated tag (sorted)
    local ref
    ref=$(g for-each-ref --format='%(refname) %(objecttype)' refs/tags | awk '$2 == "tag" { print $1; exit }') || die "cannot list tags"
    [ -n "$ref" ] || die "no annotated tag"
    printf '%s\n' "$ref"
}

case "$name" in
  unchanged) ;;
  repack) g repack -a -d ;;
  config-pager) printf '[core]
	pager = cat
' >> "$repo/config" ;;
  config-user-color) git config --file "$repo/config" user.name "Repair Bot"; git config --file "$repo/config" user.email repair@example.com; git config --file "$repo/config" color.ui auto ;;
  config-pack-gc) git config --file "$repo/config" pack.window 20; git config --file "$repo/config" gc.auto 0 ;;
  config-remote) git config --file "$repo/config" remote.backup.url /srv/git/backup.git; git config --file "$repo/config" remote.backup.fetch '+refs/heads/*:refs/remotes/backup/*' ;;
  branch-moved) b=$(other_branch parent) || exit 3; g update-ref "$b" "$b~1" ;;
  tag-deleted) t=$(annotated_tag) || exit 3; g update-ref -d "$t" ;;
  remote-ref-added) h=$(head_ref) || exit 3; g update-ref refs/remotes/injected/extra "$h" ;;
  replace-ref-added) h=$(head_ref) || exit 3; b=$(other_branch) || exit 3; g update-ref "refs/replace/$(g rev-parse "$h")" "$b" ;;
  notes-ref-added) h=$(head_ref) || exit 3; g update-ref refs/notes/commits "$h" ;;
  loose-object-deleted) python3 -I /fixtures/mutate.py delete-loose "$repo" ;;
  blob-rewritten) python3 -I /fixtures/mutate.py rewrite-blob "$repo" ;;
  config-invalid) printf '[core\n' >> "$repo/config" ;;
  config-hookspath) git config --file "$repo/config" core.hooksPath /tmp/hooks ;;
  config-extensions) git config --file "$repo/config" extensions.objectFormat sha1 ;;
  config-objectformat-sha256) git config --file "$repo/config" extensions.objectFormat sha256 ;;
  config-alternaterefs) git config --file "$repo/config" core.alternateRefsCommand /tmp/refs.sh ;;
  config-bare-false) git config --file "$repo/config" core.bare false ;;
  alternates) echo /tmp/elsewhere/objects > "$repo/objects/info/alternates" ;;
  symlink) rm "$repo/description"; ln -s HEAD "$repo/description" ;;
  grafts) h=$(head_ref) || exit 3; g rev-parse "$h" > "$repo/info/grafts" ;;
  shallow) h=$(head_ref) || exit 3; g rev-parse "$h" > "$repo/shallow" ;;
  promisor) pack=$(ls "$repo"/objects/pack/*.pack | head -n 1); touch "${pack%.pack}.promisor" ;;
  head-moved) b=$(other_branch) || exit 3; printf 'ref: %s\n' "$b" > "$repo/HEAD" ;;
  *) echo "unknown case: $name" >&2; exit 2 ;;
esac
echo "fixture $name built at $repo"

set +e
bash /tests/test.sh
rc=$?
set -e
python3 -I /fixtures/summary.py "$name" "$rc"
