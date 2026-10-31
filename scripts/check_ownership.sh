#!/usr/bin/env bash
set -euo pipefail

role="${1:?usage: scripts/check_ownership.sh A|B [base-ref]}"
base="${2:-origin/main}"
[ "${BLOCK0:-0}" = "1" ] && exit 0

owner_of() {
  case "$1" in
    frontend/src/features/catalog/*|frontend/src/features/customers/*|frontend/src/features/reports/*|frontend/src/features/staff/*) echo A ;;
    frontend/*|backend/app/ai/*|backend/tests/ai/*|docs/ai.md) echo B ;;
    *) echo A ;;
  esac
}

bad=0
while IFS= read -r file; do
  [ -z "$file" ] && continue
  owner="$(owner_of "$file")"
  if [ "$owner" != "$role" ]; then
    echo "NOT YOURS ($owner owns): $file"
    bad=1
  fi
done < <(git diff --name-only --no-renames "$base"...HEAD)

[ "$bad" = "0" ] && echo "ownership OK for $role"
exit "$bad"

