#!/usr/bin/env bash
# Safe test runner for cleanmac.
# Ensures tests cannot trigger real sudo, AppleScript, launchctl, or unsafe recursive removal.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

export CLEANMAC_TEST_NO_AUTH=1
export CLEANMAC_TEST_MODE=1

TEST_SYSTEM_STUB_DIR="$(mktemp -d "${TMPDIR:-/tmp}/cleanmac-test-stubs.XXXXXX")"
TEST_STUB_LOG="${CLEANMAC_TEST_STUB_LOG:-$TEST_SYSTEM_STUB_DIR/stub-invocations.log}"

cleanup_test_stubs() {
    if [[ -d "$TEST_SYSTEM_STUB_DIR" ]]; then
        /bin/rm -R "$TEST_SYSTEM_STUB_DIR"
    fi
}
trap cleanup_test_stubs EXIT

cat > "$TEST_SYSTEM_STUB_DIR/sudo" <<'EOF'
#!/usr/bin/env bash
printf 'cleanmac test blocked sudo: %s\n' "$*" >&2
printf 'sudo %s\n' "$*" >> "${TEST_STUB_LOG:?}"
exit 1
EOF

cat > "$TEST_SYSTEM_STUB_DIR/osascript" <<'EOF'
#!/usr/bin/env bash
printf 'cleanmac test blocked osascript: %s\n' "$*" >&2
printf 'osascript %s\n' "$*" >> "${TEST_STUB_LOG:?}"
exit 1
EOF

cat > "$TEST_SYSTEM_STUB_DIR/launchctl" <<'EOF'
#!/usr/bin/env bash
printf 'cleanmac test blocked launchctl: %s\n' "$*" >&2
printf 'launchctl %s\n' "$*" >> "${TEST_STUB_LOG:?}"
exit 1
EOF

cat > "$TEST_SYSTEM_STUB_DIR/rm" <<'EOF'
#!/usr/bin/env bash
for arg in "$@"; do
    case "$arg" in
        -*r*f*|-*f*r*)
            printf 'cleanmac test blocked rm -rf style command: %s\n' "$*" >&2
            printf 'rm %s\n' "$*" >> "${TEST_STUB_LOG:?}"
            exit 1
            ;;
    esac
done
exec /bin/rm "$@"
EOF

chmod +x \
    "$TEST_SYSTEM_STUB_DIR/sudo" \
    "$TEST_SYSTEM_STUB_DIR/osascript" \
    "$TEST_SYSTEM_STUB_DIR/launchctl" \
    "$TEST_SYSTEM_STUB_DIR/rm"

export TEST_STUB_LOG
export PATH="$TEST_SYSTEM_STUB_DIR:$PATH"

PYTHON_BIN="${PYTHON:-python3}"
MAKE_BIN="${MAKE:-make}"

echo "==============================="
echo "cleanmac Safe Test Runner"
echo "==============================="
echo "CLEANMAC_TEST_NO_AUTH=$CLEANMAC_TEST_NO_AUTH"
echo "CLEANMAC_TEST_MODE=$CLEANMAC_TEST_MODE"
echo "stub_bin=$TEST_SYSTEM_STUB_DIR"
echo ""

"$PYTHON_BIN" -m unittest -v
"$MAKE_BIN" governance-smoke
"$MAKE_BIN" script-smoke

echo ""
echo "cleanmac safe test runner passed"
