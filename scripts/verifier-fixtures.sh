#!/usr/bin/env bash
# Mutation fixtures for the verifier: build the verifier image, then grade a set of scratch repositories, each a
# fresh copy of tests/original changed in exactly one way, and compare every reward with the one it must get.
#
#   scripts/verifier-fixtures.sh [case ...]        (no arguments: every case)
#
# Each case runs in its own container of the verifier image: scripts/verifier-fixtures/run-case.sh builds the
# mutation there with the image's git, /tests/test.sh grades it the way Harbor does, and the verifier output is
# copied to tmp/verifier-fixtures/<case>/. Prints a table (case, expected, observed, status, the check
# that must fail, the failed checks observed). A 0 without the expected check among them is MISMATCH.
# INFRA means the container or the verifier itself failed and no reward was produced; it is never counted as 0.
# Exits non-zero when any case is MISMATCH or INFRA.
# VERIFIER_FIXTURES_TESTS, VERIFIER_FIXTURES_IMAGE and VERIFIER_FIXTURES_OUT override the tests directory the
# image is built from, the image tag and the output directory (used to grade an older verifier on the same cases).
# No bind mounts (Windows path mangling): files travel with docker cp, so this works on Docker Desktop and Linux.
set -uo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
TESTS="${VERIFIER_FIXTURES_TESTS:-$ROOT/tasks/git-repo-recovery/tests}"
FIXTURES="$HERE/verifier-fixtures"
OUT="${VERIFIER_FIXTURES_OUT:-$ROOT/tmp/verifier-fixtures}"
IMAGE="${VERIFIER_FIXTURES_IMAGE:-grr-verifier-fixtures}"

# "<case> <expected reward> <check>"; the check is the name that must be among the failed checks of every 0-case
# ("-" for the cases that must pass). The mutations themselves live in verifier-fixtures/run-case.sh.
CASES=(
  "unchanged 1 -"
  "repack 1 -"
  "config-pager 1 -"
  "config-user-color 1 -"
  "config-pack-gc 1 -"
  "config-remote 1 -"
  "branch-moved 0 test_refs_restored"
  "tag-deleted 0 test_refs_restored"
  "remote-ref-added 0 test_no_history_rewrite"
  "replace-ref-added 0 test_no_history_rewrite"
  "notes-ref-added 0 test_no_history_rewrite"
  "loose-object-deleted 0 test_fsck_clean"
  "blob-rewritten 0 test_fsck_clean"
  "config-invalid 0 test_artifact_staged"
  "config-hookspath 0 test_artifact_staged"
  "config-extensions 0 test_artifact_staged"
  "config-objectformat-sha256 0 test_artifact_staged"
  "config-alternaterefs 0 test_artifact_staged"
  "alternates 0 test_artifact_staged"
  "symlink 0 test_artifact_staged"
  "grafts 0 test_artifact_staged"
  "shallow 0 test_artifact_staged"
  "promisor 0 test_artifact_staged"
  "config-bare-false 0 test_artifact_staged"
  "head-moved 0 test_refs_restored"
)

hostpath() {
    if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else printf '%s' "$1"; fi
}
export MSYS_NO_PATHCONV=1

selected=()
for wanted in "$@"; do
    known=0
    for entry in "${CASES[@]}"; do
        [ "${entry%% *}" = "$wanted" ] && known=1
    done
    if [ "$known" -eq 0 ]; then
        echo "unknown case: $wanted (known: $(printf '%s\n' "${CASES[@]}" | cut -d' ' -f1 | tr '\n' ' '))" >&2
        exit 2
    fi
    selected+=("$wanted")
done

if ! docker version --format '{{.Server.Os}}' >/dev/null 2>&1; then
    echo "docker is not reachable; start Docker Desktop (Linux containers) or the docker daemon" >&2
    exit 2
