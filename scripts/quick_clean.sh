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
BUDGET_ARGS=(cleanmac.py --json clean)
if ((${#PROFILE_ARG[@]})); then
  BUDGET_ARGS+=("${PROFILE_ARG[@]}")
fi
if ((${#CATEGORIES_ARG[@]})); then
  BUDGET_ARGS+=("${CATEGORIES_ARG[@]}")
fi
BUDGET_ARGS+=(--max-items 10000 --allow-live-root)
BUDGET_OUTPUT="$("$PYTHON_BIN" -c '
import json
import math
import subprocess
import sys

fallback_mb = 4096
args = [sys.executable, *sys.argv[1:]]


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


try:
    completed = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip().splitlines()
        tail = detail[-1] if detail else "no output"
        raise RuntimeError(f"dry-run exited {completed.returncode}: {tail}")
    data = json.loads(completed.stdout)
    pre_report = data.get("pre_clean_report") if isinstance(data, dict) else None
    safety_gate = data.get("safety_gate") if isinstance(data, dict) else None
    ai_confirmation = data.get("ai_confirmation_summary") if isinstance(data, dict) else None
    total = pre_report.get("candidate_total_bytes") if isinstance(pre_report, dict) else None
    if not numeric(total):
        summary = pre_report.get("summary") if isinstance(pre_report, dict) else None
        total = summary.get("estimated_reclaimable_bytes") if isinstance(summary, dict) else None
    if not numeric(total):
        total = safety_gate.get("candidate_bytes") if isinstance(safety_gate, dict) else None
    if not numeric(total):
        total = data.get("total_bytes") if isinstance(data, dict) else None
    if not numeric(total):
        total = (
            ai_confirmation.get("estimated_reclaimable_bytes")
            if isinstance(ai_confirmation, dict)
            else None
        )
    if not numeric(total):
        raise KeyError("dry-run JSON did not include candidate bytes")
    estimated_mb = int(math.ceil(float(total) / 1024 / 1024))
    budget_mb = max(4, int(math.ceil(estimated_mb * 1.2)))
    print(budget_mb)
    print(estimated_mb)
except Exception as exc:
    print(
        f"Warning: dynamic budget calculation failed ({exc}); using fallback budget {fallback_mb} MB.",
        file=sys.stderr,
    )
    print(fallback_mb)
    print(0)
' "${BUDGET_ARGS[@]}")"
BUDGET_MB="$(printf "%s\n" "$BUDGET_OUTPUT" | sed -n '1p')"
ESTIMATE_MB="$(printf "%s\n" "$BUDGET_OUTPUT" | sed -n '2p')"
if [[ ! "$BUDGET_MB" =~ ^[0-9]+$ ]]; then
  echo "Warning: invalid dynamic budget '$BUDGET_MB'; using fallback budget 4096 MB." >&2
  BUDGET_MB=4096
fi
if [[ ! "$ESTIMATE_MB" =~ ^[0-9]+$ ]]; then
  ESTIMATE_MB=0
fi

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
if [[ "$ESTIMATE_MB" -gt 0 ]]; then
  echo "Estimated candidates: ${ESTIMATE_MB} MB"
fi
echo ""

# Step 3: ask for confirmation
read -r -p "Proceed with Trash-mode cleanup? [y/N] " answer
case "$answer" in
  [yY]|[yY][eE][sS])
    echo ""
    echo "--- Executing (Trash mode) ---"
    EXEC_OUTPUT="$(mktemp "${TMPDIR:-/tmp}/cleanmac-quick-clean.XXXXXX")"
    set +e
    "$PYTHON_BIN" cleanmac.py clean \
      ${PROFILE_ARG[@]+"${PROFILE_ARG[@]}"} \
      ${CATEGORIES_ARG[@]+"${CATEGORIES_ARG[@]}"} \
      --max-items 10000 \
      --execute --yes \
      --allow-live-root \
      --max-delete-mb "$BUDGET_MB" \
      --delete-mode trash >"$EXEC_OUTPUT" 2>&1
    EXIT_CODE=$?
    set -e
    cat "$EXEC_OUTPUT"

    if [[ $EXIT_CODE -eq 0 ]]; then
      echo ""
      echo "Done. Files moved to Trash (recoverable)."
    else
      echo ""
      echo "Cleanup exited with code $EXIT_CODE."
      if grep -q -- "--max-delete-mb budget" "$EXEC_OUTPUT"; then
        echo "Budget guidance:"
        if [[ "$ESTIMATE_MB" -gt 0 ]]; then
          echo "  - Estimated candidates : ${ESTIMATE_MB} MB"
        fi
        echo "  - Current budget       : ${BUDGET_MB} MB"
        echo "  - Re-run dry-run and raise --max-delete-mb only after reviewing the candidate list."
      fi
      echo "Common issues:"
      echo "  - Operation log write error: check ~/.cleanmac/ permissions"
      echo "  - Permission denied on paths: may need Full Disk Access"
      echo "  - Symlink Trash: Trash mode fails closed (safe)"
      rm -f "$EXEC_OUTPUT"
      exit $EXIT_CODE
    fi
    rm -f "$EXEC_OUTPUT"
    ;;
  *)
    echo ""
    echo "Cancelled. No files were modified."
    ;;
esac
