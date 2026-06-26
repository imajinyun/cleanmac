#!/usr/bin/env bash
# Convenience wrapper for real cleanmac cleanup.
# Flow: dry-run preview -> confirmation -> Trash-mode execution.
#
# Usage:
#   ./scripts/quick_clean.sh [profile|categories]
#   ./scripts/quick_clean.sh developer
#   ./scripts/quick_clean.sh trash,xcode,goBuildCaches
#
# Profiles: safe, developer, browser
# Categories: comma-separated keys (see 'cleanmac list')

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN="${PYTHON:-python3}"
TARGET="${1:-safe}"

# Resolve profile vs. categories
if [[ "$TARGET" == "safe" || "$TARGET" == "developer" || "$TARGET" == "browser" ]]; then
  PROFILE_ARG=(--profile "$TARGET")
  CATEGORIES_ARG=()
  LABEL="profile '$TARGET'"
else
  PROFILE_ARG=()
  CATEGORIES_ARG=(--categories "$TARGET")
  LABEL="categories '$TARGET'"
fi

echo "========================================"
echo " cleanmac Quick Clean"
echo "========================================"
echo "Target : $LABEL"
echo "Delete : Trash (recoverable)"
echo ""

# Step 1: compute the budget from a JSON dry-run
BUDGET_MB="$("$PYTHON_BIN" -c "
import json, subprocess, math, sys
args = [sys.executable, 'cleanmac.py', '--json', 'clean']
args += $(printf "'%s' " "${PROFILE_ARG[@]+"${PROFILE_ARG[@]}"}")
args += $(printf "'%s' " "${CATEGORIES_ARG[@]+"${CATEGORIES_ARG[@]}"}")
args += ['--max-items', '10000', '--allow-live-root']
try:
    out = subprocess.check_output(args, text=True)
    d = json.loads(out)
    total = d.get('pre_clean_report', {}).get('candidate_total_bytes', 0)
    mb = max(4, int(math.ceil(total / 1024 / 1024 * 1.2)))
    print(mb)
except Exception as e:
    print('4096', file=sys.stderr)
    print('4096')
    sys.exit(0)
" 2>/dev/null)"

# Step 2: show human-readable dry-run
echo "--- Dry-run preview ---"
"$PYTHON_BIN" cleanmac.py clean \
  ${PROFILE_ARG[@]+"${PROFILE_ARG[@]}"} \
  ${CATEGORIES_ARG[@]+"${CATEGORIES_ARG[@]}"} \
  --max-items 50 \
  --allow-live-root \
  2>&1 | head -50
echo ""

echo "Safety budget: ${BUDGET_MB} MB (20% margin over estimate)"
echo ""

# Step 3: ask for confirmation
read -r -p "Proceed with Trash-mode cleanup? [y/N] " answer
case "$answer" in
  [yY]|[yY][eE][sS])
    echo ""
    echo "--- Executing (Trash mode) ---"
    set +e
    "$PYTHON_BIN" cleanmac.py clean \
      ${PROFILE_ARG[@]+"${PROFILE_ARG[@]}"} \
      ${CATEGORIES_ARG[@]+"${CATEGORIES_ARG[@]}"} \
      --max-items 10000 \
      --execute --yes \
      --allow-live-root \
      --max-delete-mb "$BUDGET_MB" \
      --delete-mode trash
    EXIT_CODE=$?
    set -e

    if [[ $EXIT_CODE -eq 0 ]]; then
      echo ""
      echo "Done. Files moved to Trash (recoverable)."
    else
      echo ""
      echo "Cleanup exited with code $EXIT_CODE."
      echo "Common issues:"
      echo "  - Operation log write error: check ~/.cleanmac/ permissions"
      echo "  - Permission denied on paths: may need Full Disk Access"
      echo "  - Symlink Trash: Trash mode fails closed (safe)"
      exit $EXIT_CODE
    fi
    ;;
  *)
    echo ""
    echo "Cancelled. No files were modified."
    ;;
esac