fi
if ! docker build -q -t "$IMAGE" "$(hostpath "$TESTS")" >/dev/null; then
    echo "building the verifier image from $TESTS failed" >&2
    exit 2
fi
image_id=$(docker image inspect --format '{{.Id}}' "$IMAGE")
base_image=$(grep -m1 '^FROM' "$TESTS/Dockerfile" | awk '{print $2}')
git_version=$(docker run --rm "$IMAGE" git --version 2>/dev/null || echo "unknown")
echo "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "verifier image: $IMAGE $image_id"
echo "base image: $base_image"
echo "git in the image: $git_version"
echo "output: $OUT"
echo

rows=()
bad=0
total=0
for entry in "${CASES[@]}"; do
    read -r name expected check <<<"$entry"
    if [ "${#selected[@]}" -gt 0 ]; then
        wanted=0
        for pick in "${selected[@]}"; do [ "$pick" = "$name" ] && wanted=1; done
        [ "$wanted" -eq 1 ] || continue
    fi
    total=$((total + 1))
    dir="$OUT/$name"
    rm -rf "$dir"
    mkdir -p "$dir/verifier"
    log="$dir/run.log"
    observed=none
    failed=-
    cid=$(docker create "$IMAGE" bash /fixtures/run-case.sh "$name" 2>>"$log")
    if [ -n "$cid" ]; then
        if docker cp "$(hostpath "$FIXTURES")" "$cid:/fixtures" >>"$log" 2>&1; then
            docker start -a "$cid" >>"$log" 2>&1
            echo "container exit=$?" >>"$log"
        fi
        docker cp "$cid:/logs/verifier/." "$(hostpath "$dir/verifier")" >/dev/null 2>&1 || true
        docker rm -f "$cid" >/dev/null 2>&1 || true
        result=$(grep '^RESULT ' "$log" | tail -n 1)
        if [ -n "$result" ]; then
            observed=$(printf '%s\n' "$result" | sed -n 's/.* reward=\([^ ]*\).*/\1/p')
            failed=$(printf '%s\n' "$result" | sed -n 's/.* failed=\([^ ]*\).*/\1/p')
        fi
    fi
    case "$observed" in
        0|1)
            status=PASS
            [ "$observed" = "$expected" ] || status=MISMATCH
            # A 0 for the wrong reason is a mismatch: the expected check must be among the failed ones.
            if [ "$status" = PASS ] && [ "$check" != "-" ]; then
                case ",$failed," in *",$check,"*) ;; *) status=MISMATCH ;; esac
            fi ;;
        *) observed=none; status=INFRA; failed=- ;;
    esac
    [ "$status" = PASS ] || bad=$((bad + 1))
    rows+=("$name|$expected|$observed|$status|$check|$failed")
    printf '%-22s expected %s  observed %-4s  %s  failed=%s\n' "$name" "$expected" "$observed" "$status" "$failed" >&2
    if [ "$status" = INFRA ]; then
        echo "  log tail ($log):" >&2
        tail -n 8 "$log" | sed 's/^/    /' >&2
    fi
done

echo
printf '| %-22s | %-8s | %-8s | %-8s | %-24s | %s |\n' case expected observed status "must fail" "failed checks (observed)"
printf '|%s|%s|%s|%s|%s|%s|\n' "$(printf -- '-%.0s' $(seq 24))" "$(printf -- '-%.0s' $(seq 10))" \
    "$(printf -- '-%.0s' $(seq 10))" "$(printf -- '-%.0s' $(seq 10))" "$(printf -- '-%.0s' $(seq 26))" \
    "$(printf -- '-%.0s' $(seq 26))"
for row in "${rows[@]}"; do
    IFS='|' read -r name expected observed status check failed <<<"$row"
    printf '| %-22s | %-8s | %-8s | %-8s | %-24s | %s |\n' "$name" "$expected" "$observed" "$status" "$check" "$failed"
done
echo
echo "$total cases, $bad not as expected"
[ "$bad" -eq 0 ]
