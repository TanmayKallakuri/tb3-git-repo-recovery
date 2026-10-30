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

case "$name" in
  unchanged) ;;
  repack) g repack -a -d ;;
  branch-moved) g update-ref refs/heads/feature/cache-warmup refs/heads/feature/cache-warmup~1 ;;
  tag-deleted) g update-ref -d refs/tags/v1.2.0 ;;
  remote-ref-added) g update-ref refs/remotes/injected/extra refs/heads/main ;;
  replace-ref-added) g update-ref "refs/replace/$(g rev-parse refs/heads/main)" refs/heads/develop ;;
  notes-ref-added) g update-ref refs/notes/commits refs/heads/main ;;
  loose-object-deleted) python3 -I /fixtures/mutate.py delete-loose "$repo" ;;
  blob-rewritten) python3 -I /fixtures/mutate.py rewrite-blob "$repo" ;;
  config-invalid) printf '[core\n' >> "$repo/config" ;;
  config-hookspath) git config --file "$repo/config" core.hooksPath /tmp/hooks ;;
  config-extensions) git config --file "$repo/config" extensions.objectFormat sha1 ;;
  config-bare-false) git config --file "$repo/config" core.bare false ;;
  alternates) echo /tmp/elsewhere/objects > "$repo/objects/info/alternates" ;;
  symlink) rm "$repo/description"; ln -s HEAD "$repo/description" ;;
  grafts) g rev-parse refs/heads/main > "$repo/info/grafts" ;;
  shallow) g rev-parse refs/heads/main > "$repo/shallow" ;;
  promisor) pack=$(ls "$repo"/objects/pack/*.pack | head -n 1); touch "${pack%.pack}.promisor" ;;
  head-moved) printf 'ref: refs/heads/develop\n' > "$repo/HEAD" ;;
  *) echo "unknown case: $name" >&2; exit 2 ;;
esac
echo "fixture $name built at $repo"

set +e
bash /tests/test.sh
rc=$?
set -e
python3 -I /fixtures/summary.py "$name" "$rc"
