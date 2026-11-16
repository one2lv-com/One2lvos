#!/bin/bash
# tag_known_good.sh — run every test suite; only if ALL pass, tag HEAD as working-YYYYMMDD (item 17).
# Used by the 4 AM run before the push. Prints one PASS/FAIL line per suite. Exit 0 = tagged (or already tagged).
# Usage: tools/tag_known_good.sh [--dry-run]
set -u
cd "$(dirname "$0")/.." || exit 2
PY=.venv/bin/python3; [ -x "$PY" ] || PY=python3
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "FAIL: uncommitted changes; commit first (nothing tagged)"; exit 1
fi
fail=0
for t in tests/test_tool_engine.py tests/test_whodat.py tests/test_vision.py tests/test_nimlab_tools.py \
         tests/test_reactor_layers.py tests/test_ai_lobby.py tests/test_dream_checks.py tests/test_gaming.py; do
  [ -f "$t" ] || { echo "MISSING $t"; fail=1; continue; }
  out=$(timeout 900 "$PY" "$t" 2>&1); rc=$?
  last=$(echo "$out" | grep -E "passed|failed|PASS|FAIL" | tail -1)
  if [ $rc -eq 0 ]; then echo "PASS $t  $last"; else echo "FAIL $t (exit $rc)  $last"; fail=1; fi
done
if [ -f tests/voice_test.py ]; then
  out=$(timeout 600 "$PY" tests/voice_test.py 2>&1); rc=$?
  if [ $rc -eq 0 ]; then echo "PASS tests/voice_test.py  $(echo "$out" | tail -1)"; else echo "FAIL tests/voice_test.py (exit $rc)"; fail=1; fi
fi
if [ $fail -ne 0 ]; then echo "NOT TAGGED: a suite failed"; exit 1; fi
h=$(git rev-parse HEAD)
if git tag --points-at "$h" | grep -q '^working-'; then echo "ALREADY TAGGED: $(git tag --points-at "$h" | grep '^working-' | head -1)"; exit 0; fi
base="working-$(date +%Y%m%d)"; tag=$base; n=2
while git rev-parse -q --verify "refs/tags/$tag" >/dev/null; do tag="$base-$n"; n=$((n+1)); done
if [ $DRY -eq 1 ]; then echo "DRY RUN: would tag $tag at $(git rev-parse --short HEAD)"; exit 0; fi
git tag -a "$tag" -m "All test suites passed at $(date -Iseconds)" && echo "TAGGED $tag at $(git rev-parse --short HEAD)"
